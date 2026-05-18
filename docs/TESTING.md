# Render Verification

## 로컬 검증 (PowerShell)

```powershell
cd C:\projects\malrocut-ai-mvp
.\scripts\verify-render.ps1
```

성공 예시:

```text
✅ Render verification passed
```

실패 예시:

```text
❌ Render verification failed
원인:
Rendered output is identical to input despite edit commands
```

## 최근 job 진단

```powershell
.\scripts\diagnose-last-job.ps1
```

출력 항목:
- 최신 job 폴더 파일 목록
- `job.json`(UTF-8)
- `input.mp4`/`edited_video.mp4` SHA256 비교
- `subtitle.srt`, `edit_command.json`(UTF-8)
- 가능하면 `/status` API 응답
- 최종 판정: PASS / FAIL / BUG / WARN

## CI

GitHub Actions:
- `.github/workflows/backend-render-check.yml`
- FFmpeg 설치 후 `scripts/verify_render.py`를 실행해 실제 렌더링 검증을 수행합니다.
