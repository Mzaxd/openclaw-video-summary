from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class TaskPaths:
    task_dir: Path
    video_path: Path
    summary_md: Path
    timeline_json: Path
    transcript_json: Path
    run_manifest_json: Path


def build_task_paths(output_root: Path | str, task_id: str) -> TaskPaths:
    root = Path(output_root)
    task_dir = root / task_id
    task_dir.mkdir(parents=True, exist_ok=True)
    return TaskPaths(
        task_dir=task_dir,
        video_path=task_dir / "video.mp4",
        summary_md=task_dir / "summary_zh.md",
        timeline_json=task_dir / "timeline.json",
        transcript_json=task_dir / "transcript.json",
        run_manifest_json=task_dir / "summarize_manifest.json",
    )
