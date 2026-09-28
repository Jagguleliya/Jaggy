import os
import json
import logging
import time
from typing import List, Dict, Optional
import yaml
import praw
import tweepy
import requests

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ClipCurator:
    def __init__(self, config_path: str = 'config/config.yaml'):
        self.config_path = config_path
        self._load_config()
        self.used_topics_file = self.config.get('paths', {}).get('used_topics', 'data/used_topics.json')
        self._init_apis()
        
        # Ensure used topics file exists
        os.makedirs(os.path.dirname(self.used_topics_file) or '.', exist_ok=True)
        if not os.path.exists(self.used_topics_file):
            with open(self.used_topics_file, 'w') as f:
                json.dump([], f)

    def _load_config(self):
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    self.config = yaml.safe_load(f) or {}
            else:
                self.config = {}
        except Exception as e:
            logger.error(f"Failed to load config from {self.config_path}: {e}")
            self.config = {}

    def _init_apis(self):
        # Initialize Reddit
        try:
            api_keys = self.config.get('api_keys', {})
            reddit_client_id = api_keys.get('reddit_client_id')
            reddit_client_secret = api_keys.get('reddit_client_secret')
            if reddit_client_id and reddit_client_secret:
                self.reddit = praw.Reddit(
                    client_id=reddit_client_id,
                    client_secret=reddit_client_secret,
                    user_agent="windows:youtube-shorts-bot:v1.0"
                )
            else:
                self.reddit = None
                logger.warning("Reddit credentials not found in config.")
        except Exception as e:
            logger.error(f"Failed to initialize Reddit API: {e}")
            self.reddit = None

        # Initialize X / Twitter
        try:
            platforms = self.config.get('platforms', {})
            x_config = platforms.get('x_twitter', {})
            x_api_key = x_config.get('api_key')
            x_api_secret = x_config.get('api_secret')
            x_access_token = x_config.get('access_token')
            x_access_secret = x_config.get('access_secret')
            
            if all([x_api_key, x_api_secret, x_access_token, x_access_secret]):
                auth = tweepy.OAuth1UserHandler(x_api_key, x_api_secret, x_access_token, x_access_secret)
                self.x_client = tweepy.API(auth)
            else:
                self.x_client = None
                logger.warning("X (Twitter) credentials not found in config.")
        except Exception as e:
            logger.error(f"Failed to initialize X API: {e}")
            self.x_client = None

    def find_viral_clips_reddit(self, subreddits: List[str] = None, limit: int = 10) -> List[Dict]:
        if not self.reddit:
            return []
        
        if not subreddits:
            subreddits = ["interestingasfuck", "BeAmazed", "todayilearned", "Damnthatsinteresting", "nextfuckinglevel"]
            
        clips = []
        try:
            for sub_name in subreddits:
                subreddit = self.reddit.subreddit(sub_name)
                for post in subreddit.hot(limit=limit):
                    if post.score < 1000:
                        continue
                        
                    # Check if post is a video or gif
                    if post.is_video or getattr(post, 'url', '').endswith(('.gif', '.mp4')):
                        clip_id = f"reddit_{post.id}"
                        media_url = getattr(post, 'url', '')
                        if post.is_video and hasattr(post, 'media') and post.media:
                            media_url = post.media.get('reddit_video', {}).get('fallback_url', media_url)
                            
                        clip_info = {
                            'id': clip_id,
                            'title': post.title,
                            'url': post.url,
                            'subreddit': sub_name,
                            'score': post.score,
                            'media_url': media_url,
                            'permalink': f"https://reddit.com{post.permalink}",
                            'source': 'reddit'
                        }
                        clips.append(clip_info)
        except Exception as e:
            logger.error(f"Error fetching from Reddit: {e}")
            
        return clips

    def find_viral_clips_x(self, query: str = None, limit: int = 5) -> List[Dict]:
        if not self.x_client:
            return []
            
        clips = []
        if not query:
            query = "filter:media min_faves:1000"
            
        try:
            tweets = self.x_client.search_tweets(q=query, count=limit, tweet_mode='extended')
            for tweet in tweets:
                media = tweet.entities.get('media', [])
                if media and media[0]['type'] in ['video', 'animated_gif']:
                    clip_id = f"x_{tweet.id}"
                    
                    # Get best video variant
                    variants = media[0].get('video_info', {}).get('variants', [])
                    media_url = ""
                    best_bitrate = -1
                    for v in variants:
                        if v.get('content_type') == 'video/mp4' and v.get('bitrate', -1) > best_bitrate:
                            best_bitrate = v.get('bitrate', -1)
                            media_url = v.get('url')
                            
                    if media_url:
                        clip_info = {
                            'id': clip_id,
                            'title': tweet.full_text,
                            'url': f"https://twitter.com/user/status/{tweet.id}",
                            'subreddit': 'X',
                            'score': tweet.favorite_count,
                            'media_url': media_url,
                            'permalink': f"https://twitter.com/user/status/{tweet.id}",
                            'source': 'x'
                        }
                        clips.append(clip_info)
        except Exception as e:
            logger.error(f"Error fetching from X: {e}")
            
        return clips

    def find_viral_clips_youtube(self, queries: List[str] = None, limit: int = 15) -> List[Dict]:
        """
        Discovers high-performing, verified mega-viral Shorts directly from YouTube.
        Uses view-count sorted search (&sp=CAMSAhAB) to guarantee 100k+ to millions of views.
        """
        import yt_dlp
        import random
        import urllib.parse
        
        if not queries:
            queries = [
                "unbelievable skills shorts",
                "caught on camera shorts",
                "instant regret funny shorts",
                "most satisfying video shorts",
                "insane stunts people are awesome shorts",
                "crazy reflex save shorts",
                "impossible optical illusion shorts"
            ]
        
        # Shuffle queries to ensure fresh niche diversity on every run
        queries = list(queries)
        random.shuffle(queries)
        
        ydl_opts = {
            'quiet': True,
            'extract_flat': True,
            'skip_download': True,
            'no_warnings': True
        }
        
        clips = []
        bad_words = ['compilation', 'how to', 'tips & tricks', 'tutorial', 'highlights', 'episode', 'guide']
        
        for query in queries:
            encoded_q = urllib.parse.quote_plus(query)
            # &sp=CAMSAhAB sorts YouTube search results by view count descending
            search_url = f"https://www.youtube.com/results?search_query={encoded_q}&sp=CAMSAhAB"
            logger.info(f"Discovering viral Shorts for query: '{query}' (sorted by views)...")
            
            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    res = ydl.extract_info(search_url, download=False)
                    for entry in res.get('entries', []):
                        duration = entry.get('duration') or 0
                        views = entry.get('view_count') or 0
                        title = entry.get('title') or ''
                        vid_id = entry.get('id')
                        
                        if not vid_id:
                            continue
                            
                        # Must be genuine vertical Short duration (12s to 58s)
                        if not (12 <= duration <= 58):
                            continue
                            
                        # Must have proven viral engagement (at least 100k views)
                        if views < 100000:
                            continue
                            
                        # Skip multi-clip compilations or tutorials
                        title_lower = title.lower()
                        if any(bad in title_lower for bad in bad_words):
                            continue
                            
                        clip_id = f"yt_{vid_id}"
                        if not self._is_used(clip_id):
                            clips.append({
                                'id': clip_id,
                                'title': title,
                                'url': f"https://www.youtube.com/watch?v={vid_id}",
                                'duration': duration,
                                'source': 'youtube',
                                'author': entry.get('uploader', 'Original Creator'),
                                'score': views
                            })
                            
                if len(clips) >= limit:
                    break
            except Exception as e:
                logger.error(f"Error discovering viral Shorts for '{query}': {e}")
                continue
                
        # Sort by view count descending so the absolute most viral clip is prioritized
        clips.sort(key=lambda x: x.get('score', 0), reverse=True)
        return clips

    def download_clip(self, clip_info: Dict, save_dir: str = 'data/clip_cache') -> str:
        os.makedirs(save_dir, exist_ok=True)
        
        # 1. If YouTube clip, download using yt-dlp
        if clip_info.get('source') == 'youtube':
            import yt_dlp
            save_path = os.path.join(save_dir, f"{clip_info['id']}.mp4")
            if os.path.exists(save_path):
                logger.info(f"Clip already downloaded: {save_path}")
                return save_path
                
            try:
                import imageio_ffmpeg
                ffmpeg_path = imageio_ffmpeg.get_ffmpeg_exe()
            except Exception:
                ffmpeg_path = None

            ydl_opts = {
                'format': 'bestvideo*+bestaudio/best',
                'outtmpl': save_path,
                'quiet': True,
                'no_warnings': True,
                'merge_output_format': 'mp4'
            }
            if ffmpeg_path and os.path.exists(ffmpeg_path):
                ydl_opts['ffmpeg_location'] = ffmpeg_path

            try:
                logger.info(f"Downloading YouTube viral clip from {clip_info['url']}...")
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([clip_info['url']])
                return save_path
            except Exception as e:
                logger.error(f"Failed to download YouTube clip: {e}")
                return ""

        # 2. Reddit / Direct URL download
        media_url = clip_info.get('media_url')
        if not media_url:
            logger.error("No media URL found for clip.")
            return ""
            
        file_ext = media_url.split('.')[-1].split('?')[0]
        if len(file_ext) > 4 or not file_ext:
            file_ext = "mp4"
            
        save_path = os.path.join(save_dir, f"{clip_info['id']}.{file_ext}")
        
        if os.path.exists(save_path):
            logger.info(f"Clip already downloaded: {save_path}")
            return save_path
            
        try:
            logger.info(f"Downloading clip to {save_path}")
            response = requests.get(media_url, stream=True, timeout=20)
            response.raise_for_status()
            with open(save_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            return save_path
        except Exception as e:
            logger.error(f"Failed to download clip: {e}")
            return ""

    def _is_used(self, clip_id: str) -> bool:
        try:
            if not os.path.exists(self.used_topics_file):
                return False
            with open(self.used_topics_file, 'r') as f:
                used = json.load(f)
            for item in used:
                if item.get('id') == clip_id:
                    return True
        except Exception as e:
            logger.error(f"Error checking used topics: {e}")
        return False

    def _mark_used(self, clip_id: str, metadata: Dict):
        try:
            used = []
            if os.path.exists(self.used_topics_file):
                with open(self.used_topics_file, 'r') as f:
                    try:
                        used = json.load(f)
                    except json.JSONDecodeError:
                        used = []
            
            entry = {'id': clip_id, 'timestamp': time.time()}
            entry.update(metadata)
            used.append(entry)
            
            with open(self.used_topics_file, 'w') as f:
                json.dump(used, f, indent=4)
        except Exception as e:
            logger.error(f"Error marking clip as used: {e}")

    def get_best_clip(self) -> Optional[Dict]:
        logger.info("Searching for the best viral clip...")
        
        yt_clips = self.find_viral_clips_youtube(limit=10)
        reddit_clips = self.find_viral_clips_reddit(limit=10)
        x_clips = self.find_viral_clips_x(limit=5)
        
        all_clips = yt_clips + reddit_clips + x_clips
        all_clips.sort(key=lambda x: x.get('score', 0), reverse=True)
        
        for clip in all_clips:
            if not self._is_used(clip['id']):
                cache_dir = self.config.get('paths', {}).get('clip_cache', 'data/clip_cache')
                path = self.download_clip(clip, save_dir=cache_dir)
                if path:
                    clip['local_path'] = path
                    self._mark_used(clip['id'], {'title': clip['title'], 'source': clip['source']})
                    return clip
                    
        logger.warning("No unused suitable clips found.")
        return None

if __name__ == "__main__":
    curator = ClipCurator()
    best = curator.get_best_clip()
    if best:
        print(f"Found best clip: {best['title']}")
        print(f"Path: {best.get('local_path')}")
    else:
        print("No clips found.")
