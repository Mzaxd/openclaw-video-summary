from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class VisualEvidence:
    start: float
    end: float
    observation: str
    confidence: str
    metadata: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class VisionAnalyzer:
    def analyze_video(self, video_path: str | Path) -> list[VisualEvidence]:
        raise NotImplementedError("VisionAnalyzer.analyze_video() must be implemented by a provider adapter")
