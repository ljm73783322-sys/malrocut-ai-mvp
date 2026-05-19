import uuid
import os
from fastapi import APIRouter, UploadFile, File, BackgroundTasks, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from ..models.job import JobStatus
from ..services import job_store, video_service, edit_service, render_service, thumbnail_service
from ..utils.paths import get_job_dir, STORAGE_DIR

router = APIRouter()


def _safe_job_file_path(job_id: str, filename: str) -> str:
    """Return a safe file path inside backend/storage/jobs/<job_id>."""
    if os.path.basename(filename) != filename:
        raise HTTPException(status_code=400, detail="Invalid filename")

    storage_root = os.path.abspath(STORAGE_DIR)
    job_dir = os.path.abspath(os.path.join(storage_root, job_id))
    file_path = os.path.abspath(os.path.join(job_dir, filename))

    if os.path.commonpath([storage_root, job_dir]) != storage_root:
        raise HTTPException(status_code=400, detail="Invalid job id")
    if os.path.commonpath([job_dir, file_path]) != job_dir:
        raise HTTPException(status_code=400, detail="Invalid file path")

    return file_path

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
    return JobStatus(
        job_id=job_id,
        status=job["status"],
        progress=job["progress"],
        error=job.get("error"),
    )

@router.get("/{job_id}/download/{file_type}")
async def download_file(job_id: str, file_type: str):
    filename_map = {
        "video": "edited_video.mp4",
        "original_video": "input.mp4",
        "thumbnail": "thumbnail.jpg",
        "subtitle": "subtitle.srt",
        "original_subtitle": "subtitle_original.srt"
    }
    
    if file_type not in filename_map:
        raise HTTPException(status_code=400, detail="Invalid file type")
        
    filename = filename_map[file_type]
    file_path = _safe_job_file_path(job_id, filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not ready")

    media_type = "video/mp4" if "video" in file_type else "image/jpeg" if file_type == "thumbnail" else "text/plain"
    return FileResponse(path=file_path, filename=filename, media_type=media_type)


@router.get("/{job_id}/thumbnail")
async def get_representative_thumbnail(job_id: str):
    """렌더링된 대표 썸네일(thumbnail.jpg)만 안전하게 반환합니다."""
    filename = "thumbnail.jpg"
    file_path = _safe_job_file_path(job_id, filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Thumbnail not found")

    return FileResponse(path=file_path, filename=filename, media_type="image/jpeg")


# ---------------------------------------------------------------------------
# 타임라인 썸네일 API
# ---------------------------------------------------------------------------

@router.get("/{job_id}/timeline-thumbnails")
async def get_timeline_thumbnails(job_id: str):
    """1초 간격 타임라인 썸네일 목록을 반환합니다."""
    job_dir = get_job_dir(job_id)
    input_path = os.path.join(job_dir, "input.mp4")
    if not os.path.exists(input_path):
        raise HTTPException(status_code=404, detail="Input video not found")

    meta = thumbnail_service.generate_timeline_thumbnails(job_id)

    base_url = f"/api/jobs/{job_id}/thumbnails"
    thumbnails = []
    for i in range(meta["count"]):
        filename = f"thumb_{i:03d}.jpg"
        thumbnails.append({
            "time": i,
            "url": f"{base_url}/{filename}",
        })

    return {
        "job_id": job_id,
        "duration": meta["duration"],
        "thumbnails": thumbnails,
    }


@router.get("/{job_id}/thumbnails/{filename}")
async def get_thumbnail_file(job_id: str, filename: str):
    """개별 타임라인 썸네일 파일을 반환합니다."""
    # 보안: 파일명에 경로 이탈 방지
    if "/" in filename or "\\" in filename or ".." in filename:
        raise HTTPException(status_code=400, detail="Invalid filename")

    job_dir = get_job_dir(job_id)
    file_path = os.path.join(job_dir, "thumbnails", filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Thumbnail not found")

    return FileResponse(path=file_path, filename=filename, media_type="image/jpeg")

