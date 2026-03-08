---
name: openclaw-video-summary
description: "Prepare video summary artifacts for YouTube/Bilibili/local files in OpenClaw using only skill-local scripts. Use when users paste video links, ask for timeline/evidence summaries, want subtitle-first processing, or want to customize summary templates by video type. For setup/install tasks, load references/install-index.md first."
---

# OpenClaw Video Summary

## Quick Routing

- If the user asks to install, configure, or fix environment issues, read `references/install-index.md` first.
- For Python dependency installation, prefer `skill/scripts/install_dependencies.sh`.
- If the user asks to summarize a video, run the summarize flow below.
- If the user asks to tune summary style, edit `templates/*.md` and `config/template_rules.json`.

## Summarize Flow

1. Accept input:
- YouTube URL
- Bilibili URL
- local video path

2. Always materialize a local `video.mp4` in task directory before any model call.

3. Run script:

```bash
python3 skill/scripts/video_summary.py summarize "<input>" --mode auto --output-root ./runs --json-summary
```

For platforms with subtitle/rate-limit issues, pass cookies:
- `--cookies-from-browser chrome`
- or `--cookies-file /absolute/path/cookies.txt`

4. Script is preprocessing only (no external LLM call):
- try subtitles first
- fallback to ASR when subtitles miss
- split video into chunks in `fusion` when visual understanding is needed
- write `summary_task_prompt.md` for OpenClaw model summarization in-session

5. Template routing:
- script auto-detects video type using `config/template_rules.json`
- matched template loaded from `templates/<type>.md`
- user can force template via `--template-type`
- manifest records `template_type` and `template_file`

6. OpenClaw should read artifacts and complete the final Chinese summary in chat:
- follow `summary_task_prompt.md`
- use `timeline.json` / `transcript.json`
- if present, use `evidence.json` and `fusion_report.md`
- include artifact paths in final response

## Artifact Contract

Report existing files in task directory:
- `summary_zh.md`
- `summary_task_prompt.md`
- `timeline.json`
- `transcript.json`
- `summarize_manifest.json`
- `template_type` / `template_file` in manifest

Optional enhanced artifacts:
- `evidence.json`
- `fusion_report.md`

## Notes

- Do not infer success from chat text only. Check artifact files.
- `summary_zh.md` is placeholder content when script-side summary is disabled by design.
- Final high-quality summary should be produced by OpenClaw model from `summary_task_prompt.md`.
- Runtime helper scripts are colocated under `skill/scripts/` and do not require `tools/`.
