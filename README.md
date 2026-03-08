# openclaw-video-summary

Skill-first video summarization for OpenClaw.

This repository is organized around one user experience:

1. Paste a YouTube or Bilibili link into OpenClaw.
2. Download the video locally before model work.
3. Run an ASR-first summary pipeline.
4. Return a Chinese summary, timeline excerpts, key evidence, and artifact paths.

## Current Status

The repository currently includes:

- source detection and local video normalization
- transcript, timeline, and summary contracts
- `fast`, `fusion`, and `quality` pipeline orchestration layers
- a local CLI module
- an OpenClaw skill document and response formatter
- unit, integration, and opt-in E2E templates

The heavy runtime backends are still partially placeholder-driven in the current branch. The tests verify pipeline wiring, artifact contracts, downgrade behavior, and response formatting. They do not yet prove live ASR or live provider execution end to end.

## Installation

System dependencies:

- `python >= 3.10`
- `yt-dlp`
- `ffmpeg`

Project install:

```bash
python3 -m pip install -e .
```

## CLI Usage

The reliable entrypoint on this branch is:

```bash
python3 -m openclaw_video_summary.interfaces.cli summarize <input>
```

Example:

```bash
python3 -m openclaw_video_summary.interfaces.cli summarize \
  "https://www.youtube.com/watch?v=example" \
  --mode fast \
  --output-root ./runs \
  --api-base "$OCVS_API_BASE" \
  --api-key "$OCVS_API_KEY" \
  --model glm-4.6v
```

Supported inputs:

- YouTube URL
- Bilibili URL
- local video path

Important behavior:

- remote URLs are downloaded locally first
- the pipeline works against local `video.mp4`
- the default mode is `fast`

## Modes

### `fast`

Default path:

- download or normalize local input
- generate transcript artifacts
- build timeline from ASR output
- generate Chinese summary

Expected base artifacts:

- `summary_zh.md`
- `timeline.json`
- `transcript.json`
- `run_manifest.json`

### `fusion`

Enhances `fast` with visual evidence and consistency checks.

Additional artifacts:

- `evidence.json`
- `fusion_report.md`

If the visual path fails, the current implementation is designed to downgrade cleanly to `fast` and record fallback metadata.

### `quality`

Quality-first orchestration above `fusion`.

Current behavior:

- attempt `quality`
- if enhancement fails, downgrade to `fusion`
- if `fusion` fails, downgrade to `fast`

The selected mode and fallback path are written into `run_manifest.json`.

## Provider Configuration

The current branch uses an OpenAI-compatible request surface for summary generation.

Typical environment variables:

```bash
export OCVS_API_BASE="https://your-openai-compatible-endpoint"
export OCVS_API_KEY="your-api-key"
```

The CLI can also take `--api-base` and `--api-key` directly.

## OpenClaw Skill Usage

The intended OpenClaw flow is:

1. paste a YouTube or Bilibili link
2. default to `fast` unless the user explicitly asks for `fusion` or `quality`
3. return:
   - Chinese summary
   - timeline highlights
   - key evidence summary
   - task directory and artifact paths

The skill contract is documented in [skill/SKILL.md](skill/SKILL.md).

## Artifact Layout

Every run creates a task directory under the chosen output root.

Base artifact names are stable:

- `video.mp4`
- `summary_zh.md`
- `timeline.json`
- `transcript.json`
- `run_manifest.json`

Enhanced modes may add:

- `evidence.json`
- `fusion_report.md`

## Downgrade Behavior

Current downgrade intent:

- `fusion` falls back to `fast`
- `quality` falls back to `fusion`, then `fast`

The fallback path is written into the manifest so the chat layer and local artifacts stay consistent.

## Tests

Run the current unit and integration suite:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -p 'test_*.py' -v
```

## Optional E2E Templates

The E2E templates are intentionally opt-in and skipped by default.

Files:

- `tests/e2e/test_youtube_url.py`
- `tests/e2e/test_bilibili_url.py`

Required environment variables:

```bash
export OCVS_E2E=1
export OCVS_API_BASE="https://your-openai-compatible-endpoint"
export OCVS_API_KEY="your-api-key"
export OCVS_YOUTUBE_URL="https://www.youtube.com/watch?v=..."
export OCVS_BILIBILI_URL="https://www.bilibili.com/video/BV..."
```

Run them with:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.e2e.test_youtube_url -v
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.e2e.test_bilibili_url -v
```

## More Detail

See [docs/usage.md](docs/usage.md) for a fuller operator guide.
