"""
Main pipeline orchestrator for the YouTube Shorts automation bot.
"""
import os
import sys
import json
import yaml
import time
import argparse
import logging
import traceback
import random
from datetime import datetime
from typing import Dict, Any, List, Optional

# Configure logging (both console and logs/bot.log)
os.makedirs('logs', exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('logs/bot.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

# Component Imports
try:
    from core.content_generator import ContentGenerator
    from core.clip_curator import ClipCurator
    from core.commentary_engine import CommentaryEngine
    from core.tts_engine import TTSEngine
    from core.stock_fetcher import StockFetcher
    from core.music_manager import MusicManager
    from core.human_clip_mixer import HumanClipMixer
    from core.video_engine import VideoEngine
    from core.youtube_uploader import YouTubeUploader
    from core.x_poster import XPoster
    from core.facebook_poster import FacebookPoster
    from core.engagement_bot import EngagementBot
    from core.analytics_engine import AnalyticsEngine
    from core.story_universe_engine import StoryUniverseEngine
except ImportError as e:
    logger.warning(f"Failed to import a core module: {e}. Some pipeline parts may fail.")

class ShortsBotPipeline:
    """Main orchestrator that wires up all components of the YouTube Shorts Bot."""
    def __init__(self, config_path='config/config.yaml'):
        self.config_path = config_path
        self.config = self._load_config(config_path)
        
        # Initialize all engines with try/except
        self.content_generator = self._init_component(ContentGenerator)
        self.clip_curator = self._init_component(ClipCurator)
        self.commentary_engine = self._init_component(CommentaryEngine)
        self.story_universe_engine = self._init_component(StoryUniverseEngine)
        self.tts_engine = self._init_component(TTSEngine)
        self.stock_fetcher = self._init_component(StockFetcher)
        self.music_manager = self._init_component(MusicManager)
        self.human_clip_mixer = self._init_component(HumanClipMixer)
        self.video_engine = self._init_component(VideoEngine)
        self.youtube_uploader = self._init_component(YouTubeUploader)
        self.x_poster = self._init_component(XPoster)
        self.facebook_poster = self._init_component(FacebookPoster)
        self.engagement_bot = self._init_component(EngagementBot)
        self.analytics_engine = self._init_component(AnalyticsEngine)

        # Ensure output directory exists
        os.makedirs('output', exist_ok=True)

    def _load_config(self, path: str) -> Dict[str, Any]:
        """Load YAML configuration."""
        try:
            if os.path.exists(path):
                with open(path, 'r', encoding='utf-8') as f:
                    return yaml.safe_load(f) or {}
            else:
                logger.warning(f"Config file not found at {path}")
        except Exception as e:
            logger.error(f"Failed to load config from {path}: {e}")
        return {}

    def _init_component(self, component_class) -> Any:
        """Helper to initialize a component safely."""
        try:
            # Try passing config_path first, fallback to config dict or no args
            try:
                return component_class(self.config_path)
            except Exception:
                try:
                    return component_class(self.config)
                except Exception:
                    return component_class()
        except Exception as e:
            logger.error(f"Failed to initialize {component_class.__name__}: {e}")
            return None

    def _build_description(self, script: Dict[str, Any]) -> str:
        """Build YouTube description with hashtags, AI disclosure."""
        title = script.get('title', 'Awesome Short')
        desc = script.get('description', '')
        tags = script.get('tags', [])
        
        description_lines = [title, "", desc, ""]
        
        if tags:
            hashtags = " ".join([f"#{t.replace(' ', '')}" for t in tags])
            description_lines.extend([hashtags, ""])
            
        metadata = script.get('metadata', {})
        if metadata.get('author'):
            description_lines.append(f"Original clip credit: {metadata.get('author')}")
        if metadata.get('url'):
            description_lines.append(f"Original source: {metadata.get('url')}")
        description_lines.append("")
        description_lines.append("Disclaimer: This video is transformative commentary and fair use review.")
        return "\n".join(description_lines)

    def _cleanup(self, temp_files: List[str]):
        """Remove temp files in output/ directory."""
        for file in temp_files:
            if file and os.path.exists(file):
                try:
                    os.remove(file)
                    logger.info(f"Cleaned up {file}")
                except Exception as e:
                    logger.warning(f"Failed to remove {file}: {e}")

    def run_engagement_only(self):
        """Wire up engagement bot with youtube uploader."""
        logger.info("Running engagement cycle only.")
        if not self.engagement_bot or not self.youtube_uploader:
            logger.error("EngagementBot or YouTubeUploader not initialized. Cannot run engagement.")
            return
            
        try:
            self.engagement_bot.run_engagement_cycle(self.youtube_uploader)
            logger.info("Engagement cycle completed.")
        except Exception as e:
            logger.error(f"Failed during engagement cycle: {e}")

    def run_analytics_only(self):
        """Collect all analytics, generate and print report."""
        logger.info("Running analytics only.")
        if not self.analytics_engine:
            logger.error("AnalyticsEngine not initialized.")
            return
            
        try:
            data = self.analytics_engine.collect_recent_data()
            report = self.analytics_engine.generate_report(data)
            print("\n" + "="*50 + "\nANALYTICS REPORT\n" + "="*50)
            print(report)
        except Exception as e:
            logger.error(f"Failed during analytics collection: {e}")

    def _can_upload_now(self) -> (bool, str):
        """
        Smart cooldown and frequency manager:
        - Reads upload_frequency from config (e.g. 3 shorts/day).
        - Enforces minimum 3.0 hour cooldown between uploads so YouTube's algorithm
          gives each Short maximum distribution without cannibalizing views.
        - Returns (True, "") if ready to post, or (False, reason) if in cooldown/limit.
        """
        history_file = "data/upload_history.json"
        now = time.time()
        max_daily = self.config.get('content', {}).get('upload_frequency', 3)
        min_cooldown_hours = 3.0
        
        if not os.path.exists(history_file):
            return True, ""
            
        try:
            with open(history_file, 'r', encoding='utf-8') as f:
                history = json.load(f)
        except Exception:
            history = []
            
        today_str = datetime.now().strftime("%Y-%m-%d")
        today_uploads = [t for t in history if t.get('date') == today_str]
        
        if len(today_uploads) >= max_daily:
            return False, f"Daily limit reached ({len(today_uploads)}/{max_daily} posted today)."
            
        if history:
            last_timestamp = history[-1].get('timestamp', 0)
            elapsed_hours = (now - last_timestamp) / 3600.0
            if elapsed_hours < min_cooldown_hours:
                rem_mins = int((min_cooldown_hours - elapsed_hours) * 60)
                return False, f"Cooldown active: posted {elapsed_hours:.1f}h ago. Next post in ~{rem_mins} mins."
                
        return True, ""

    def _record_upload_success(self, video_title: str):
        history_file = "data/upload_history.json"
        os.makedirs("data", exist_ok=True)
        now = time.time()
        today_str = datetime.now().strftime("%Y-%m-%d")
        
        history = []
        if os.path.exists(history_file):
            try:
                with open(history_file, 'r', encoding='utf-8') as f:
                    history = json.load(f)
            except Exception:
                history = []
                
        history.append({
            'timestamp': now,
            'date': today_str,
            'title': video_title,
            'time_str': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
        
        history = history[-50:]
        try:
            with open(history_file, 'w', encoding='utf-8') as f:
                json.dump(history, f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to record upload history: {e}")

    def run(self, dry_run=False, mode=None, force=False) -> Dict[str, Any]:
        """
        Full pipeline execution.
        Returns summary dict.
        """
        # Guard: Smart frequency and cooldown check (bypassed with --force or --dry-run)
        if not dry_run and not force:
            can_post, reason = self._can_upload_now()
            if not can_post:
                logger.info(f"⏳ Auto-run skipped: {reason}")
                return {"status": "skipped", "message": reason}

        logger.info(f"Starting pipeline. mode={mode}, dry_run={dry_run}, force={force}")
        summary = {
            'timestamp': datetime.now().isoformat(),
            'success': False,
            'mode': mode,
            'dry_run': dry_run,
            'platforms': {},
            'errors': []
        }
        
        temp_files = []

        try:
            # 1. Analytics & AI Post-Mortem Diagnosis
            feedback = ""
            strategy = "original"
            try:
                if self.analytics_engine:
                    logger.info("Running AI Post-Mortem diagnosis on previous uploads...")
                    feedback = self.analytics_engine.diagnose_previous_shorts(
                        self.youtube_uploader, 
                        self.content_generator
                    )
                    timing_info = self.analytics_engine.get_optimal_posting_hour()
                    logger.info(f"Audience Timing Recommendation: {timing_info.get('recommendation')}")
                    logger.info(f"AI Feedback & Mandatory Fixes for next Short:\n{feedback[:250]}...")
                    
                    strat_dict = self.analytics_engine.get_best_content_strategy()
                    strategy = strat_dict.get('content_mode', 'original')
            except Exception as e:
                logger.warning(f"Analytics & Diagnosis step failed: {e}")

            # 2. Decide mode (Always prioritize 'clips' as configured)
            configured_mode = self.config.get('content', {}).get('mode', 'clips')
            actual_mode = mode or configured_mode or 'clips'
            summary['mode'] = actual_mode
            logger.info(f"Selected mode: {actual_mode}")

            # 3. Content generation
            script = {}
            background = None
            audio_path = None
            human_clips = {}
            music_path = None
            
            try:
                if actual_mode == 'clips':
                    if not self.clip_curator or not self.commentary_engine:
                        raise ValueError("Clip components missing.")
                    clip = self.clip_curator.get_best_clip()
                    commentary = self.commentary_engine.generate_commentary(clip, self.content_generator)
                    script = self.commentary_engine.build_video_script(clip, commentary)
                    background = clip.get('local_path')
                elif actual_mode in ['story', 'story_universe']:
                    if not self.story_universe_engine:
                        raise ValueError("StoryUniverseEngine missing.")
                    logger.info("🎬 Generating next daily movie chapter from Story Universe...")
                    ep = self.story_universe_engine.generate_next_episode()
                    if not ep or not ep.get('narration'):
                        raise ValueError("StoryUniverseEngine failed to generate episode.")
                    script = ep
                    script['title'] = ep.get('youtube_title', 'Movie Episode')
                    script['top_banner_text'] = ep.get('top_banner_text', f"PART 0{ep.get('part', 1)}")
                    
                    if self.stock_fetcher:
                        queries = ep.get('visual_queries', ['dark cinematic mystery'])
                        bg_query = queries[0] if queries else 'dark cinematic mystery'
                        logger.info(f"Fetching cinematic atmospheric background for: '{bg_query}'...")
                        background = self.stock_fetcher.get_background_video(bg_query)
                else:
                    if not self.content_generator:
                        raise ValueError("ContentGenerator missing.")
                    pick = random.choice(['fun_fact', 'reddit_story'])
                    if pick == 'fun_fact':
                        script = self.content_generator.generate_fun_fact_script(performance_feedback=feedback)
                    else:
                        script = self.content_generator.generate_reddit_story_script(performance_feedback=feedback)
                    
                    if self.stock_fetcher:
                        search_term = script.get('pexels_search_term', 'nature')
                        background = self.stock_fetcher.get_background_video(search_term)
            except Exception as e:
                logger.error(f"Content generation failed: {e}")
                summary['errors'].append(f"Content: {e}")
                raise

            # 4. TTS with Voice Selection (Mood-Matched for clips and story movie, Tournament for others)
            selected_voice_config = None
            voice_name = "Default"
            try:
                if self.tts_engine:
                    if actual_mode in ['clips', 'story', 'story_universe']:
                        short_mood = script.get('mood', 'dramatic')
                        selected_voice_config = self.tts_engine.select_voice_for_mood(short_mood)
                    else:
                        selected_voice_config = self.tts_engine.select_tournament_voice(self.analytics_engine)
                    voice_name = selected_voice_config.get('name', 'Default')
                    logger.info(f"🎤 Voice matched to Short: {voice_name} ({selected_voice_config.get('voice')})")
                    voiceover_dest = f"output/voiceover_{int(time.time())}.mp3"
                    audio_path = self.tts_engine.generate_speech_sync(
                        script.get('narration', ''), 
                        voiceover_dest,
                        voice_config=selected_voice_config
                    )
                    if audio_path:
                        temp_files.append(audio_path)
            except Exception as e:
                logger.warning(f"TTS failed: {e}")

            # 5. Music
            try:
                if self.music_manager:
                    music_path = self.music_manager.select_track(script.get('mood', 'neutral'))
            except Exception as e:
                logger.warning(f"Music failed: {e}")

            # 6. Human clips
            try:
                if self.human_clip_mixer and self.human_clip_mixer.clips_available():
                    seed = int(time.time())
                    human_clips = {
                        'intro': self.human_clip_mixer.get_intro_clip(seed),
                        'reaction': self.human_clip_mixer.get_reaction_clip(seed),
                        'outro': self.human_clip_mixer.get_outro_clip(seed)
                    }
            except Exception as e:
                logger.warning(f"Human clips failed: {e}")

            # 7. Video Engine
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            video_output_path = f"output/short_{timestamp}.mp4"
            
            try:
                if not self.video_engine:
                    raise ValueError("VideoEngine missing.")
                video_path = self.video_engine.create_video(
                    script=script,
                    audio_path=audio_path,
                    background_path=background,
                    human_clips=human_clips,
                    music_path=music_path,
                    output_path=video_output_path
                )
                summary['video_path'] = video_path
            except Exception as e:
                logger.error(f"Video creation failed: {e}")
                summary['errors'].append(f"Video: {e}")
                raise

            # 8. Uploading & 9. Engagement
            if not dry_run:
                desc_text = self._build_description(script)
                
                # YouTube
                try:
                    if self.youtube_uploader:
                        yt_id = self.youtube_uploader.upload_short(
                            video_path,
                            script.get('title', 'Short')[:100],
                            desc_text,
                            script.get('tags', [])
                        )
                        if yt_id:
                            summary['platforms']['youtube'] = yt_id
                            # Immediately record upload so cooldown and daily limits are strictly enforced!
                            self._record_upload_success(script.get('title', 'Short'))
                            
                            try:
                                if script.get('pinned_comment'):
                                    self.youtube_uploader.post_comment(yt_id, script['pinned_comment'])
                                if self.engagement_bot:
                                    self.engagement_bot.run_engagement_cycle(
                                        self.youtube_uploader, 
                                        video_id=yt_id, 
                                        video_title=script.get('title', 'Short')
                                    )
                            except Exception as e:
                                logger.warning(f"Engagement bot error: {e}")
                        else:
                            logger.error("YouTube upload returned None (authentication expired or upload failed).")
                            summary['errors'].append("YouTube: Authentication expired or upload failed")
                except Exception as e:
                    logger.error(f"YouTube upload failed: {e}")
                    summary['errors'].append(f"YouTube: {e}")

                # X (Twitter) - only if configured
                if self.config.get('platforms', {}).get('x_twitter', {}).get('api_key') != "YOUR_X_API_KEY":
                    try:
                        if self.x_poster:
                            x_title = script.get('title', 'Short')[:200]
                            tweet_id = self.x_poster.post_video(video_path, x_title)
                            summary['platforms']['x'] = tweet_id
                    except Exception as e:
                        logger.error(f"X upload failed: {e}")

                # Facebook - only if configured
                if self.config.get('platforms', {}).get('facebook', {}).get('page_id') != "YOUR_PAGE_ID":
                    try:
                        if self.facebook_poster:
                            fb_id = self.facebook_poster.post_reel(video_path, desc_text)
                            summary['platforms']['facebook'] = fb_id
                    except Exception as e:
                        logger.error(f"Facebook upload failed: {e}")

            # 10. Log to analytics
            try:
                if self.analytics_engine and not dry_run and summary.get('platforms', {}).get('youtube'):
                    self.analytics_engine.log_upload(
                        platform="youtube",
                        content_id=summary['platforms']['youtube'],
                        metadata={
                            "title": script.get('title'),
                            "topic": script.get('pexels_search_term'),
                            "duration": getattr(self.video_engine, 'duration', 45),
                            "tags": script.get('tags', []),
                            "voice_name": voice_name
                        }
                    )
            except Exception as e:
                logger.warning(f"Analytics logging failed: {e}")

            summary['success'] = len(summary['errors']) == 0
            
        except Exception as e:
            logger.error(f"Pipeline failed critically: {e}")
            logger.error(traceback.format_exc())
            summary['errors'].append(f"Critical error: {e}")
            
        finally:
            # 11. Cleanup temp files
            self._cleanup(temp_files)
            if dry_run and 'video_path' in summary:
                logger.info(f"Dry run complete. Generated video kept at {summary.get('video_path')}")

        return summary

def main():
    parser = argparse.ArgumentParser(description="YouTube Shorts Automation Bot Orchestrator")
    parser.add_argument('--dry-run', action='store_true', help="Run the entire pipeline without actually uploading the video to any platforms.")
    parser.add_argument('--force', action='store_true', help="Bypass cooldown and upload immediately.")
    parser.add_argument('--mode', choices=['clips', 'original', 'story_universe', 'story'], help="Force a specific content generation mode.")
    parser.add_argument('--engage-only', action='store_true', help="Run only the engagement bot.")
    parser.add_argument('--analytics-only', action='store_true', help="Run analytics, collect recent data, and print a comprehensive report.")
    parser.add_argument('--report', action='store_true', help="Alias for --analytics-only.")
    parser.add_argument('--test-clips', action='store_true', help="Shorthand for running pipeline in clips mode with dry-run on.")
    
    args = parser.parse_args()

    # Initialize bot pipeline
    bot = ShortsBotPipeline()

    if args.engage_only:
        bot.run_engagement_only()
    elif args.analytics_only or args.report:
        bot.run_analytics_only()
    elif args.test_clips:
        result = bot.run(dry_run=True, mode='clips', force=True)
        logger.info(f"Test result: {result}")
    else:
        result = bot.run(dry_run=args.dry_run, mode=args.mode, force=args.force)
        logger.info(f"Pipeline execution finished. Summary: {result}")

if __name__ == '__main__':
    main()
