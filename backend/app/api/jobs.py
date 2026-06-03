import uuid
import os
import zipfile
import tempfile
import json
import shutil
import sys
from datetime import datetime, timezone
from fastapi import APIRouter, UploadFile, File, BackgroundTasks, HTTPException
from fastapi.responses import FileResponse
from starlette.background import BackgroundTask
from pydantic import BaseModel
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont, UnidentifiedImageError

from ..models.job import JobStatus
from ..services import job_store, video_service, edit_service, render_service, thumbnail_service
from ..utils.paths import get_job_dir, STORAGE_DIR

router = APIRouter()


VALID_JOB_STATUSES = {"completed", "failed", "rendering", "pending", "unknown"}
THUMBNAIL_BASE_FILENAME = "thumbnail_base.jpg"
THUMBNAIL_UPLOADED_BASE_FILENAME = "thumbnail_uploaded_base.jpg"
THUMBNAIL_SELECTED_BASE_FILENAME = "thumbnail_selected_base.jpg"
VALID_THUMBNAIL_COVER_STYLES = {"black_box", "blur", "dim", "none"}
DEFAULT_THUMBNAIL_COVER_STYLE = "blur"
DEFAULT_THUMBNAIL_SUBTITLE_COVER_RATIO = 0.30
DEFAULT_THUMBNAIL_SUBTITLE_COVER_CENTER_Y = 0.68


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


def _clamp_number(value: float, minimum: float, maximum: float) -> float:
    return min(maximum, max(minimum, value))


def _text_position(position: str, image_size: tuple[int, int], text_size: tuple[int, int]) -> tuple[int, int]:
    width, height = image_size
    text_width, text_height = text_size
    x = int(_clamp_number((width - text_width) / 2, 0, max(0, width - text_width)))

    if position == "top":
        y = int(_clamp_number(height * 0.2 - text_height / 2, 0, max(0, height - text_height)))
    elif position == "bottom":
        y = int(_clamp_number(height * 0.8 - text_height / 2, 0, max(0, height - text_height)))
    else:
        y = int(_clamp_number((height - text_height) / 2, 0, max(0, height - text_height)))

    return x, y


def _text_position_from_percent(
    position_x: float,
    position_y: float,
    image_size: tuple[int, int],
    text_bbox: tuple[int, int, int, int],
) -> tuple[int, int]:
    image_width, image_height = image_size
    bbox_left, bbox_top, bbox_right, bbox_bottom = text_bbox
    text_width = bbox_right - bbox_left
    text_height = bbox_bottom - bbox_top

    center_x = (_clamp_number(float(position_x), 0, 100) / 100) * image_width
    center_y = (_clamp_number(float(position_y), 0, 100) / 100) * image_height
    box_left = _clamp_number(center_x - text_width / 2, 0, max(0, image_width - text_width))
    box_top = _clamp_number(center_y - text_height / 2, 0, max(0, image_height - text_height))

    return int(round(box_left - bbox_left)), int(round(box_top - bbox_top))


def _thumbnail_base_path(job_dir: str) -> str:
    return os.path.join(job_dir, THUMBNAIL_BASE_FILENAME)


def _thumbnail_uploaded_base_path(job_dir: str) -> str:
    return os.path.join(job_dir, THUMBNAIL_UPLOADED_BASE_FILENAME)


def _thumbnail_selected_base_path(job_dir: str) -> str:
    return os.path.join(job_dir, THUMBNAIL_SELECTED_BASE_FILENAME)


