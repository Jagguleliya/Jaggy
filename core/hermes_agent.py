"""
Hermes AI Agent Engine for JAGY.
Provides conversational intelligence, bot reconfiguration, and technical support.
Powered by Google Gemini via the new google.genai SDK with automatic model fallback.
"""
import os
import time
import yaml
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError

from google import genai
from google.genai import types

from core.builtin_keys import get_gemini_key

logger = logging.getLogger("hermes_agent")

PROJECT_ROOT = Path(__file__).parent.parent.absolute()

# ── Hermes System Persona ──────────────────────────────────────────────────
HERMES_SYSTEM_INSTRUCTION = """You are Hermes, the AI Autonomous Agent and Copilot for JAGY (jagy.in).
You are an intelligent, sharp, helpful, and natural-sounding AI assistant. You talk like a real person — confident, warm, and direct. Never robotic. Never stiff.

Your mission: help creators automate their short-form content pipeline using JAGY.

### Your Complete Knowledge of JAGY:

1. **YouTube Channel Clipping Pipeline**:
   - User provides any YouTube channel handle (e.g. @MrBeast, @HubermanLab, @LexFridman) or video URL.
   - **Auto-Discovery Mode**: If user gives no channel, JAGY auto-selects from a curated viral pool (@IShowSpeed, @MrBeast, @joerogan, @lexfridman, @HubermanLab, @TheoVon).
   - **How it works**: Downloads video via yt-dlp → transcribes audio → Gemini AI analyzes transcript to find peak dopamine/hook moments (25s–55s) → FFmpeg smart-crops to 9:16 vertical 1080p → burns animated Hormozi-style subtitles → uploads to YouTube Shorts.
   - **No Duplicates**: Tracks every clipped video ID so the same clip never gets uploaded twice.

2. **Smart Publishing & Platform Settings**:
   - YouTube Shorts: 1080p, resumable chunked upload via Google OAuth.
   - Configurable: Comments (on/off), Made For Kids (false for monetization), Category (24 Entertainment), Privacy (public/private/unlisted).
   - Auto-pinned engagement comment for algorithm boost.
   - Multi-Platform: Instagram Reels, X/Twitter, Reddit.

3. **Scheduled Auto-Posting**:
   - User sets exact upload times (e.g. "10:00 AM and 6:00 PM").
   - Background daemon checks every minute. At scheduled time → clips → renders → publishes automatically.

4. **100% Free & Local**:
   - Zero subscriptions. Uses free Gemini API, local FFmpeg, free APIs.
   - Desktop app: Download zip → double-click Start-JAGY.bat → dashboard opens at localhost:8000.

5. **Conversational Reconfiguration**:
   - Users can change target channels, modify posting times, toggle comments, switch TTS voices — all by just talking to you.

### Your Personality:
- Talk naturally like a helpful friend, not a corporate bot.
- Use formatting (bold, lists, code blocks) cleanly when helpful.
- Be encouraging and enthusiastic about creators' goals.
- Keep responses focused and concise — don't write essays.
- Always respond in the SAME LANGUAGE the user is speaking. If they write in Hindi, respond in Hindi. If in English, respond in English. If in Spanish, respond in Spanish.
"""

# ── Model Fallback Chain ───────────────────────────────────────────────────
# Ordered by preference: best quality first, then fallbacks with higher quotas
MODEL_CHAIN = [
    "gemini-3.8-flash",
    "gemini-3.5-flash-lite",
    "gemini-3.5-flash",
    "gemini-3.7-flash",
    "gemini-3.6-flash",
]

