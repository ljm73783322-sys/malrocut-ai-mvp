"""
render_service.py
-----------------
MVP 렌더링 서비스.

FFmpeg가 설치된 경우:
  - edit_command.json의 zoom/brightness/subtitle 설정을 반영
  - drawtext 실패 시 자막 없이 재시도

FFmpeg가 없거나 모든 시도가 실패한 경우:
  - input.mp4를 edited_video.mp4로 복사 (재생 가능 보장)

결과 파일이 1 KB 미만이면 job 상태를 'failed'로 저장.

Windows PowerShell 환경에서 안전하게 동작하도록 subprocess 처리.
"""

import asyncio
import json
import os
import shutil
import subprocess
import sys
from .job_store import update_job_status, fail_job
from ..utils.paths import get_job_dir

try:
    from PIL import Image, ImageDraw, ImageFont
    HAS_PILLOW = True
except ImportError:
    HAS_PILLOW = False

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SUBTITLE_TEXT = "말로컷 AI로 새롭게 편집된 영상입니다"
MIN_VALID_BYTES = 1024  # 1 KB

# Windows system font candidates (tried in order)
KOREAN_FONT_CANDIDATES = [
    r"C:\Windows\Fonts\malgun.ttf",      # 맑은 고딕 Regular
    r"C:\Windows\Fonts\malgunbd.ttf",    # 맑은 고딕 Bold
    r"C:\Windows\Fonts\gulim.ttc",       # 굴림
    r"C:\Windows\Fonts\batang.ttc",      # 바탕
    r"C:\Windows\Fonts\NanumGothic.ttf", # 나눔고딕 (선택 설치)
    r"C:\Windows\Fonts\arial.ttf",       # Arial (ASCII fallback)
]


# ---------------------------------------------------------------------------
# Font helpers
# ---------------------------------------------------------------------------

def _find_korean_font() -> str | None:
    for p in KOREAN_FONT_CANDIDATES:
        if os.path.exists(p):
            return p
    return None


def _escape_ffmpeg_path(path: str) -> str:
    """
    FFmpeg filtergraph 안에서 파일 경로를 안전하게 사용하기 위한 이스케이프.
    - 백슬래시 → 슬래시
    - 드라이브 문자 뒤 콜론 → \\: (e.g. C:/ → C\\:/)
    """
    path = path.replace("\\", "/")
    if len(path) >= 2 and path[1] == ":":
        path = path[0] + "\\:" + path[2:]
    return path


def _load_pil_font(size: int):
    """Pillow용 폰트 로드. 실패 시 기본 폰트 반환."""
    for candidate in KOREAN_FONT_CANDIDATES:
        if os.path.exists(candidate):
            try:
                return ImageFont.truetype(candidate, size)
            except Exception:
                continue
    return ImageFont.load_default()


# ---------------------------------------------------------------------------
# Thumbnail helpers
# ---------------------------------------------------------------------------

def _create_fallback_thumbnail(path: str) -> bool:
    """
    Pillow로 1280×720 fallback 썸네일을 생성합니다.
    성공 시 True, 실패 시 False.
    """
    if not HAS_PILLOW:
        return False

    try:
        width, height = 1280, 720
        img = Image.new("RGB", (width, height), color=(30, 30, 45))
        draw = ImageDraw.Draw(img)

        font_title  = _load_pil_font(80)
        font_body   = _load_pil_font(55)
        font_footer = _load_pil_font(40)

        # 그라데이션 배경 대신 간단한 구분선
        draw.rectangle([0, 0, width, 8], fill=(100, 150, 255))
        draw.rectangle([0, height - 8, width, height], fill=(100, 150, 255))

        def draw_centered(text, font, y, color=(255, 255, 255)):
            try:
                bbox = draw.textbbox((0, 0), text, font=font)
                w = bbox[2] - bbox[0]
            except AttributeError:
                w, _ = draw.textsize(text, font=font)
            x = (width - w) / 2
            # 그림자
            draw.text((x + 2, y + 2), text, font=font, fill=(0, 0, 0, 180))
            draw.text((x, y), text, font=font, fill=color)

        draw_centered("말로컷 AI", font_title, 130, color=(120, 170, 255))
        draw_centered("편집된 영상입니다", font_body, 270, color=(240, 240, 240))
        draw_centered("thumbnail.jpg", font_footer, height - 110, color=(140, 140, 160))

        img.save(path, format="JPEG", quality=90)
        return True
    except Exception as exc:
        print(f"[render_service] Fallback thumbnail 생성 실패: {exc}", file=sys.stderr)
        return False


