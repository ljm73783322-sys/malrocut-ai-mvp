import asyncio
import os
import shutil
import subprocess
import sys
from .job_store import update_job_status
from ..utils.paths import get_job_dir

try:
    from PIL import Image, ImageDraw, ImageFont
    HAS_PILLOW = True
except ImportError:
    HAS_PILLOW = False

# ---------------------------------------------------------------------------
# Subtitle text to be burned into the video
# ---------------------------------------------------------------------------
SUBTITLE_TEXT = "말로컷 AI로 새롭게 편집된 영상입니다"

# ---------------------------------------------------------------------------
# Korean font candidates (Windows system fonts)
# ---------------------------------------------------------------------------
KOREAN_FONT_CANDIDATES = [
    r"C:\Windows\Fonts\malgun.ttf",       # 맑은 고딕 Regular
    r"C:\Windows\Fonts\malgunbd.ttf",     # 맑은 고딕 Bold
    r"C:\Windows\Fonts\gulim.ttc",        # 굴림
    r"C:\Windows\Fonts\batang.ttc",       # 바탕
    r"C:\Windows\Fonts\NanumGothic.ttf",  # 나눔고딕 (설치된 경우)
    r"C:\Windows\Fonts\arial.ttf",        # Arial (ASCII fallback)
]


def _find_korean_font() -> str | None:
    """Return path of first available Korean/system font, or None."""
    for p in KOREAN_FONT_CANDIDATES:
        if os.path.exists(p):
            return p
    return None


def _escape_ffmpeg_path(path: str) -> str:
    """
    Escape a file path for use inside an FFmpeg filtergraph string.
    On Windows forward-slashes are required; colons in drive letters must be
    escaped as '\\:' when the path appears inside a filter option value.
    """
    # Convert backslashes to forward slashes
    path = path.replace("\\", "/")
    # Escape the colon after drive letter  e.g. C:/ -> C\:/
    if len(path) >= 2 and path[1] == ":":
        path = path[0] + "\\:" + path[2:]
    return path


# ---------------------------------------------------------------------------
# Thumbnail helpers
# ---------------------------------------------------------------------------

def _create_fallback_thumbnail(path: str):
    if not HAS_PILLOW:
        return

    width, height = 1280, 720
    img = Image.new("RGB", (width, height), color=(40, 40, 40))
    draw = ImageDraw.Draw(img)

    def _load_font(size: int):
        for candidate in KOREAN_FONT_CANDIDATES:
            if os.path.exists(candidate):
                try:
                    return ImageFont.truetype(candidate, size)
                except Exception:
                    continue
        return ImageFont.load_default()

    font_large = _load_font(80)
    font_medium = _load_font(50)

    def draw_centered(text, font, y, color=(255, 255, 255)):
        try:
            bbox = draw.textbbox((0, 0), text, font=font)
            w = bbox[2] - bbox[0]
        except AttributeError:
            w, _ = draw.textsize(text, font=font)
        x = (width - w) / 2
        draw.text((x, y), text, font=font, fill=color)

    draw_centered("말로컷 AI", font_large, 100, color=(100, 150, 255))
    draw_centered("새롭게 편집된 영상", font_large, height / 2 - 50, color=(255, 255, 255))
    draw_centered("thumbnail.jpg", font_medium, height - 130, color=(150, 150, 150))

    img.save(path, format="JPEG", quality=90)


def _is_valid_thumbnail(path: str) -> bool:
    if not os.path.exists(path):
        return False
    if os.path.getsize(path) < 1024:
        return False
    if HAS_PILLOW:
        try:
            with Image.open(path) as img:
                w, h = img.size
                if w <= 10 or h <= 10:
                    return False
        except Exception:
            return False
    return True


# ---------------------------------------------------------------------------
# FFmpeg rendering helpers
# ---------------------------------------------------------------------------

def _run_ffmpeg(args: list[str]) -> bool:
    """
    Run an FFmpeg command. Returns True on success, False on failure.
    stderr is captured and discarded unless a non-zero exit code occurs
    (where we log to stderr for diagnostics without crashing the server).
    """
    try:
        result = subprocess.run(
            args,
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            # Do NOT use shell=True — avoids Windows path quoting pitfalls
        )
        return True
    except subprocess.CalledProcessError as exc:
        # Print stderr so developers can diagnose filter issues
        print(
            f"[render_service] FFmpeg failed (exit {exc.returncode}):\n"
            f"{exc.stderr.decode(errors='replace')}",
            file=sys.stderr,
        )
        return False
    except FileNotFoundError:
        print("[render_service] FFmpeg executable not found.", file=sys.stderr)
        return False


