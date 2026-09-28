import asyncio
import logging
import os
import yaml
from typing import Optional, List, Dict
import edge_tts
from gtts import gTTS
import mutagen.mp3

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TTSEngine:
    def __init__(self, config_path: str = 'config/config.yaml'):
        self.config_path = config_path
        self.config = self._load_config()
        tts_config = self.config.get('tts', {})
        self.engine = tts_config.get('engine', 'edge-tts')
        self.voice = tts_config.get('voice', 'en-US-ChristopherNeural')
        self.elevenlabs_voice_id = tts_config.get('elevenlabs_voice_id', '')
        self.rate = tts_config.get('rate', '+0%')
        self.volume = tts_config.get('volume', '+0%')
        self.current_voice_name = "Default"
        self.elevenlabs_api_key = self.config.get('api_keys', {}).get('elevenlabs', '')

    def _load_config(self) -> dict:
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    return yaml.safe_load(f) or {}
        except Exception as e:
            logger.warning(f"Could not load config from {self.config_path}: {e}")
        return {}

    def select_tournament_voice(self, analytics_engine=None) -> Dict:
        """
        Selects the best voice for the current Short:
        - If locked_winner exists, uses that winning voice permanently.
        - If in tournament mode, rotates voices to test which gets the most views.
        - Once min_samples_to_lock is reached, auto-locks the highest performing voice!
        """
        self.config = self._load_config()
        tts_config = self.config.get('tts', {})
        locked_winner = tts_config.get('locked_winner', '')

        tournament_voices = tts_config.get('tournament_voices', [
            {"name": "Eric", "voice": "en-US-EricNeural", "rate": "+3%", "pitch": "-1Hz"},
            {"name": "Christopher", "voice": "en-US-ChristopherNeural", "rate": "+0%", "pitch": "+0Hz"},
            {"name": "Andrew", "voice": "en-US-AndrewNeural", "rate": "-1%", "pitch": "-2Hz"},
            {"name": "Brian", "voice": "en-US-BrianMultilingualNeural", "rate": "+2%", "pitch": "+0Hz"}
        ])

        # If winner already crowned, use it permanently
        if locked_winner:
            for v in tournament_voices:
                if v.get('name') == locked_winner:
                    logger.info(f"Using crowned tournament champion voice: {locked_winner}")
                    self.current_voice_name = locked_winner
                    return v

        if not analytics_engine or not hasattr(analytics_engine, 'get_voice_rankings'):
            # Default rotation if no analytics
            selected = tournament_voices[0]
            self.current_voice_name = selected.get('name', 'Default')
            return selected

        rankings = analytics_engine.get_voice_rankings()
        min_samples = tts_config.get('min_samples_to_lock', 8)
        total_tests = sum(data.get('tests', 0) for data in rankings.values())

        # Check if tournament complete -> Lock Winner!
        if total_tests >= min_samples and rankings:
            best_name = max(rankings.items(), key=lambda x: (x[1].get('avg_score', 0), x[1].get('total_views', 0)))[0]
            logger.info(f"🏆 TOURNAMENT WINNER CROWNED: {best_name}! Locking permanently.")
            tts_config['locked_winner'] = best_name
            try:
                with open(self.config_path, 'w', encoding='utf-8') as f:
                    yaml.safe_dump(self.config, f)
            except Exception as e:
                logger.warning(f"Failed to save locked winner: {e}")
            for v in tournament_voices:
                if v.get('name') == best_name:
                    self.current_voice_name = best_name
                    return v

        # Still testing: Pick the voice with the fewest tests (fair round-robin)
        candidate_counts = {v['name']: rankings.get(v['name'], {}).get('tests', 0) for v in tournament_voices}
        least_tested = min(candidate_counts, key=candidate_counts.get)
        for v in tournament_voices:
            if v['name'] == least_tested:
                logger.info(f"Tournament Testing: Selected voice '{least_tested}' (tested {candidate_counts[least_tested]} times so far).")
                self.current_voice_name = least_tested
                return v

        self.current_voice_name = tournament_voices[0].get('name', 'Default')
        return tournament_voices[0]

    def select_voice_for_mood(self, mood: str = 'dramatic') -> Dict:
        """
        Dynamically matches voice to the Short's mood & genre:
        - dramatic / extreme / stunt / close call / shock -> Brian (deep, cinematic movie trailer narrator)
        - funny / comedy / fail / instant regret -> Eric (energetic, expressive, entertaining, amused)
        - skills / satisfying / craft / talent -> Christopher (clear, engaging, admiring documentary narrator)
        - mysterious / twist / weird / optical illusion -> Andrew (intriguing, curious, suspenseful)
        """
        mood_lower = (mood or 'dramatic').lower()
        
        mood_voice_map = {
            "dramatic": {"name": "Brian", "voice": "en-US-BrianMultilingualNeural", "rate": "+7%", "pitch": "-2Hz"},
            "shocking": {"name": "Brian", "voice": "en-US-BrianMultilingualNeural", "rate": "+7%", "pitch": "-2Hz"},
            "stunt": {"name": "Brian", "voice": "en-US-BrianMultilingualNeural", "rate": "+7%", "pitch": "-2Hz"},
            
            "funny": {"name": "Eric", "voice": "en-US-EricNeural", "rate": "+8%", "pitch": "+0Hz"},
            "fail": {"name": "Eric", "voice": "en-US-EricNeural", "rate": "+8%", "pitch": "+0Hz"},
            "comedy": {"name": "Eric", "voice": "en-US-EricNeural", "rate": "+8%", "pitch": "+0Hz"},
            
            "skills": {"name": "Christopher", "voice": "en-US-ChristopherNeural", "rate": "+5%", "pitch": "+0Hz"},
            "satisfying": {"name": "Christopher", "voice": "en-US-ChristopherNeural", "rate": "+4%", "pitch": "+0Hz"},
            "talent": {"name": "Christopher", "voice": "en-US-ChristopherNeural", "rate": "+5%", "pitch": "+0Hz"},
            
            "mysterious": {"name": "Andrew", "voice": "en-US-AndrewNeural", "rate": "+4%", "pitch": "-1Hz"},
            "twist": {"name": "Andrew", "voice": "en-US-AndrewNeural", "rate": "+5%", "pitch": "-1Hz"},
            "illusion": {"name": "Andrew", "voice": "en-US-AndrewNeural", "rate": "+4%", "pitch": "-1Hz"},
        }
        
        for key, v_config in mood_voice_map.items():
            if key in mood_lower:
                logger.info(f"🎙️ Matched voice to Short mood '{mood}': {v_config['name']} ({v_config['voice']})")
                self.current_voice_name = v_config['name']
                return v_config
                
        # Default to Brian (deep cinematic)
        default_voice = {"name": "Brian", "voice": "en-US-BrianMultilingualNeural", "rate": "+7%", "pitch": "-2Hz"}
        logger.info(f"🎙️ Using cinematic voice: Brian for mood '{mood}'")
        self.current_voice_name = "Brian"
        return default_voice

    async def generate_speech(self, text: str, output_path: str, voice_config: Optional[Dict] = None) -> str:
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        
        # Reload config in case keys were updated
        self.config = self._load_config()
        tts_config = self.config.get('tts', {})
        self.engine = tts_config.get('engine', 'edge-tts')

        # Extract voice parameters
        if voice_config and isinstance(voice_config, dict):
            used_voice = voice_config.get('voice', self.voice)
            used_rate = voice_config.get('rate', self.rate)
            used_pitch = voice_config.get('pitch', '+0Hz')
            self.current_voice_name = voice_config.get('name', self.current_voice_name)
        else:
            used_voice = self.voice
            used_rate = self.rate
            used_pitch = '+0Hz'

        try:
            if self.engine == 'edge-tts':
                await self._generate_edge_tts(text, output_path, used_voice, used_rate, self.volume, used_pitch)
            else:
                self._generate_gtts(text, output_path)
        except Exception as e:
            logger.error(f"TTS generation failed with edge-tts: {e}. Falling back to gTTS.")
            self._generate_gtts(text, output_path)
            
        return output_path

    def _generate_elevenlabs(self, text: str, output_path: str) -> bool:
        """Generates speech using ElevenLabs API."""
        import requests
        try:
            voice_id = self.elevenlabs_voice_id
            headers = {
                "xi-api-key": self.elevenlabs_api_key,
                "Content-Type": "application/json"
            }

            # If no direct voice_id is set, query voices to find matching name
            if not voice_id:
                try:
                    resp = requests.get("https://api.elevenlabs.io/v1/voices", headers=headers, timeout=10)
                    if resp.status_code == 200:
                        voices_data = resp.json().get("voices", [])
                        target_name = self.voice.lower()
                        for v in voices_data:
                            if target_name in v.get("name", "").lower():
                                voice_id = v.get("voice_id")
                                logger.info(f"Found ElevenLabs voice '{v.get('name')}' with ID: {voice_id}")
                                break
                except Exception as ex:
                    logger.warning(f"Failed to search ElevenLabs voices: {ex}")

            # Default to first available voice or Pablo
            if not voice_id:
                voice_id = "21m00Tcm4TlvDq8ikWAM" # default Rachel fallback if not found

            url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
            payload = {
                "text": text,
                "model_id": "eleven_multilingual_v2",
                "voice_settings": {
                    "stability": 0.5,
                    "similarity_boost": 0.8
                }
            }

            logger.info(f"Calling ElevenLabs API for voice ID: {voice_id}...")
            response = requests.post(url, json=payload, headers=headers, timeout=30)
            if response.status_code == 200:
                with open(output_path, "wb") as f:
                    f.write(response.content)
                logger.info(f"Successfully generated ElevenLabs voiceover at {output_path}")
                return True
            else:
                logger.error(f"ElevenLabs API error ({response.status_code}): {response.text}")
                return False
        except Exception as e:
            logger.error(f"ElevenLabs TTS exception: {e}")
            return False

    def generate_speech_sync(self, text: str, output_path: str, voice_config: Optional[Dict] = None) -> str:
        return asyncio.run(self.generate_speech(text, output_path, voice_config))

    async def _generate_edge_tts(self, text: str, output_path: str, voice: str, rate: str, volume: str, pitch: str = '+0Hz') -> None:
        communicate = edge_tts.Communicate(text, voice, rate=rate, volume=volume, pitch=pitch)
        await communicate.save(output_path)

    def _generate_gtts(self, text: str, output_path: str) -> None:
        tts = gTTS(text=text, lang='en')
        tts.save(output_path)

    async def list_voices(self) -> List[Dict]:
        return await edge_tts.list_voices()

    def get_audio_duration(self, audio_path: str) -> float:
        try:
            audio = mutagen.mp3.MP3(audio_path)
            return audio.info.length
        except Exception as e:
            logger.error(f"Failed to get audio duration: {e}")
            return 0.0

if __name__ == "__main__":
    engine = TTSEngine()
    out_path = "output/test_speech.mp3"
    print(f"Generating speech to {out_path}...")
    engine.generate_speech_sync("Hello, this is a test of the TTS engine.", out_path)
    dur = engine.get_audio_duration(out_path)
    print(f"Audio duration: {dur} seconds")
