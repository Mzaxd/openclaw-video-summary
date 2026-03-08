# openclaw-video-summary

Default README is Chinese. Click here for Chinese: [README.md](README.md)

A video summarization tool for OpenClaw. It accepts YouTube / Bilibili URLs or local video files, materializes them locally first, runs an ASR-first summary pipeline, and upgrades to `fusion` only when visual evidence is likely useful.

## Overview

- Default mode is `auto`
- Main flow is `download/localize -> ASR -> timeline -> Chinese summary`
- Mostly verbal videos usually stay in `fast`
- Tutorials, demos, UI walkthroughs, and chart-heavy videos are more likely to upgrade to `fusion`
- Outputs are stable, traceable, and reproducible

## Core Capabilities

- Inputs: YouTube URL, Bilibili URL, local video file
- Modes: `auto`, `fast`, `fusion`, `quality`
- Supports persistent summary-template overrides
- Works with OpenAI-compatible APIs
- Produces summary, timeline, transcript, manifest, and `fusion` evidence artifacts

## Installation

### System Dependencies

```bash
python3 --version
yt-dlp --version
ffmpeg -version
```

Required:
- `python >= 3.10`
- `yt-dlp`
- `ffmpeg`

### Project Install

```bash
python3 -m pip install -e .
```

## Quick Start

### CLI

```bash
python3 -m openclaw_video_summary.interfaces.cli summarize \
  "https://www.bilibili.com/video/BV..." \
  --mode auto \
  --output-root ./runs \
  --api-base "$OCVS_API_BASE" \
  --api-key "$OCVS_API_KEY" \
  --model glm-4.6v \
  --json-summary
```

`--mode auto` is the recommended default.

### OpenClaw Usage

1. Paste a YouTube / Bilibili link
2. The tool downloads the video locally first
3. It runs `auto` by default
4. It returns a Chinese summary, timeline excerpts, key evidence, and artifact paths

## Modes

### `auto`

- Runs `fast` once first
- Uses transcript and timeline to decide whether visual evidence matters
- Keeps `fast` for talking-head / low-visual-value videos
- Upgrades to `fusion` for tutorials, demos, operational walkthroughs, and chart-driven content

Manifest fields:
- `selected_mode`
- `auto_selection.reason`
- `auto_selection.signals`

### `fast`

- ASR-first path
- Produces transcript, timeline, and Chinese summary
- Faster and cheaper
- Good for talking-head, commentary, interview, and podcast-like videos

### `fusion`

- Adds visual evidence on top of `fast`
- Current implementation uses chunked video analysis
- Best for tutorials, demos, UI workflows, and chart-heavy videos
- Downgrades to `fast` when the visual path fails

### `quality`

Reserved as a quality-first layer above `fusion`.

## Provider Configuration

Both summary generation and multimodal analysis currently use an OpenAI-compatible interface.

Environment variables:

```bash
export OCVS_API_BASE="https://your-openai-compatible-endpoint"
export OCVS_API_KEY="your-api-key"
```

Or pass them through CLI flags:
- `--api-base`
- `--api-key`
- `--model`

## Custom Summary Template

Persistent summary-template customization is supported without changing Python code.

Override priority:
1. `OCVS_SUMMARY_TEMPLATE_FILE=/absolute/path/to/summary_prompt.md`
2. Repo-local `summary_prompt.local.md`
3. Global `~/.config/openclaw-video-summary/summary_prompt.md`
4. Built-in default template

Template placeholders:
- `{{visual_context}}`
- `{{timeline_brief}}`
- `{{transcript_text}}`

Repo-local quick start:

```bash
cp summary_prompt.local.md.example summary_prompt.local.md
```

Global template:

```bash
mkdir -p ~/.config/openclaw-video-summary
cp summary_prompt.local.md.example ~/.config/openclaw-video-summary/summary_prompt.md
```

Reference files:
- [summary_prompt.local.md.example](summary_prompt.local.md.example)
- [summary_prompt.default.md](openclaw_video_summary/summary/summary_prompt.default.md)

## Artifact Contract

Every run produces one task directory.

Base artifacts:
- `video.mp4`
- `summary_zh.md`
- `timeline.json`
- `transcript.json`
- `summarize_manifest.json`

Additional artifacts for enhanced modes:
- `evidence.json`
- `fusion_report.md`

Chat responses should be treated as a summarized view of these saved artifacts.

## Downgrade Behavior

- `fusion -> fast`
- `quality -> fusion`
- `quality -> fast`

Fallback metadata is written into the manifest.

## Tests

### Unit + Integration

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -p 'test_*.py' -v
```

### Optional E2E

```bash
export OCVS_E2E=1
export OCVS_API_BASE="https://your-openai-compatible-endpoint"
export OCVS_API_KEY="your-api-key"
export OCVS_YOUTUBE_URL="https://www.youtube.com/watch?v=..."
export OCVS_BILIBILI_URL="https://www.bilibili.com/video/BV..."
```

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.e2e.test_youtube_url -v
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.e2e.test_bilibili_url -v
```

## Current Limitations

- Local ASR can be slow on CPU-only environments
- Chunked multimodal requests in `fusion` can be latency-heavy
- Remote provider stability directly affects `fusion`
- This branch is suitable for ongoing iteration, not yet for strong production-ready claims

## More Detail

- Usage guide: [docs/usage.md](docs/usage.md)
- Skill contract: [skill/SKILL.md](skill/SKILL.md)
