"""
YouTube Channel Clipper & Viral Moment Extraction Engine.
Features:
- Scrapes target channel videos via yt-dlp
- Extracts timed transcripts
- Uses Gemini 3.8 Flash to pinpoint peak viral moments (20s - 55s)
- Downloads exact segment stream without downloading full multi-hour files
- Smart 9:16 vertical reframe with FFmpeg 7.1
- Exports both final Short MP4 and DaVinci Resolve Timeline FCPXML project
"""
import os
import sys
import json
import logging
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
import yaml
import yt_dlp
import imageio_ffmpeg
from youtube_transcript_api import YouTubeTranscriptApi
from google import genai
from google.genai import types
from core.builtin_keys import get_gemini_key

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("channel_clipper")

PROJECT_ROOT = Path(__file__).parent.parent.absolute()

class YouTubeChannelClipper:
    def __init__(self, config_path: str = "config/config.yaml"):
        # Put venv Scripts into PATH so ffmpeg.exe is found by yt-dlp
        venv_scripts = str(PROJECT_ROOT / "venv" / "Scripts")
        if venv_scripts not in os.environ.get("PATH", ""):
            os.environ["PATH"] = venv_scripts + os.pathsep + os.environ.get("PATH", "")

        self.config = self._load_config(config_path)
        self.ffmpeg_exe = str(PROJECT_ROOT / "venv" / "Scripts" / "ffmpeg.exe")
        self.output_dir = PROJECT_ROOT / "output"
        self.temp_dir = PROJECT_ROOT / "data" / "temp_clips"
        os.makedirs(self.output_dir, exist_ok=True)
        os.makedirs(self.temp_dir, exist_ok=True)

        # Init Gemini (new google.genai SDK — built-in key, no user setup needed)
        gemini_key = get_gemini_key(self.config)
        self.gemini_client = None
        self.gemini_models = ["gemini-3.8-flash", "gemini-3.5-flash-lite", "gemini-3.5-flash", "gemini-3.7-flash"]
        if gemini_key:
            self.gemini_client = genai.Client(
                api_key=gemini_key,
                http_options=types.HttpOptions(timeout=30_000)
            )

    def _load_config(self, path: str) -> Dict[str, Any]:
        cfg_file = Path(path)
        if cfg_file.exists():
            with open(cfg_file, "r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        return {}

    def get_latest_channel_videos(self, channel_url_or_handle: str, max_videos: int = 5) -> List[Dict[str, Any]]:
        """Fetch list of latest video IDs and metadata from target channel."""
        logger.info(f"Scanning target channel: {channel_url_or_handle}...")
        if not channel_url_or_handle.startswith("http"):
            if not channel_url_or_handle.startswith("@"):
                channel_url_or_handle = f"@{channel_url_or_handle}"
            url = f"https://www.youtube.com/{channel_url_or_handle}/videos"
        else:
            url = channel_url_or_handle

        ydl_opts = {
            'quiet': True,
            'extract_flat': True,
            'playlistend': max_videos
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            entries = info.get('entries', [])
            videos = []
            for entry in entries:
                if entry:
                    videos.append({
                        "id": entry.get("id"),
                        "title": entry.get("title"),
                        "duration": entry.get("duration", 0),
                        "url": f"https://www.youtube.com/watch?v={entry.get('id')}"
                    })
            return videos

    def fetch_transcript(self, video_id: str) -> Optional[List[Dict[str, Any]]]:
        """Fetch timed transcript items."""
        try:
            raw_transcript = YouTubeTranscriptApi().fetch(video_id)
            items = []
            for t in raw_transcript:
                start = getattr(t, 'start', getattr(t, 'start_time', 0.0))
                duration = getattr(t, 'duration', 2.0)
                text = getattr(t, 'text', '')
                items.append({
                    "start": float(start),
                    "duration": float(duration),
                    "text": text.strip()
                })
            return items
        except Exception as e:
            logger.warning(f"Could not fetch transcript via API for {video_id}: {e}")
            return None

    def find_viral_moment_with_ai(self, transcript_items: List[Dict[str, Any]], video_title: str) -> Dict[str, Any]:
        """Send timed transcript to Gemini AI to locate the best 25-50s viral moment."""
        logger.info(f"Analyzing transcript for viral moments in: '{video_title}'...")
        if not self.gemini_client:
            return {
                "start": 5.0,
                "end": 45.0,
                "duration": 40.0,
                "hook": "Opening highlight moment",
                "viral_title": video_title
            }

        lines = []
        for item in transcript_items[:300]:
            mins = int(item['start'] // 60)
            secs = int(item['start'] % 60)
            lines.append(f"[{mins:02d}:{secs:02d}] {item['text']}")
        transcript_text = "\n".join(lines)

        prompt = f"""You are an elite short-form video editor for MrBeast, IShowSpeed, and top YouTube creators.
Analyze the following timed transcript from the video titled "{video_title}".

Identify the SINGLE MOST VIRAL, FUNNY, CONTROVERSIAL, OR HIGH-ENERGY MOMENT for a YouTube Short (25 to 50 seconds long).
It must start with a punchy hook that grabs attention within the first 3 seconds, and end cleanly or on a climax/cliffhanger.

Transcript:
{transcript_text}

Respond STRICTLY in JSON format with no other text:
{{
  "start_seconds": <float starting timestamp>,
  "end_seconds": <float ending timestamp, duration between 25 and 50 seconds>,
  "hook_reason": "<1 sentence explanation of why this moment is viral>",
  "viral_title": "<Click-worthy high-CTR Title with emoji, max 60 chars>",
  "key_phrase": "<3-5 words shouted or emphasized in this clip for caption highlight>"
}}
"""
        # Try each model in fallback chain
        response_text = None
        for model_name in self.gemini_models:
            try:
                response = self.gemini_client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                    config=types.GenerateContentConfig(temperature=0.7, max_output_tokens=500)
                )
                if response and response.text:
                    response_text = response.text.strip()
                    break
            except Exception as e:
                logger.warning(f"Model {model_name} failed: {e}")
                continue

        if not response_text:
            return {
                "start": 5.0, "end": 45.0, "duration": 40.0,
                "hook": "Opening highlight moment", "viral_title": video_title
            }

        text = response_text
        if text.startswith("```json"):
            text = text[7:]
        if text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]

        try:
            result = json.loads(text.strip())
            start = float(result.get("start_seconds", 10.0))
            end = float(result.get("end_seconds", start + 35.0))
            if end - start < 15:
                end = start + 35
            return {
                "start": start,
                "end": end,
                "duration": round(end - start, 2),
                "hook": result.get("hook_reason", "High energy viral moment"),
                "viral_title": result.get("viral_title", video_title),
                "key_phrase": result.get("key_phrase", "")
            }
        except Exception as e:
            logger.error(f"Failed to parse Gemini viral moment JSON: {e}, text: {text}")
            return {
                "start": 5.0,
                "end": 45.0,
                "duration": 40.0,
                "hook": "Opening energetic segment",
                "viral_title": video_title,
                "key_phrase": ""
            }

    def download_precise_segment(self, video_url: str, start_sec: float, end_sec: float, output_path: str) -> Optional[str]:
        """Download exact segment via direct stream seek using FFmpeg + yt-dlp."""
        logger.info(f"Downloading stream segment {start_sec:.1f}s to {end_sec:.1f}s...")
        try:
            ydl_opts = {
                'quiet': True,
                'format': 'bestvideo[height<=1080]+bestaudio/best',
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(video_url, download=False)
                if 'requested_formats' in info and len(info['requested_formats']) > 1:
                    v_url = info['requested_formats'][0]['url']
                    a_url = info['requested_formats'][1]['url']
                elif 'url' in info:
                    v_url = info['url']
                    a_url = info['url']
                else:
                    v_url = info['formats'][-1]['url']
                    a_url = v_url

            out_mp4 = str(Path(output_path).with_suffix(".mp4"))
            cmd = [
                self.ffmpeg_exe, "-y",
                "-ss", str(start_sec), "-to", str(end_sec), "-i", v_url,
                "-ss", str(start_sec), "-to", str(end_sec), "-i", a_url,
                "-c:v", "libx264", "-preset", "veryfast", "-crf", "18",
                "-c:a", "aac", "-b:a", "192k",
                out_mp4
            ]
            res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            if res.returncode == 0 and os.path.exists(out_mp4) and os.path.getsize(out_mp4) > 0:
                logger.info(f"✓ Video segment downloaded successfully: {Path(out_mp4).name} ({os.path.getsize(out_mp4)} bytes)")
                return out_mp4
            return None
        except Exception as e:
            logger.error(f"Segment download error: {e}")
            return None

    def render_916_short(self, raw_clip_path: str, output_short_path: str, overlay_text: str = "") -> bool:
        """
        Formats video to 9:16 vertical (1080x1920) Short.
        Handles both 16:9 widescreen and vertical videos seamlessly.
        """
        logger.info(f"Rendering 9:16 vertical short using FFmpeg 7.1...")
        cmd = [
            self.ffmpeg_exe, "-y",
            "-i", raw_clip_path,
            "-vf", "scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2:black",
            "-c:v", "libx264", "-preset", "fast", "-crf", "18",
            "-c:a", "copy",
            "-movflags", "+faststart",
            output_short_path
        ]
        try:
            res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
            return os.path.exists(output_short_path) and os.path.getsize(output_short_path) > 0
        except subprocess.CalledProcessError as e:
            logger.error(f"FFmpeg render error: {e.stderr.decode('utf-8', errors='ignore')}")
            return False

    def export_davinci_fcpxml(self, media_path: str, start_sec: float, end_sec: float, title: str, xml_out_path: str):
        """Generate a DaVinci Resolve compatible FCPXML project file."""
        abs_media = Path(media_path).resolve().as_uri()
        duration_frames = int((end_sec - start_sec) * 30)

        xml_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE fcpxml>
<fcpxml version="1.9">
  <resources>
    <format id="r1" name="FFVideoFormat1080x1920p30" frameDuration="1/30s" width="1080" height="1920"/>
    <asset id="r2" name="{Path(media_path).name}" src="{abs_media}" format="r1" hasVideo="1" hasAudio="1"/>
  </resources>
  <library>
    <event name="JAGY Automated Clips">
      <project name="{title}">
        <sequence format="r1" duration="{duration_frames}/30s">
          <spine>
            <asset-clip name="{title}" offset="0/30s" ref="r2" duration="{duration_frames}/30s" start="{int(start_sec*30)}/30s">
            </asset-clip>
          </spine>
        </sequence>
      </project>
    </event>
  </library>
</fcpxml>
"""
        with open(xml_out_path, "w", encoding="utf-8") as f:
            f.write(xml_content)
        logger.info(f"✓ DaVinci Resolve FCPXML project exported to: {xml_out_path}")

    def clip_channel_video(self, channel_or_url: str = "@IShowSpeed") -> Optional[Dict[str, Any]]:
        """Complete autonomous pipeline to clip target channel."""
        videos = self.get_latest_channel_videos(channel_or_url, max_videos=3)
        if not videos:
            logger.error(f"No videos found for {channel_or_url}")
            return None

        target_video = videos[0]
        logger.info(f"Targeting Video: '{target_video['title']}' ({target_video['url']})")

        # 1. Fetch Transcripts
        transcript = self.fetch_transcript(target_video["id"])
        if not transcript:
            logger.warning("No transcript found, using fallback time window (00:05 - 00:45)")
            moment = {
                "start": 5.0,
                "end": 45.0,
                "duration": 40.0,
                "hook": "Opening energetic segment",
                "viral_title": f"{target_video['title']} #shorts",
                "key_phrase": "Crazy Moment"
            }
        else:
            # 2. AI Moment Detection
            moment = self.find_viral_moment_with_ai(transcript, target_video["title"])

        logger.info(f"Viral Moment Identified: {moment['start']:.1f}s -> {moment['end']:.1f}s | Hook: {moment['hook']}")

        # 3. Download Segment
        raw_clip_target = str(self.temp_dir / f"raw_{target_video['id']}.mp4")
        downloaded_clip = self.download_precise_segment(target_video["url"], moment["start"], moment["end"], raw_clip_target)
        if not downloaded_clip:
            logger.error("Failed to download video segment.")
            return None
        raw_clip = downloaded_clip

        # 4. Render 9:16 Vertical Short
        short_filename = f"speed_short_{target_video['id']}.mp4"
        short_out = str(self.output_dir / short_filename)
        rendered = self.render_916_short(raw_clip, short_out, overlay_text=moment["viral_title"])
        
        # 5. Export DaVinci Resolve Timeline FCPXML
        davinci_xml = str(self.output_dir / f"speed_short_{target_video['id']}_davinci.fcpxml")
        self.export_davinci_fcpxml(raw_clip, moment["start"], moment["end"], moment["viral_title"], davinci_xml)

        return {
            "success": rendered,
            "video_title": target_video["title"],
            "viral_title": moment["viral_title"],
            "hook_reason": moment["hook"],
            "duration": moment["duration"],
            "short_video_path": short_out,
            "davinci_xml_path": davinci_xml,
            "source_url": target_video["url"]
        }

if __name__ == "__main__":
    clipper = YouTubeChannelClipper()
    result = clipper.clip_channel_video("@IShowSpeed")
    print("\n" + "="*50)
    print("CLIPPING RESULT:")
    print(json.dumps(result, indent=2))
    print("="*50)