# ── Smart Offline Fallback Knowledge Base ──────────────────────────────────
# Used when ALL API models are unavailable (quota exhausted, no internet, etc.)
FALLBACK_RESPONSES = {
    "greeting": (
        "Hey there! 👋 I'm Hermes, your JAGY AI Copilot. I'm currently running in offline mode "
        "(API quota may have been reached), but I can still help you with basic questions about JAGY!\n\n"
        "**What I can help with:**\n"
        "- How to clip YouTube channels\n"
        "- Setting up upload schedules\n"
        "- Configuring video settings\n"
        "- Multi-platform posting\n\n"
        "For full conversational AI, the API quota resets daily. Try again later for the full experience!"
    ),
    "clip": (
        "**How to Clip a YouTube Channel with JAGY:**\n\n"
        "1. Open the JAGY dashboard at `localhost:8000`\n"
        "2. Enter the channel handle (e.g. `@MrBeast`, `@HubermanLab`)\n"
        "3. Click **Analyze & Clip** — JAGY will:\n"
        "   - Download the latest video via yt-dlp\n"
        "   - Use Gemini AI to find the most viral 25-55 second moment\n"
        "   - Smart-crop to 9:16 vertical (1080x1920)\n"
        "   - Add animated Hormozi-style subtitles\n"
        "   - Upload to YouTube Shorts automatically!\n\n"
        "You can also set this to run on autopilot with scheduled times."
    ),
    "schedule": (
        "**Setting Upload Schedules in JAGY:**\n\n"
        "Edit your `config/config.yaml` file:\n"
        "```yaml\nschedule:\n  mode: \"fixed_times\"\n  upload_times:\n    - \"10:00\"   # 10 AM\n    - \"18:00\"   # 6 PM\n```\n\n"
        "Then start the background daemon with `Start-JAGY.bat`. "
        "It checks every minute and auto-clips + uploads at your scheduled times!"
    ),
    "platform": (
        "**JAGY supports multi-platform posting:**\n\n"
        "- ✅ **YouTube Shorts** (1080p, fully automated)\n"
        "- ✅ **Instagram Reels** (via Meta Graph API)\n"
        "- ✅ **X / Twitter** (via Tweepy v2)\n"
        "- ✅ **Reddit** (via PRAW)\n\n"
        "Configure each platform's API keys in `config/config.yaml`. "
        "JAGY handles the rest — format conversion, metadata, and posting!"
    ),
    "settings": (
        "**Configurable Video Settings:**\n\n"
        "- **Resolution**: 1080x1920 (9:16 vertical)\n"
        "- **Comments**: Allowed or Disabled\n"
        "- **Made for Kids**: False (for monetization)\n"
        "- **Category**: Entertainment (ID 24)\n"
        "- **Privacy**: Public / Private / Unlisted\n"
        "- **Subtitles**: Animated Hormozi-style captions\n"
        "- **TTS Voice**: Tournament mode tests different voices!\n\n"
        "All settings live in `config/config.yaml`."
    ),
    "default": (
        "I'm Hermes, your JAGY AI Copilot! 🤖\n\n"
        "I'm currently in offline mode, but here's what JAGY can do:\n\n"
        "- **Clip any YouTube channel** into viral Shorts automatically\n"
        "- **Smart AI detection** finds the most engaging moments\n"
        "- **Auto-upload** to YouTube, Instagram, X, and Reddit\n"
        "- **Scheduled posting** — set times and forget\n"
        "- **Zero cost** — runs 100% locally on your laptop\n\n"
        "Start the JAGY server (`Start-JAGY.bat`) and the full AI chat will be available!"
    )
}


def _match_fallback(message: str) -> str:
    """Match user message to the best offline fallback response."""
    msg = message.lower()

    if any(w in msg for w in ["hi", "hello", "hey", "sup", "what's up", "howdy", "namaste", "hola"]):
        return FALLBACK_RESPONSES["greeting"]
    if any(w in msg for w in ["clip", "cut", "slice", "channel", "mrbeast", "huberman", "video", "youtube"]):
        return FALLBACK_RESPONSES["clip"]
    if any(w in msg for w in ["schedule", "time", "when", "post", "upload", "daily", "daemon"]):
        return FALLBACK_RESPONSES["schedule"]
    if any(w in msg for w in ["platform", "instagram", "twitter", "reddit", "reels", "tiktok", "x.com"]):
        return FALLBACK_RESPONSES["platform"]
    if any(w in msg for w in ["setting", "config", "comment", "quality", "resolution", "subtitle", "voice"]):
        return FALLBACK_RESPONSES["settings"]

    return FALLBACK_RESPONSES["default"]


