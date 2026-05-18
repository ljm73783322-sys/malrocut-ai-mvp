"""
edit_service.py
---------------
Rule-based 편집 명령 파서.

사용자 프롬프트 → edit_command dict + plan_items 리스트 생성
AI API 미사용 — 키워드 기반 처리
"""

import json
import os
import re
from ..utils.paths import get_job_dir
from .job_store import jobs_db


# ---------------------------------------------------------------------------
# Clip reorder parser
# ---------------------------------------------------------------------------

# 시간 구간 패턴: "1~3초", "1-3초", "1초~3초", "1초부터 3초", "1초에서 3초"
_RANGE_RE = re.compile(
    r'(\d+(?:\.\d+)?)\s*초?\s*(?:[~\-–—]|부터\s*|에서\s*)\s*(\d+(?:\.\d+)?)\s*초'
)

_SWAP_KW = ["바꿔", "교체", "순서", "변경", "swap", "reorder", "스왑"]


def _parse_clip_reorder(prompt: str) -> dict | None:
    """
    프롬프트에서 컷 순서 변경 명령을 추출합니다.
    "1~3초 영상과 6~8초 영상 순서 바꿔줘" 같은 패턴을 인식합니다.
    """
    p = prompt.lower()

    if not any(kw in p for kw in _SWAP_KW):
        return None

    matches = _RANGE_RE.findall(prompt)
    if len(matches) < 2:
        return None

    s1, e1 = float(matches[0][0]), float(matches[0][1])
    s2, e2 = float(matches[1][0]), float(matches[1][1])

    # 유효성: 각 구간의 시작 < 끝
    if s1 >= e1 or s2 >= e2:
        return None

    # 구간이 겹치지 않게 정렬
    if s1 > s2:
        s1, e1, s2, e2 = s2, e2, s1, e1

    clips = [
        {"id": "clip_1", "source_start": s1, "source_end": e1, "new_order": 2},
        {"id": "clip_2", "source_start": s2, "source_end": e2, "new_order": 1},
    ]

    return {"enabled": True, "clips": clips}


# ---------------------------------------------------------------------------
# Rule-based prompt parser
# ---------------------------------------------------------------------------

def _parse_prompt(prompt: str) -> dict:
    p = prompt.lower()

    # ── 자막 ──────────────────────────────────────────────────────────────
    add_subtitle = any(kw in p for kw in [
        "자막", "subtitle", "텍스트", "글씨", "text",
    ])

    cover_subtitle_area = any(kw in p for kw in [
        "기존 자막", "자막 가려", "자막 제거", "자막 없애",
        "remove subtitle", "cover subtitle", "자막 지워",
    ])

    if any(kw in p for kw in ["크게", "큰 글씨", "large", "크고", "크게 달아", "크게 넣어"]):
        subtitle_size = "large"
    elif any(kw in p for kw in ["작게", "small", "작은"]):
        subtitle_size = "small"
    else:
        subtitle_size = "large"

    if any(kw in p for kw in ["일본어", "japanese", "일어"]):
        subtitle_language = "ja"
    elif any(kw in p for kw in ["영어", "english"]):
        subtitle_language = "en"
    else:
        subtitle_language = "ko"

    # ── 밝기/대비 ────────────────────────────────────────────────────────
    BRIGHT_KW = ["밝게", "화사", "환하게", "bright", "brighter"]
    DARK_KW   = ["어둡게", "어두운", "dark", "darker"]

    if any(kw in p for kw in BRIGHT_KW):
        brightness: float | None = 0.08
        contrast:   float | None = 1.05
    elif any(kw in p for kw in DARK_KW):
        brightness = -0.08
        contrast   = 1.05
    else:
        brightness = None
        contrast   = None

    # ── 줌 ───────────────────────────────────────────────────────────────
    ZOOM_KW = ["확대", "zoom", "줌", "크게 보여", "키워", "살짝 확대"]
    zoom = 1.03 if any(kw in p for kw in ZOOM_KW) else 1.0

    # ── 컷 편집 ──────────────────────────────────────────────────────────
    cut_silence = any(kw in p for kw in [
        "무음", "silence",
    ])

    # ── 클립 순서 변경 ───────────────────────────────────────────────────
    clip_reorder = _parse_clip_reorder(prompt)

    return {
        "add_subtitle":        add_subtitle,
        "cover_subtitle_area": cover_subtitle_area,
        "subtitle_size":       subtitle_size,
        "subtitle_language":   subtitle_language,
        "zoom":                zoom,
        "brightness":          brightness,
        "contrast":            contrast,
        "cut_silence":         cut_silence,
        "clip_reorder":        clip_reorder,
    }


# ---------------------------------------------------------------------------
# Plan items builder
# ---------------------------------------------------------------------------

def _build_plan_items(cmd: dict, prompt: str) -> list[str]:
    items: list[str] = []

    if not prompt.strip():
        items.append("기본 설정으로 편집합니다.")

    if cmd["cover_subtitle_area"]:
        items.append("기존 자막 영역을 검은 박스로 가립니다.")

    if cmd["add_subtitle"]:
        size_label = "크게" if cmd["subtitle_size"] == "large" else "작게"
        lang_label = {"ko": "한국어", "en": "영어", "ja": "일본어"}.get(
            cmd["subtitle_language"], "한국어"
        )
        items.append(f"새 자막을 {size_label} ({lang_label}) 추가합니다.")

    if cmd["zoom"] > 1.0:
        items.append(f"화면을 {cmd['zoom']}× 확대합니다.")

    brightness = cmd.get("brightness")
    if brightness is not None:
        if brightness > 0:
            items.append("밝기와 대비를 밝은 방향으로 보정합니다.")
        else:
            items.append("밝기를 어둡게 보정합니다.")

    # 클립 순서 변경
    cr = cmd.get("clip_reorder")
    if cr and cr.get("enabled"):
        clips = cr.get("clips", [])
        if len(clips) >= 2:
            sorted_clips = sorted(clips, key=lambda c: c["source_start"])
            a, b = sorted_clips[0], sorted_clips[1]
            items.append(
                f"적용 예정: {a['source_start']}초~{a['source_end']}초 구간과 "
                f"{b['source_start']}초~{b['source_end']}초 구간의 순서를 바꿉니다."
            )

    if cmd["cut_silence"]:
        items.append("미구현: 자동 무음 분석은 아직 지원하지 않습니다.")

    if not items:
        items.append("입력하신 내용에서 편집 작업을 감지하지 못했습니다. 기본 설정으로 편집합니다.")

    return items


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def create_edit_plan(job_id: str, prompt: str) -> dict:
    cmd = _parse_prompt(prompt)
    plan_items = _build_plan_items(cmd, prompt)

    job_dir = get_job_dir(job_id)
    cmd_path = os.path.join(job_dir, "edit_command.json")
    with open(cmd_path, "w", encoding="utf-8") as f:
        json.dump({"prompt": prompt, "edit_command": cmd}, f, ensure_ascii=False, indent=2)

    if job_id in jobs_db:
        jobs_db[job_id]["prompt"] = prompt
        jobs_db[job_id]["status"] = "edited"
        jobs_db[job_id]["plan"] = plan_items

    return {
        "job_id": job_id,
        "prompt": prompt,
        "edit_command": cmd,
        "plan_items": plan_items,
    }


def create_edit_plan_mock(job_id: str, prompt: str) -> dict:
    return create_edit_plan(job_id, prompt)
