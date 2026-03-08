# openclaw-video-summary

Skill-first video summarization for OpenClaw.

## Scope

- Paste a YouTube or Bilibili link into OpenClaw
- Download the video locally before analysis
- Produce Chinese summaries with timeline-aligned artifacts

## Planned Modes

- `fast`: ASR-first summary path
- `fusion`: ASR summary plus visual evidence
- `quality`: slower quality-first enhancement mode

## Development Status

This repository currently contains:

- pipeline contracts and orchestration skeletons for `fast`, `fusion`, and `quality`
- a local CLI entrypoint via `python -m openclaw_video_summary.interfaces.cli`
- an OpenClaw skill wrapper and response formatter

The heavy runtime backends are still intentionally thin or placeholder-driven in parts of the stack, so local unit and integration tests focus on orchestration and artifact contracts rather than live model execution.

## Run Tests

Unit and integration tests:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -p 'test_*.py' -v
```

## Optional E2E Templates

Two source-specific E2E templates are included:

- `tests/e2e/test_youtube_url.py`
- `tests/e2e/test_bilibili_url.py`

They are skipped by default. Enable them only when the runtime dependencies and provider credentials are available.

Required environment variables:

```bash
export OCVS_E2E=1
export OCVS_API_BASE="https://your-openai-compatible-endpoint"
export OCVS_API_KEY="your-api-key"
export OCVS_YOUTUBE_URL="https://www.youtube.com/watch?v=..."
export OCVS_BILIBILI_URL="https://www.bilibili.com/video/BV..."
```

Example commands:

```bash
PYTHONDONTWRITEBYTECODE=1 OCVS_E2E=1 \
python3 -m unittest tests.e2e.test_youtube_url -v

PYTHONDONTWRITEBYTECODE=1 OCVS_E2E=1 \
python3 -m unittest tests.e2e.test_bilibili_url -v
```

What the E2E templates validate:

- the CLI accepts a real YouTube or Bilibili URL
- a run directory is created under the chosen output root
- `summary_zh.md`, `timeline.json`, `transcript.json`, and `run_manifest.json` are produced
- CLI JSON output matches the expected mode and artifact locations
