# Install Index

Canonical installation guide for this skill and tool:
- `skill/references/openclaw-install-for-ai.md`

If you are running inside this repository, follow that guide directly.
If only the `skill/` folder is available, use the quick-install fallback below.

## What It Covers

- OS auto-branch install for macOS / Linux / Windows (WSL2)
- OpenClaw setup
- System dependencies (`python`, `ffmpeg`, `yt-dlp`)
- Python dependencies (`faster-whisper`)
- Skill install paths (`./.openclaw/skills` and `~/.openclaw/skills`)
- Verification and troubleshooting

## Minimum Verification

```bash
yt-dlp --version
ffmpeg -version
python3 skill/scripts/video_summary.py summarize "<video_or_url>" --mode auto --output-root ./runs --json-summary
```

## Quick-Install Fallback (Minimal Context)

When the full install guide is not loaded into context, use:

1. Install system dependencies (`python>=3.10`, `ffmpeg`, `yt-dlp`).
2. Install Python packages from the project root (recommended script):

```bash
bash skill/scripts/install_dependencies.sh
```

3. Install skill files to one of:
- `./.openclaw/skills/openclaw-video-summary/`
- `~/.openclaw/skills/openclaw-video-summary/`

Optional:
- Force `mlx-whisper`: `bash skill/scripts/install_dependencies.sh --with-mlx`
- Disable `mlx-whisper`: `bash skill/scripts/install_dependencies.sh --skip-mlx`
