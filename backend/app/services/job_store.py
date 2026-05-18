# In-memory store for MVP skeleton
jobs_db = {}

def create_job(job_id: str):
    jobs_db[job_id] = {
        "status": "uploaded",
        "progress": 0,
        "analysis": None,
        "plan": None,
        "error": None,
    }

def update_job_status(job_id: str, status: str, progress: int = 0):
    if job_id in jobs_db:
        jobs_db[job_id]["status"] = status
        jobs_db[job_id]["progress"] = progress

def fail_job(job_id: str, error_message: str):
    """렌더링 실패 시 status를 'failed'로 저장하고 에러 메시지를 남깁니다."""
    if job_id in jobs_db:
        jobs_db[job_id]["status"] = "failed"
        jobs_db[job_id]["progress"] = 0
        jobs_db[job_id]["error"] = error_message

def get_job(job_id: str):
    return jobs_db.get(job_id)
