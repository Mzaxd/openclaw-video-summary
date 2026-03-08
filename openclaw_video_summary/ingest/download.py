from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from openclaw_video_summary.ingest.source import detect_source_kind


@dataclass(frozen=True)
class NormalizedVideo:
    input_value: str
    source_kind: str
    video_path: Path


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
