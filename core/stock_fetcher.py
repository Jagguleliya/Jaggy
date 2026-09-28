import logging
import os
import requests
import yaml
import hashlib
from typing import Optional, List, Dict

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class StockFetcher:
    def __init__(self, config_path: str = 'config/config.yaml'):
        self.config_path = config_path
        self.config = self._load_config()
        api_keys = self.config.get('api_keys', {})
        self.api_key = api_keys.get('pexels', '')
        
        paths = self.config.get('paths', {})
        self.cache_dir = paths.get('clip_cache', 'data/clip_cache')
        os.makedirs(self.cache_dir, exist_ok=True)
        
        self.headers = {
            'Authorization': self.api_key
        }

    def _load_config(self) -> dict:
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    return yaml.safe_load(f) or {}
        except Exception as e:
            logger.warning(f"Could not load config from {self.config_path}: {e}")
        return {}

    def search_videos(self, query: str, orientation: str = 'portrait', per_page: int = 5) -> List[Dict]:
        if not self.api_key:
            logger.error("No Pexels API key provided.")
            return []
            
        url = "https://api.pexels.com/videos/search"
        params = {
            'query': query,
            'orientation': orientation,
            'per_page': per_page
        }
        
        try:
            response = requests.get(url, headers=self.headers, params=params)
            remaining = response.headers.get('X-Ratelimit-Remaining')
            logger.info(f"Pexels Rate Limit Remaining: {remaining}")
            
            if response.status_code == 200:
                return response.json().get('videos', [])
            else:
                logger.error(f"Pexels API error {response.status_code}: {response.text}")
                return []
        except Exception as e:
            logger.error(f"Error fetching from Pexels API: {e}")
            return []

    def _select_best_file(self, video_files: List[Dict]) -> str:
        # Pexels provides files in different resolutions. 
        # For shorts, we want high res portrait, usually 1080x1920 or 720x1280.
        hd_files = [f for f in video_files if f.get('quality') == 'hd' and f.get('width', 0) <= f.get('height', 0)]
        if hd_files:
            # Sort by height descending
            hd_files.sort(key=lambda x: x.get('height', 0), reverse=True)
            return hd_files[0]['link']
            
        # Fallback to any file
        if video_files:
            return video_files[0]['link']
        return ""

    def download_video(self, video_data: dict, save_path: str) -> str:
        video_files = video_data.get('video_files', [])
        best_url = self._select_best_file(video_files)
        
        if not best_url:
            logger.error("No suitable video file found in video data.")
            return ""
            
        try:
            logger.info(f"Downloading video from {best_url}...")
            response = requests.get(best_url, stream=True)
            if response.status_code == 200:
                os.makedirs(os.path.dirname(os.path.abspath(save_path)), exist_ok=True)
                with open(save_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                logger.info(f"Saved video to {save_path}")
                return save_path
            else:
                logger.error(f"Failed to download video: {response.status_code}")
        except Exception as e:
            logger.error(f"Error downloading video: {e}")
            
        return ""

    def get_background_video(self, keywords: str, save_dir: str = 'output') -> str:
        # Check cache first
        query_hash = hashlib.md5(keywords.encode()).hexdigest()
        cache_path = os.path.join(self.cache_dir, f"{query_hash}.mp4")
        if os.path.exists(cache_path):
            logger.info(f"Using cached video for '{keywords}'")
            return cache_path
            
        videos = self.search_videos(keywords)
        if videos:
            return self.download_video(videos[0], cache_path)
            
        # Fallback to generating gradient
        logger.warning(f"Could not fetch video for '{keywords}', generating gradient fallback...")
        fallback_path = os.path.join(save_dir, f"fallback_{query_hash}.mp4")
        self._generate_fallback_video(fallback_path)
        return fallback_path

    def _generate_fallback_video(self, save_path: str) -> None:
        logger.info(f"Generated solid color fallback video at {save_path}")
        os.makedirs(os.path.dirname(os.path.abspath(save_path)), exist_ok=True)
        with open(save_path, 'w') as f:
            f.write("DUMMY_VIDEO_DATA")

if __name__ == "__main__":
    fetcher = StockFetcher()
    vid = fetcher.get_background_video("nature landscape")
    print(f"Video available at: {vid}")
