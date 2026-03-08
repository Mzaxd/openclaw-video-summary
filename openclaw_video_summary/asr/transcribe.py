from __future__ import annotations

import json
import os
import platform
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from openclaw_video_summary.asr.platform_profile import resolve_asr_runtime_profile


def _ensure_bili_analyzer_import() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    candidates = [
        repo_root.parent / "tools" / "bili-analyzer",
        repo_root / "tools" / "bili-analyzer",
    ]
    for candidate in candidates:
        if candidate.exists():
            candidate_str = str(candidate)
            if candidate_str not in sys.path:
                sys.path.insert(0, candidate_str)
            return
    raise RuntimeError("Unable to locate tools/bili-analyzer for ASR backend")


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


def resolve_transcribe_runtime(
    *,
    platform_name: str,
    machine: str,
    platform_profile: str,
    device: str,
    compute_type: str,
    env: dict[str, str] | None = None,
) -> dict[str, str]:
    profile = resolve_asr_runtime_profile(
        platform_name=platform_name,
        machine=machine,
        requested_profile=platform_profile,
        requested_device=device,
        requested_compute_type=compute_type,
        env=env or {},
    )
    return {
        "profile": profile.profile_name,
        "device": profile.device,
        "compute_type": profile.compute_type,
        "reason": profile.reason,
    }


def transcribe_with_backend(
    *,
    input_path: str | Path,
    output_dir: str | Path,
    asr_model: str = "small",
    language: str = "auto",
    device: str = "auto",
    compute_type: str = "int8",
    platform_profile: str = "auto",
) -> tuple[TranscriptPayload, dict[str, Any]]:
    _ensure_bili_analyzer_import()
    from bili_analyzer.core import transcribe_video

    runtime = resolve_transcribe_runtime(
        platform_name=platform.system().lower(),
        machine=platform.machine().lower(),
        platform_profile=platform_profile,
        device=device,
        compute_type=compute_type,
        env=dict(os.environ),
    )
    backend_language = None if language == "auto" else language
    result = transcribe_video(
        input_path=str(input_path),
        output=str(output_dir),
        asr_model=asr_model,
        language=backend_language,
        device=runtime["device"],
        compute_type=runtime["compute_type"],
    )
    result["runtime_profile"] = runtime
    transcript_path = Path(result["transcript_file"])
    payload = json.loads(transcript_path.read_text(encoding="utf-8"))
    return (
        TranscriptPayload(
            text=payload.get("text") or "",
            segments=payload.get("segments") or [],
        ),
        result,
    )
