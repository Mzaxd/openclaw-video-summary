from __future__ import annotations

from typing import Any


def _to_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def build_timeline(segments: list[dict[str, Any]], window_sec: float = 90.0) -> list[dict[str, Any]]:
    if window_sec <= 0:
        window_sec = 90.0

    normalized: list[dict[str, Any]] = []
    for seg in segments or []:
        start = _to_float(seg.get("start"), 0.0)
        end = _to_float(seg.get("end"), start)
        text = (seg.get("text") or "").strip()
        if not text:
            continue
        if end < start:
            end = start
        normalized.append({"start": start, "end": end, "text": text})

    normalized.sort(key=lambda x: (x["start"], x["end"]))
    if not normalized:
        return []

    timeline: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None

    for seg in normalized:
        if current is None:
            current = {
                "start": round(seg["start"], 3),
                "end": round(seg["end"], 3),
                "text_parts": [seg["text"]],
            }
            continue

        if seg["start"] - float(current["start"]) <= window_sec:
            current["end"] = round(max(float(current["end"]), seg["end"]), 3)
            current["text_parts"].append(seg["text"])
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
            "start": round(seg["start"], 3),
            "end": round(seg["end"], 3),
            "text_parts": [seg["text"]],
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
