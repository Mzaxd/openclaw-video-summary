# Subtitle-First Retrieval Design (YouTube/Bilibili)

**Date:** 2026-03-08  
**Status:** Approved

## 1. Problem Statement

Current pipeline always executes `download -> ASR transcribe` for remote videos. In real use this is slow, especially for videos that already provide platform subtitles. We need a subtitle-first path that attempts to fetch existing subtitles before any download/transcribe work.

## 2. Goals and Non-Goals

### Goals
- For YouTube/Bilibili URLs, attempt subtitle retrieval first.
- If subtitles are available, skip video download and ASR entirely.
- Keep current ASR pipeline as a guaranteed fallback.
- Preserve existing downstream contracts (`transcript.json`, timeline, summary generation).
- Minimize latency impact when subtitles are not available.

### Non-Goals
- No dependency on official platform APIs that require uploader-level permissions.
- No changes to summary prompt strategy in this phase.
- No mandatory E2E stability guarantees for volatile site-side behavior.

## 3. Research Summary

### YouTube
- `yt-dlp` supports subtitle listing/downloading with `--list-subs`, `--write-subs`, `--write-auto-subs`, and can run with `--skip-download`.
- `youtube-transcript-api` is widely used for transcript retrieval without downloading media.
- YouTube official `captions.download` requires authorization scope and uploader-related access; not suitable for arbitrary public videos.

### Bilibili
- `yt-dlp` Bilibili extractor contains subtitle retrieval logic (including `subtitle_url` extraction).
- Community signals indicate subtitle behavior can regress across versions; fallback must remain robust.

### Decision
Use a non-official approach centered on `yt-dlp`, with fast fallback to ASR.

## 4. Recommended Approach

### Primary Path (Recommended)
- Use `yt-dlp` as a unified subtitle probe/fetch tool for both YouTube and Bilibili.
- Run subtitle probe before normalization/download.
- Timebox probe to 5 seconds.
- Enable cookie-based access attempt (`--cookies-from-browser`) to improve hit rate.

### Fallback Path
- Any subtitle miss/timeout/error immediately falls back to existing `download -> ASR` flow.
- Fallback must be transparent to callers and preserve current output schema.

## 5. Architecture and Data Flow

### Current
`input -> normalize_input_to_video (download/copy) -> transcribe_with_backend (ASR) -> timeline -> summary`

### Target
`input -> subtitle_probe (5s) -> [subtitle hit] transcript normalize -> timeline -> summary`
`                                     [miss/fail] normalize_input_to_video -> ASR -> timeline -> summary`

### Insertion Point
- Insert subtitle-first branch at the beginning of `run_fast` before `normalize_input_to_video`.

## 6. Component Design

### 6.1 `openclaw_video_summary/subtitle/probe.py`
- Responsibility: probe and optionally fetch subtitles via `yt-dlp` without video download.
- API:
  - `probe_subtitle(input_value: str, timeout_sec: float = 5.0, cookies_from_browser: bool = True) -> ProbeResult`
- Output includes:
  - `status`: `success | miss | timeout | error`
  - `provider`: `yt-dlp`
  - `language`
  - `subtitle_path` (if success)
  - `duration_sec`
  - `reason` (for miss/error)

### 6.2 `openclaw_video_summary/subtitle/normalize.py`
- Responsibility: convert subtitle files (`.vtt/.srt/.json3`) into existing `TranscriptPayload` contract.
- Output:
  - `text` (concatenated transcript)
  - `segments` with `{start, end, text}`

### 6.3 Pipeline Integration (`openclaw_video_summary/pipeline/fast.py`)
- In `run_fast`:
  - Attempt `probe_subtitle` first.
  - If success:
    - Build `TranscriptPayload` from subtitle.
    - Write `transcript.json`.
    - Skip `normalize_input_to_video` and `_transcribe_video`.
  - Else:
    - Run current ASR path unchanged.

## 7. Error Handling and Reliability

- Subtitle probe timeout (>5s): immediate ASR fallback (no retry to protect latency).
- Empty/invalid subtitle file: ASR fallback.
- Subtitle parse failure: ASR fallback.
- Cookie read failure: retry once without cookies, then ASR fallback.
- All subtitle-path failures are non-fatal and must not reduce overall completion rate.

## 8. Observability and Manifest Contract

Add manifest fields:
- `transcript_source: "subtitle" | "asr"`
- `subtitle_probe` object:
  - `attempted`
  - `success`
  - `provider`
  - `language`
  - `duration_sec`
  - `reason`

Keep existing `transcribe.runtime_profile` semantics for ASR executions.

## 9. Testing Strategy

### Unit Tests
- `subtitle/probe`:
  - success, miss, timeout, cookie-failure-then-retry
- `subtitle/normalize`:
  - vtt/srt/json3 parsing
  - timestamp edge cases
  - mixed-language text handling

### Integration Tests (mock external commands)
- Subtitle success path:
  - does not call download
  - does not call ASR
  - produces `transcript.json`, `timeline.json`, `summary_zh.md`, manifest
- Subtitle miss/failure path:
  - uses existing download+ASR flow
  - output compatibility retained

### Optional E2E
- One YouTube URL and one Bilibili URL with available subtitles.
- Validate subtitle-first short-circuit under real network conditions.

## 10. Acceptance Criteria

- For subtitle-available videos, end-to-end time improves significantly (target: >50% vs baseline).
- For subtitle-unavailable videos, added overhead remains bounded by probe timeout (~5s + command overhead).
- Overall pipeline success rate is not lower than baseline due to mandatory ASR fallback.

## 11. Trade-offs

- Non-official extraction improves speed and coverage but may be brittle against platform/extractor changes.
- 5-second timebox prioritizes responsiveness over exhaustive subtitle probing.
- Cookie-based retrieval improves hit rate but depends on local browser state and environment constraints.

## 12. Sources

- yt-dlp repository and subtitle options: https://github.com/yt-dlp/yt-dlp
- yt-dlp Bilibili extractor: https://github.com/yt-dlp/yt-dlp/blob/master/yt_dlp/extractor/bilibili.py
- youtube-transcript-api: https://github.com/jdepoix/youtube-transcript-api
- YouTube Data API captions.download: https://developers.google.com/youtube/v3/docs/captions/download
- YouTube Data API captions: https://developers.google.com/youtube/v3/docs/captions
- yt-dlp subtitle stability signals (Bilibili issues):
  - https://github.com/yt-dlp/yt-dlp/issues/14973
  - https://github.com/yt-dlp/yt-dlp/issues/14463
- bilibili-API-collect archival notice: https://github.com/SocialSisterYi/bilibili-API-collect
