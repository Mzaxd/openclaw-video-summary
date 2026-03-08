# OpenClaw Video Summary Usage

## Goal

This document explains how to operate the current `openclaw-video-summary` branch as it exists today. It focuses on the real behavior of the code in the repository, not an idealized future state.

## What Works Today

The repository already has:

- canonical task directory generation
- source detection for YouTube, Bilibili, and local files
- local normalization to `video.mp4`
- transcript and timeline data contracts
- summary request prompt generation
- `fast`, `fusion`, and `quality` orchestration layers
- a thin CLI module
- a skill response formatter for OpenClaw

The repository does not yet fully wire live backends into every heavy runtime edge. In particular, some orchestration points are intentionally left swappable or placeholder-based so tests can validate the structure without forcing network or ASR execution.

## Installation

### System Requirements

- Python 3.10 or newer
- `yt-dlp`
- `ffmpeg`

### Editable Install

```bash
python3 -m pip install -e .
```

## CLI Workflow

Current entrypoint:

```bash
python3 -m openclaw_video_summary.interfaces.cli summarize <input>
```

Common options:

- `--mode fast|fusion|quality`
- `--output-root <dir>`
- `--api-base <url>`
- `--api-key <key>`
- `--model <name>`
- `--window-sec <seconds>`
- `--json-summary`

Example:

```bash
python3 -m openclaw_video_summary.interfaces.cli summarize \
  "./sample.mp4" \
  --mode fusion \
  --output-root ./runs \
  --api-base "$OCVS_API_BASE" \
  --api-key "$OCVS_API_KEY" \
  --model glm-4.6v \
  --json-summary
```

## Skill Workflow

The intended OpenClaw interaction is simpler than the CLI:

1. User pastes a YouTube or Bilibili link.
2. The system downloads the video locally.
3. `fast` runs by default.
4. OpenClaw replies with:
   - Chinese summary
   - timeline excerpts
   - key evidence summary
   - artifact paths

Mode guidance:

- default to `fast`
- use `fusion` when the user asks for visual evidence or consistency checking
- use `quality` when the user explicitly asks for a slower quality-first pass

## Provider Configuration

The current summary client assumes an OpenAI-compatible API.

Recommended environment variables:

```bash
export OCVS_API_BASE="https://your-openai-compatible-endpoint"
export OCVS_API_KEY="your-api-key"
```

You can also pass the same values directly through CLI flags.

## Artifact Contract

Each run gets a task directory under the selected output root.

Stable artifact names:

- `video.mp4`
- `summary_zh.md`
- `timeline.json`
- `transcript.json`
- `run_manifest.json`

Enhanced-mode artifacts:

- `evidence.json`
- `fusion_report.md`

The artifact contract is important because the skill layer is expected to summarize the same saved outputs instead of inventing a separate chat-only result.

## Downgrade Semantics

Current intended downgrade rules:

- `fusion -> fast`
- `quality -> fusion`
- `quality -> fast` if the `fusion` path fails entirely

The selected mode and fallback metadata should be reflected in `run_manifest.json`.

## Testing Strategy

### Unit + Integration

Run everything currently expected to pass by default:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -p 'test_*.py' -v
```

### Opt-In E2E

Enable the E2E templates only when runtime dependencies and provider credentials are available:

```bash
export OCVS_E2E=1
export OCVS_API_BASE="https://your-openai-compatible-endpoint"
export OCVS_API_KEY="your-api-key"
export OCVS_YOUTUBE_URL="https://www.youtube.com/watch?v=..."
export OCVS_BILIBILI_URL="https://www.bilibili.com/video/BV..."
```

Run them:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.e2e.test_youtube_url -v
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.e2e.test_bilibili_url -v
```

By default these should stay skipped.

## Operational Caveats

- The CLI module is the reliable entrypoint on this branch.
- The console script declared in package metadata has not been documented here as the primary path because the current task focused on user guidance, not script wiring.
- Some heavy backend hooks remain placeholders by design, so a green test suite does not mean full live provider execution is complete.
- The current branch is good for contract validation and continued implementation, not yet for claiming full production readiness.
