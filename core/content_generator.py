import os
import json
import logging
import random
from typing import Dict, Any, List
import yaml
from google import genai
from google.genai import types

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ContentGenerator:
    def __init__(self, config_path: str = 'config/config.yaml'):
        self.config_path = config_path
        self._load_config()
        self._init_gemini()
        self.used_topics_file = self.config.get('paths', {}).get('used_topics', 'data/used_topics.json')

    def _load_config(self):
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    self.config = yaml.safe_load(f) or {}
            else:
                self.config = {}
        except Exception as e:
            logger.error(f"Failed to load config: {e}")
            self.config = {}

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
            logger.info(f"Gemini client initialized with model: {self.model_name}")
        except Exception as e:
            logger.error(f"Failed to initialize Gemini: {e}")
            self.client = None

    def _get_random_topic(self) -> str:
        topics = [
            "Ridiculous animal facts", 
            "Weird human body glitches", 
            "Bizarre laws that actually exist", 
            "Crazy historical facts that sound fake", 
            "Unbelievable food facts", 
            "Mind-blowing psychology facts",
            "Hilarious facts about everyday objects",
            "Crazy facts about space"
        ]
        return random.choice(topics)

    def _build_prompt(self, template: str, **kwargs) -> str:
        prompt = template.format(**kwargs)
        if kwargs.get('performance_feedback'):
            prompt += f"\n\nTake into account this feedback from past performance:\n{kwargs.get('performance_feedback')}"
        return prompt

    def _generate_json(self, prompt: str) -> Dict[str, Any]:
        if not self.client:
            logger.error("Gemini client not initialized.")
            return {}
            
        models_to_try = [self.model_name] + self.fallback_models
        for model in models_to_try:
            try:
                response = self.client.models.generate_content(
                    model=model,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json"
                    )
                )
                if response.text:
                    return json.loads(response.text)
            except Exception as e:
                logger.warning(f"Model {model} failed: {e}. Trying next fallback...")
                continue
                
        logger.error("All Gemini models failed.")
        return {}

    def generate_fun_fact_script(self, topic: str = None, performance_feedback: str = '') -> Dict[str, Any]:
        topic = topic or self._get_random_topic()
        template = """You are a top-tier viral YouTube Shorts creator known for hilarious, absurd, and mind-blowing 'Did You Know' facts.
Topic: {topic}

Rules:
1. HOOK: Must start immediately with a funny, shocking, or crazy statement in the very first 3 seconds (e.g., "Did you know that...", "Stop scrolling, your life has been a lie...").
2. PACING: Ultra fast, funny, engaging, and witty. Zero boring academic filler. Use casual conversational internet humor.
3. DURATION: Exactly 50 to 75 words total (targets 20 to 28 seconds of speech). Keep it fast-paced so nobody skips!
4. PEXELS SEARCH TERM: A simple, highly visual 2-3 word search query for funny/surprising stock footage (e.g. 'funny cat', 'crazy face', 'laughing monkey', 'explosion', 'confused person').
5. Output strictly in JSON format with keys:
   - title: Short, punchy, clicky title with #Shorts #DidYouKnow #Viral (e.g. 'This Fact Will Ruin Your Day 😂 #Shorts')
   - hook: The first 5 words
   - narration: The full 50-75 word narration without stage directions
   - pexels_search_term: The search query
   - tags: List of 5 viral tags like ['shorts', 'funfacts', 'didyouknow', 'funny', 'humor']
   - category_id: 23 (Comedy/Entertainment)
   - mood: 'upbeat'"""
        prompt = self._build_prompt(template, topic=topic, performance_feedback=performance_feedback)
        return self._generate_json(prompt)

    def generate_reddit_story_script(self, topic: str = None, performance_feedback: str = '') -> Dict[str, Any]:
        topic = topic or self._get_random_topic()
        template = """You are a YouTube Shorts creator who tells crazy Reddit-style stories. Write a compelling story script about {topic}.
Rules:
- Strong hook in the first 3 seconds.
- Narration 90-120 words.
- JSON output with keys: title, hook, narration, pexels_search_term, tags, category_id, mood."""
        prompt = self._build_prompt(template, topic=topic, performance_feedback=performance_feedback)
        return self._generate_json(prompt)

    def generate_commentary(self, clip_context: str, clip_title: str, performance_feedback: str = '') -> Dict[str, Any]:
        template = """You are an elite, multi-million view viral YouTube Shorts narrator (like Daily Dose of Internet or Sambucha).
Analyze this viral video clip:
Clip Title: {clip_title}
Clip Context: {clip_context}

Write a viral, transformative commentary script optimized to hit 10 Million views on YouTube Shorts:
Key Algorithmic Rules:
1. THE 2-SECOND HOOK: Open immediately with high stakes or extreme curiosity. Do NOT say 'Did you know' or 'Hey guys'. Start right in the action: e.g. "Watch what happens in the next three seconds..." or "This looked like a total disaster until..."
2. SEAMLESS INFINITE LOOP (MANDATORY): The very last sentence of the narration MUST flow naturally and grammatically straight back into the opening first sentence without a pause. When the Short loops, the viewer shouldn't realize it started over. This spikes Average Percentage Viewed (APV) above 100%!
3. DURATION & WORD COUNT: Between 40 and 65 words total. Keep sentences fast, punchy, and captivating.
4. SPICY PINNED COMMENT: Write a short, debate-provoking question for the pinned comment (under 12 words) to get hundreds of viewers commenting (e.g., "Would you have survived this? Be honest 👇" or "Rate this skill from 1 to 10 👇").
5. HIGH CTR TITLE: Click-worthy title under 60 characters with emojis.
6. TOP BANNER HOOK: 3 to 5 words in ALL CAPS (e.g., "WAIT FOR THE END 😱" or "0.01% CHANCE OF SURVIVAL 🤯").
7. JSON Output strictly with keys:
   - "commentary_script": string (the spoken narration with seamless loop ending)
   - "top_banner_text": string (short 3-5 word uppercase hook)
   - "pinned_comment": string (interactive debate-provoking question)
   - "viral_title": string (high CTR title under 60 chars)
   - "educational_facts": list of strings
   - "mood": string ("dramatic", "funny", "skills", or "mysterious")"""
        prompt = self._build_prompt(template, clip_title=clip_title, clip_context=clip_context, performance_feedback=performance_feedback)
        return self._generate_json(prompt)

    def generate_comment_reply(self, video_title: str, comment_text: str) -> str:
        if not self.client:
            return "Thanks for watching!"
            
        prompt = f"You are the creator of a YouTube Short titled '{video_title}'. A viewer commented: '{comment_text}'. Write a friendly, engaging, and short reply."
        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt
            )
            return response.text.strip()
        except Exception as e:
            logger.error(f"Failed to generate comment reply: {e}")
            return "Thanks for the comment!"

    def generate_community_post(self, recent_topics: List[str]) -> str:
        if not self.client:
            return "What kind of videos would you like to see next?"
            
        topics_str = ", ".join(recent_topics)
        prompt = f"Write an engaging YouTube community post poll or question based on our recent topics: {topics_str}. Make it interactive to drive engagement."
        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt
            )
            return response.text.strip()
        except Exception as e:
            logger.error(f"Failed to generate community post: {e}")
            return "What should we cover next?"

if __name__ == "__main__":
    generator = ContentGenerator()
    fact_script = generator.generate_fun_fact_script("Space")
    print("Generated Script Test:")
    print(json.dumps(fact_script, indent=2))
