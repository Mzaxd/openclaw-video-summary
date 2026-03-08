from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class TranscriptPayload:
    text: str
    segments: list[dict[str, Any]]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def write_transcript(payload: TranscriptPayload, output_path: Path | str) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
    return path
