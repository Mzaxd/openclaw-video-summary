# openclaw-video-summary

Default README is Chinese. Click here for Chinese: [README.md](README.md)

Paste a video link into OpenClaw and get an auto-downloaded, auto-transcribed, Chinese summary with traceable artifacts.

## Fastest OpenClaw Setup (Recommended)

Use this guide directly:
- [docs/openclaw-install-for-ai.md](docs/openclaw-install-for-ai.md)

It already includes:
- macOS / Linux / Windows (WSL2) auto-branch installation
- OpenClaw + system deps + Python deps setup
- Skill installation (workspace / global / ClawHub)
- One-pass verification and common fixes

## 3-Step Quick Start

### 1) Install dependencies

```bash
python3 -m pip install -e .
python3 -m pip install -e 'tools/bili-analyzer[asr]'
```

### 2) Configure provider

```bash
export OCVS_API_BASE="https://your-openai-compatible-endpoint"
export OCVS_API_KEY="your-api-key"
```

### 3) Run

```bash
python3 -m openclaw_video_summary.interfaces.cli summarize \
  "https://www.bilibili.com/video/BV..." \
  --mode auto \
  --platform-profile auto \
  --output-root ./runs \
  --api-base "$OCVS_API_BASE" \
  --api-key "$OCVS_API_KEY" \
  --json-summary
```

## Platform ASR Acceleration

- Default `--platform-profile auto` picks a runtime profile by platform
- Manual profile override: `--platform-profile apple_silicon|nvidia|intel|amd|cpu`
- On Apple Silicon, it prefers `mlx-whisper` (Metal) and automatically falls back to `faster-whisper(cpu)` if `mlx-whisper` is unavailable or fails
- Explicit `--device` / `--compute-type` overrides profile selection

## Why It Feels Easy

- Simple: paste a link, `auto` picks the right mode
- Reliable: local artifacts are always saved and traceable
- Practical: fallback still gives usable output when upstream fails

## Template Customization (Key Feature)

Customize summary style long-term without changing Python code.

Priority order:
1. `OCVS_SUMMARY_TEMPLATE_FILE=/absolute/path/to/summary_prompt.md`
2. repo-local `summary_prompt.local.md`
3. global `~/.config/openclaw-video-summary/summary_prompt.md`
4. built-in default template

Quick start:

```bash
cp summary_prompt.local.md.example summary_prompt.local.md
```

Template placeholders:
- `{{visual_context}}`
- `{{timeline_brief}}`
- `{{transcript_text}}`

References:
- [summary_prompt.local.md.example](summary_prompt.local.md.example)
- [summary_prompt.default.md](openclaw_video_summary/summary/summary_prompt.default.md)

## Output Artifacts

Each run creates a task folder with core files:
- `summary_zh.md`
- `timeline.json`
- `transcript.json`
- `summarize_manifest.json`

## Technical Details (Short)

- Inputs: YouTube / Bilibili / local video
- Modes: `auto` (default), `fast`, `fusion`, `quality`
- Required: `python>=3.10`, `yt-dlp`, `ffmpeg`
- API: OpenAI-compatible

More details:
- Usage guide: [docs/usage.md](docs/usage.md)
- Skill contract: [skill/SKILL.md](skill/SKILL.md)
- Install guide for OpenClaw: [docs/openclaw-install-for-ai.md](docs/openclaw-install-for-ai.md)