def _is_valid_thumbnail(path: str) -> bool:
    """
    파일이 존재하고, 1 KB 이상이며, Pillow로 열 수 있고,
    실제 이미지 크기가 10×10 초과인지 검증합니다.
    """
    if not os.path.exists(path):
        return False
    if os.path.getsize(path) < MIN_VALID_BYTES:
        return False
    if HAS_PILLOW:
        try:
            with Image.open(path) as img:
                img.verify()   # 파일 무결성 확인
        except Exception:
            return False
        try:
            with Image.open(path) as img:
                w, h = img.size
                if w <= 10 or h <= 10:
                    return False
        except Exception:
            return False
    return True


def _ensure_valid_thumbnail(thumbnail_path: str, input_path: str):
    """
    FFmpeg 추출 → 재시도 → Pillow fallback 순서로 썸네일을 확보합니다.
    """
    has_ffmpeg = shutil.which("ffmpeg") is not None

    if has_ffmpeg and os.path.exists(input_path):
        for seek in ("00:00:01", "00:00:00"):
            ok = _run_ffmpeg([
                "ffmpeg", "-y",
                "-i", input_path,
                "-ss", seek,
                "-vframes", "1",
                "-q:v", "2",      # JPEG 품질 높임
                thumbnail_path,
            ])
            if ok and _is_valid_thumbnail(thumbnail_path):
                return  # 성공

    # FFmpeg 실패 또는 FFmpeg 없음 → Pillow fallback
    if not _is_valid_thumbnail(thumbnail_path):
        _create_fallback_thumbnail(thumbnail_path)

    # 그래도 깨져 있으면 강제로 Pillow 재생성
    if not _is_valid_thumbnail(thumbnail_path):
        _create_fallback_thumbnail(thumbnail_path)


# ---------------------------------------------------------------------------
# FFmpeg helpers
# ---------------------------------------------------------------------------

def _run_ffmpeg(args: list[str]) -> bool:
    """
    FFmpeg 명령 실행. 성공 시 True, 실패 시 False.
    shell=False로 Windows 경로 인용 문제를 회피합니다.
    """
    try:
        subprocess.run(
            args,
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
        )
        return True
    except subprocess.CalledProcessError as exc:
        print(
            f"[render_service] FFmpeg 실패 (exit {exc.returncode}):\n"
            f"{exc.stderr.decode(errors='replace')}",
            file=sys.stderr,
        )
        return False
    except FileNotFoundError:
        print("[render_service] ffmpeg 실행 파일을 찾을 수 없습니다.", file=sys.stderr)
        return False


def _get_video_dimensions(video_path: str) -> tuple[int, int]:
    """ffprobe로 영상 해상도 조회. 실패 시 (1920, 1080) 반환."""
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
            timeout=15,
        )
        parts = result.stdout.strip().split(",")
        if len(parts) >= 2:
            return int(parts[0]), int(parts[1])
    except Exception:
        pass
    return 1920, 1080


def _get_video_duration(video_path: str) -> float:
    """ffprobe로 영상 길이를 조회합니다."""
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
        return float(result.stdout.strip())
    except Exception:
        pass
    return 60.0  # 실패 시 안전한 기본값 (너무 짧게 자르는 것 방지)


