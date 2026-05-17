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

### ⚠️ 테스트 모드 알림
- 현재 MVP 렌더링은 실제 고급 편집이 아닌 **테스트용 렌더링**입니다.
- 시스템에 `FFmpeg`가 설치되어 있으면 화면 보정(밝기 증대, 약간 확대, 1080x1920 리사이징)을 수행하며, `input.mp4`의 1초 또는 0초 프레임을 추출하여 썸네일을 자동 생성합니다.
- `FFmpeg`가 없을 경우 시스템 장애를 방지하기 위해 **원본 MP4 파일을 그대로 복사**하며, 1280x720 크기의 텍스트 안내가 포함된 고화질 Fallback 썸네일을 자동 생성합니다.
