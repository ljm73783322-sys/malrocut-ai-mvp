# In-memory store for MVP skeleton
jobs_db = {}

def create_job(job_id: str):
    jobs_db[job_id] = {"status": "uploaded", "progress": 0, "analysis": None, "plan": None}

def update_job_status(job_id: str, status: str, progress: int = 0):
    if job_id in jobs_db:
        jobs_db[job_id]["status"] = status
        jobs_db[job_id]["progress"] = progress

def get_job(job_id: str):
    return jobs_db.get(job_id)