def _build_filtergraph(font_path: str | None, video_width: int, video_height: int) -> str:
    """
    Build the FFmpeg -vf filtergraph string that applies all visible edits:

    1. zoompan-style zoom: crop centre 1/1.03 of the frame, scale back to original
    2. brightness +0.06 and contrast +1.05 via eq filter
    3. semi-transparent black box covering the bottom subtitle band
    4. large Korean subtitle text centred at the bottom

    If no Korean font is available the drawtext filter is omitted.
    """

    # ── 1. Zoom + colour correction ────────────────────────────────────────
    # crop to the inner 97% (1/1.03 ≈ 0.9709), then scale back
    filters = [
        "crop=iw/1.03:ih/1.03",
        "scale=iw:ih",
        "eq=brightness=0.06:contrast=1.05:saturation=1.1",
    ]

    # ── 2. Semi-transparent black bar at the bottom ────────────────────────
    # Covers roughly the bottom 18% of the frame (old subtitle area)
    bar_height = max(120, int(video_height * 0.18))
    bar_y = video_height - bar_height
    filters.append(
        f"drawbox=x=0:y={bar_y}:w=iw:h={bar_height}:color=black@0.70:t=fill"
    )

    # ── 3. Subtitle text ────────────────────────────────────────────────────
    if font_path:
        esc_font = _escape_ffmpeg_path(font_path)
        # Font size: at least 48px; scale with video height for readability
        font_size = max(48, int(video_height * 0.065))
        # Vertical position: 90 % down the frame so it sits in the black bar
        text_y = f"h*0.90-{font_size // 2}"
        filters.append(
            f"drawtext=fontfile='{esc_font}'"
            f":text='{SUBTITLE_TEXT}'"
            f":fontsize={font_size}"
            f":fontcolor=white"
            f":borderw=3"
            f":bordercolor=black"
            f":x=(w-text_w)/2"
            f":y={text_y}"
        )

    return ",".join(filters)


def _get_video_dimensions(video_path: str) -> tuple[int, int]:
    """Return (width, height) of the video, or (1920, 1080) as fallback."""
    try:
        result = subprocess.run(
            [
                "ffprobe",
                "-v", "error",
                "-select_streams", "v:0",
                "-show_entries", "stream=width,height",
                "-of", "csv=p=0",
                video_path,
            ],
            capture_output=True,
            text=True,
        )
        parts = result.stdout.strip().split(",")
        if len(parts) >= 2:
            return int(parts[0]), int(parts[1])
    except Exception:
        pass
    return 1920, 1080


# ---------------------------------------------------------------------------
# Main async render function
# ---------------------------------------------------------------------------

async def render_video_mock(job_id: str):
    update_job_status(job_id, "rendering", 0)

    # Fake progress while we set up
    for i in range(1, 4):
        await asyncio.sleep(0.4)
        update_job_status(job_id, "rendering", i * 8)

    job_dir = get_job_dir(job_id)
    input_path = os.path.join(job_dir, "input.mp4")
    output_video_path = os.path.join(job_dir, "edited_video.mp4")
    thumbnail_path = os.path.join(job_dir, "thumbnail.jpg")
    subtitle_path = os.path.join(job_dir, "subtitle.srt")

    has_ffmpeg = shutil.which("ffmpeg") is not None

    # ── Video rendering ─────────────────────────────────────────────────────
    if os.path.exists(input_path):
        if has_ffmpeg:
            # Detect source dimensions for filter tuning
            width, height = _get_video_dimensions(input_path)
            font_path = _find_korean_font()

            vf_filter = _build_filtergraph(font_path, width, height)

            ffmpeg_args = [
                "ffmpeg", "-y",
                "-i", input_path,
                "-vf", vf_filter,
                "-c:v", "libx264",
                "-preset", "fast",
                "-crf", "23",
                "-c:a", "aac",
                "-b:a", "128k",
                output_video_path,
            ]

            update_job_status(job_id, "rendering", 30)
            success = _run_ffmpeg(ffmpeg_args)

            if not success:
                # FFmpeg failed → safe copy fallback
                print(
                    "[render_service] FFmpeg filter failed; copying input as fallback.",
                    file=sys.stderr,
                )
                shutil.copy(input_path, output_video_path)

            update_job_status(job_id, "rendering", 65)

            # ── Thumbnail extraction ────────────────────────────────────────
            for seek in ("00:00:01", "00:00:00"):
                ok = _run_ffmpeg([
                    "ffmpeg", "-y",
                    "-i", input_path,
                    "-ss", seek,
                    "-vframes", "1",
                    thumbnail_path,
                ])
                if ok and _is_valid_thumbnail(thumbnail_path):
                    break

            if not _is_valid_thumbnail(thumbnail_path):
                _create_fallback_thumbnail(thumbnail_path)

        else:
            # No FFmpeg → plain copy
            shutil.copy(input_path, output_video_path)
            _create_fallback_thumbnail(thumbnail_path)

    else:
        # No input file at all
        open(output_video_path, "wb").close()
        _create_fallback_thumbnail(thumbnail_path)

    update_job_status(job_id, "rendering", 75)

    # ── Subtitle file ───────────────────────────────────────────────────────
    with open(subtitle_path, "w", encoding="utf-8") as f:
        f.write(
            "1\n"
            "00:00:00,000 --> 00:00:05,000\n"
            f"{SUBTITLE_TEXT}\n"
            "\n"
        )

    # Fake progress to 100
    for i in range(8, 11):
        await asyncio.sleep(0.2)
        update_job_status(job_id, "rendering", i * 10)

    update_job_status(job_id, "completed", 100)