def _load_edit_command(job_dir: str) -> dict:
    """
    edit_command.json을 읽어서 edit_command dict를 반환합니다.
    파일이 없거나 읽기 실패 시 기본값을 반환합니다.
    """
    default = {
        "add_subtitle": True,
        "cover_subtitle_area": True,
        "subtitle_size": "large",
        "subtitle_language": "ko",
        "zoom": 1.03,
        "brightness": 0.06,
        "contrast": 1.05,
        "cut_silence": False,
    }
    cmd_path = os.path.join(job_dir, "edit_command.json")
    if not os.path.exists(cmd_path):
        return default
    try:
        with open(cmd_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        cmd = data.get("edit_command", {})
        # 누락된 키는 기본값으로 채움
        for k, v in default.items():
            cmd.setdefault(k, v)
        return cmd
    except Exception as exc:
        print(f"[render_service] edit_command.json 읽기 실패: {exc}", file=sys.stderr)
        return default


def _build_filtergraph_with_text(
    font_path: str,
    video_width: int,
    video_height: int,
    cmd: dict,
) -> str:
    """
    edit_command의 zoom/brightness/cover_subtitle_area 값을 반영하여
    자막 텍스트 포함 filtergraph 문자열을 생성합니다.
    """
    esc_font   = _escape_ffmpeg_path(font_path)
    font_size  = max(48, int(video_height * 0.065))
    text_y     = f"h*0.90-{font_size // 2}"
    bar_height = max(100, int(video_height * 0.18))
    bar_y      = video_height - bar_height

    zoom       = float(cmd.get("zoom") or 1.03)
    # brightness=None → 사용자 미요청, 렌더링 시 기본값(0.06) 적용
    brightness = float(cmd["brightness"]) if cmd.get("brightness") is not None else 0.06
    contrast   = float(cmd["contrast"])   if cmd.get("contrast")   is not None else 1.05
    cover_box  = cmd.get("cover_subtitle_area", True)
    add_text   = cmd.get("add_subtitle", True)

    filters = []

    # 1. 줌인 (zoom > 1.0 일 때만 crop)
    if zoom > 1.0:
        filters.append(f"crop=iw/{zoom}:ih/{zoom},scale={video_width}:{video_height}")

    # 2. 밝기/대비/채도 보정
    filters.append(f"eq=brightness={brightness}:contrast={contrast}:saturation=1.1")

    # 3. 하단 반투명 검은 박스
    if cover_box:
        filters.append(
            f"drawbox=x=0:y={bar_y}:w=iw:h={bar_height}:color=black@0.70:t=fill"
        )

    # 4. 자막 텍스트
    if add_text:
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

    return ",".join(filters) if filters else "null"


def _build_filtergraph_no_text(
    video_width: int,
    video_height: int,
    cmd: dict,
) -> str:
    """
    자막 없이 줌인 + 보정 + 박스만 적용하는 filtergraph.
    drawtext 실패 시 fallback으로 사용.
    """
    bar_height = max(100, int(video_height * 0.18))
    bar_y      = video_height - bar_height

    zoom       = float(cmd.get("zoom") or 1.03)
    brightness = float(cmd["brightness"]) if cmd.get("brightness") is not None else 0.06
    contrast   = float(cmd["contrast"])   if cmd.get("contrast")   is not None else 1.05
    cover_box  = cmd.get("cover_subtitle_area", True)

    filters = []
    if zoom > 1.0:
        filters.append(f"crop=iw/{zoom}:ih/{zoom},scale={video_width}:{video_height}")
    filters.append(f"eq=brightness={brightness}:contrast={contrast}:saturation=1.1")
    if cover_box:
        filters.append(
            f"drawbox=x=0:y={bar_y}:w=iw:h={bar_height}:color=black@0.70:t=fill"
        )
    return ",".join(filters) if filters else "null"


def _build_reorder_filtergraph(base_vf: str, duration: float, clip_reorder: dict) -> str:
    """
    기본 vf(zoom, drawbox 등)를 적용한 비디오와 원본 오디오를
    여러 구간으로 자른 뒤, 요청된 순서대로 이어붙이는 filter_complex 문자열을 생성합니다.
    """
    clips = clip_reorder.get("clips", [])
    if len(clips) != 2:
        return ""
    
    sorted_clips = sorted(clips, key=lambda c: c["source_start"])
    c1, c2 = sorted_clips[0], sorted_clips[1]
    
    s1, e1 = float(c1["source_start"]), float(c1["source_end"])
    s2, e2 = float(c2["source_start"]), float(c2["source_end"])
    
    # duration을 넘지 않도록 제한
    e2 = min(e2, duration)
    if e2 <= s2:
        return ""

    # 잘라낼 구간 정의 (순서대로)
    segments = [
        (0.0, s1),
        (s2, e2),  # 순서 바뀜: 뒷부분
        (e1, s2),
        (s1, e1),  # 순서 바뀜: 앞부분
        (e2, duration)
    ]
    
    valid_segments = []
    for s, e in segments:
        if e - s > 0.1:  # 0.1초 이상인 구간만 포함 (빈 구간 방지)
            valid_segments.append((s, e))
            
    if not valid_segments:
        return ""
        
    fg = []
    if base_vf and base_vf != "null":
        fg.append(f"[0:v]{base_vf}[v_base]")
        v_in = "v_base"
    else:
        v_in = "0:v"
        
    concat_inputs = []
    for i, (s, e) in enumerate(valid_segments):
        # Video
        fg.append(f"[{v_in}]trim=start={s}:end={e},setpts=PTS-STARTPTS[v{i}]")
        # Audio
        fg.append(f"[0:a]atrim=start={s}:end={e},asetpts=PTS-STARTPTS[a{i}]")
        concat_inputs.append(f"[v{i}][a{i}]")
        
    n = len(valid_segments)
    concat_str = "".join(concat_inputs)
    fg.append(f"{concat_str}concat=n={n}:v=1:a=1[outv][outa]")
    
    return ";".join(fg)


def _ffmpeg_render(
    input_path: str,
    output_path: str,
    video_width: int,
    video_height: int,
    duration: float,
    cmd: dict,
) -> bool:
    """
    FFmpeg로 영상을 렌더링합니다. edit_command의 설정을 반영합니다.

    시도 순서:
    1. 자막(drawtext) 포함 filtergraph + 한글 폰트
    2. 자막 없는 filtergraph (drawtext 지원 없는 FFmpeg 빌드 대비)
    3. 모두 실패 시 False 반환
    """
    font_path = _find_korean_font()
    cr = cmd.get("clip_reorder", {})
    use_reorder = cr.get("enabled", False)

    base_args = [
        "ffmpeg", "-y",
        "-i", input_path,
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "23",
        "-c:a", "aac",
        "-b:a", "128k",
    ]

    def _try_render(vf_str: str) -> bool:
        if use_reorder:
            fc = _build_reorder_filtergraph(vf_str, duration, cr)
            if fc:
                args = base_args.copy()
                args.extend(["-filter_complex", fc, "-map", "[outv]", "-map", "[outa]", output_path])
                return _run_ffmpeg(args)
        # reorder 안 할 때
        if vf_str != "null":
            return _run_ffmpeg(base_args + ["-vf", vf_str, output_path])
        return False

    # 시도 1: 자막 포함
    if font_path:
        vf = _build_filtergraph_with_text(font_path, video_width, video_height, cmd)
        if _try_render(vf):
            return True
        _remove_if_invalid(output_path)

    # 시도 2: 자막 없음
    vf = _build_filtergraph_no_text(video_width, video_height, cmd)
    if _try_render(vf):
        return True
    _remove_if_invalid(output_path)

    # 시도 3: 필터 없이 단순 재인코딩 (reorder도 무시됨)
    if _run_ffmpeg(base_args + [output_path]):
        return True
    _remove_if_invalid(output_path)

    return False


def _remove_if_invalid(path: str):
    """파일이 1 KB 미만이면 삭제하여 잔존 오류 방지."""
    if os.path.exists(path) and os.path.getsize(path) < MIN_VALID_BYTES:
        try:
            os.remove(path)
        except OSError:
            pass


def _is_valid_video(path: str) -> bool:
    """파일이 존재하고 1 KB 이상인지 확인."""
    return os.path.exists(path) and os.path.getsize(path) >= MIN_VALID_BYTES


# ---------------------------------------------------------------------------
# Main async render function
# ---------------------------------------------------------------------------

async def render_video_mock(job_id: str):
    update_job_status(job_id, "rendering", 0)

    for i in range(1, 4):
        await asyncio.sleep(0.4)
        update_job_status(job_id, "rendering", i * 8)

    job_dir           = get_job_dir(job_id)
    input_path        = os.path.join(job_dir, "input.mp4")
    output_video_path = os.path.join(job_dir, "edited_video.mp4")
    thumbnail_path    = os.path.join(job_dir, "thumbnail.jpg")
    subtitle_path     = os.path.join(job_dir, "subtitle.srt")

    # ── edit_command.json 로드 ─────────────────────────────────────────────
    cmd = _load_edit_command(job_dir)
    print(f"[render_service] edit_command 적용: {cmd}", file=sys.stderr)

    has_ffmpeg = shutil.which("ffmpeg") is not None

    # ── 비디오 렌더링 ──────────────────────────────────────────────────────
    if os.path.exists(input_path):

        rendered_with_effects = False

        if has_ffmpeg:
            width, height = _get_video_dimensions(input_path)
            duration = _get_video_duration(input_path)
            update_job_status(job_id, "rendering", 25)

            rendered_with_effects = _ffmpeg_render(
                input_path, output_video_path, width, height, duration, cmd
            )
            update_job_status(job_id, "rendering", 60)

        # FFmpeg 없거나 렌더링 실패 → 원본 복사 (재생 가능 보장)
        if not rendered_with_effects:
            print(
                "[render_service] FFmpeg 렌더링 없음 → input.mp4 복사 fallback.",
                file=sys.stderr,
            )
            shutil.copy2(input_path, output_video_path)

        # 결과 파일 크기 검증
        if not _is_valid_video(output_video_path):
            fail_job(
                job_id,
                "edited_video.mp4가 1KB 미만입니다. 원본 파일을 확인하세요."
            )
            return

    else:
        # input.mp4 자체가 없음
        fail_job(job_id, "input.mp4가 존재하지 않습니다.")
        return

    update_job_status(job_id, "rendering", 70)

    # ── 썸네일 생성 ────────────────────────────────────────────────────────
    _ensure_valid_thumbnail(thumbnail_path, input_path)

    # thumbnail도 깨진 경우 → 경고만 (렌더링 자체는 성공)
    if not _is_valid_thumbnail(thumbnail_path):
        print(
            "[render_service] thumbnail.jpg 생성 실패 — Pillow가 설치되어 있는지 확인하세요.",
            file=sys.stderr,
        )

    update_job_status(job_id, "rendering", 85)

    # ── 자막 파일 (SRT) ────────────────────────────────────────────────────
    with open(subtitle_path, "w", encoding="utf-8") as f:
        f.write(
            "1\n"
            "00:00:00,000 --> 00:00:05,000\n"
            f"{SUBTITLE_TEXT}\n"
            "\n"
        )

    # ── 완료 ──────────────────────────────────────────────────────────────
    for i in range(9, 11):
        await asyncio.sleep(0.2)
        update_job_status(job_id, "rendering", i * 10)

    update_job_status(job_id, "completed", 100)