def _read_edit_command(job_dir: str) -> dict:
    edit_command_path = os.path.join(job_dir, "edit_command.json")
    if not os.path.isfile(edit_command_path):
        return {}

    try:
        with open(edit_command_path, "r", encoding="utf-8") as f:
            payload = json.load(f)
        return payload if isinstance(payload, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def _thumbnail_subtitle_cover_ratio(job_dir: str) -> float:
    cmd = _read_edit_command(job_dir)

    try:
        ratio = float(cmd.get("subtitle_cover_ratio", DEFAULT_THUMBNAIL_SUBTITLE_COVER_RATIO))
    except (TypeError, ValueError):
        ratio = DEFAULT_THUMBNAIL_SUBTITLE_COVER_RATIO
    return _clamp_number(ratio, 0, 0.5)


def _normalize_thumbnail_cover_style(value: str | None) -> str:
    style = (value or DEFAULT_THUMBNAIL_COVER_STYLE).strip().lower()
    if style not in VALID_THUMBNAIL_COVER_STYLES:
        raise HTTPException(status_code=400, detail="Invalid cover_style")
    return style


def _save_image_as_jpeg(source_path: str, destination_path: str) -> None:
    with Image.open(source_path) as source_image:
        source_image.convert("RGB").save(destination_path, format="JPEG", quality=92)


def _ensure_thumbnail_base(job_dir: str) -> str:
    """Ensure thumbnail_base.jpg exists using the trusted source priority order."""
    base_path = _thumbnail_base_path(job_dir)
    selected_base_path = _thumbnail_selected_base_path(job_dir)
    uploaded_base_path = _thumbnail_uploaded_base_path(job_dir)
    input_path = os.path.join(job_dir, "input.mp4")
    thumbnail_path = os.path.join(job_dir, "thumbnail.jpg")
    job_id = os.path.basename(job_dir)

    if os.path.isfile(selected_base_path):
        _save_image_as_jpeg(selected_base_path, base_path)
        return base_path

    if os.path.isfile(uploaded_base_path):
        _save_image_as_jpeg(uploaded_base_path, base_path)
        return base_path

    try:
        os.remove(base_path)
    except FileNotFoundError:
        pass
    except OSError as exc:
        print(f"[jobs] thumbnail_base.jpg 삭제 실패: {exc}", file=sys.stderr)

    if os.path.isfile(input_path):
        render_service._ensure_valid_thumbnail(base_path, input_path)
        if render_service._is_valid_thumbnail(base_path):
            return base_path

    if os.path.isfile(thumbnail_path):
        print(
            f"[jobs] WARNING: {job_id} thumbnail_base.jpg 생성 실패 - "
            "오염 가능성이 있는 thumbnail.jpg를 최후 fallback으로 사용합니다.",
            file=sys.stderr,
        )
        _save_image_as_jpeg(thumbnail_path, base_path)
        return base_path

    raise HTTPException(status_code=404, detail="Thumbnail base not found")


def regenerate_thumbnail_base(job_id: str) -> str:
    """Regenerate a clean base thumbnail without trusting a possibly text-composited thumbnail.jpg."""
    job_dir = _require_existing_job_dir(job_id)
    return _ensure_thumbnail_base(job_dir)


def _thumbnail_subtitle_cover_bounds(image_size: tuple[int, int], job_dir: str) -> tuple[int, int, int, int] | None:
    ratio = _thumbnail_subtitle_cover_ratio(job_dir)
    if ratio <= 0:
        return None

    image_width, image_height = image_size
    cover_height = max(1, int(image_height * ratio))

    # 기존 자막은 맨 아래가 아니라 화면 중하단에 위치하는 경우가 많습니다.
    # 하단 30%만 덮으면 y=70% 위쪽 자막 픽셀이 남을 수 있으므로,
    # 기본 30% band를 화면 높이 68% 중심에 배치해 대략 53%~83%를 처리합니다.
    cover_center_y = int(image_height * DEFAULT_THUMBNAIL_SUBTITLE_COVER_CENTER_Y)
    cover_top = int(cover_center_y - cover_height / 2)
    cover_top = int(_clamp_number(cover_top, 0, max(0, image_height - cover_height)))
    cover_bottom = min(image_height, cover_top + cover_height)
    return (0, cover_top, image_width, cover_bottom)


def _apply_thumbnail_subtitle_cover(image: Image.Image, job_dir: str, cover_style: str | None) -> Image.Image:
    style = _normalize_thumbnail_cover_style(cover_style)
    if style == "none":
        return image

    cover_box = _thumbnail_subtitle_cover_bounds(image.size, job_dir)
    if cover_box is None:
        return image

    if style == "black_box":
        draw = ImageDraw.Draw(image)
        draw.rectangle(cover_box, fill=(0, 0, 0))
        return image

    region = image.crop(cover_box)
    if style == "dim":
        covered_region = ImageEnhance.Brightness(region).enhance(0.35)
    else:
        blur_radius = max(8, int(image.size[1] * 0.025))
        covered_region = region.filter(ImageFilter.GaussianBlur(radius=blur_radius))
        covered_region = ImageEnhance.Brightness(covered_region).enhance(0.72)

    image.paste(covered_region, cover_box)
    return image


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
    position_x: float | None = None
    position_y: float | None = None
    reset_base: bool = False
    cover_style: str = DEFAULT_THUMBNAIL_COVER_STYLE


class ThumbnailBaseSelectRequest(BaseModel):
    filename: str


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

    base_path = _thumbnail_base_path(job_dir)

    try:
        with Image.open(file.file) as image:
            clean_image = image.convert("RGB")
            selected_base_path = _thumbnail_selected_base_path(job_dir)
            uploaded_base_path = _thumbnail_uploaded_base_path(job_dir)
            clean_image.save(thumbnail_path, format="JPEG", quality=92)
            clean_image.save(base_path, format="JPEG", quality=92)
            clean_image.save(uploaded_base_path, format="JPEG", quality=92)
            try:
                os.remove(selected_base_path)
            except FileNotFoundError:
                pass
            except OSError:
                pass
    except (UnidentifiedImageError, OSError, ValueError):
        raise HTTPException(status_code=400, detail="Invalid image file")

    return _thumbnail_success(job_id)


@router.post("/{job_id}/thumbnail/text")
async def update_job_thumbnail_text(job_id: str, req: ThumbnailTextRequest):
    job_dir = _require_existing_job_dir(job_id)
    thumbnail_path = os.path.join(job_dir, "thumbnail.jpg")

    text = req.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="Thumbnail text is required")
    if req.position not in {"center", "top", "bottom"}:
        raise HTTPException(status_code=400, detail="Invalid position")

    # text_color controls the rendered text glyphs.
    text_color = _parse_hex_color(req.text_color, "text_color")
    # background_color controls only the rectangle behind the text.
    background_color = _parse_optional_background_color(req.background_color)
    font = _thumbnail_font(req.font_size)

    try:
        base_path = regenerate_thumbnail_base(job_id)
        with Image.open(base_path) as base_image:
            image = base_image.convert("RGB")

        image = _apply_thumbnail_subtitle_cover(image, job_dir, req.cover_style)
        draw = ImageDraw.Draw(image)
        text_box = draw.multiline_textbbox((0, 0), text, font=font, spacing=12, stroke_width=3)
        text_width = text_box[2] - text_box[0]
        text_height = text_box[3] - text_box[1]
        if req.position_x is not None and req.position_y is not None:
            x, y = _text_position_from_percent(req.position_x, req.position_y, image.size, text_box)
        else:
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


