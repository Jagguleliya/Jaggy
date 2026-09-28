import os
import logging
import re
import textwrap
import numpy as np
from pathlib import Path
import yaml
from PIL import Image, ImageDraw, ImageFont

# Monkeypatch Pillow 10+ compatibility for MoviePy 1.x
if not hasattr(Image, 'ANTIALIAS'):
    Image.ANTIALIAS = Image.Resampling.LANCZOS

logger = logging.getLogger(__name__)

try:
    from moviepy.editor import VideoFileClip, AudioFileClip, ImageClip, CompositeVideoClip, CompositeAudioClip, ColorClip
    import moviepy.video.fx.all as vfx
except ImportError:
    from moviepy import *

class VideoEngine:
    """Production-ready video engine for YouTube Shorts using MoviePy and Pillow."""
    
    def __init__(self, config_path: str = "config/config.yaml"):
        self.config_path = config_path
        self._load_config()
        self.width = 1080
        self.height = 1920
        self.font_paths = [
            "C:/Windows/Fonts/impact.ttf",
            "C:/Windows/Fonts/arialbd.ttf",
            "templates/fonts/Montserrat-Bold.ttf",
            "arial.ttf"
        ]

    def _load_config(self):
        if os.path.exists(self.config_path):
            with open(self.config_path, 'r') as f:
                self.config = yaml.safe_load(f) or {}
        else:
            self.config = {}

    def create_video(self, script: str, audio_path: str, background_path: str = None, 
                     human_clips: list = None, music_path: str = None, 
                     style: dict = None, output_path: str = None) -> str:
        """
        Full orchestration: load audio, measure duration, prepare background, 
        create captions, insert human clips, mix music, apply effects, render.
        """
        if not output_path:
            os.makedirs("output", exist_ok=True)
            output_path = "output/final_video.mp4"
            
        logger.info(f"Creating video. Output will be saved to {output_path}")

        try:
            # 1. Load Audio
            main_audio = AudioFileClip(audio_path)
            duration = main_audio.duration
            
            # 2. Prepare Background
            if background_path and os.path.exists(background_path):
                bg_clip = self._prepare_background(background_path, duration)
            else:
                bg_clip = self._create_gradient_background(duration, style)

            # 3. Create Caption Clips (Fast, punchy 2-3 word bursts)
            narration_text = script.get('narration', '') if isinstance(script, dict) else str(script)
            caption_clips = self._create_caption_clips(narration_text, duration, style)
            
            # Top Hook Banner (Stops the scroll during the crucial first 4.5s)
            top_banner_text = script.get('top_banner_text', '') if isinstance(script, dict) else ''
            banner_clips = []
            if top_banner_text:
                banner_clip = self._create_top_banner_clip(top_banner_text, duration=min(duration, 4.5))
                if banner_clip:
                    banner_clips.append(banner_clip)
            
            # Combine background, hook banner, and dynamic captions
            video_layers = [bg_clip] + banner_clips + caption_clips
            
            # 4. Insert Human Clips
            if human_clips:
                video_layers = self._insert_human_clips(video_layers, human_clips, duration)
                
            # 5. Composite Video
            composite_video = CompositeVideoClip(video_layers, size=(self.width, self.height))
            
            # Mix background audio if available at low ambient volume (12%)
            if bg_clip.audio:
                try:
                    ambient_audio = bg_clip.audio.volumex(0.12)
                    if ambient_audio.duration < duration:
                        import moviepy.audio.fx.all as afx
                        ambient_audio = afx.audio_loop(ambient_audio, duration=duration)
                    ambient_audio = ambient_audio.subclip(0, duration)
                    composite_video = composite_video.set_audio(CompositeAudioClip([main_audio, ambient_audio]))
                except Exception as e:
                    logger.warning(f"Could not mix ambient clip audio: {e}")
                    composite_video = composite_video.set_audio(main_audio)
            else:
                composite_video = composite_video.set_audio(main_audio)
            
            # 6. Apply Effects
            composite_video = self._apply_effects(composite_video)
            
            # 7. Add Music
            if music_path and os.path.exists(music_path):
                composite_video = self._add_music(composite_video, music_path)
                
            # 8. Render
            return self._render(composite_video, output_path)
            
        except Exception as e:
            logger.error(f"Error creating video: {e}")
            raise
        
    def _prepare_background(self, bg_path: str, duration: float):
        """
        Load video, crop to vertical 9:16, resize to 1080x1920, loop if needed.
        """
        clip = VideoFileClip(bg_path)
        
        target_aspect = self.width / self.height  # 1080 / 1920 = 0.5625
        clip_aspect = clip.w / clip.h
        
        # Crop to 9:16 if aspect ratio doesn't match
        if abs(clip_aspect - target_aspect) > 0.01:
            if clip_aspect > target_aspect:
                # Video is wider than 9:16 -> crop left & right
                new_w = int(clip.h * target_aspect)
                x1 = (clip.w - new_w) // 2
                x2 = x1 + new_w
                try:
                    clip = clip.crop(x1=x1, x2=x2)
                except Exception:
                    pass
            else:
                # Video is taller than 9:16 -> crop top & bottom
                new_h = int(clip.w / target_aspect)
                y1 = (clip.h - new_h) // 2
                y2 = y1 + new_h
                try:
                    clip = clip.crop(y1=y1, y2=y2)
                except Exception:
                    pass
                
        # Resize to 1080x1920
        try:
            import moviepy.video.fx.all as vfx
            clip = clip.fx(vfx.resize, newsize=(self.width, self.height))
        except Exception:
            clip = clip.resize((self.width, self.height))

        # Loop if shorter
        if clip.duration < duration:
            has_audio = clip.audio is not None
            try:
                import moviepy.video.fx.all as vfx
                clip = vfx.loop(clip, duration=duration)
            except Exception:
                clip = clip.loop(duration=duration)
            if has_audio:
                try:
                    import moviepy.audio.fx.all as afx
                    clip = clip.set_audio(afx.audio_loop(clip.audio, duration=duration))
                except Exception:
                    clip = clip.set_audio(None)
                
        return clip.set_duration(duration)

    def _create_gradient_background(self, duration: float, style: dict):
        """
        Create a gradient image with Pillow and convert to VideoClip.
        """
        style = style or {}
        top_color = style.get("bg_color", "#1a1a2e")
        bottom_color = style.get("accent_color", "#16213e")
        
        def hex_to_rgb(hex_col):
            hex_col = hex_col.lstrip('#')
            if len(hex_col) == 6:
                return tuple(int(hex_col[i:i+2], 16) for i in (0, 2, 4))
            return (0, 0, 0)
        
        c1 = hex_to_rgb(top_color)
        c2 = hex_to_rgb(bottom_color)
        
        img = Image.new('RGB', (self.width, self.height), color=top_color)
        draw = ImageDraw.Draw(img)
        
        for y in range(self.height):
            ratio = y / self.height
            r = int(c1[0] * (1 - ratio) + c2[0] * ratio)
            g = int(c1[1] * (1 - ratio) + c2[1] * ratio)
            b = int(c1[2] * (1 - ratio) + c2[2] * ratio)
            draw.line([(0, y), (self.width, y)], fill=(r, g, b))
            
        arr = np.array(img)
        return ImageClip(arr).set_duration(duration)
        
    def _create_caption_clips(self, narration: str, audio_duration: float, style: dict) -> list:
        """
        Creates rapid 2-3 word burst captions in modern viral Shorts style.
        """
        raw_words = narration.strip().split()
        if not raw_words:
            return []
            
        total_words = len(raw_words)
        
        # Group words into punchy 2-3 word chunks
        chunks = []
        i = 0
        while i < total_words:
            # 2 to 3 words per chunk
            chunk_size = 2 if (i % 2 == 0) else 3
            chunk = raw_words[i:i+chunk_size]
            chunks.append(chunk)
            i += len(chunk)
            
        clips = []
        current_time = 0.0
        
        # Alternate colors for visual energy: Yellow (#FFE600), White (#FFFFFF), Cyan (#00F0FF)
        colors = ["#FFE600", "#FFFFFF", "#00F0FF", "#FFE600"]
        
        for idx, chunk in enumerate(chunks):
            chunk_duration = (len(chunk) / total_words) * audio_duration
            text_str = " ".join(chunk).upper()
            color = colors[idx % len(colors)]
            
            img_arr = self._render_text_image(text_str, width=1000, font_size=74, text_color=color)
            
            clip = ImageClip(img_arr)
            # Position centered in lower third (clear view of video, perfect for mobile)
            clip = clip.set_position(('center', 1220))
            clip = clip.set_start(current_time)
            clip = clip.set_duration(chunk_duration)
            
            clips.append(clip)
            current_time += chunk_duration
            
        return clips

    def _create_top_banner_clip(self, text: str, duration: float = 4.5) -> Optional[ImageClip]:
        """
        Creates an ultra-high-contrast top hook banner (e.g. 'WAIT FOR THE END 😱').
        Placed at Y=260 to freeze viewers during the critical 0.5s swipe decision.
        """
        try:
            import re
            text = re.sub(r'[^\x00-\x7F]+', '', text).strip()
            if not text:
                return None
            width = 980
            height = 130
            img = Image.new('RGBA', (width, height), (0, 0, 0, 0))
            draw = ImageDraw.Draw(img)
            
            # Semi-translucent dark rounded pill background
            draw.rounded_rectangle(
                [0, 0, width, height],
                radius=25,
                fill=(0, 0, 0, 175)
            )
            
            # Auto-scaled bold font
            current_size = 56
            font = None
            while current_size >= 32:
                for fp in self.font_paths:
                    try:
                        font = ImageFont.truetype(fp, current_size)
                        break
                    except Exception:
                        continue
                if font is None:
                    font = ImageFont.load_default()
                    break
                try:
                    bbox = draw.textbbox((0, 0), text, font=font)
                    tw = bbox[2] - bbox[0]
                    th = bbox[3] - bbox[1]
                except AttributeError:
                    tw, th = draw.textsize(text, font=font)
                if tw <= width - 60:
                    break
                current_size -= 4
                
            tx = (width - tw) // 2
            ty = (height - th) // 2
            
            # Bold Electric Yellow high-visibility text with black stroke
            draw.text((tx, ty), text, font=font, fill="#FFE600", stroke_width=4, stroke_fill="black")
            
            banner_clip = ImageClip(np.array(img))
            banner_clip = banner_clip.set_position(('center', 260)).set_start(0).set_duration(duration)
            return banner_clip
        except Exception as e:
            logger.warning(f"Failed to create top banner clip: {e}")
            return None

    def _render_text_image(self, text: str, width: int = 1000, font_size: int = 78, text_color: str = "#FFE600") -> np.ndarray:
        """
        Render ultra-bold, viral typography with heavy black outline and 3D shadow.
        NO dark background box! Auto-scales font size to fit width.
        """
        import re
        text = re.sub(r'[^\x00-\x7F]+', '', text).strip()
        img_h = 240
        img = Image.new('RGBA', (width, img_h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        
        # Dynamically scale font size if text is long
        current_size = font_size
        font = None
        text_w, text_h = 0, 0
        while current_size >= 44:
            font = None
            for fp in self.font_paths:
                try:
                    font = ImageFont.truetype(fp, current_size)
                    break
                except Exception:
                    continue
            if font is None:
                font = ImageFont.load_default()
                break
                
            try:
                bbox = draw.textbbox((0, 0), text, font=font)
                text_w = bbox[2] - bbox[0]
                text_h = bbox[3] - bbox[1]
            except AttributeError:
                text_w, text_h = draw.textsize(text, font=font)
                
            if text_w <= width - 100:
                break
            current_size -= 4
            
        text_x = (width - text_w) // 2
        text_y = (img_h - text_h) // 2
        
        # 1. Draw 3D drop shadow (black offset)
        shadow_offset = 6
        draw.text(
            (text_x + shadow_offset, text_y + shadow_offset),
            text,
            font=font,
            fill=(0, 0, 0, 180),
            stroke_width=7,
            stroke_fill="black"
        )
        
        # 2. Draw main bold text with heavy 7px stroke outline
        draw.text(
            (text_x, text_y), 
            text, 
            font=font, 
            fill=text_color, 
            stroke_width=7, 
            stroke_fill="black"
        )
        
        return np.array(img)

    def _add_music(self, video, music_path: str, volume: float = 0.15):
        """
        Add background music, looped and faded.
        """
        try:
            music = AudioFileClip(music_path).volumex(volume)
            
            if music.duration < video.duration:
                try:
                    import moviepy.audio.fx.all as afx
                    music = afx.audio_loop(music, duration=video.duration)
                except Exception:
                    pass
                
            music = music.set_duration(video.duration)
            
            try:
                import moviepy.audio.fx.all as afx
                music = afx.audio_fadein(music, 1.0)
                music = afx.audio_fadeout(music, 2.0)
            except Exception:
                pass
                
            final_audio = CompositeAudioClip([video.audio, music])
            return video.set_audio(final_audio)
        except Exception as e:
            logger.warning(f"Could not add music: {e}")
            return video

    def _insert_human_clips(self, clips_list: list, human_clips: list, total_duration: float) -> list:
        """
        Insert human clips at intro, midpoint, outro.
        """
        for idx, hc_path in enumerate(human_clips):
            if not os.path.exists(hc_path):
                continue
            try:
                hc = VideoFileClip(hc_path)
                hc = hc.set_position(('center', 'center'))
                
                try:
                    hc = hc.fadein(0.5).fadeout(0.5)
                except AttributeError:
                    pass
                    
                if idx == 0:
                    hc = hc.set_start(0.0)
                elif idx == 1:
                    hc = hc.set_start(total_duration / 2.0)
                else:
                    hc = hc.set_start(max(0, total_duration - hc.duration - 1.0))
                    
                clips_list.append(hc)
            except Exception as e:
                logger.warning(f"Failed to insert human clip {hc_path}: {e}")
                
        return clips_list

    def _apply_effects(self, clip):
        """
        Apply global effects (fade in/out).
        """
        try:
            return clip.fadein(0.5).fadeout(0.5)
        except AttributeError:
            return clip

    def _render(self, composite, output_path: str) -> str:
        """
        Render final video with specific encoding settings.
        """
        out_dir = os.path.dirname(output_path)
        if out_dir:
            os.makedirs(out_dir, exist_ok=True)
            
        composite.write_videofile(
            output_path,
            fps=30,
            codec="libx264",
            audio_codec="aac",
            bitrate="8000k",
            threads=4,
            logger=None
        )
        return output_path

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    engine = VideoEngine()
    print("VideoEngine initialized. Ready to create production videos.")
