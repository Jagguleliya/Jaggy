import yaml
import json
import os
import logging
from datetime import datetime
from typing import Dict, List
from core.youtube_uploader import YouTubeUploader

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class EngagementBot:
    def __init__(self, config_path: str = 'config/config.yaml', content_generator=None):
        self.config_path = config_path
        self.content_generator = content_generator
        self._load_config()
        self.engagement_log_path = self.config.get('paths', {}).get('engagement_log', 'engagement_log.json')
        
    def _load_config(self):
        try:
            with open(self.config_path, 'r') as f:
                self.config = yaml.safe_load(f)
        except Exception as e:
            logger.error(f"Failed to load config from {self.config_path}: {e}")
            self.config = {}

    def run_engagement_cycle(self, youtube_uploader: YouTubeUploader, video_id: str, video_title: str) -> Dict:
        """Run one cycle of engagement (reply to comments, heart them)."""
        logger.info(f"Running engagement cycle for video {video_id}")
        
        stats = {
            'replied': 0,
            'hearted': 0
        }
        
        # Heart recent comments
        self.heart_recent_comments(youtube_uploader, video_id)
        stats['hearted'] = 15 # Assuming we limit to 15
        
        # Process and reply to comments
        replies_made = self.process_video_comments(youtube_uploader, video_id, video_title)
        stats['replied'] = replies_made
        
        return stats

    def process_video_comments(self, youtube: YouTubeUploader, video_id: str, video_title: str) -> int:
        """Fetch recent comments, generate AI replies, post them. Return count of replies made."""
        engagement_config = self.config.get('engagement', {})
        max_replies_per_day = engagement_config.get('max_replies_per_day', 12)
        
        if self._get_today_reply_count() >= max_replies_per_day:
            logger.info("Max daily replies reached. Skipping comment replies.")
            return 0
            
        comments = youtube.get_recent_comments(video_id)
        replies_made = 0
        
        for item in comments:
            if self._get_today_reply_count() >= max_replies_per_day:
                break
                
            top_level_comment = item.get('snippet', {}).get('topLevelComment', {})
            snippet = top_level_comment.get('snippet', {})
            comment_id = top_level_comment.get('id')
            text = snippet.get('textOriginal', '')
            author = snippet.get('authorDisplayName', 'User')
            
            if self._should_reply(text):
                if self.content_generator:
                    # Mock content generator method to get AI reply
                    reply_text = getattr(self.content_generator, 'generate_comment_reply', lambda x, y: f"Thanks for the comment, {author}! Glad you liked {y}.")(text, video_title)
                else:
                    reply_text = f"Thanks for sharing your thoughts, {author}! Really appreciate the feedback on this short."
                    
                youtube.reply_to_comment(comment_id, reply_text)
                self._log_engagement('reply', {'video_id': video_id, 'comment_id': comment_id})
                replies_made += 1
                
        return replies_made

    def pin_first_comment(self, youtube: YouTubeUploader, video_id: str, text: str):
        """Post and pin a discussion-starter comment."""
        comment_id = youtube.post_comment(video_id, text)
        if comment_id:
            youtube.pin_comment(comment_id)
            self._log_engagement('pin', {'video_id': video_id, 'comment_id': comment_id})

    def heart_recent_comments(self, youtube: YouTubeUploader, video_id: str, limit: int = 15):
        """Heart the first N comments."""
        comments = youtube.get_recent_comments(video_id, max_results=limit)
        for item in comments:
            comment_id = item.get('snippet', {}).get('topLevelComment', {}).get('id')
            if comment_id:
                youtube.heart_comment(comment_id)
                self._log_engagement('heart', {'video_id': video_id, 'comment_id': comment_id})

    def generate_community_post(self) -> str:
        """Generate a community post using ContentGenerator."""
        if self.content_generator and hasattr(self.content_generator, 'generate_community_post'):
            return self.content_generator.generate_community_post()
        return "Hey everyone! What kind of Shorts do you want to see next? Drop your ideas below! 👇"

    def _should_reply(self, comment_text: str) -> bool:
        """Decide if a comment warrants a reply (skip spam, short comments, etc.)."""
        if len(comment_text) < 5:
            return False
        # simple spam filter mock
        spam_keywords = ['sub4sub', 'click here', 'free robux', 'my channel']
        if any(keyword in comment_text.lower() for keyword in spam_keywords):
            return False
        return True

    def _get_today_reply_count(self) -> int:
        """Check engagement_log for today's count."""
        if not os.path.exists(self.engagement_log_path):
            return 0
            
        today = datetime.now().strftime('%Y-%m-%d')
        count = 0
        try:
            with open(self.engagement_log_path, 'r') as f:
                logs = [json.loads(line) for line in f]
                for log in logs:
                    if log.get('action') == 'reply' and log.get('timestamp', '').startswith(today):
                        count += 1
        except Exception as e:
            logger.error(f"Error reading engagement log: {e}")
            
        return count

    def _log_engagement(self, action: str, details: Dict):
        """Log to engagement_log.json"""
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'action': action,
            'details': details
        }
        
        try:
            os.makedirs(os.path.dirname(self.engagement_log_path) or '.', exist_ok=True)
            with open(self.engagement_log_path, 'a') as f:
                f.write(json.dumps(log_entry) + '\n')
        except Exception as e:
            logger.error(f"Failed to write to engagement log: {e}")

if __name__ == "__main__":
    bot = EngagementBot()
    # bot.generate_community_post()
