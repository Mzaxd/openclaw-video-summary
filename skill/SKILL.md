---
name: openclaw-video-summary
description: "Summarize YouTube/Bilibili/local videos in OpenClaw with a local-first pipeline and Chinese output. Use when users paste video links, request timeline/evidence summaries, or ask to install/configure this tool. For setup tasks, load references/install-index.md first."
---

# OpenClaw Video Summary

## Quick Routing

- If the user asks to install, configure, or fix environment issues, read `references/install-index.md` first.
- If the user asks to summarize a video, run the summarize flow below.

## Summarize Flow

1. Accept input:
- YouTube URL
- Bilibili URL
- local video path

2. Always materialize a local `video.mp4` in task directory before any model call.

3. Default mode is `auto`.
- Use `fusion` when user explicitly asks for stronger visual evidence.
- Use `quality` only when user explicitly asks for slower quality-first processing.

4. Return concise chat response from saved artifacts:
- Chinese summary
- timeline highlights
- key evidence
- artifact paths

## Artifact Contract

Report existing files in task directory:
- `summary_zh.md`
- `timeline.json`
- `transcript.json`
- `summarize_manifest.json`

Optional enhanced artifacts:
- `evidence.json`
- `fusion_report.md`

## Minimal Run Command

```bash
python3 -m openclaw_video_summary.interfaces.cli summarize "<input>" --mode auto --platform-profile auto --output-root ./runs --json-summary
```

Use `--api-base` and `--api-key` flags or environment variables when provider credentials are required.
Recommended env vars:
- `OCVS_API_BASE` / `OCVS_API_KEY`
- compatible fallback: `OPENAI_BASE_URL` / `OPENAI_API_KEY`

## Notes

- Do not infer success from chat text only. Check artifact files.
- If provider is unavailable, fallback summary may appear; surface this clearly.
- ASR runtime can be controlled with `--platform-profile`.
- On Apple Silicon, `apple_silicon` profile prefers `mlx-whisper`; if unavailable/fails, it auto-falls back to `faster-whisper(cpu)`.
- Check `summarize_manifest.json -> transcribe.engine` and `transcribe.runtime_profile` to report which ASR path actually ran.
