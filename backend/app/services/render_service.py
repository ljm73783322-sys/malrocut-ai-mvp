import asyncio
import os
from .job_store import update_job_status
from ..utils.paths import get_job_dir

async def render_video_mock(job_id: str):
    update_job_status(job_id, "rendering", 0)
    
    for i in range(1, 11):
        await asyncio.sleep(0.5)
        update_job_status(job_id, "rendering", i * 10)
        
    job_dir = get_job_dir(job_id)
    
    # Create mock dummy files for download
    with open(os.path.join(job_dir, "edited_video.mp4"), "wb") as f:
        f.write(b"dummy video content")
    with open(os.path.join(job_dir, "thumbnail.jpg"), "wb") as f:
        f.write(b"dummy thumbnail content")
    with open(os.path.join(job_dir, "subtitle.srt"), "wb") as f:
        f.write(b"1\n00:00:01,000 --> 00:00:03,000\n\xec\x95\x88\xeb\x85\x95\xed\x95\x98\xec\x84\xb8\xec\x9a\x94\n")

    update_job_status(job_id, "completed", 100)
