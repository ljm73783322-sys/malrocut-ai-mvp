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

## 🎬 렌더링 파이프라인 상세 설명

### FFmpeg가 설치된 경우 (권장)

`render_service.py`는 `ffmpeg` 실행 파일이 PATH에 있을 때 다음 편집 효과를 **하나의 filtergraph**로 실제 영상에 적용합니다.

| 순서 | 필터 | 내용 |
|------|------|------|
| 1 | `crop` + `scale` | 원본의 약 97% 영역만 잘라서 다시 원본 해상도로 확대 → **1.03× 줌인** 효과 |
| 2 | `eq` | `brightness=+0.06`, `contrast=1.05`, `saturation=1.1` → **밝기·대비·채도 보정** |
| 3 | `drawbox` | 하단 약 18% 영역에 **반투명 검정 박스** 삽입 (기존 자막 영역 가림) |
| 4 | `drawtext` | `"말로컷 AI로 새롭게 편집된 영상입니다"` 문구를 **흰색 큰 글씨·검은 외곽선**으로 하단 중앙에 삽입 |

- 자막 폰트는 Windows 시스템 폰트(`malgun.ttf` → `gulim.ttc` → `arial.ttf`) 순으로 자동 탐색합니다.
- 폰트 크기는 영상 세로 해상도 기준으로 자동 계산되어 70대 사용자도 읽기 쉬운 크기(최소 48px)로 설정됩니다.
- 인코딩: `libx264 / AAC`, preset `fast`, CRF 23.
- 썸네일은 `input.mp4`의 1초(또는 0초) 프레임을 FFmpeg로 추출합니다.

### FFmpeg가 없는 경우 (Fallback)

- `input.mp4`를 `edited_video.mp4`로 **그대로 복사**합니다 (영상 변환 없음).
- Pillow가 설치된 경우 1280×720 텍스트 안내 이미지를 `thumbnail.jpg`로 생성합니다.
- Pillow도 없는 경우 빈 파일이 생성됩니다.

### 오류 처리

FFmpeg가 있더라도 filtergraph 실행 중 오류 발생 시, `subprocess.CalledProcessError`를 잡아 서버 stderr에 진단 메시지를 출력하고 **원본 복사 fallback**으로 자동 전환합니다. 서버가 중단되지 않습니다.

### ⚠️ 현재 미구현 기능
- Whisper 기반 음성 인식 / 자막 자동 추출
- OCR 기반 기존 자막 감지
- AI 인페인팅 (자막 영역 완전 제거)
- 실제 편집 계획 반영 (컷 편집, 장면 재배치 등)
