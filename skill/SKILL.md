---
name: openclaw-video-summary
description: "Paste a YouTube or Bilibili link into OpenClaw, download it locally, then return a Chinese summary with timeline excerpts and key visual evidence."
---

# OpenClaw Video Summary

## Purpose

This skill is the primary user-facing entrypoint for `openclaw-video-summary`.

The intended interaction is simple:

1. User pastes a YouTube or Bilibili link into OpenClaw.
2. The video is downloaded locally first.
3. The pipeline runs in `fast` mode by default.
4. OpenClaw replies with:
   - full Chinese summary
   - timeline excerpts
   - key visual evidence summary
   - task directory and artifact paths

## Input Handling

Accepted inputs:

- YouTube URL
- Bilibili URL
- local video path

Do not send remote video URLs directly to a model. Always materialize a local `video.mp4` in the task directory first.

## Mode Selection

- Default: `fast`
- Optional: `fusion`
- Optional: `quality`

If the user only pastes a link with no extra instruction, run `fast`.

Use `fusion` when the user asks for visual evidence or consistency checks.

Use `quality` only when the user explicitly asks for a slower, quality-first pass.

## Artifact Reporting

Every successful run should report the task directory plus the key artifacts that exist, typically:

- `summary_zh.md`
- `timeline.json`
- `transcript.json`
- `run_manifest.json`

Enhanced modes may also report:

- `evidence.json`
- `fusion_report.md`

## Response Shape

OpenClaw should present the saved output in a concise chat-friendly structure:

1. Chinese summary
2. timeline highlights
3. key evidence
4. artifact paths

The response shown in chat should be derived from the same saved artifacts rather than a separate one-off format.
