from __future__ import annotations

import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from openclaw_video_summary.ingest.source import detect_source_kind


@dataclass(frozen=True)
class NormalizedVideo:
    input_value: str
    source_kind: str
    video_path: Path


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
    raise RuntimeError("Unable to locate tools/bili-analyzer for frame analysis backend")


def _download_video(url: str, video_path: Path) -> None:
    if shutil.which("yt-dlp") is None:
        raise RuntimeError("yt-dlp is required to download remote videos")

    cmd = [
        "yt-dlp",
        "--no-part",
        "--force-overwrites",
        "--merge-output-format",
        "mp4",
        "-o",
        str(video_path),
        url,
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        details = proc.stderr.strip() or proc.stdout.strip() or "yt-dlp failed"
        raise RuntimeError(details)


def normalize_input_to_video(input_value: str, output_dir: Path | str) -> NormalizedVideo:
    source_kind = detect_source_kind(input_value)
    target_dir = Path(output_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    video_path = target_dir / "video.mp4"

    if source_kind == "local_file":
        shutil.copy2(Path(input_value).expanduser(), video_path)
    else:
        _download_video(input_value, video_path)

    return NormalizedVideo(
        input_value=input_value,
        source_kind=source_kind,
        video_path=video_path,
    )


def analyze_frames_with_backend(images_dir: Path | str) -> dict:
    _ensure_bili_analyzer_import()
    from bili_analyzer.core import analyze_frames_dir

    return analyze_frames_dir(Path(images_dir))
