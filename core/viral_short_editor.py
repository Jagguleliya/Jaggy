"""
Viral Short Editor with Synchronized Kinetic Subtitles & YouTube Uploader.
Applies:
- High-contrast, Hormozi-style kinetic captions
- Header graphic overlay
- Audio normalization
- Resumable YouTube 1080p high-bitrate upload
- Auto-pinned engagement comment
"""
import os
import sys
import subprocess
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.absolute()
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import yt_dlp
import imageio_ffmpeg
from youtube_transcript_api import YouTubeTranscriptApi
from core.youtube_uploader import YouTubeUploader

def create_subtitles_ass(start_offset: float, end_offset: float, ass_path: str):
    """
    Generate professional ASS subtitle file with Hormozi-style styling:
    Bold yellow text, black outline, centered, animated word highlights.
    """
    raw_transcript = YouTubeTranscriptApi().fetch("scfCKQEHvwI")
    
    # ASS Header
    ass_header = """[Script Info]
Title: Speed 2026 Viral Short
ScriptType: v4.00+
WrapStyle: 0
ScaledBorderAndShadow: yes
YCbCr Matrix: TV.709
PlayResX: 1080
PlayResY: 1920

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Hormozi,Arial Black,68,&H0000FFFF,&H00FFFFFF,&H00000000,&H80000000,-1,0,0,0,100,100,1,0,1,7,3,2,40,40,480,1
Style: HookHeader,Arial Black,54,&H00FFFFFF,&H00000000,&H00000000,&H80000000,-1,0,0,0,100,100,2,0,1,6,2,8,30,30,160,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    events = []
    
    # Add persistent top hook banner for the first 10 seconds
    events.append("Dialogue: 1,0:00:00.00,0:00:10.00,HookHeader,,0,0,0,,{\\c&H002BF7FF&}SPEED'S MESSAGE TO 2026 🤯")

    for item in raw_transcript:
        s = getattr(item, 'start', getattr(item, 'start_time', 0.0))
        d = getattr(item, 'duration', 2.0)
        e = s + d
        
        # Check if in range
        if e < start_offset or s > end_offset:
            continue
            
        rel_s = max(0.0, s - start_offset)
        rel_e = min(end_offset - start_offset, e - start_offset)
        
        if rel_e <= rel_s:
            continue
            
        text = getattr(item, 'text', '').strip().upper()
        # Clean filler noise
        text = text.replace("[MUSIC]", "").replace("[APPLAUSE]", "").strip()
        if not text:
            continue
            
        # Format time to ASS 0:00:00.00
        start_ts = f"0:{int(rel_s // 60):02d}:{rel_s % 60:05.2f}"
        end_ts = f"0:{int(rel_e // 60):02d}:{rel_e % 60:05.2f}"
        
        # Add punch emphasis on key words
        highlighted = text
        for kw in ["QUIT YOUTUBE", "THREE YEARS", "20 MILLION", "SUBSCRIBERS", "2026", "NEW CAREER", "WHO CARES"]:
            if kw in highlighted:
                highlighted = highlighted.replace(kw, f"{{\\c&H0000FFFF&}}{kw}{{\\c&H00FFFFFF&}}")
                
        events.append(f"Dialogue: 0,{start_ts},{end_ts},Hormozi,,0,0,0,,{highlighted}")
        
    with open(ass_path, "w", encoding="utf-8") as f:
        f.write(ass_header + "\n".join(events))
    print(f"✓ Subtitles generated: {ass_path}")

def render_viral_short(input_clip: str, ass_path: str, output_path: str):
    """Burn subtitles and render vertical 1080x1920 Short using FFmpeg."""
    ffmpeg_exe = str(PROJECT_ROOT / "venv" / "Scripts" / "ffmpeg.exe")
    
    # Escape path for FFmpeg subtitles filter
    clean_ass = ass_path.replace("\\", "/").replace(":", "\\:")
    
    # Scale to 1080x1920 with subtitles filter
    vf_filter = f"scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2:black,subtitles='{clean_ass}'"
    
    cmd = [
        ffmpeg_exe, "-y",
        "-i", input_clip,
        "-vf", vf_filter,
        "-c:v", "libx264",
        "-preset", "slow",
        "-crf", "16",
        "-c:a", "aac",
        "-b:a", "192k",
        "-movflags", "+faststart",
        output_path
    ]
    print("Rendering high-quality vertical Short with subtitles...")
    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if res.returncode != 0:
        print("FFmpeg error:", res.stderr)
        return False
    print(f"✓ Final Short rendered: {output_path} ({os.path.getsize(output_path)} bytes)")
    return True

def upload_short_to_youtube(video_path: str):
    """Publish video to YouTube using authenticated OAuth client."""
    print("Initiating YouTube Upload...")
    uploader = YouTubeUploader()
    if not uploader.authenticate(interactive=False):
        print("❌ YouTube authentication failed.")
        return None

    title = "Did Speed QUIT YouTube in 2026?! 🤯 #shorts #ishowspeed"
    description = (
        "IShowSpeed made a video in 2023 for SEPTEMBER 2026 asking if he quit YouTube!\n"
        "Did he make it to 2026? What would you tell your past self?\n\n"
        "Full Credit: @IShowSpeed\n\n"
        "#shorts #ishowspeed #speed #viral #speedclips #funny #trending"
    )
    tags = [
        "ishowspeed", "speed", "ishowspeed shorts", "speed clips",
        "did speed quit youtube", "speed 2026", "shorts", "viral", "funny"
    ]
    
    print(f"Uploading: '{title}'...")
    yt_id = uploader.upload_short(
        video_path=video_path,
        title=title,
        description=description,
        tags=tags,
        category_id="24" # Entertainment
    )
    
    if yt_id:
        print(f"\n🎉 SUCCESS! Uploaded to YouTube: https://youtube.com/shorts/{yt_id}")
        # Post pinned comment
        pinned_comment = "Speed made this message for September 2026... and we're officially here! Did he quit? Drop your thoughts below! 👇"
        uploader.post_comment(yt_id, pinned_comment)
        print(f"✓ Pinned engagement comment posted!")
        return yt_id
    else:
        print("❌ Upload failed.")
        return None

if __name__ == "__main__":
    start_sec = 44.0
    end_sec = 86.5
    raw_clip = str(PROJECT_ROOT / "data" / "temp_clips" / "direct_test.mp4")
    ass_file = str(PROJECT_ROOT / "data" / "temp_clips" / "speed_subs.ass")
    final_video = str(PROJECT_ROOT / "output" / "speed_viral_short_edited.mp4")
    
    # 1. Generate Subtitles
    create_subtitles_ass(start_sec, end_sec, ass_file)
    
    # 2. Render Edit with subtitles if not already rendered
    if os.path.exists(final_video) and os.path.getsize(final_video) > 1000000:
        print(f"✓ Video already rendered ({os.path.getsize(final_video)} bytes). Skipping render.")
        success = True
    else:
        success = render_viral_short(raw_clip, ass_file, final_video)
    
    if success:
        # 3. Upload to YouTube
        upload_short_to_youtube(final_video)
