import uuid
import os
from fastapi import APIRouter, UploadFile, File, BackgroundTasks, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from ..models.job import JobStatus
from ..services import job_store, video_service, edit_service, render_service
from ..utils.paths import get_job_dir

router = APIRouter()

@router.post("/upload")
async def upload_video(file: UploadFile = File(...)):
    job_id = str(uuid.uuid4())
    job_store.create_job(job_id)
    
    job_dir = get_job_dir(job_id)
    file_path = os.path.join(job_dir, "input.mp4")
    
    with open(file_path, "wb") as buffer:
        content = await file.read()
        buffer.write(content)
        
    return {"job_id": job_id}

@router.post("/{job_id}/analyze")
async def analyze_job(job_id: str, background_tasks: BackgroundTasks):
    job = job_store.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    background_tasks.add_task(video_service.analyze_video_mock, job_id)
    return {"status": "started"}

@router.get("/{job_id}/analysis")
async def get_analysis(job_id: str):
    job = job_store.get_job(job_id)
    if not job or not job.get("analysis"):
        raise HTTPException(status_code=404, detail="Analysis not found")
    return job["analysis"]

class EditRequest(BaseModel):
    prompt: str = ""

@router.post("/{job_id}/edit")
async def edit_job(job_id: str, req: EditRequest):
    job = job_store.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    # create_edit_plan_mock returns { job_id, prompt, edit_command, plan_items }
    result = edit_service.create_edit_plan_mock(job_id, req.prompt)
    return result

@router.post("/{job_id}/render")
async def render_job(job_id: str, background_tasks: BackgroundTasks):
    job = job_store.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    background_tasks.add_task(render_service.render_video_mock, job_id)
    return {"status": "started"}

@router.get("/{job_id}/status", response_model=JobStatus)
async def get_status(job_id: str):
    job = job_store.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return JobStatus(job_id=job_id, status=job["status"], progress=job["progress"])

@router.get("/{job_id}/download/{file_type}")
async def download_file(job_id: str, file_type: str):
    job_dir = get_job_dir(job_id)
    
    filename_map = {
        "video": "edited_video.mp4",
        "original_video": "input.mp4",
        "thumbnail": "thumbnail.jpg",
        "subtitle": "subtitle.srt",
        "original_subtitle": "subtitle_original.srt"
    }
    
    if file_type not in filename_map:
        raise HTTPException(status_code=400, detail="Invalid file type")
        
    file_path = os.path.join(job_dir, filename_map[file_type])
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not ready")
        
    media_type = "video/mp4" if "video" in file_type else "image/jpeg" if file_type == "thumbnail" else "text/plain"
    return FileResponse(path=file_path, filename=filename_map[file_type], media_type=media_type)
