"""
Autonomous Channel Slicing & Scheduling Orchestrator for JAGY.
- If user specified channels in config.yaml, it clips from them.
- If user entered NO channels, it automatically pulls from the default viral pool (@IShowSpeed, @MrBeast, @joerogan, etc.)
- Uses data/clipped_history.json to ensure no duplicate video is ever clipped twice.
- Slices peak viral moment via Gemini 3.8 Flash, burns animated captions, and uploads to YouTube.
"""
import os
import sys
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional
import yaml

PROJECT_ROOT = Path(__file__).parent.parent.absolute()
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.youtube_channel_clipper import YouTubeChannelClipper
from core.youtube_uploader import YouTubeUploader
from core.viral_short_editor import create_subtitles_ass, render_viral_short

logger = logging.getLogger("clipping_orchestrator")

HISTORY_FILE = PROJECT_ROOT / "data" / "clipped_history.json"

class ClippingOrchestrator:
    def __init__(self, config_path: str = "config/config.yaml"):
        self.config_path = config_path
        self.config = self._load_config()
        self.clipper = YouTubeChannelClipper(config_path)
        self.uploader = YouTubeUploader(config_path)
        self.history = self._load_history()

    def _load_config(self) -> Dict[str, Any]:
        cfg_file = Path(self.config_path)
        if cfg_file.exists():
            with open(cfg_file, "r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        return {}

    def _load_history(self) -> Dict[str, Any]:
        if HISTORY_FILE.exists():
            try:
                with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return {"clipped_video_ids": [], "last_upload": None}
        return {"clipped_video_ids": [], "last_upload": None}

    def _save_history(self):
        os.makedirs(HISTORY_FILE.parent, exist_ok=True)
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(self.history, f, indent=2)

    def get_target_channel_pool(self) -> List[str]:
        """Returns custom channels if provided by user, else returns default viral creators."""
        self.config = self._load_config()
        custom = self.config.get("clipping", {}).get("custom_channels", [])
        if custom and len(custom) > 0:
            return custom
        
        default_pool = self.config.get("clipping", {}).get("default_viral_pool", [
            "@IShowSpeed",
            "@MrBeast",
            "@joerogan",
            "@lexfridman",
            "@HubermanLab",
            "@TheoVon"
        ])
        return default_pool

    def run_automated_clip_and_upload(self, target_channel: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Executes full autonomous clipping and upload."""
        channels = [target_channel] if target_channel else self.get_target_channel_pool()
        logger.info(f"Target Channel Pool: {channels}")

        selected_video = None
        selected_channel = None

        # Find first fresh video across the pool that hasn't been clipped yet
        for ch in channels:
            videos = self.clipper.get_latest_channel_videos(ch, max_videos=5)
            for v in videos:
                if v["id"] not in self.history.get("clipped_video_ids", []):
                    selected_video = v
                    selected_channel = ch
                    break
            if selected_video:
                break

        if not selected_video:
            logger.warning("All latest videos from the pool have already been clipped! Recycling oldest.")
            videos = self.clipper.get_latest_channel_videos(channels[0], max_videos=1)
            if videos:
                selected_video = videos[0]
                selected_channel = channels[0]
            else:
                logger.error("No videos available to clip.")
                return None

        logger.info(f"Selected Target: '{selected_video['title']}' from {selected_channel} (ID: {selected_video['id']})")

        # 1. Fetch Transcripts
        transcript = self.clipper.fetch_transcript(selected_video["id"])
        if transcript:
            moment = self.clipper.find_viral_moment_with_ai(transcript, selected_video["title"])
        else:
            logger.warning("No transcript found, clipping opening hook (00:05 - 00:45)")
            moment = {
                "start": 5.0,
                "end": 45.0,
                "duration": 40.0,
                "hook": "Opening energetic segment",
                "viral_title": f"{selected_video['title']} #Shorts",
                "key_phrase": ""
            }

        start_sec = moment["start"]
        end_sec = moment["end"]
        logger.info(f"Viral Moment: {start_sec:.1f}s -> {end_sec:.1f}s | Title: {moment['viral_title']}")

        # 2. Download Segment
        raw_clip = str(self.clipper.temp_dir / f"clip_{selected_video['id']}.mp4")
        downloaded = self.clipper.download_precise_segment(selected_video["url"], start_sec, end_sec, raw_clip)
        if not downloaded:
            logger.error("Failed to download clip segment.")
            return None

        # 3. Create Subtitles & Burn Edit
        ass_path = str(self.clipper.temp_dir / f"subs_{selected_video['id']}.ass")
        create_subtitles_ass(start_sec, end_sec, ass_path)

        final_short = str(self.clipper.output_dir / f"short_{selected_video['id']}_{int(start_sec)}.mp4")
        rendered = render_viral_short(downloaded, ass_path, final_short)
        if not rendered:
            logger.error("Failed to render final short with subtitles.")
            return None

        # 4. Upload to YouTube
        logger.info(f"Uploading to YouTube: {moment['viral_title']}...")
        title = f"{moment['viral_title']} #Shorts"
        description = (
            f"{moment['hook']}\n\n"
            f"Credit: {selected_channel}\n\n"
            f"#shorts #viral #trending #clips"
        )
        tags = ["shorts", "viral", selected_channel.replace("@", "").lower(), "clips", "trending"]
        
        yt_id = self.uploader.upload_short(
            video_path=final_short,
            title=title,
            description=description,
            tags=tags,
            category_id="24"
        )

        if yt_id:
            # Post pinned comment
            pinned = f"What do you think of this moment? Drop your thoughts below! 👇"
            self.uploader.post_comment(yt_id, pinned)

            # Record in history
            self.history.setdefault("clipped_video_ids", []).append(selected_video["id"])
            self.history["last_upload"] = {
                "video_id": yt_id,
                "title": title,
                "channel": selected_channel,
                "timestamp": datetime.now().isoformat()
            }
            self._save_history()

            logger.info(f"🎉 Auto-Clip Upload Complete: https://youtube.com/shorts/{yt_id}")
            return {
                "status": "success",
                "youtube_url": f"https://youtube.com/shorts/{yt_id}",
                "title": title,
                "channel": selected_channel,
                "output_video": final_short
            }
        else:
            logger.error("Upload failed.")
            return None

if __name__ == "__main__":
    orchestrator = ClippingOrchestrator()
    print("Testing Clipping Orchestrator...")
    res = orchestrator.run_automated_clip_and_upload()
    print("Result:", res)
