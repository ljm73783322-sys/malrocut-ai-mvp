#!/usr/bin/env python3
"""
말로컷 AI 렌더링 핵심 검증 스크립트.

검증 항목:
- synthetic input.mp4 자동 생성 (ffmpeg)
- edit_command.json(UTF-8, 한글) 저장
- render_service.render_video_mock 실제 호출
- output 존재/크기/해시/metadata/job.json/subtitle.srt 검증
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import shutil
import subprocess
import sys
import uuid
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = REPO_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.services.job_store import create_job, get_job  # noqa: E402
from app.services.render_service import render_video_mock  # noqa: E402
from app.utils.paths import get_job_dir  # noqa: E402

KOREAN_TEXT = "말로컷 AI로 새롭게 편집된 영상입니다"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            chunk = f.read(1024 * 1024)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def require_ffmpeg() -> None:
    ffmpeg = shutil.which("ffmpeg")
    ffprobe = shutil.which("ffprobe")
    if not ffmpeg or not ffprobe:
        raise RuntimeError(
            "FFmpeg/ffprobe not found. Install FFmpeg and ensure PATH is configured."
        )


def build_synthetic_video(path: Path) -> None:
    """
    10초 synthetic 영상(+오디오) 생성.
    testsrc + sine 오디오를 사용해 trim/concat 경로도 검증 가능하게 구성.
    """
    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", "testsrc=duration=10:size=1280x720:rate=30",
        "-f", "lavfi", "-i", "sine=frequency=880:duration=10",
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-shortest",
        str(path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"Failed to generate synthetic video: {result.stderr}")


def write_edit_command(path: Path) -> dict:
    payload = {
        "prompt": "1~3초 영상과 6~8초 영상 순서 바꿔줘. 기존 자막을 가리고 새 한국어 자막을 크게 넣어줘. 화면도 살짝 밝게 해줘.",
        "edit_command": {
            "add_subtitle": True,
            "cover_subtitle_area": True,
            "subtitle_text": KOREAN_TEXT,
            "subtitle_size": "large",
            "subtitle_language": "ko",
            "zoom": 1.03,
            "brightness": 0.08,
            "contrast": 1.05,
            "cut_silence": False,
            "clip_reorder": {
                "enabled": True,
                "clips": [
                    {"id": "clip_1", "source_start": 1.0, "source_end": 3.0, "new_order": 2},
                    {"id": "clip_2", "source_start": 6.0, "source_end": 8.0, "new_order": 1},
                ],
            },
        },
    }
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    return payload


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


async def run() -> None:
    require_ffmpeg()

    job_id = f"verify-{uuid.uuid4().hex[:10]}"
    create_job(job_id)
    job_dir = Path(get_job_dir(job_id))
    input_path = job_dir / "input.mp4"
    output_path = job_dir / "edited_video.mp4"
    thumb_path = job_dir / "thumbnail.jpg"
    subtitle_path = job_dir / "subtitle.srt"
    edit_cmd_path = job_dir / "edit_command.json"
    job_json_path = job_dir / "job.json"

    build_synthetic_video(input_path)
    _ = write_edit_command(edit_cmd_path)

    await render_video_mock(job_id)

    # Core output assertions
    assert_true(output_path.exists(), "edited_video.mp4 not found")
    assert_true(output_path.stat().st_size > 1024, "edited_video.mp4 size is too small")

    input_hash = sha256_file(input_path)
    output_hash = sha256_file(output_path)
    assert_true(
        input_hash != output_hash,
        "Rendered output is identical to input despite edit commands",
    )

    assert_true(job_json_path.exists(), "job.json not found")
    with job_json_path.open("r", encoding="utf-8") as f:
        job_meta = json.load(f)
    assert_true(job_meta.get("status") == "completed", f"job.json status is not completed: {job_meta}")
    assert_true(job_meta.get("error") is None, f"job.json error is not null: {job_meta.get('error')}")

    assert_true(thumb_path.exists(), "thumbnail.jpg not found")
    assert_true(thumb_path.stat().st_size > 1024, "thumbnail.jpg size is too small")

    assert_true(subtitle_path.exists(), "subtitle.srt not found")
    sub_text = subtitle_path.read_text(encoding="utf-8")
    assert_true(KOREAN_TEXT in sub_text, "subtitle.srt UTF-8/Korean text validation failed")

    edit_text = edit_cmd_path.read_text(encoding="utf-8")
    assert_true(KOREAN_TEXT in edit_text, "edit_command.json UTF-8/Korean text validation failed")

    # status check from in-memory store
    job = get_job(job_id)
    assert_true(job is not None, "job store entry missing")
    assert_true(job.get("status") == "completed", f"job store status is not completed: {job}")
    assert_true(job.get("error") is None, f"job store error is not null: {job.get('error')}")

    print("✅ Render verification passed")
    print(f"job_id={job_id}")
    print(f"job_dir={job_dir}")
    print(f"input_sha256={input_hash}")
    print(f"output_sha256={output_hash}")


if __name__ == "__main__":
    try:
        asyncio.run(run())
    except Exception as exc:
        print("❌ Render verification failed")
        print("원인:")
        print(str(exc))
        sys.exit(1)
