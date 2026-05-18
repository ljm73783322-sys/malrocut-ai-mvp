from pydantic import BaseModel

class JobStatus(BaseModel):
    job_id: str
    status: str
    progress: int = 0
    error: str | None = None
