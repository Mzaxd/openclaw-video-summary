from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path

from openclaw_video_summary.asr.transcribe import TranscriptPayload, write_transcript
from openclaw_video_summary.ingest.download import normalize_input_to_video
from openclaw_video_summary.pipeline.task_layout import TaskPaths, build_task_paths
from openclaw_video_summary.summary.client import request_summary
from openclaw_video_summary.summary.prompts import build_summary_messages
from openclaw_video_summary.timeline.build import build_timeline


@dataclass(frozen=True)
class FastRunResult:
    task_id: str
    task_dir: Path
    video_path: Path
    summary_md: Path
    timeline_json: Path
    transcript_json: Path
    run_manifest_json: Path
    source_kind: str
    mode: str = "fast"


def _build_task_id(input_value: str) -> str:
    digest = hashlib.sha1(input_value.encode("utf-8")).hexdigest()
    return f"run-{digest[:12]}"


def _transcribe_video(*, video_path: Path, transcript_path: Path) -> TranscriptPayload:
    raise RuntimeError(
        "ASR backend is not wired into run_fast yet. Inject or monkeypatch _transcribe_video in tests, "
        "or implement the real backend in a later task."
    )


def _request_summary_text(
    *,
    transcript_text: str,
    timeline: list[dict[str, object]],
    api_base: str,
    api_key: str,
    model: str,
) -> str:
    messages = build_summary_messages(transcript_text, timeline, None)
    return request_summary(
        api_base=api_base,
        api_key=api_key,
        model=model,
        messages=messages,
    )


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _write_text(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")


def _write_manifest(
    *,
    paths: TaskPaths,
    task_id: str,
    input_value: str,
    source_kind: str,
    timeline: list[dict[str, object]],
) -> None:
    manifest = {
        "task_id": task_id,
        "mode": "fast",
        "input_value": input_value,
        "source_kind": source_kind,
        "task_dir": str(paths.task_dir),
        "video_path": str(paths.video_path),
        "summary_md": str(paths.summary_md),
        "timeline_json": str(paths.timeline_json),
        "transcript_json": str(paths.transcript_json),
        "run_manifest_json": str(paths.run_manifest_json),
        "timeline_items": len(timeline),
    }
    _write_json(paths.run_manifest_json, manifest)


def run_fast(
    input_value: str,
    *,
    output_root: Path | str,
    api_base: str = "",
    api_key: str = "",
    model: str = "glm-4.6v",
    window_sec: float = 90.0,
) -> FastRunResult:
    task_id = _build_task_id(input_value)
    paths = build_task_paths(output_root, task_id)

    normalized = normalize_input_to_video(input_value, paths.task_dir)
    transcript = _transcribe_video(video_path=paths.video_path, transcript_path=paths.transcript_json)
    write_transcript(transcript, paths.transcript_json)

    timeline = build_timeline(transcript.segments, window_sec=window_sec)
    _write_json(
        paths.timeline_json,
        {
            "timeline": timeline,
            "meta": {
                "mode": "fast",
                "task_id": task_id,
                "window_sec": window_sec,
            },
        },
    )

    summary_text = _request_summary_text(
        transcript_text=transcript.text,
        timeline=timeline,
        api_base=api_base,
        api_key=api_key,
        model=model,
    )
    _write_text(paths.summary_md, summary_text)
    _write_manifest(
        paths=paths,
        task_id=task_id,
        input_value=input_value,
        source_kind=normalized.source_kind,
        timeline=timeline,
    )

    return FastRunResult(
        task_id=task_id,
        task_dir=paths.task_dir,
        video_path=paths.video_path,
        summary_md=paths.summary_md,
        timeline_json=paths.timeline_json,
        transcript_json=paths.transcript_json,
        run_manifest_json=paths.run_manifest_json,
        source_kind=normalized.source_kind,
    )
