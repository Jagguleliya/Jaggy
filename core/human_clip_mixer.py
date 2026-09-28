import logging
import os
import yaml
import random
from typing import Optional
from moviepy.editor import VideoFileClip
import moviepy.video.fx.all as vfx

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class HumanClipMixer:
    def __init__(self, config_path: str = 'config/config.yaml'):
        self.config_path = config_path
        self.config = self._load_config()
        
        user_clips_config = self.config.get('user_clips', {})
        self.clip_1_path = user_clips_config.get('clip_1', 'data/clips/clip_1.mp4')
        self.clip_2_path = user_clips_config.get('clip_2', 'data/clips/clip_2.mp4')
        self.insert_points = user_clips_config.get('insert_points', ['intro', 'reaction', 'outro'])
        
        self.clips_loaded = self.load_clips()

    def _load_config(self) -> dict:
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    return yaml.safe_load(f) or {}
        except Exception as e:
            logger.warning(f"Could not load config from {self.config_path}: {e}")
        return {}

    def load_clips(self) -> bool:
        missing = False
        if not os.path.exists(self.clip_1_path):
            logger.warning(f"User clip 1 not found at {self.clip_1_path}")
            missing = True
        if not os.path.exists(self.clip_2_path):
            logger.warning(f"User clip 2 not found at {self.clip_2_path}")
            missing = True
            
        return not missing

    def clips_available(self) -> bool:
        return self.clips_loaded

    def extract_segment(self, clip_path: str, duration: float = 3.0, variation_seed: Optional[int] = None) -> Optional[VideoFileClip]:
        if not os.path.exists(clip_path):
            return None
            
        try:
            clip = VideoFileClip(clip_path)
            clip_dur = clip.duration
            
            if variation_seed is not None:
                random.seed(variation_seed)
                
            if clip_dur > duration:
                start_time = random.uniform(0, clip_dur - duration)
            else:
                start_time = 0
                duration = clip_dur
                
            segment = clip.subclip(start_time, start_time + duration)
            
            # Apply variations
            zoom_factor = random.uniform(1.0, 1.15)
            if zoom_factor > 1.01:
                # Resize to zoom in, then crop to original size to maintain aspect ratio
                w, h = segment.size
                segment = segment.resize(zoom_factor).crop(x_center=w*zoom_factor/2, y_center=h*zoom_factor/2, width=w, height=h)
                
            # Optional: brightness adjustment could be done using vfx.colorx
            brightness_adj = random.uniform(0.95, 1.05)
            segment = segment.fx(vfx.colorx, brightness_adj)
                
            return segment
        except Exception as e:
            logger.error(f"Error extracting segment from {clip_path}: {e}")
            return None

    def get_intro_clip(self, seed: Optional[int] = None) -> Optional[VideoFileClip]:
        if not self.clips_available():
            return None
        return self.extract_segment(self.clip_1_path, duration=3.0, variation_seed=seed)

    def get_reaction_clip(self, seed: Optional[int] = None) -> Optional[VideoFileClip]:
        if not self.clips_available():
            return None
        return self.extract_segment(self.clip_2_path, duration=2.5, variation_seed=seed)

    def get_outro_clip(self, seed: Optional[int] = None) -> Optional[VideoFileClip]:
        if not self.clips_available():
            return None
        return self.extract_segment(self.clip_2_path, duration=4.0, variation_seed=seed)

if __name__ == "__main__":
    mixer = HumanClipMixer()
    if mixer.clips_available():
        intro = mixer.get_intro_clip()
        if intro:
            print(f"Got intro clip of duration {intro.duration}")
            intro.close()
    else:
        print("Clips not available. Provide clips to test.")
