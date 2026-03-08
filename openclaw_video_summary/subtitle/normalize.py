from __future__ import annotations

import json
import re
from pathlib import Path

from openclaw_video_summary.asr.transcribe import TranscriptPayload

_TIMESTAMP_RE = re.compile(
    r"(?P<h>\d{1,2}):(?P<m>\d{2}):(?P<s>\d{2})[,.](?P<ms>\d{1,3})"
)


def _timestamp_to_seconds(value: str) -> float:
    match = _TIMESTAMP_RE.search(value.strip())
    if not match:
        return 0.0
    hours = int(match.group("h"))
    minutes = int(match.group("m"))
    seconds = int(match.group("s"))
    millis = int(match.group("ms").ljust(3, "0"))
    return round(hours * 3600 + minutes * 60 + seconds + millis / 1000.0, 3)


def _clean_text_lines(lines: list[str]) -> str:
    return " ".join(line.strip() for line in lines if line.strip()).strip()


def _parse_text_subtitle(text: str) -> list[dict]:
    lines = text.splitlines()
    segments: list[dict] = []
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if not line or line.upper() == "WEBVTT" or line.startswith("NOTE"):
            i += 1
            continue
        if "-->" not in line:
            i += 1
            continue

        start_raw, end_raw = [part.strip() for part in line.split("-->", 1)]
        cue_lines: list[str] = []
        i += 1
        while i < len(lines) and lines[i].strip():
            cue_lines.append(lines[i])
            i += 1

        text_value = _clean_text_lines(cue_lines)
        if text_value:
            segments.append(
                {
                    "start": _timestamp_to_seconds(start_raw),
                    "end": _timestamp_to_seconds(end_raw),
                    "text": text_value,
                }
            )
        i += 1
    return segments


def _parse_json3_subtitle(raw: str) -> list[dict]:
    data = json.loads(raw)
    events = list(data.get("events") or [])
    segments: list[dict] = []
    for event in events:
        segs = event.get("segs") or []
        text_value = "".join(str(seg.get("utf8") or "") for seg in segs).strip()
        if not text_value:
            continue
        start = round(float(event.get("tStartMs") or 0) / 1000.0, 3)
        duration = round(float(event.get("dDurationMs") or 0) / 1000.0, 3)
        segments.append(
            {
                "start": start,
                "end": round(start + duration, 3),
                "text": text_value,
            }
        )
    return segments


def subtitle_file_to_transcript(path: str | Path) -> TranscriptPayload:
    subtitle_path = Path(path)
    raw = subtitle_path.read_text(encoding="utf-8", errors="ignore")
    suffix = subtitle_path.suffix.lower()

    if suffix == ".json3":
        segments = _parse_json3_subtitle(raw)
    else:
        segments = _parse_text_subtitle(raw)

    merged_text = "\n".join(segment["text"] for segment in segments).strip()
    return TranscriptPayload(text=merged_text, segments=segments)
