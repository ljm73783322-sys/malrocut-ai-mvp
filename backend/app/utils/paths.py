import os

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
STORAGE_DIR = os.path.join(BASE_DIR, "storage", "jobs")

def get_job_dir(job_id: str) -> str:
    path = os.path.join(STORAGE_DIR, job_id)
    os.makedirs(path, exist_ok=True)
    return path
