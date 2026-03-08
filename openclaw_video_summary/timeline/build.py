from __future__ import annotations

from typing import Any


def _to_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def build_timeline(segments: list[dict[str, Any]], window_sec: float = 90.0) -> list[dict[str, Any]]:
    if window_sec <= 0:
        window_sec = 90.0

    normalized: list[dict[str, Any]] = []
    for segment in segments:
        start = _to_float(segment.get("start"), 0.0)
        end = _to_float(segment.get("end"), start)
        text = str(segment.get("text") or "").strip()
        if not text:
            continue
        normalized.append(
            {
                "start": start,
                "end": max(start, end),
                "text": text,
            }
        )

    normalized.sort(key=lambda item: (item["start"], item["end"]))
    if not normalized:
        return []

    timeline: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None

    for segment in normalized:
        if current is None:
            current = {
                "start": round(segment["start"], 3),
                "end": round(segment["end"], 3),
                "text_parts": [segment["text"]],
            }
            continue

        if segment["start"] - float(current["start"]) <= window_sec:
            current["end"] = round(max(float(current["end"]), segment["end"]), 3)
            current["text_parts"].append(segment["text"])
            continue

        text = " ".join(current["text_parts"]).strip()
        timeline.append(
            {
                "start": current["start"],
                "end": current["end"],
                "text": text,
                "summary": text[:140],
            }
        )
        current = {
            "start": round(segment["start"], 3),
            "end": round(segment["end"], 3),
            "text_parts": [segment["text"]],
        }

    if current is not None:
        text = " ".join(current["text_parts"]).strip()
        timeline.append(
            {
                "start": current["start"],
                "end": current["end"],
                "text": text,
                "summary": text[:140],
            }
        )

    return timeline
