"""
Caption & Description Idea Generator powered by Google Gemini.
Generates:
- High CTR viral Short titles
- Attention-grabbing 3-second hook captions (Hormozi / MrBeast style)
- SEO-optimized YouTube Shorts descriptions
- Viral trending hashtags
- Engagement-maximizing pinned comments
"""
import os
import json
import logging
from typing import Dict, Any, List, Optional
import yaml
from google import genai
from google.genai import types
from core.builtin_keys import get_gemini_key

logger = logging.getLogger("caption_generator")

class CaptionGenerator:
    def __init__(self, config_path: str = "config/config.yaml"):
        self.config = self._load_config(config_path)
        gemini_key = get_gemini_key(self.config)
        self.client = None
        self.models = ["gemini-3.8-flash", "gemini-3.5-flash-lite", "gemini-3.5-flash", "gemini-3.7-flash"]
        if gemini_key:
            try:
                self.client = genai.Client(
                    api_key=gemini_key,
                    http_options=types.HttpOptions(timeout=20_000)
                )
            except Exception as e:
                logger.warning(f"CaptionGenerator client init error: {e}")

    def _load_config(self, path: str) -> dict:
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return yaml.safe_load(f) or {}
            except Exception:
                pass
        return {}

    def generate_ideas(self, channel: str = "@IShowSpeed", topic_or_title: str = "Viral Moments") -> Dict[str, Any]:
        """Generate titles, hook captions, description, and hashtags using Gemini."""
        prompt = f"""You are the world's best viral YouTube Shorts copywriter and algorithm specialist.
Target Channel: {channel}
Topic/Context: {topic_or_title}

Generate viral copy optimized for YouTube Shorts algorithm:
1. 3 High-CTR Titles (under 60 characters, highly clickable with emojis, e.g. "HE ACTUALLY DID THIS?! 😱 #Shorts")
2. Viral Hook Caption (first 3-5 seconds text overlay that stops scrolling immediately)
3. Full YouTube Short Description (engaging, includes channel attribution, fair-use notice, and call to action)
4. 6 Viral Hashtags (e.g. #Shorts, #Viral, #Trending)
5. Pinned Comment Question (irresistible question under 12 words that forces viewers to comment)

Output strictly in JSON format with keys:
{{
  "titles": ["title 1", "title 2", "title 3"],
  "hook_caption": "3-second screen hook caption",
  "description": "Full YouTube Shorts description text",
  "hashtags": ["#tag1", "#tag2", "#tag3", "#tag4", "#tag5", "#tag6"],
  "pinned_comment": "Question to pin in comments"
}}
"""
        if self.client:
            for model in self.models:
                try:
                    resp = self.client.models.generate_content(
                        model=model,
                        contents=prompt,
                        config=types.GenerateContentConfig(response_mime_type="application/json")
                    )
                    if resp and resp.text:
                        return json.loads(resp.text)
                except Exception as e:
                    logger.warning(f"CaptionGenerator model {model} failed: {e}")

        # Fallback offline template if API is offline
        clean_ch = channel.replace("@", "")
        return {
            "titles": [
                f"{clean_ch.upper()} LOST HIS MIND! 🤯 #Shorts",
                f"Nobody Expected {clean_ch} To Do This... 😱",
                f"The Craziest Moment From {clean_ch} Ever 😂"
            ],
            "hook_caption": f"Wait for what {clean_ch} does next... 💀",
            "description": f"Watch until the end to see this insane moment from @{clean_ch}!\n\nSubscribe for daily clips and viral edits.\nCredit: @{clean_ch}\nDisclaimer: Transformative commentary and entertainment.",
            "hashtags": ["#Shorts", "#Viral", "#Trending", f"#{clean_ch.replace(' ', '')}", "#Clips", "#FYP"],
            "pinned_comment": f"What would you do in this situation? Be honest 👇"
        }
