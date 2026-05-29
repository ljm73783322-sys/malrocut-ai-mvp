# Malrocut User Guide

Malrocut helps test simple AI-assisted video editing flows in a local beta package.

## Basic workflow

1. Open the frontend at http://localhost:3000.
2. Upload a video.
3. Enter an editing instruction.
4. Preview A/B segments when the app shows the planned edit timeline.
5. Render the edited result.
6. Download the generated video, thumbnail, subtitle file, or ZIP package from the result page.

## Example prompt

```text
1~3초 영상과 6~8초 영상 순서를 바꿔줘. 기존 자막을 가리고 새 한국어 자막을 크게 넣어줘. 화면도 살짝 밝게 해줘.
```

## What Malrocut can do now

- Upload a video for a local edit job.
- Create an edit plan from a text instruction.
- Preview planned timeline segments.
- Render a beta output video.
- Cover existing subtitles in supported flows.
- Add new Korean subtitles in supported flows.
- Produce downloadable assets such as video, thumbnail, subtitle, and ZIP outputs.

## What Malrocut cannot do yet

- It does not include a payment system or license server.
- It does not include cloud rendering or a job queue.
- It does not include CapCut project export.
- It does not include Whisper-based speech recognition in this beta package.
- It is not guaranteed to understand every natural-language editing request.
- It may not handle very long videos reliably in beta.

## Recommended video length for beta

For the best beta experience, start with short videos around 10 to 60 seconds. After confirming your computer can render reliably, try longer videos gradually.