@router.post("/{job_id}/thumbnail/base/regenerate")
async def regenerate_representative_thumbnail_base(job_id: str):
    regenerate_thumbnail_base(job_id)
    return _thumbnail_success(job_id)


@router.post("/{job_id}/thumbnail/base/select")
async def select_representative_thumbnail_base(job_id: str, req: ThumbnailBaseSelectRequest):
    job_dir = _require_existing_job_dir(job_id)
    filename = req.filename
    if os.path.basename(filename) != filename or not filename.lower().endswith(".jpg"):
        raise HTTPException(status_code=400, detail="Invalid thumbnail filename")

    source_path = os.path.join(job_dir, "thumbnails", filename)
    if not os.path.isfile(source_path):
        raise HTTPException(status_code=404, detail="Thumbnail candidate not found")

    base_path = _thumbnail_base_path(job_dir)
    selected_base_path = _thumbnail_selected_base_path(job_dir)
    try:
        _save_image_as_jpeg(source_path, base_path)
        _save_image_as_jpeg(source_path, selected_base_path)
    except OSError:
        raise HTTPException(status_code=400, detail="Thumbnail candidate could not be selected")

    return _thumbnail_success(job_id)


@router.get("/{job_id}/thumbnail/base")
async def get_representative_thumbnail_base(job_id: str, cover_style: str = DEFAULT_THUMBNAIL_COVER_STYLE):
    """문구 편집용 base 썸네일을 반환하되 기존 자막 영역은 선택한 방식으로 정리합니다."""
    job_dir = _require_existing_job_dir(job_id)
    try:
        source_path = regenerate_thumbnail_base(job_id)
        with Image.open(source_path) as source_image:
            image = source_image.convert("RGB")
            image = _apply_thumbnail_subtitle_cover(image, job_dir, cover_style)
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".jpg")
            tmp_path = tmp.name
            tmp.close()
            image.save(tmp_path, format="JPEG", quality=92)
    except OSError:
        raise HTTPException(status_code=400, detail="Thumbnail could not be loaded")

    return FileResponse(
        path=tmp_path,
        filename="thumbnail_base.jpg",
        media_type="image/jpeg",
        background=BackgroundTask(os.remove, tmp_path),
    )


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

