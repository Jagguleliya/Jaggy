import json
import logging
import os
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from collections import defaultdict
import yaml

try:
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
except ImportError:
    Credentials = None
    build = None

logger = logging.getLogger(__name__)

class AnalyticsEngine:
    """
    AnalyticsEngine serves as the self-improving brain for the YouTube Shorts bot.
    It collects and analyzes performance data across platforms to optimize content strategy.
    """

    def __init__(self, config_path: str = "config/config.yaml") -> None:
        """
        Initializes the AnalyticsEngine.

        Args:
            config_path (str): Path to the YAML configuration file.
        """
        self.config_path = config_path
        self.config = self._load_config(config_path)
        
        # Determine the path for the performance log
        self.log_path = self.config.get("analytics", {}).get("performance_log_path", "performance_log.json")
        self.log_path = os.path.abspath(self.log_path)
        self.performance_log = self._load_performance_log()

    def _load_config(self, path: str) -> Dict[str, Any]:
        """Loads configuration from YAML file."""
        if os.path.exists(path):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    return yaml.safe_load(f) or {}
            except Exception as e:
                logger.error(f"Failed to load config from {path}: {e}")
        return {}

    def _load_performance_log(self) -> List[Dict[str, Any]]:
        """Loads the performance log from JSON file."""
        if os.path.exists(self.log_path):
            try:
                with open(self.log_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Failed to load performance log from {self.log_path}: {e}")
        return []

    def _save_performance_log(self) -> None:
        """Saves the performance log to JSON file."""
        os.makedirs(os.path.dirname(self.log_path) or '.', exist_ok=True)
        try:
            with open(self.log_path, 'w', encoding='utf-8') as f:
                json.dump(self.performance_log, f, indent=4)
        except Exception as e:
            logger.error(f"Failed to save performance log to {self.log_path}: {e}")

    def log_upload(self, platform: str, content_id: str, metadata: Dict[str, Any]) -> None:
        """
        Logs a new upload with its initial metadata.

        Args:
            platform (str): Platform name (e.g., 'youtube', 'x', 'facebook').
            content_id (str): ID of the uploaded content.
            metadata (Dict[str, Any]): Additional metadata (topic, niche, hook_style, etc.).
        """
        entry = {
            "platform": platform,
            "video_id": content_id,
            "topic": metadata.get("topic", "Unknown"),
            "niche": metadata.get("niche", "Unknown"),
            "hook_style": metadata.get("hook_style", "Unknown"),
            "duration": metadata.get("duration", 0),
            "style_name": metadata.get("style_name", "Unknown"),
            "voice_name": metadata.get("voice_name", "Unknown"),
            "upload_timestamp": metadata.get("upload_timestamp", datetime.utcnow().isoformat()),
            "tags": metadata.get("tags", []),
            "metrics": {
                "views": 0,
                "likes": 0,
                "comments": 0,
                "shares": 0,
                "retention_pct": metadata.get("retention_pct", 50.0),
                "view_velocity": 0.0,
                "engagement_rate": 0.0
            },
            "score": 0.0
        }
        
        # Store alternative platform IDs if provided
        if "x_tweet_id" in metadata:
            entry["x_tweet_id"] = metadata["x_tweet_id"]
        if "fb_post_id" in metadata:
            entry["fb_post_id"] = metadata["fb_post_id"]

        self.performance_log.append(entry)
        self._save_performance_log()
        logger.info(f"Logged new upload: {content_id} on {platform} (Voice: {metadata.get('voice_name', 'Default')})")

    def get_voice_rankings(self) -> Dict[str, Any]:
        """Calculates performance scores, total views, and sample count for each voice tested."""
        voice_stats = defaultdict(list)
        for entry in self.performance_log:
            v_name = entry.get("voice_name", "Unknown")
            if v_name and v_name != "Unknown":
                score = entry.get("score", 0.0)
                views = entry.get("metrics", {}).get("views", 0)
                voice_stats[v_name].append({"score": score, "views": views})

        rankings = {}
        for v_name, records in voice_stats.items():
            avg_score = sum(r["score"] for r in records) / len(records) if records else 0
            total_views = sum(r["views"] for r in records)
            rankings[v_name] = {
                "tests": len(records),
                "avg_score": round(avg_score, 2),
                "total_views": total_views
            }
        return rankings

    def _get_hours_since_upload(self, upload_timestamp: str) -> float:
        """Calculates hours since the given upload timestamp."""
        try:
            upload_time = datetime.fromisoformat(upload_timestamp)
            delta = datetime.utcnow() - upload_time
            return delta.total_seconds() / 3600.0
        except Exception as e:
            logger.warning(f"Error parsing timestamp {upload_timestamp}: {e}")
            return 1.0

    def collect_youtube_analytics(self, youtube_uploader: Any, video_ids: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """
        Collects analytics for YouTube videos from the performance log.

        Args:
            youtube_uploader: Uploader instance with get_video_stats method.
            video_ids: Optional list of specific video IDs to update.

        Returns:
            List of updated entries.
        """
        if youtube_uploader is None:
            logger.warning("No YouTube uploader provided for analytics collection.")
            return []

        updated_entries = []
        for entry in self.performance_log:
            if entry.get("platform") != "youtube":
                continue
                
            vid = entry.get("video_id")
            if video_ids and vid not in video_ids:
                continue

            try:
                stats = youtube_uploader.get_video_stats(vid)
                views = stats.get("views", 0)
                likes = stats.get("likes", 0)
                comments = stats.get("comments", 0)
                
                metrics = entry["metrics"]
                metrics["views"] = views
                metrics["likes"] = likes
                metrics["comments"] = comments

                hours_since = self._get_hours_since_upload(entry.get("upload_timestamp", ""))
                metrics["view_velocity"] = views / max(hours_since, 1.0)
                metrics["engagement_rate"] = (likes + comments) / max(views, 1)

                entry["score"] = self.calculate_score(metrics)
                updated_entries.append(entry)
                
            except Exception as e:
                logger.error(f"Error fetching YouTube stats for {vid}: {e}")

        self._save_performance_log()
        return updated_entries

    def collect_x_analytics(self, x_poster: Any, tweet_ids: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """Collects analytics for X (Twitter) posts."""
        if x_poster is None:
            return []
            
        updated_entries = []
        for entry in self.performance_log:
            tweet_id = entry.get("x_tweet_id")
            if not tweet_id:
                continue
                
            if tweet_ids and tweet_id not in tweet_ids:
                continue

            try:
                stats = x_poster.get_tweet_metrics(tweet_id)
                entry["metrics"]["views"] = stats.get("views", entry["metrics"]["views"])
                entry["metrics"]["likes"] = stats.get("likes", entry["metrics"]["likes"])
                entry["metrics"]["comments"] = stats.get("comments", entry["metrics"]["comments"])
                
                hours_since = self._get_hours_since_upload(entry.get("upload_timestamp", ""))
                entry["metrics"]["view_velocity"] = entry["metrics"]["views"] / max(hours_since, 1.0)
                entry["metrics"]["engagement_rate"] = (entry["metrics"]["likes"] + entry["metrics"]["comments"]) / max(entry["metrics"]["views"], 1)
                
                entry["score"] = self.calculate_score(entry["metrics"])
                updated_entries.append(entry)
            except Exception as e:
                logger.error(f"Error fetching X stats for {tweet_id}: {e}")

        self._save_performance_log()
        return updated_entries

    def collect_facebook_analytics(self, fb_poster: Any, post_ids: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """Collects analytics for Facebook posts."""
        if fb_poster is None:
            return []
            
        updated_entries = []
        for entry in self.performance_log:
            post_id = entry.get("fb_post_id")
            if not post_id:
                continue
                
            if post_ids and post_id not in post_ids:
                continue

            try:
                stats = fb_poster.get_post_metrics(post_id)
                entry["metrics"]["views"] = stats.get("views", entry["metrics"]["views"])
                entry["metrics"]["likes"] = stats.get("likes", entry["metrics"]["likes"])
                entry["metrics"]["comments"] = stats.get("comments", entry["metrics"]["comments"])
                
                hours_since = self._get_hours_since_upload(entry.get("upload_timestamp", ""))
                entry["metrics"]["view_velocity"] = entry["metrics"]["views"] / max(hours_since, 1.0)
                entry["metrics"]["engagement_rate"] = (entry["metrics"]["likes"] + entry["metrics"]["comments"]) / max(entry["metrics"]["views"], 1)
                
                entry["score"] = self.calculate_score(entry["metrics"])
                updated_entries.append(entry)
            except Exception as e:
                logger.error(f"Error fetching FB stats for {post_id}: {e}")

        self._save_performance_log()
        return updated_entries

    def _get_average_velocity(self) -> float:
        """Calculates average view_velocity across all entries."""
        if not self.performance_log:
            return 0.0
        total_velocity = sum(entry.get("metrics", {}).get("view_velocity", 0.0) for entry in self.performance_log)
        return total_velocity / len(self.performance_log)

    def calculate_score(self, metrics: Dict[str, float]) -> float:
        """
        Calculates a performance score based on retention, velocity, and engagement.
        """
        retention = metrics.get('retention_pct', 50.0)
        velocity = metrics.get('view_velocity', 0.0)
        engagement = metrics.get('engagement_rate', 0.0)
        
        avg_velocity = self._get_average_velocity()
        norm_velocity = (velocity / max(avg_velocity, 0.01)) * 100.0
        
        score = (retention * 0.50) + (min(norm_velocity, 200) * 0.30) + (min(engagement * 1000, 200) * 0.20)
        return round(score, 2)

    def _get_duration_bucket(self, duration: float) -> str:
        """Categorizes duration into buckets."""
        if duration < 40:
            return "short (<40s)"
        elif duration <= 50:
            return "medium (40-50s)"
        else:
            return "long (>50s)"

    def diagnose_previous_shorts(self, youtube_uploader: Any, content_gen: Any) -> str:
        """
        Pulls recent upload performance from YouTube API, performs an AI post-mortem diagnosis 
        using Gemini to figure out WHY videos succeeded or failed, and gives mandatory fixes.
        """
        if not self.performance_log:
            return "No previous shorts recorded yet. Focus on explosive 1-second hook, fast witty pacing, and curiosity loop."

        # Step 1: Update stats from YouTube for recent videos
        self.collect_youtube_analytics(youtube_uploader)

        # Step 2: Grab the last 3-5 videos
        recent_videos = self.performance_log[-5:]
        summary_stats = []
        for v in recent_videos:
            metrics = v.get("metrics", {})
            summary_stats.append({
                "video_id": v.get("video_id"),
                "topic": v.get("topic"),
                "duration": v.get("duration"),
                "views": metrics.get("views", 0),
                "likes": metrics.get("likes", 0),
                "comments": metrics.get("comments", 0),
                "view_velocity": round(metrics.get("view_velocity", 0), 2)
            })

        # Step 3: Ask Gemini to diagnose performance
        if content_gen and content_gen.client:
            prompt = f"""You are a master YouTube Shorts growth strategist. 
Analyze the performance of our recent YouTube Shorts:
{json.dumps(summary_stats, indent=2)}

Perform a ruthless post-mortem diagnosis:
1. Identify the likely reasons why underperforming videos didn't get enough views/subscribers (e.g. hook too slow, topic not controversial/curious enough, weak retention).
2. Highlight what worked in any higher-performing video.
3. Provide 3 MANDATORY RULES for the NEXT Short script to guarantee higher retention, more shares, and subscribers from US/UK viewers.

Format as concise, powerful bullet points."""
            try:
                diagnosis = content_gen.client.models.generate_content(
                    model=content_gen.model_name,
                    contents=prompt
                )
                if diagnosis.text:
                    logger.info("AI Post-Mortem Diagnosis generated successfully.")
                    return diagnosis.text.strip()
            except Exception as e:
                logger.warning(f"Failed to generate AI diagnosis: {e}")

        return self.get_performance_feedback()

    def get_optimal_posting_hour(self) -> Dict[str, Any]:
        """
        Determines the best hour to post for peak audience engagement.
        Calculates historical view velocity by upload hour, or targets peak US viewer windows.
        """
        # Peak US viewing hours in IST (India Standard Time):
        # 1. US Prime Evening (7 PM - 10 PM EST) = 4:30 AM - 7:30 AM IST
        # 2. US Lunchtime (12 PM - 2 PM EST) = 9:30 PM - 11:30 PM IST
        default_best_windows = [
            {"label": "US Evening Peak", "ist_window": "05:00 - 07:30 IST", "hour_start": 5, "hour_end": 7},
            {"label": "US Lunch Peak", "ist_window": "21:30 - 23:30 IST", "hour_start": 21, "hour_end": 23}
        ]

        if len(self.performance_log) < 5:
            return {
                "recommendation": "Target US Prime Scrolling Windows",
                "best_windows": default_best_windows,
                "current_best": "05:30 IST (Morning in India = US Evening)",
                "data_points": len(self.performance_log)
            }

        # Group performance by hour of upload
        hour_scores = defaultdict(list)
        for entry in self.performance_log:
            try:
                dt = datetime.fromisoformat(entry.get("upload_timestamp", ""))
                velocity = entry.get("metrics", {}).get("view_velocity", 0.0)
                hour_scores[dt.hour].append(velocity)
            except Exception:
                continue

        if hour_scores:
            avg_by_hour = {h: sum(v)/len(v) for h, v in hour_scores.items()}
            best_hour = max(avg_by_hour.items(), key=lambda x: x[1])[0]
            return {
                "recommendation": f"Upload at {best_hour:02d}:00 IST (Highest historical view velocity: {avg_by_hour[best_hour]:.1f} views/hr)",
                "best_windows": default_best_windows,
                "current_best": f"{best_hour:02d}:00 IST",
                "data_points": len(self.performance_log)
            }

        return {
            "recommendation": "Target US Prime Scrolling Windows",
            "best_windows": default_best_windows,
            "current_best": "05:30 IST",
            "data_points": len(self.performance_log)
        }

    def get_performance_feedback(self, top_n: int = 3, bottom_n: int = 3) -> str:
        """
        Analyzes patterns and generates actionable feedback.
        """
        if not self.performance_log:
            return "No data available yet."

        topics = defaultdict(list)
        styles = defaultdict(list)
        durations = defaultdict(list)

        for entry in self.performance_log:
            score = entry.get("score", 0.0)
            topics[entry.get("topic", "Unknown")].append(score)
            styles[entry.get("style_name", "Unknown")].append(score)
            
            bucket = self._get_duration_bucket(entry.get("duration", 0))
            durations[bucket].append(score)

        avg_topics = {k: sum(v)/len(v) for k, v in topics.items()}
        sorted_topics = sorted(avg_topics.items(), key=lambda x: x[1], reverse=True)
        
        avg_styles = {k: sum(v)/len(v) for k, v in styles.items()}
        sorted_styles = sorted(avg_styles.items(), key=lambda x: x[1], reverse=True)

        avg_durations = {k: sum(v)/len(v) for k, v in durations.items()}
        sorted_durations = sorted(avg_durations.items(), key=lambda x: x[1], reverse=True)

        top_themes = [f"[{t[0]}: avg score {t[1]:.2f}, {len(topics[t[0]])} videos]" for t in sorted_topics[:top_n]]
        bottom_themes = [f"[{t[0]}: avg score {t[1]:.2f}]" for t in sorted_topics[-bottom_n:]]

        best_style = sorted_styles[0][0] if sorted_styles else "Unknown"
        best_duration = sorted_durations[0][0] if sorted_durations else "Unknown"

        feedback = (
            f"Top performing themes on this channel: {', '.join(top_themes)}.\n"
            f"Underperforming themes to avoid: {', '.join(bottom_themes)}.\n"
            f"Best performing style: {best_style}.\n"
            f"Optimal video duration: {best_duration}.\n"
            "Emulate: strong hook in first 3 seconds, surprising facts."
        )
        return feedback

    def get_best_content_strategy(self) -> Dict[str, Any]:
        """
        Returns the best content strategy based on analytics data.
        """
        if len(self.performance_log) < 10:
            return {
                "content_mode": "clips",
                "topic_weights": {"general": 1.0},
                "style_preference": "dynamic",
                "optimal_duration": "40-50s"
            }

        topics = defaultdict(list)
        styles = defaultdict(list)
        durations = defaultdict(list)

        for entry in self.performance_log:
            score = entry.get("score", 0.0)
            topics[entry.get("topic", "Unknown")].append(score)
            styles[entry.get("style_name", "Unknown")].append(score)
            durations[self._get_duration_bucket(entry.get("duration", 0))].append(score)

        avg_topics = {k: sum(v)/len(v) for k, v in topics.items()}
        total_topic_score = sum(avg_topics.values())
        topic_weights = {k: (v/total_topic_score if total_topic_score > 0 else 0) for k, v in avg_topics.items()}
        
        avg_styles = {k: sum(v)/len(v) for k, v in styles.items()}
        best_style = max(avg_styles.items(), key=lambda x: x[1])[0] if avg_styles else "dynamic"
        
        avg_durations = {k: sum(v)/len(v) for k, v in durations.items()}
        best_duration = max(avg_durations.items(), key=lambda x: x[1])[0] if avg_durations else "40-50s"

        return {
            "content_mode": "clips",
            "topic_weights": topic_weights,
            "style_preference": best_style,
            "optimal_duration": best_duration
        }

    def generate_weekly_report(self) -> str:
        """
        Generates a markdown report summarizing the week's performance.
        """
        one_week_ago = datetime.utcnow() - timedelta(days=7)
        recent_videos = []
        for entry in self.performance_log:
            try:
                dt = datetime.fromisoformat(entry.get("upload_timestamp", ""))
                if dt >= one_week_ago:
                    recent_videos.append(entry)
            except ValueError:
                pass

        total_videos = len(recent_videos)
        total_views = sum(e.get("metrics", {}).get("views", 0) for e in recent_videos)
        total_likes = sum(e.get("metrics", {}).get("likes", 0) for e in recent_videos)
        total_comments = sum(e.get("metrics", {}).get("comments", 0) for e in recent_videos)

        sorted_recent = sorted(recent_videos, key=lambda x: x.get("score", 0.0), reverse=True)
        top_performers = sorted_recent[:3]
        needs_improvement = sorted_recent[-3:] if total_videos > 3 else []

        # Compare avg score this week vs overall
        recent_avg_score = sum(e.get("score", 0.0) for e in recent_videos) / total_videos if total_videos > 0 else 0
        overall_avg_score = sum(e.get("score", 0.0) for e in self.performance_log) / len(self.performance_log) if self.performance_log else 0
        
        if recent_avg_score > overall_avg_score * 1.05:
            trend = "up"
        elif recent_avg_score < overall_avg_score * 0.95:
            trend = "down"
        else:
            trend = "stable"

        report = [
            "# Weekly Performance Report",
            "## Summary",
            f"- Total videos this week: {total_videos}",
            f"- Total views: {total_views} | Likes: {total_likes} | Comments: {total_comments}",
            "## Top Performers"
        ]
        for idx, p in enumerate(top_performers, 1):
            vid = p.get('video_id', 'Unknown')
            views = p.get('metrics', {}).get('views', 0)
            ret = p.get('metrics', {}).get('retention_pct', 0)
            score = p.get('score', 0)
            report.append(f"{idx}. [{vid}] - {views} views, {ret}% retention, score: {score}")

        if needs_improvement:
            report.append("## Needs Improvement")
            for idx, p in enumerate(needs_improvement, 1):
                vid = p.get('video_id', 'Unknown')
                views = p.get('metrics', {}).get('views', 0)
                score = p.get('score', 0)
                report.append(f"{idx}. [{vid}] - {views} views, score: {score}")

        strategy = self.get_best_content_strategy()
        top_topics = ", ".join(sorted(strategy.get("topic_weights", {}).keys(), key=lambda k: strategy["topic_weights"][k], reverse=True)[:3])

        report.extend([
            "## Trends",
            f"- Avg score trending: {trend}",
            "## Recommendations",
            f"- Focus on: [{top_topics}]",
            f"- Use style: [{strategy.get('style_preference', 'dynamic')}]",
            f"- Optimal duration: {strategy.get('optimal_duration', '40-50s')}"
        ])

        return "\n".join(report)

    def _get_youtube_analytics_service(self) -> Optional[Any]:
        """
        Tries to build the youtubeAnalytics v2 service using config/token.json.
        """
        if Credentials is None or build is None:
            logger.error("google-auth or google-api-python-client is not installed.")
            return None

        token_path = os.path.join(os.path.dirname(self.config_path), "token.json")
        if not os.path.exists(token_path):
            logger.warning(f"No token.json found at {token_path}.")
            return None

        try:
            creds = Credentials.from_authorized_user_file(token_path, ["https://www.googleapis.com/auth/yt-analytics.readonly"])
            service = build('youtubeAnalytics', 'v2', credentials=creds)
            return service
        except Exception as e:
            logger.error(f"Failed to build youtubeAnalytics service: {e}")
            return None

if __name__ == '__main__':
    # Test block
    logging.basicConfig(level=logging.INFO)
    engine = AnalyticsEngine()
    
    # Simulate adding data
    engine.log_upload("youtube", "test_video_1", {
        "topic": "space", "niche": "science", "hook_style": "question", "duration": 45, "style_name": "educational",
        "retention_pct": 65.0
    })
    
    # Simulate dummy uploader
    class DummyUploader:
        def get_video_stats(self, vid):
            return {"views": 1500, "likes": 120, "comments": 15}
    
    engine.collect_youtube_analytics(DummyUploader())
    print(engine.get_performance_feedback())
    print(engine.generate_weekly_report())
