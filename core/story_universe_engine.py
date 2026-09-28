"""
Story Universe Engine for Episodic YouTube Shorts Movie Series.
Maintains persistent world-building, episode continuity, lore, and cliffhangers.
Guarantees 100% YouTube monetization compliance through original narrative IP.
"""
import os
import json
import logging
from typing import Dict, Any, List, Optional
import yaml
from google import genai
from google.genai import types

logger = logging.getLogger(__name__)

DEFAULT_UNIVERSE = {
    "name": "THE STERLING INQUIRY",
    "genre": "Victorian Detective Thriller (Cinematic Movie Scenes)",
    "logline": "London, 1894. Consulting detective Silas Sterling uncovers an empire of crime through lightning deductions, high-stakes ambushes, and live confrontations with the shadowy Obsidian Syndicate.",
    "setting": "Victorian London — Gaslit cobblestone streets, locked manor studies, subterranean vaults, rain-streaked windows, ticking antique clocks.",
    "protagonist": "Silas Sterling — An intensely observant, razor-sharp private consulting detective who talks directly in the scene as the movie plays out.",
    "antagonist_or_threat": "The Obsidian Syndicate — A secret empire orchestrating high-stakes political heists and impossible murders.",
    "current_episode": 0,
    "episodes": []
}

class StoryUniverseEngine:
    def __init__(self, config_path: str = 'config/config.yaml', universe_file: str = 'data/story_universe.json'):
        self.config_path = config_path
        self.universe_file = universe_file
        self.config = self._load_config()
        self._init_gemini()
        self.universe = self._load_universe()

    def _load_config(self) -> dict:
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    return yaml.safe_load(f) or {}
        except Exception as e:
            logger.warning(f"Failed to load config: {e}")
        return {}

    def _init_gemini(self):
        try:
            from core.builtin_keys import get_gemini_key
            api_key = get_gemini_key(self.config)
            if not api_key:
                logger.warning("Gemini API key unavailable.")
                self.client = None
                return
            self.client = genai.Client(api_key=api_key)
            self.model_name = 'gemini-3.1-flash-lite'
            self.fallback_models = ['gemini-3.8-flash', 'gemini-flash-latest', 'gemini-flash-lite-latest']
        except Exception as e:
            logger.error(f"Failed to init Gemini in StoryUniverseEngine: {e}")
            self.client = None

    def _load_universe(self) -> dict:
        os.makedirs(os.path.dirname(os.path.abspath(self.universe_file)), exist_ok=True)
        if os.path.exists(self.universe_file):
            try:
                with open(self.universe_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if data.get('name') == DEFAULT_UNIVERSE['name']:
                        return data
            except Exception as e:
                logger.warning(f"Could not load universe file: {e}. Using default.")
        
        # Save default initial universe
        self._save_universe(DEFAULT_UNIVERSE)
        return DEFAULT_UNIVERSE

    def _save_universe(self, data: dict):
        try:
            with open(self.universe_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save universe file: {e}")

    def reset_universe(self):
        """Resets the universe back to Episode 0."""
        self.universe = dict(DEFAULT_UNIVERSE)
        self.universe["episodes"] = []
        self.universe["current_episode"] = 0
        self._save_universe(self.universe)
        logger.info("Reset story universe back to Scene 1.")

    def switch_universe(self, universe_data: dict):
        """Allows switching or re-initializing the universe lore."""
        self.universe = universe_data
        self._save_universe(self.universe)
        logger.info(f"Switched story universe to: {self.universe.get('name')}")

    def generate_next_episode(self) -> Dict[str, Any]:
        """
        Generates the next episodic live movie scene with strict narrative continuity.
        """
        current_ep = self.universe.get('current_episode', 0)
        next_ep = current_ep + 1
        
        # Gather previous episode context for continuity
        recent_episodes = self.universe.get('episodes', [])[-3:]
        past_context = ""
        if recent_episodes:
            past_context = "PREVIOUS SCENES CONTINUITY (Pick up IMMEDIATELY from the last cliffhanger):\n"
            for ep in recent_episodes:
                past_context += f"- Scene {ep.get('part')}: {ep.get('title')} | Ending/Cliffhanger: {ep.get('cliffhanger')}\n"
        else:
            past_context = "This is SCENE 1 (THE CRIME SCENE AMBUSH). Start in medias res. Silas Sterling is inside Lord Harrington's locked study at midnight, shouting at the police to halt before they destroy the crime scene, revealing it was never suicide, and discovering the killer is trapped in the room."

        prompt = f"""You are the head cinematic screenwriter and director for a viral, serialized YouTube Shorts detective movie series: '{self.universe.get("name")}'.
Universe Lore:
- Genre: {self.universe.get("genre")}
- Logline: {self.universe.get("logline")}
- Setting: {self.universe.get("setting")}
- Main Character: {self.universe.get("protagonist")}
- Antagonist: {self.universe.get("antagonist_or_threat")}

{past_context}

Write SCENE {next_ep} (Part {next_ep}) of this ongoing cinematic movie.

CRITICAL DIRECTIVE - LIVE MOVIE SCENE (NOT A STORYTELLER / NOT AN AUDIOBOOK):
The user explicitly demands: "make live scene like you create a movie not a story teller, make a movie get a main character as a detective and start making scenes".
1. IN-SCENE LIVE ACTING: Silas Sterling is NOT narrating a story from the past. He is IN THE ACTIVE SCENE speaking right now in the present tense to characters around him (e.g. Inspector Lestrade, a Constable, an assassin in the dark).
2. DO NOT use storyteller intros like "Once upon a time", "In London 1894", "Silas walked into the room", or "Scotland Yard called it suicide. In three seconds, I found...".
3. IMMEDIATE ACTION & DIALOGUE: Drop the viewer directly into dramatic movie dialogue and immediate tension.
   - Example tone: "Halt! Constable, don't move your boot! You're an inch away from the only clue left in this study. Look at the victim's collar. Stained with bitter almond oil, but the glass on the table is untouched..."
4. RAPID DEDUCTIVE BRILLIANCE (Sherlock style): In 15 seconds, Silas points out 2 impossible physical details that flip the entire situation on its head.
5. CONTINUITY: If this is Scene 2 or later, pick up directly from where the previous scene cut to black. The tension must never reset.
6. HIGH-STAKES CLIFFHANGER & CTA: End on an intense cinematic cliffhanger (a cocked pistol, a shadow lunging, an impossible cipher revealed). The very last sentence MUST be exactly:
   "Part {next_ep + 1} drops tomorrow. Subscribe to solve the case."
7. WORD COUNT: Exactly 65 to 78 spoken words total (around 28-32 seconds). Clean spoken script ONLY. Do NOT write stage directions or parentheticals like '[whispering]' or '[gunshot sound]' because the text will be spoken directly by the voice engine.
8. CINEMATIC B-ROLL QUERIES: 3 atmospheric, high-contrast stock video search queries (e.g. 'detective examining magnifying glass antique', 'victorian foggy london street night lantern', 'shadowy figure vintage corridor dark coat').
9. PINNED DEDUCTION QUESTION: An irresistible mystery question (under 12 words) that forces viewers to comment their theory.
10. YOUTUBE TITLE: Click-worthy title under 60 characters formatted as:
   SCENE {next_ep}: [Punchy 3-5 Word Movie Beat] 🕵️‍♂️🎬 #Shorts #Sherlock

Output strictly in JSON format with keys:
{{
  "part": {next_ep},
  "series_title": "{self.universe.get("name")}",
  "episode_title": string,
  "youtube_title": string,
  "top_banner_text": "SCENE 0{next_ep} // LIVE DETECTIVE MOVIE",
  "narration": string,
  "visual_queries": [string, string, string],
  "cliffhanger_summary": string,
  "pinned_comment": string,
  "mood": "dramatic"
}}"""

        episode_data = self._generate_json(prompt)
        if not episode_data:
            logger.error("Failed to generate episode from Gemini.")
            return {}

        # Save to episode history
        self.universe['current_episode'] = next_ep
        self.universe['episodes'].append({
            "part": next_ep,
            "title": episode_data.get('episode_title', f'Part {next_ep}'),
            "youtube_title": episode_data.get('youtube_title'),
            "cliffhanger": episode_data.get('cliffhanger_summary'),
            "timestamp": episode_data.get('narration')
        })
        self._save_universe(self.universe)
        logger.info(f"Generated Episode {next_ep}: {episode_data.get('episode_title')}")
        return episode_data

    def _generate_json(self, prompt: str) -> Dict[str, Any]:
        if not self.client:
            return {}
        import time
        models = [self.model_name] + self.fallback_models
        for m in models:
            for attempt in range(3):
                try:
                    response = self.client.models.generate_content(
                        model=m,
                        contents=prompt,
                        config=types.GenerateContentConfig(response_mime_type="application/json")
                    )
                    if response.text:
                        return json.loads(response.text)
                except Exception as e:
                    logger.warning(f"Model {m} attempt {attempt+1} failed in StoryUniverseEngine: {e}")
                    time.sleep(2)
        return {}

if __name__ == '__main__':
    engine = StoryUniverseEngine()
    ep = engine.generate_next_episode()
    print("Generated Next Episode:")
    print(json.dumps(ep, indent=2))
