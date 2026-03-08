# openclaw-video-summary

Default README is Chinese. Chinese version: [README.md](README.md)

Paste a video link into OpenClaw. The skill-local script prepares subtitles/transcript/timeline/chunks, then OpenClaw summarizes in-session from generated prompts.

## Fastest OpenClaw Setup (Recommended)

Use this guide directly:
- [skill/references/openclaw-install-for-ai.md](skill/references/openclaw-install-for-ai.md)

## Quick Start

### 1) Install dependencies

```bash
python3 -m pip install "faster-whisper>=1.0.0"
```

### 2) Run

```bash
python3 skill/scripts/video_summary.py summarize \
  "https://www.bilibili.com/video/BV..." \
  --mode auto \
  --output-root ./runs \
  --json-summary
```

## Template System

Templates:
- `skill/templates/default.md`
- `skill/templates/tutorial.md`
- `skill/templates/interview.md`
- `skill/templates/review.md`
- `skill/templates/news.md`

Routing rules:
- `skill/config/template_rules.json`
- Override with `--template-type`

## Output Artifacts

- `summary_zh.md` (placeholder note)
- `summary_task_prompt.md` (for OpenClaw summarization)
- `timeline.json`
- `transcript.json`
- `summarize_manifest.json`

## References

- Usage guide: [skill/references/usage.md](skill/references/usage.md)
- Install guide: [skill/references/openclaw-install-for-ai.md](skill/references/openclaw-install-for-ai.md)
- Skill contract: [skill/SKILL.md](skill/SKILL.md)
