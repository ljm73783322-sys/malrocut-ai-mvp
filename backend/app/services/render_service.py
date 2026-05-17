import asyncio
import os
import shutil
import subprocess
from .job_store import update_job_status
from ..utils.paths import get_job_dir

try:
    from PIL import Image, ImageDraw, ImageFont
    HAS_PILLOW = True
except ImportError:
    HAS_PILLOW = False

def _create_fallback_thumbnail(path: str):
    if not HAS_PILLOW:
        return
        
    width, height = 1280, 720
    img = Image.new('RGB', (width, height), color=(40, 40, 40))
    draw = ImageDraw.Draw(img)
    
    try:
        font_large = ImageFont.truetype("malgun.ttf", 80)
        font_medium = ImageFont.truetype("malgun.ttf", 60)
    except IOError:
        try:
            font_large = ImageFont.truetype("arial.ttf", 80)
            font_medium = ImageFont.truetype("arial.ttf", 60)
        except IOError:
            font_large = ImageFont.load_default()
            font_medium = ImageFont.load_default()

    text_top = "말로컷 AI"
    text_center = "편집된 영상입니다"
    text_bottom = "thumbnail.jpg"
    
    def draw_centered_text(text, font, y_pos, color=(255, 255, 255)):
        try:
            bbox = draw.textbbox((0, 0), text, font=font)
            w = bbox[2] - bbox[0]
            h = bbox[3] - bbox[1]
        except AttributeError:
            w, h = draw.textsize(text, font=font)
            
        x = (width - w) / 2
        draw.text((x, y_pos), text, font=font, fill=color)

    draw_centered_text(text_top, font_large, 100, color=(100, 150, 255))
    draw_centered_text(text_center, font_large, height / 2 - 40, color=(255, 255, 255))
    draw_centered_text(text_bottom, font_medium, height - 150, color=(150, 150, 150))
    
    img.save(path, format='JPEG', quality=90)

def _is_valid_thumbnail(path: str) -> bool:
    if not os.path.exists(path):
        return False
    if os.path.getsize(path) < 1024:  # Smaller than 1KB
        return False
    
    if HAS_PILLOW:
        try:
            with Image.open(path) as img:
                w, h = img.size
                if w <= 10 or h <= 10:
                    return False
        except Exception:
            return False
            
    return True

async def render_video_mock(job_id: str):
    update_job_status(job_id, "rendering", 0)
    
    for i in range(1, 6):
        await asyncio.sleep(0.5)
        update_job_status(job_id, "rendering", i * 10)
        
    job_dir = get_job_dir(job_id)
    input_path = os.path.join(job_dir, "input.mp4")
    output_video_path = os.path.join(job_dir, "edited_video.mp4")
    thumbnail_path = os.path.join(job_dir, "thumbnail.jpg")
    subtitle_path = os.path.join(job_dir, "subtitle.srt")
    
    has_ffmpeg = shutil.which("ffmpeg") is not None
    
    if os.path.exists(input_path):
        if has_ffmpeg:
            vf_filter = "crop=iw/1.03:ih/1.03,scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2,eq=brightness=0.05"
            try:
                subprocess.run([
                    "ffmpeg", "-y", "-i", input_path,
                    "-vf", vf_filter,
                    "-c:a", "copy",
                    output_video_path
                ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except Exception:
                shutil.copy(input_path, output_video_path)
            
            # Extract thumbnail (try 00:00:01)
            try:
                subprocess.run([
                    "ffmpeg", "-y", "-i", input_path,
                    "-ss", "00:00:01", "-vframes", "1",
                    thumbnail_path
                ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except Exception:
                pass
                
            # If failed or invalid, try 00:00:00
            if not _is_valid_thumbnail(thumbnail_path):
                try:
                    subprocess.run([
                        "ffmpeg", "-y", "-i", input_path,
                        "-ss", "00:00:00", "-vframes", "1",
                        thumbnail_path
                    ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                except Exception:
                    pass
            
            # If still invalid, use fallback
            if not _is_valid_thumbnail(thumbnail_path):
                _create_fallback_thumbnail(thumbnail_path)
        else:
            shutil.copy(input_path, output_video_path)
            _create_fallback_thumbnail(thumbnail_path)
    else:
        with open(output_video_path, "wb") as f:
            f.write(b"")
        _create_fallback_thumbnail(thumbnail_path)
        
    with open(subtitle_path, "w", encoding="utf-8") as f:
        f.write("1\n00:00:00,000 --> 00:00:03,000\n말로컷 AI로 편집된 영상입니다.\n")

    for i in range(6, 11):
        await asyncio.sleep(0.2)
        update_job_status(job_id, "rendering", i * 10)

    update_job_status(job_id, "completed", 100)
