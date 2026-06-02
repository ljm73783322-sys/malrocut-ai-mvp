import uuid
import os
import zipfile
import tempfile
import json
import shutil
from datetime import datetime, timezone
from fastapi import APIRouter, UploadFile, File, BackgroundTasks, HTTPException
from fastapi.responses import FileResponse
from starlette.background import BackgroundTask
from pydantic import BaseModel
from PIL import Image, ImageDraw, ImageFont, UnidentifiedImageError
from PIL import Image, ImageColor, ImageDraw, ImageFont, UnidentifiedImageError

from ..models.job import JobStatus
from ..services import job_store, video_service, edit_service, render_service, thumbnail_service
from ..utils.paths import get_job_dir, STORAGE_DIR

router = APIRouter()


VALID_JOB_STATUSES = {"completed", "failed", "rendering", "pending", "unknown"}


def _storage_root() -> str:
    root = os.path.abspath(STORAGE_DIR)
    os.makedirs(root, exist_ok=True)
    return root


def _safe_job_dir_path(job_id: str) -> str:
    """Return a safe job directory path without creating it."""
    if not job_id or os.path.basename(job_id) != job_id:
        raise HTTPException(status_code=400, detail="Invalid job id")

    storage_root = _storage_root()
    job_dir = os.path.abspath(os.path.join(storage_root, job_id))

    if os.path.commonpath([storage_root, job_dir]) != storage_root:
        raise HTTPException(status_code=400, detail="Invalid job id")

    return job_dir


def _iso_from_timestamp(timestamp: float) -> str:
    return datetime.fromtimestamp(timestamp, tz=timezone.utc).isoformat().replace("+00:00", "Z")


