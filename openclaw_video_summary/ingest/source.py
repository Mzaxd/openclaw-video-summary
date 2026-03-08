from __future__ import annotations

from pathlib import Path


def detect_source_kind(value: str) -> str:
    candidate = value.strip()
    lowered = candidate.lower()

    if lowered.startswith(("https://www.youtube.com/", "https://youtube.com/", "https://youtu.be/")):
        return "youtube"

    if lowered.startswith(("https://www.bilibili.com/video/", "https://b23.tv/")):
        return "bilibili"

    if Path(candidate).expanduser().exists():
        return "local_file"

    raise ValueError(f"unsupported input source: {value}")
