"""
thumbnail_service.py
--------------------
input.mp4에서 1초 간격으로 타임라인 썸네일을 생성합니다.

- FFmpeg가 있으면 fps=1로 프레임 추출
- FFmpeg 실패 시 Pillow fallback (시간 표시가 있는 색상 이미지)
- 썸네일 파일은 최소 1KB 이상의 유효한 JPG
"""

import os
import subprocess
import sys
import math

from ..utils.paths import get_job_dir

try:
    from PIL import Image, ImageDraw, ImageFont
    HAS_PILLOW = True
except ImportError:
    HAS_PILLOW = False

THUMB_WIDTH = 160
THUMB_HEIGHT = 90
MIN_VALID_BYTES = 1024


def _get_video_duration(video_path: str) -> float:
    """
    영상 길이를 초 단위로 반환합니다.
    1차: ffprobe  →  2차: ffmpeg -i stderr 파싱  →  실패 시 0.0
    """
    # ── 1차: ffprobe ──────────────────────────────────────────────────────
    try:
        result = subprocess.run(
            [
                "ffprobe",
                "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                video_path,
            ],
            capture_output=True,
            text=True,
            timeout=15,
        )
        val = result.stdout.strip()
        if val:
            d = float(val)
            if d > 0:
                return d
    except Exception as exc:
        print(f"[thumbnail_service] ffprobe duration 실패: {exc}", file=sys.stderr)

    # ── 2차: ffmpeg -i stderr에서 Duration 파싱 ──────────────────────────
    try:
        import re
        result = subprocess.run(
            ["ffmpeg", "-i", video_path],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
            timeout=15,
        )
        # "Duration: 00:00:45.12" 패턴 검색
        match = re.search(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)", result.stderr)
        if match:
            h, m, s = float(match.group(1)), float(match.group(2)), float(match.group(3))
            d = h * 3600 + m * 60 + s
            if d > 0:
                return d
    except Exception as exc:
        print(f"[thumbnail_service] ffmpeg -i duration 파싱 실패: {exc}", file=sys.stderr)

    return 0.0


def _generate_thumbnails_ffmpeg(video_path: str, out_dir: str, duration: float) -> bool:
    """FFmpeg로 1초 간격 썸네일을 생성합니다."""
    try:
        ok = subprocess.run(
            [
                "ffmpeg", "-y",
                "-i", video_path,
                "-vf", f"fps=1,scale={THUMB_WIDTH}:{THUMB_HEIGHT}",
                "-q:v", "5",
                os.path.join(out_dir, "thumb_%03d.jpg"),
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            timeout=120,
        )
        if ok.returncode != 0:
            print(
                f"[thumbnail_service] FFmpeg 썸네일 생성 실패:\n"
                f"{ok.stderr.decode(errors='replace')}",
                file=sys.stderr,
            )
            return False

        # FFmpeg fps=1 → thumb_001.jpg(0초), thumb_002.jpg(1초), ...
        # 파일명을 thumb_000.jpg(0초), thumb_001.jpg(1초)로 맞춤
        count = int(math.ceil(duration))
        for i in range(count):
            src = os.path.join(out_dir, f"thumb_{i + 1:03d}.jpg")
            dst = os.path.join(out_dir, f"thumb_{i:03d}.jpg")
            if os.path.exists(src):
                if src != dst:
                    os.replace(src, dst)

        # 남은 불필요 파일 정리
        for f in os.listdir(out_dir):
            if f.startswith("thumb_") and f.endswith(".jpg"):
                idx_str = f.replace("thumb_", "").replace(".jpg", "")
                try:
                    idx = int(idx_str)
                    if idx >= count:
                        os.remove(os.path.join(out_dir, f))
                except ValueError:
                    pass

        return True
    except FileNotFoundError:
        print("[thumbnail_service] ffmpeg 실행 파일을 찾을 수 없습니다.", file=sys.stderr)
        return False
    except Exception as exc:
        print(f"[thumbnail_service] FFmpeg 썸네일 생성 예외: {exc}", file=sys.stderr)
        return False


def _generate_thumbnails_pillow(out_dir: str, duration: float) -> bool:
    """Pillow로 시간 정보가 표시된 fallback 썸네일을 생성합니다."""
    if not HAS_PILLOW:
        return False

    count = int(math.ceil(duration))
    if count <= 0:
        count = 1

    for i in range(count):
        img = Image.new("RGB", (THUMB_WIDTH, THUMB_HEIGHT), color=(40, 40, 50))
        draw = ImageDraw.Draw(img)

        # 시간 표시
        try:
            font = ImageFont.truetype("arial.ttf", 20)
        except Exception:
            font = ImageFont.load_default()

        text = f"{i}s"
        bbox = draw.textbbox((0, 0), text, font=font)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
        draw.text(
            ((THUMB_WIDTH - tw) / 2, (THUMB_HEIGHT - th) / 2),
            text,
            fill=(200, 200, 200),
            font=font,
        )

        # 테두리
        draw.rectangle(
            [0, 0, THUMB_WIDTH - 1, THUMB_HEIGHT - 1],
            outline=(80, 80, 100),
            width=1,
        )

        path = os.path.join(out_dir, f"thumb_{i:03d}.jpg")
        img.save(path, "JPEG", quality=85)

    return True


def generate_timeline_thumbnails(job_id: str) -> dict:
    """
    타임라인 썸네일을 생성하고 메타데이터를 반환합니다.

    Returns:
        {
            "job_id": str,
            "duration": float,
            "count": int,
            "thumbnails_dir": str,  # 절대 경로
        }
    """
    job_dir = get_job_dir(job_id)
    input_path = os.path.join(job_dir, "input.mp4")
    thumbs_dir = os.path.join(job_dir, "thumbnails")
    os.makedirs(thumbs_dir, exist_ok=True)

    # 이미 생성된 썸네일이 있으면 스킵
    existing = [f for f in os.listdir(thumbs_dir) if f.startswith("thumb_") and f.endswith(".jpg")]
    duration = _get_video_duration(input_path) if os.path.exists(input_path) else 0.0

    if len(existing) >= 1 and all(
        os.path.getsize(os.path.join(thumbs_dir, f)) >= MIN_VALID_BYTES
        for f in existing[:3]  # 처음 3개만 검증
    ):
        count = len(existing)
        return {
            "job_id": job_id,
            "duration": duration,
            "count": count,
            "thumbnails_dir": thumbs_dir,
        }

    if not os.path.exists(input_path):
        return {
            "job_id": job_id,
            "duration": 0.0,
            "count": 0,
            "thumbnails_dir": thumbs_dir,
        }

    if duration <= 0:
        duration = 10.0  # 안전한 기본값

    # FFmpeg 시도
    success = _generate_thumbnails_ffmpeg(input_path, thumbs_dir, duration)

    # FFmpeg 실패 시 Pillow fallback
    if not success:
        _generate_thumbnails_pillow(thumbs_dir, duration)

    # 최종 카운트
    final_files = sorted([
        f for f in os.listdir(thumbs_dir)
        if f.startswith("thumb_") and f.endswith(".jpg")
    ])
    count = len(final_files)

    return {
        "job_id": job_id,
        "duration": duration,
        "count": count,
        "thumbnails_dir": thumbs_dir,
    }