def _read_job_json(job_dir: str) -> dict:
    job_json_path = os.path.join(job_dir, "job.json")
    if not os.path.isfile(job_json_path):
        return {}

    try:
        with open(job_json_path, "r", encoding="utf-8") as f:
            payload = json.load(f)
        return payload if isinstance(payload, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def _coerce_status(value: object, job_dir: str) -> str:
    status = value if isinstance(value, str) else ""
    if status in VALID_JOB_STATUSES:
        return status
    if os.path.isfile(os.path.join(job_dir, "edited_video.mp4")):
        return "completed"
    if os.path.isfile(os.path.join(job_dir, "input.mp4")):
        return "pending"
    return "unknown"


def _coerce_progress(value: object, status: str) -> int:
    try:
        progress = int(value)
    except (TypeError, ValueError):
        progress = 100 if status == "completed" else 0
    return max(0, min(100, progress))


def _job_summary(job_id: str, job_dir: str) -> dict:
    metadata = _read_job_json(job_dir)
    stat = os.stat(job_dir)
    fallback_time = _iso_from_timestamp(stat.st_mtime)
    status = _coerce_status(metadata.get("status"), job_dir)

    created_at = metadata.get("created_at") if isinstance(metadata.get("created_at"), str) else fallback_time
    updated_at = metadata.get("updated_at") if isinstance(metadata.get("updated_at"), str) else fallback_time

    has_video = os.path.isfile(os.path.join(job_dir, "edited_video.mp4"))
    has_thumbnail = os.path.isfile(os.path.join(job_dir, "thumbnail.jpg"))
    has_subtitle = os.path.isfile(os.path.join(job_dir, "subtitle.srt"))
    has_job_json = os.path.isfile(os.path.join(job_dir, "job.json"))
    has_edit_command = os.path.isfile(os.path.join(job_dir, "edit_command.json"))

    return {
        "job_id": job_id,
        "status": status,
        "progress": _coerce_progress(metadata.get("progress"), status),
        "created_at": created_at,
        "updated_at": updated_at,
        "has_video": has_video,
        "has_thumbnail": has_thumbnail,
        "has_subtitle": has_subtitle,
        "has_job_json": has_job_json,
        "has_edit_command": has_edit_command,
        "video_download_url": f"/api/jobs/{job_id}/download/video",
        "thumbnail_download_url": f"/api/jobs/{job_id}/download/thumbnail",
        "subtitle_download_url": f"/api/jobs/{job_id}/download/subtitle",
        "package_download_url": f"/api/jobs/{job_id}/download/package",
        "result_url": f"/result/{job_id}",
        "thumbnail_url": f"/api/jobs/{job_id}/thumbnail",
    }


@router.get("")
@router.get("/")
async def list_jobs():
    storage_root = _storage_root()
    summaries = []

    for entry in os.scandir(storage_root):
        if not entry.is_dir(follow_symlinks=False):
            continue

        job_id = entry.name
        try:
            job_dir = _safe_job_dir_path(job_id)
            if not os.path.isdir(job_dir):
                continue
            summaries.append(_job_summary(job_id, job_dir))
        except (HTTPException, OSError):
            continue

    summaries.sort(key=lambda item: item["updated_at"], reverse=True)
    return summaries


def _safe_job_file_path(job_id: str, filename: str) -> str:
    """Return a safe file path inside backend/storage/jobs/<job_id>."""
    if os.path.basename(filename) != filename:
        raise HTTPException(status_code=400, detail="Invalid filename")

    storage_root = _storage_root()
    job_dir = os.path.abspath(os.path.join(storage_root, job_id))
    file_path = os.path.abspath(os.path.join(job_dir, filename))

    if os.path.commonpath([storage_root, job_dir]) != storage_root:
        raise HTTPException(status_code=400, detail="Invalid job id")
    if os.path.commonpath([job_dir, file_path]) != job_dir:
        raise HTTPException(status_code=400, detail="Invalid file path")

    return file_path


def _require_existing_job_dir(job_id: str) -> str:
    job_dir = _safe_job_dir_path(job_id)
    if os.path.islink(job_dir) or not os.path.isdir(job_dir):
        raise HTTPException(status_code=404, detail="Job folder not found")
    return job_dir


def _thumbnail_success(job_id: str) -> dict:
    return {
        "ok": True,
        "job_id": job_id,
        "thumbnail_url": f"/api/jobs/{job_id}/thumbnail",
    }


def _parse_hex_color(value: str, field_name: str) -> tuple[int, int, int]:
    color_value = value.strip() if isinstance(value, str) else ""
    if color_value.startswith("#"):
        color_value = color_value[1:]

    if len(color_value) == 3:
        color_value = "".join(channel * 2 for channel in color_value)

    if len(color_value) != 6 or any(char not in "0123456789abcdefABCDEF" for char in color_value):
        raise HTTPException(status_code=400, detail=f"Invalid {field_name}")

    return (
        int(color_value[0:2], 16),
        int(color_value[2:4], 16),
        int(color_value[4:6], 16),
    )
    try:
        color = ImageColor.getrgb(value)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid {field_name}")

    if len(color) == 4:
        return color[:3]
    return color


def _parse_optional_background_color(value: str) -> tuple[int, int, int] | None:
    if value is None or value.strip() == "" or value.strip().lower() == "transparent":
        return None
    return _parse_hex_color(value, "background_color")


def _thumbnail_font(size: int):
    font_size = max(12, min(180, int(size)))
    candidates = [
        "C:/Windows/Fonts/malgunbd.ttf",
        "C:/Windows/Fonts/malgun.ttf",
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Bold.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    ]

    for candidate in candidates:
        if os.path.exists(candidate):
            try:
                return ImageFont.truetype(candidate, font_size)
            except OSError:
                continue

    return ImageFont.load_default()


def _text_position(position: str, image_size: tuple[int, int], text_size: tuple[int, int]) -> tuple[int, int]:
    width, height = image_size
    text_width, text_height = text_size
    x = min(max(40, (width - text_width) // 2), max(40, width - text_width - 40))

    if position == "top":
        y = 80
    elif position == "bottom":
        y = max(40, height - text_height - 90)
    else:
        y = max(40, (height - text_height) // 2)

    return x, y


def _background_box_bounds(
    x: int,
    y: int,
    text_size: tuple[int, int],
    image_size: tuple[int, int],
    padding: int = 28,
) -> tuple[int, int, int, int]:
    text_width, text_height = text_size
    image_width, image_height = image_size
    return (
        max(0, x - padding),
        max(0, y - padding),
        min(image_width, x + text_width + padding),
        min(image_height, y + text_height + padding),
    )

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

class ThumbnailTextRequest(BaseModel):
    text: str
    font_size: int = 64
    text_color: str = "#FFFF00"
    background_color: str = "#000000"
    position: str = "center"
    reset_base: bool = False


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

def _build_result_package_response(job_id: str) -> FileResponse:
    """완성 결과물을 ZIP으로 묶어 반환합니다."""
    storage_root = _storage_root()
    job_dir = os.path.abspath(os.path.join(storage_root, job_id))

    if os.path.commonpath([storage_root, job_dir]) != storage_root:
        raise HTTPException(status_code=400, detail="Invalid job id")
    if not os.path.isdir(job_dir):
        raise HTTPException(status_code=404, detail="Job folder not found")

    package_files = [
        "edited_video.mp4",
        "thumbnail.jpg",
        "subtitle.srt",
        "job.json",
        "edit_command.json",
    ]

    existing_files: list[tuple[str, str]] = []
    for filename in package_files:
        path = _safe_job_file_path(job_id, filename)
        if os.path.isfile(path):
            existing_files.append((filename, path))

    if not existing_files:
        raise HTTPException(status_code=404, detail="No downloadable result files found")

    tmp = tempfile.NamedTemporaryFile(prefix=f"malrocut-result-{job_id}-", suffix=".zip", delete=False)
    zip_path = tmp.name
    tmp.close()

    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for filename, path in existing_files:
            zf.write(path, arcname=filename)

    return FileResponse(
        path=zip_path,
        filename=f"malrocut-result-{job_id}.zip",
        media_type="application/zip",
        background=BackgroundTask(os.remove, zip_path),
    )


@router.get("/{job_id}/download/package")
async def download_result_package(job_id: str):
    return _build_result_package_response(job_id)


@router.get("/{job_id}/download/{file_type}")
async def download_file(job_id: str, file_type: str):
    if file_type == "package":
        return _build_result_package_response(job_id)

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


@router.post("/{job_id}/thumbnail/upload")
async def upload_job_thumbnail(job_id: str, file: UploadFile = File(...)):
    job_dir = _require_existing_job_dir(job_id)

    allowed_extensions = {".png", ".jpg", ".jpeg", ".webp"}
    extension = os.path.splitext(file.filename or "")[1].lower()
    if extension not in allowed_extensions:
        raise HTTPException(status_code=400, detail="Invalid image type")

    thumbnail_path = os.path.join(job_dir, "thumbnail.jpg")

    base_path = os.path.join(job_dir, "thumbnail_base.jpg")

    try:
        with Image.open(file.file) as image:
            clean_image = image.convert("RGB")
            clean_image.save(thumbnail_path, format="JPEG", quality=92)
            clean_image.save(base_path, format="JPEG", quality=92)
    except (UnidentifiedImageError, OSError, ValueError):
        raise HTTPException(status_code=400, detail="Invalid image file")

    return _thumbnail_success(job_id)


@router.post("/{job_id}/thumbnail/text")
async def update_job_thumbnail_text(job_id: str, req: ThumbnailTextRequest):
    job_dir = _require_existing_job_dir(job_id)
    thumbnail_path = os.path.join(job_dir, "thumbnail.jpg")
    base_path = os.path.join(job_dir, "thumbnail_base.jpg")

    text = req.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="Thumbnail text is required")
    if req.position not in {"center", "top", "bottom"}:
        raise HTTPException(status_code=400, detail="Invalid position")

    # text_color controls the rendered text glyphs.
    text_color = _parse_hex_color(req.text_color, "text_color")
    # background_color controls only the rectangle behind the text.
    text_color = _parse_hex_color(req.text_color, "text_color")
    background_color = _parse_optional_background_color(req.background_color)
    font = _thumbnail_font(req.font_size)

    try:
        if req.reset_base and os.path.isfile(thumbnail_path):
            with Image.open(thumbnail_path) as current:
                current.convert("RGB").save(base_path, format="JPEG", quality=92)

        if not os.path.isfile(base_path) and os.path.isfile(thumbnail_path):
            with Image.open(thumbnail_path) as current:
                current.convert("RGB").save(base_path, format="JPEG", quality=92)

        if os.path.isfile(base_path):
            with Image.open(base_path) as base_image:
                image = base_image.convert("RGB")
        else:
            image = Image.new("RGB", (1280, 720), (24, 24, 24))

        draw = ImageDraw.Draw(image)
        text_box = draw.multiline_textbbox((0, 0), text, font=font, spacing=12, stroke_width=3)
        text_width = text_box[2] - text_box[0]
        text_height = text_box[3] - text_box[1]
        x, y = _text_position(req.position, image.size, (text_width, text_height))

        if background_color is not None:
            # Draw the selected background_color as the text box fill.
            # This must stay separate from the black stroke used only around glyphs.
            background_box = _background_box_bounds(
                x,
                y,
                (text_width, text_height),
                image.size,
            )
            draw.rectangle(background_box, fill=background_color)
     
        # TODO: Phase 3 drag-and-drop editor should let users place text visually.
        draw.multiline_text(
            (x, y),
            text,
            font=font,
            fill=text_color,
            spacing=12,
            align="center",
            stroke_width=3,
            stroke_fill=(0, 0, 0),
        )
        image.save(thumbnail_path, format="JPEG", quality=92)
    except OSError:
        raise HTTPException(status_code=400, detail="Thumbnail could not be updated")

    return _thumbnail_success(job_id)


@router.delete("/{job_id}")
async def delete_job(job_id: str):
    job_dir = _safe_job_dir_path(job_id)

    if os.path.islink(job_dir) or not os.path.isdir(job_dir):
        raise HTTPException(status_code=404, detail="Job folder not found")

    shutil.rmtree(job_dir)
    return {"ok": True, "deleted": True, "job_id": job_id}


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

