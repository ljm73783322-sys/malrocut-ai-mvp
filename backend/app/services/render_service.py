import asyncio
import os
import shutil
import subprocess
from .job_store import update_job_status
from ..utils.paths import get_job_dir

async def render_video_mock(job_id: str):
    update_job_status(job_id, "rendering", 0)
    
    # Mock progress
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
            # 1. Generate video using ffmpeg
            # 1.03x crop, scale to 1080x1920 (pad if needed), slightly brighter
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
            
            # 2. Extract thumbnail
            try:
                subprocess.run([
                    "ffmpeg", "-y", "-i", input_path,
                    "-ss", "00:00:00", "-vframes", "1",
                    thumbnail_path
                ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except Exception:
                _create_fallback_thumbnail(thumbnail_path)
        else:
            # Fallback when ffmpeg is not available
            shutil.copy(input_path, output_video_path)
            _create_fallback_thumbnail(thumbnail_path)
    else:
        # If input somehow doesn't exist, just create empty files (shouldn't happen)
        with open(output_video_path, "wb") as f:
            f.write(b"")
        _create_fallback_thumbnail(thumbnail_path)
        
    # Write normal SRT
    with open(subtitle_path, "w", encoding="utf-8") as f:
        f.write("1\n00:00:00,000 --> 00:00:03,000\n말로컷 AI로 편집된 영상입니다.\n")

    for i in range(6, 11):
        await asyncio.sleep(0.2)
        update_job_status(job_id, "rendering", i * 10)

    update_job_status(job_id, "completed", 100)

def _create_fallback_thumbnail(path: str):
    # A tiny 1x1 valid PNG image bytes as fallback
    png_1x1 = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82'
    with open(path, "wb") as f:
        f.write(png_1x1)
