# Malrocut AI MVP (말로컷 AI MVP)

## 프로젝트 소개
말로컷 AI는 사용자가 기존 동영상을 업로드하고 텍스트 프롬프트만으로 마치 캡컷(CapCut)처럼 동영상을 편집할 수 있는 웹 애플리케이션 MVP입니다. 복잡한 타임라인 조작 없이 자연어 명령을 통해 컷 편집, 자막 처리, 화면 보정 등을 자동화합니다.

## 핵심 기능
- **영상 업로드**: 기존 MP4 동영상 업로드 지원
- **자막 처리**: 기존 자막 감지 및 제거, 새로운 자막 삽입
- **다국어 지원**: 한국어, 영어, 일본어 자막 생성 및 재구성
- **대본 추출 및 편집**: 영상에서 대본을 추출하고 수정하는 기능
- **컷 편집 및 재배치**: 불필요한 컷 편집 및 장면 순서 변경
- **화면 연출**: 얼굴 중앙 정렬, 화면 확대 (Zoom in)
- **후보정**: 색감 보정 (Color grading)
- **썸네일**: 사용자 썸네일 업로드 및 자동 생성
- **내보내기**: `edited_video.mp4`, `subtitle.srt`, `thumbnail.jpg` 파일 다운로드 지원

## MVP 기본 변화 세트
- 기존 자막 제거
- 새 자막 생성 (언어 변경 및 문장 재구성 포함)
- 장면 순서 일부 변경
- 화면 확대 연출
- 색감 보정
- 새 썸네일 생성

## MVP 제외 기능
해당 MVP 버전에서는 다음 기능이 포함되지 않습니다.
- 음성 클론 (Voice cloning)
- 립싱크 (Lip sync)
- 고급 트랜지션 효과
- 캡컷 프로젝트 파일(.ccproj) 내보내기
- 유튜브 자동 업로드 API 연동
- 모바일 네이티브 앱
- 팀 협업 기능
- 완벽한 AI 인페인팅 (AI Inpainting)
- 자동 쇼츠(Shorts) 생성

## 폴더 구조
- `/docs`: 프로젝트 요구사항, 기획, API, 분석 문서
- `/frontend`: 웹 프론트엔드 (Next.js)
- `/backend`: 백엔드 API 및 AI 처리 (FastAPI)
- `/scripts`: 유틸리티 및 자동화 스크립트
- `/.codex`: AI 에이전트 스킬 및 설정

## 로컬 실행 방법 (Windows PowerShell 기준)

### 1. 백엔드 (FastAPI) 실행
```powershell
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

### 2. 프론트엔드 (Next.js) 실행
새로운 PowerShell 창을 열고 아래 명령어를 실행하세요.
```powershell
cd frontend
npm install
npm run dev
```

브라우저에서 `http://localhost:3000`에 접속하여 말로컷 AI MVP를 테스트할 수 있습니다.

---

## 🎬 렌더링 파이프라인 (MVP 테스트 렌더링)

> 현재 렌더링은 실제 AI 편집이 아닌 **MVP용 테스트 렌더링**입니다.

### FFmpeg가 설치된 경우 (가시적 효과 적용)

`ffmpeg`가 PATH에 있을 때 다음 효과를 **filtergraph** 하나로 실제 영상에 적용합니다.

| 순서 | 필터 | 내용 |
|------|------|------|
| 1 | `crop` + `scale` | 중앙 97% 잘라서 원본 해상도로 복원 → **1.03× 줌인** |
| 2 | `eq` | `brightness=+0.06`, `contrast=1.05`, `saturation=1.1` → 밝기·대비·채도 보정 |
| 3 | `drawbox` | 하단 약 18% 영역에 **반투명 검정 박스** (기존 자막 영역 가림) |
| 4 | `drawtext` | `"말로컷 AI로 새롭게 편집된 영상입니다"` 흰색 큰 글씨 + 검은 외곽선, 하단 중앙 |

**2단계 시도 방식:**
1. **자막 포함** — 한글 폰트(`malgun.ttf` → `gulim.ttc` → `arial.ttf`) + drawtext
2. **자막 제외** — drawtext 없이 줌인·보정·박스만 적용 (FFmpeg 빌드에 FreeType 없는 경우 대비)

인코딩: `libx264`, preset `fast`, CRF 23 / `aac` 128k

### FFmpeg가 없거나 모든 시도 실패 시 (Fallback)

- `input.mp4`를 `edited_video.mp4`로 **그대로 복사** → 항상 재생 가능한 파일 보장
- 복사 후에도 파일이 1 KB 미만이면 job 상태를 `failed`로 저장하고 에러 메시지를 남김

### 썸네일 생성 순서

1. FFmpeg로 `input.mp4` 1초 지점 프레임 추출
2. 실패 시 0초 지점으로 재시도
3. 그래도 실패 시 Pillow로 **1280×720 fallback JPG** 자동 생성
4. 생성 후 Pillow로 파일 무결성 검증 (`width > 10`, `height > 10`, 크기 ≥ 1 KB)
5. 검증 실패 시 Pillow fallback 재생성

### 실패 처리

- `input.mp4` 없음 또는 `edited_video.mp4`가 1 KB 미만이면 `job.status = "failed"` 저장
- 서버는 중단되지 않으며 다른 job은 정상 처리됨

### ⚠️ 현재 미구현 기능
- Whisper 기반 음성 인식 / 자막 자동 추출
- OCR 기반 기존 자막 감지 및 인페인팅
- 실제 편집 계획 반영 (컷 편집, 장면 재배치 등)
- 음성 클론, 립싱크, 고급 트랜지션


