import asyncio
from .job_store import update_job_status, jobs_db

async def analyze_video_mock(job_id: str):
    update_job_status(job_id, "analyzing", 10)
    await asyncio.sleep(2) # mock processing
    update_job_status(job_id, "analyzing", 50)
    await asyncio.sleep(2)
    
    # mock analysis result
    analysis = {
        "has_audio": True,
        "has_subtitles": True,
        "transcript_preview": "안녕하세요 오늘 날씨가 참 좋네요..."
    }
    jobs_db[job_id]["analysis"] = analysis
    update_job_status(job_id, "analyzed", 100)
