# Install Index

Canonical installation guide for this skill and tool:
- `docs/openclaw-install-for-ai.md`

If you are running inside this repository, follow that guide directly.
If only the `skill/` folder is available, use the quick-install fallback below.

## What It Covers

- OS auto-branch install for macOS / Linux / Windows (WSL2)
- OpenClaw setup
- System dependencies (`python`, `ffmpeg`, `yt-dlp`)
- Python dependencies (`openclaw-video-summary`, `tools/bili-analyzer[asr]`)
- Skill install paths (`./.openclaw/skills` and `~/.openclaw/skills`)
- Verification and troubleshooting

## Minimum Verification

```bash
yt-dlp --version
ffmpeg -version
python3 -m openclaw_video_summary.interfaces.cli summarize "<video_or_url>" --mode auto --output-root ./runs --json-summary
```

## Quick-Install Fallback (Skill-Only Distribution)

When `docs/openclaw-install-for-ai.md` is not present:

1. Install system dependencies (`python>=3.10`, `ffmpeg`, `yt-dlp`).
2. Install Python packages from the project root:

```bash
python3 -m pip install -e .
python3 -m pip install -e 'tools/bili-analyzer[asr]'
```

3. Install skill files to one of:
- `./.openclaw/skills/openclaw-video-summary/`
- `~/.openclaw/skills/openclaw-video-summary/`
4. Set provider credentials:

```bash
export OCVS_API_BASE="https://your-openai-compatible-endpoint"
export OCVS_API_KEY="your-api-key"
```
