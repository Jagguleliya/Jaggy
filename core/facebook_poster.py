import yaml
import logging
import requests
import time
import os
from typing import Dict, Optional

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class FacebookPoster:
    def __init__(self, config_path: str = 'config/config.yaml'):
        self.config_path = config_path
        self._load_config()
        self.page_id = None
        self.access_token = None
        self.api_version = "v18.0"
        
    def _load_config(self):
        try:
            with open(self.config_path, 'r') as f:
                self.config = yaml.safe_load(f)
        except Exception as e:
            logger.error(f"Failed to load config from {self.config_path}: {e}")
            self.config = {}

    def authenticate(self) -> bool:
        """Verify page access token."""
        fb_config = self.config.get('platforms', {}).get('facebook', {})
        self.page_id = fb_config.get('page_id')
        self.access_token = fb_config.get('access_token')
        
        if not self.page_id or not self.access_token:
            logger.error("Facebook page_id or access_token missing in config.")
            return False
            
        url = f"https://graph.facebook.com/{self.api_version}/{self.page_id}?access_token={self.access_token}"
        try:
            response = requests.get(url)
            if response.status_code == 200:
                logger.info("Successfully authenticated with Facebook Graph API.")
                return True
            else:
                logger.error(f"Failed to authenticate with Facebook: {response.json()}")
                return False
        except Exception as e:
            logger.error(f"Error authenticating with Facebook: {e}")
            return False

    def post_reel(self, video_path: str, description: str) -> Optional[str]:
        """Upload video as Reel to Facebook Page, return post_id."""
        if not self.page_id or not self.access_token:
            if not self.authenticate():
                return None

        video_id = self._initialize_upload(description)
        if not video_id:
            return None
            
        logger.info(f"Initialized upload. Video ID: {video_id}")
        
        # Facebook Reels upload via Graph API typically uses start, upload, finish
        # However, for Pages, Reels are often published via video endpoint with specific parameters.
        # Let's use standard Pages video upload protocol for Reels.
        
        success = self._upload_video(video_id, video_path)
        if not success:
            return None
            
        # Give Facebook some time to process the video before publishing if required
        # For standard uploads, sometimes it's published automatically if published=true
        # Here we mock the publish step if it's separate.
        
        return self._publish_reel(video_id)

    def _initialize_upload(self, description: str) -> Optional[str]:
        """Start upload session."""
        url = f"https://graph.facebook.com/{self.api_version}/{self.page_id}/video_reels"
        payload = {
            "upload_phase": "start",
            "access_token": self.access_token
        }
        
        try:
            response = requests.post(url, data=payload)
            data = response.json()
            if "video_id" in data:
                return data["video_id"]
            else:
                logger.error(f"Failed to initialize upload: {data}")
                return None
        except Exception as e:
            logger.error(f"Error in initialize upload: {e}")
            return None

    def _upload_video(self, video_id: str, video_path: str) -> bool:
        """Upload video binary."""
        url = f"https://rupload.facebook.com/video-delivery/{self.api_version}/{video_id}"
        headers = {
            "Authorization": f"OAuth {self.access_token}",
            "offset": "0",
            "file_size": str(os.path.getsize(video_path))
        }
        
        try:
            with open(video_path, 'rb') as f:
                response = requests.post(url, headers=headers, data=f)
            
            if response.status_code == 200:
                logger.info("Video binary uploaded successfully.")
                return True
            else:
                logger.error(f"Failed to upload video binary: {response.text}")
                return False
        except Exception as e:
            logger.error(f"Error uploading video binary: {e}")
            return False

    def _publish_reel(self, video_id: str, description: str = "") -> Optional[str]:
        """Publish the uploaded reel."""
        url = f"https://graph.facebook.com/{self.api_version}/{self.page_id}/video_reels"
        payload = {
            "upload_phase": "finish",
            "video_id": video_id,
            "video_state": "PUBLISHED",
            "description": description,
            "access_token": self.access_token
        }
        
        try:
            response = requests.post(url, data=payload)
            data = response.json()
            if "success" in data and data["success"]:
                logger.info(f"Successfully published Reel. Video ID: {video_id}")
                return video_id
            else:
                logger.error(f"Failed to publish reel: {data}")
                return None
        except Exception as e:
            logger.error(f"Error publishing reel: {e}")
            return None

    def get_post_metrics(self, post_id: str) -> Dict:
        """Get reach, views, reactions."""
        if not self.access_token:
            return {}
            
        url = f"https://graph.facebook.com/{self.api_version}/{post_id}?fields=insights.metric(post_video_views,post_impressions_unique)&access_token={self.access_token}"
        try:
            response = requests.get(url)
            data = response.json()
            # Extract metrics as needed
            return data
        except Exception as e:
            logger.error(f"Failed to get post metrics: {e}")
            return {}

if __name__ == "__main__":
    poster = FacebookPoster()
    # poster.authenticate()
    # poster.post_reel("test.mp4", "Check out this new reel!")
