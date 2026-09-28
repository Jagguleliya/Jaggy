import logging
import os
import yaml
import random
import glob
from typing import Optional, List, Dict

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MusicManager:
    def __init__(self, config_path: str = 'config/config.yaml'):
        self.config_path = config_path
        self.config = self._load_config()
        music_config = self.config.get('music', {})
        self.music_dir = music_config.get('directory', 'data/music')
        self.recent_tracks_file = os.path.join(self.music_dir, 'recent_tracks.txt')
        
        os.makedirs(self.music_dir, exist_ok=True)
        self.recent_tracks = self._load_recent_tracks()

    def _load_config(self) -> dict:
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    return yaml.safe_load(f) or {}
        except Exception as e:
            logger.warning(f"Could not load config from {self.config_path}: {e}")
        return {}

    def _load_recent_tracks(self) -> List[str]:
        if os.path.exists(self.recent_tracks_file):
            try:
                with open(self.recent_tracks_file, 'r', encoding='utf-8') as f:
                    return [line.strip() for line in f.readlines() if line.strip()]
            except Exception as e:
                logger.error(f"Error reading recent tracks: {e}")
        return []

    def _save_recent_tracks(self, max_history: int = 10):
        try:
            with open(self.recent_tracks_file, 'w', encoding='utf-8') as f:
                for track in self.recent_tracks[-max_history:]:
                    f.write(f"{track}\n")
        except Exception as e:
            logger.error(f"Error saving recent tracks: {e}")

    def select_track(self, mood: Optional[str] = None) -> Optional[str]:
        search_dir = os.path.join(self.music_dir, mood) if mood else self.music_dir
        
        if not os.path.exists(search_dir):
            logger.warning(f"Directory {search_dir} does not exist.")
            self.add_track_info()
            return None
            
        tracks = []
        for ext in ('*.mp3', '*.wav'):
            tracks.extend(glob.glob(os.path.join(search_dir, '**', ext), recursive=True))
            
        if not tracks:
            logger.warning(f"No music tracks found in {search_dir}.")
            self.add_track_info()
            return None
            
        # Avoid recent tracks if possible
        available_tracks = [t for t in tracks if t not in self.recent_tracks]
        if not available_tracks:
            available_tracks = tracks
            
        selected_track = random.choice(available_tracks)
        
        self.recent_tracks.append(selected_track)
        self._save_recent_tracks()
        
        return selected_track

    def get_available_moods(self) -> Dict[str, int]:
        moods = {}
        if not os.path.exists(self.music_dir):
            return moods
            
        for item in os.listdir(self.music_dir):
            item_path = os.path.join(self.music_dir, item)
            if os.path.isdir(item_path):
                tracks = glob.glob(os.path.join(item_path, '*.mp3')) + glob.glob(os.path.join(item_path, '*.wav'))
                moods[item] = len(tracks)
                
        return moods

    def add_track_info(self):
        logger.info("--- MUSIC DOWNLOAD INFO ---")
        logger.info("To add background music to your videos, download royalty-free tracks and place them in 'data/music/<mood>/'.")
        logger.info("Recommended sources:")
        logger.info(" - YouTube Audio Library: https://www.youtube.com/audiolibrary")
        logger.info(" - Pixabay Music: https://pixabay.com/music/")
        logger.info(" - Incompetech: https://incompetech.com/")
        logger.info("---------------------------")

if __name__ == "__main__":
    manager = MusicManager()
    print("Available moods:", manager.get_available_moods())
    track = manager.select_track()
    print("Selected track:", track)
