import os
import shutil
from pathlib import Path

from fastapi import APIRouter

from ..version import APP_VERSION

router = APIRouter()


def _jobs_dir() -> Path:
    return Path(__file__).resolve().parents[2] / "storage" / "jobs"


@router.get("/health")
def get_health():
    jobs_dir = _jobs_dir()
    storage_ready = False

    try:
        jobs_dir.mkdir(parents=True, exist_ok=True)
        storage_ready = jobs_dir.is_dir() and os.access(jobs_dir, os.W_OK)
    except OSError:
        storage_ready = False

    return {
        "ok": storage_ready,
        "app": "malrocut",
        "version": APP_VERSION,
        "backend": "running",
        "storage_ready": storage_ready,
        "jobs_dir": str(jobs_dir),
        "ffmpeg_available": shutil.which("ffmpeg") is not None,
        "ffprobe_available": shutil.which("ffprobe") is not None,
    }