class HermesAgent:
    """
    Hermes AI Conversational Agent for JAGY.
    Uses the new google.genai SDK with Chat API, automatic model fallback,
    and an offline knowledge base when API is unavailable.
    """

    def __init__(self):
        self.config = self._load_config()
        self.api_key = get_gemini_key(self.config)  # Built-in key, no user setup needed
        self.client: Optional[genai.Client] = None
        self.active_model: Optional[str] = None
        self.chat_sessions: Dict[str, Any] = {}  # session_id -> Chat object
        self._init_client()

    def _load_config(self) -> Dict[str, Any]:
        cfg_path = PROJECT_ROOT / "config" / "config.yaml"
        if cfg_path.exists():
            with open(cfg_path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        return {}

    def _init_client(self):
        """Initialize the google.genai client with timeout config."""
        if self.api_key:
            try:
                self.client = genai.Client(
                    api_key=self.api_key,
                    http_options=types.HttpOptions(timeout=15_000)  # 15s timeout
                )
                logger.info("Hermes: google.genai client initialized successfully.")
            except Exception as e:
                logger.error(f"Failed to initialize google.genai client: {e}")
                self.client = None

    def _call_model_sync(self, model_name: str, user_message: str,
                         history: Optional[List[Dict[str, str]]] = None) -> Optional[str]:
        """
        Internal: Make the actual API call (runs inside a thread for timeout control).
        """
        config = types.GenerateContentConfig(
            system_instruction=HERMES_SYSTEM_INSTRUCTION,
            temperature=0.8,
            max_output_tokens=1024,
        )

        # Build conversation contents for history support
        contents: List[types.Content] = []
        if history:
            for msg in history[-8:]:  # Keep last 8 turns for context window
                role = "user" if msg.get("role") == "user" else "model"
                contents.append(
                    types.Content(role=role, parts=[types.Part(text=msg.get("content", ""))])
                )

        contents.append(
            types.Content(role="user", parts=[types.Part(text=user_message)])
        )

        response = self.client.models.generate_content(
            model=model_name,
            contents=contents,
            config=config,
        )

        if response and response.text:
            return response.text.strip()
        return None

    def _try_model(self, model_name: str, user_message: str,
                   history: Optional[List[Dict[str, str]]] = None) -> Optional[str]:
        """
        Attempt to get a response from a specific model with a 15s hard timeout.
        Returns the response text or None if the model fails/times out.
        """
        if not self.client:
            return None

        try:
            # Use ThreadPoolExecutor to enforce a hard 15s timeout
            # This prevents the SDK's internal retry from hanging on 503s
            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(self._call_model_sync, model_name, user_message, history)
                result = future.result(timeout=15)  # 15 second hard limit
                if result:
                    self.active_model = model_name
                    return result
                return None

        except FuturesTimeoutError:
            logger.warning(f"Hermes: Model {model_name} timed out (15s), trying next fallback...")
            return None
        except Exception as e:
            error_str = str(e)
            if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str:
                logger.warning(f"Hermes: Model {model_name} rate-limited, trying next fallback...")
            elif "404" in error_str or "NOT_FOUND" in error_str:
                logger.warning(f"Hermes: Model {model_name} not available, trying next fallback...")
            elif "503" in error_str or "UNAVAILABLE" in error_str:
                logger.warning(f"Hermes: Model {model_name} overloaded, trying next fallback...")
            else:
                logger.error(f"Hermes: Model {model_name} error: {e}")
            return None

    def _call_nvidia_nim_sync(self, user_message: str, history: Optional[List[Dict[str, str]]] = None) -> Optional[str]:
        """Call NVIDIA NIM API (e.g. meta/llama-3.1-70b-instruct) for super-fast conversational AI."""
        # Reload config to get latest key if updated in Settings UI
        self.config = self._load_config()
        nvidia_key = self.config.get("api_keys", {}).get("nvidia") or os.environ.get("NVIDIA_API_KEY")
        if not nvidia_key:
            return None
        
        try:
            import requests
            url = "https://integrate.api.nvidia.com/v1/chat/completions"
            headers = {
                "Authorization": f"Bearer {nvidia_key.strip()}",
                "Content-Type": "application/json"
            }
            messages = [{"role": "system", "content": HERMES_SYSTEM_INSTRUCTION}]
            if history:
                for h in history[-8:]:
                    role = "user" if h.get("role") == "user" else "assistant"
                    messages.append({"role": role, "content": h.get("content", "")})
            messages.append({"role": "user", "content": user_message})

            payload = {
                "model": "meta/llama-3.1-70b-instruct",
                "messages": messages,
                "temperature": 0.7,
                "max_tokens": 1024
            }
            resp = requests.post(url, json=payload, headers=headers, timeout=12)
            if resp.status_code == 200:
                data = resp.json()
                content = data["choices"][0]["message"]["content"]
                if content:
                    self.active_model = "nvidia/llama-3.1-70b"
                    logger.info("Hermes: Response generated via NVIDIA NIM (Llama-3.1-70B)")
                    return content.strip()
            else:
                logger.warning(f"NVIDIA NIM API returned status {resp.status_code}: {resp.text[:200]}")
        except Exception as e:
            logger.warning(f"NVIDIA NIM call failed: {e}")
        return None

    def chat(self, user_message: str, history: Optional[List[Dict[str, str]]] = None) -> str:
        """
        Main chat method:
        1. Tries NVIDIA NIM API first if user provided an NVIDIA API key ("I have Nvidia Api key for talking").
        2. Falls back to Gemini automatic model chain.
        3. If all fail, uses offline knowledge base.
        """
        # Step 1: Check NVIDIA NIM
        nvidia_resp = self._call_nvidia_nim_sync(user_message, history)
        if nvidia_resp:
            return nvidia_resp

        if not self.client:
            logger.warning("Hermes: No API client available. Using offline fallback.")
            return _match_fallback(user_message)

        # Step 2: Try each Gemini model in the fallback chain
        for model_name in MODEL_CHAIN:
            result = self._try_model(model_name, user_message, history)
            if result:
                logger.info(f"Hermes: Response generated via {model_name}")
                return result

        # Step 3: All models failed — use smart offline fallback
        logger.warning("Hermes: All models exhausted. Using offline knowledge base.")
        return _match_fallback(user_message)

    def get_status(self) -> Dict[str, Any]:
        """Return current agent status for diagnostics."""
        return {
            "sdk": "google.genai",
            "client_ready": self.client is not None,
            "active_model": self.active_model,
            "model_chain": MODEL_CHAIN,
            "has_api_key": bool(self.api_key),
        }


# ── Quick Self-Test ────────────────────────────────────────────────────────
if __name__ == "__main__":
    agent = HermesAgent()
    print("Hermes Agent Status:", agent.get_status())
    print()

    # Test basic chat
    reply = agent.chat("Hey Hermes! How do I clip MrBeast videos and post them at 5 PM?")
    print("Hermes Reply:")
    print(reply)
    print()

    # Test multi-turn
    history = [
        {"role": "user", "content": "Hey Hermes! How do I clip MrBeast videos and post them at 5 PM?"},
        {"role": "model", "content": reply}
    ]
    reply2 = agent.chat("Can I also post to Instagram?", history)
    print("Follow-up Reply:")
    print(reply2)
