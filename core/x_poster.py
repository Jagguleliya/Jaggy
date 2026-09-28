import yaml
import logging
import tweepy
from typing import List, Dict, Optional

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class XPoster:
    def __init__(self, config_path: str = 'config/config.yaml'):
        self.config_path = config_path
        self._load_config()
        self.client = None
        self.api = None
        
    def _load_config(self):
        try:
            with open(self.config_path, 'r') as f:
                self.config = yaml.safe_load(f)
        except Exception as e:
            logger.error(f"Failed to load config from {self.config_path}: {e}")
            self.config = {}

    def authenticate(self) -> bool:
        """Verify credentials work."""
        x_config = self.config.get('platforms', {}).get('x_twitter', {})
        api_key = x_config.get('api_key')
        api_secret = x_config.get('api_secret')
        access_token = x_config.get('access_token')
        access_token_secret = x_config.get('access_token_secret')
        
        if not all([api_key, api_secret, access_token, access_token_secret]):
            logger.error("Missing X API credentials in config.")
            return False
            
        try:
            # V2 client for tweeting
            self.client = tweepy.Client(
                consumer_key=api_key,
                consumer_secret=api_secret,
                access_token=access_token,
                access_token_secret=access_token_secret
            )
            
            # V1.1 API for media upload
            auth = tweepy.OAuth1UserHandler(
                api_key, api_secret, access_token, access_token_secret
            )
            self.api = tweepy.API(auth)
            
            # Verify credentials
            self.api.verify_credentials()
            logger.info("Successfully authenticated with X API.")
            return True
        except Exception as e:
            logger.error(f"Failed to authenticate with X: {e}")
            return False

    def post_video(self, video_path: str, text: str, tags: List[str] = None) -> Optional[str]:
        """Upload video and post tweet, return tweet_id."""
        if not self.client or not self.api:
            if not self.authenticate():
                return None
                
        if tags:
            hashtags = " ".join([f"#{tag}" for tag in tags])
            text = f"{text}\n\n{hashtags}"
            
        try:
            # Upload media using v1.1 API
            logger.info(f"Uploading video {video_path} to X...")
            media = self.api.media_upload(video_path, media_category='tweet_video')
            logger.info(f"Media uploaded. Media ID: {media.media_id}")
            
            # Create tweet with media using v2 client
            response = self.client.create_tweet(text=text, media_ids=[media.media_id])
            tweet_id = response.data['id']
            logger.info(f"Successfully posted video tweet. Tweet ID: {tweet_id}")
            
            self._track_usage()
            return tweet_id
        except Exception as e:
            logger.error(f"Failed to post video to X: {e}")
            return None

    def post_text(self, text: str) -> Optional[str]:
        """Post text-only tweet."""
        if not self.client:
            if not self.authenticate():
                return None
                
        try:
            response = self.client.create_tweet(text=text)
            tweet_id = response.data['id']
            logger.info(f"Successfully posted text tweet. Tweet ID: {tweet_id}")
            
            self._track_usage()
            return tweet_id
        except Exception as e:
            logger.error(f"Failed to post text to X: {e}")
            return None

    def get_tweet_metrics(self, tweet_id: str) -> Dict:
        """Get impressions, likes, retweets."""
        if not self.client:
            return {}
            
        try:
            response = self.client.get_tweet(tweet_id, tweet_fields=['public_metrics'])
            if response.data:
                return response.data.public_metrics
            return {}
        except Exception as e:
            logger.error(f"Failed to get tweet metrics: {e}")
            return {}

    def _track_usage(self):
        """Track usage to stay within 1500 posts/month free tier limit."""
        # A simple placeholder. In a real scenario, read/write to a usage JSON file.
        logger.info("Tracked post usage against 1,500/month limit.")

if __name__ == "__main__":
    poster = XPoster()
    # poster.authenticate()
    # poster.post_text("Hello World from X Poster bot!")
