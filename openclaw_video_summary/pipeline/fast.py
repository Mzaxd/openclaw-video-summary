from __future__ import annotations

import os
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from openclaw_video_summary.asr.transcribe import TranscriptPayload, transcribe_with_backend
from openclaw_video_summary.common.fileio import write_json, write_text
from openclaw_video_summary.ingest.download import normalize_input_to_video
from openclaw_video_summary.ingest.source import detect_source_kind
from openclaw_video_summary.pipeline.task_layout import build_task_paths
from openclaw_video_summary.subtitle.normalize import subtitle_file_to_transcript
from openclaw_video_summary.subtitle.probe import probe_subtitle
from openclaw_video_summary.summary.client import LLMClientError, request_summary
from openclaw_video_summary.summary.prompts import build_summary_messages, normalize_summary_markdown
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
    summary_source: str = "llm"
    fallback: dict[str, Any] | None = None
    mode: str = "fast"


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
    raise RuntimeError("Unable to locate tools/bili-analyzer for summarize backend")


def _build_task_id(input_value: str) -> str:
    _ensure_bili_analyzer_import()
    from bili_analyzer.core import _safe_slug_from_url

    candidate = Path(input_value).expanduser()
    if candidate.exists():
        return candidate.stem
    return _safe_slug_from_url(input_value)


def _api_credential(api_base: str, api_key: str) -> tuple[str, str]:
    final_base = (api_base or os.environ.get("OPENAI_BASE_URL") or "").strip()
    final_key = (api_key or os.environ.get("OPENAI_API_KEY") or "").strip()
    return final_base, final_key


def _transcribe_video(
    *,
    video_path: Path,
    transcript_path: Path,
    language: str = "auto",
    asr_model: str = "small",
    device: str = "auto",
    compute_type: str = "int8",
    platform_profile: str = "auto",
) -> tuple[TranscriptPayload, dict[str, Any]]:
    return transcribe_with_backend(
        input_path=video_path,
        output_dir=transcript_path.parent,
        asr_model=asr_model,
        language=language,
        device=device,
        compute_type=compute_type,
        platform_profile=platform_profile,
    )


def _local_fallback_markdown(transcript_text: str, timeline: list[dict[str, Any]], reason: str) -> str:
    head = (transcript_text or "").strip().replace("\n", " ")
    preview = head[:300] + ("..." if len(head) > 300 else "")
    lines = [
        "# 视频中文总结（降级结果）",
        "",
        f"> 说明：LLM 总结不可用，已使用本地规则降级。原因：{reason}",
        "",
        "## 一句话总结",
        "该视频已完成转写与时间轴整理，建议在 LLM 恢复后重新生成高质量中文总结。",
        "",
        "## 转写摘录",
        preview if preview else "（转写文本为空）",
        "",
        "## 时间线",
    ]
    for item in timeline[:10]:
        lines.append(f"- {item.get('start', 0)}s - {item.get('end', 0)}s：{item.get('summary', '')}")
    return "\n".join(lines).strip() + "\n"


def _request_summary_text(
    *,
    transcript_text: str,
    timeline: list[dict[str, object]],
    visual_context: dict[str, Any] | None,
    api_base: str,
    api_key: str,
    model: str,
) -> str:
    messages = build_summary_messages(transcript_text, timeline, visual_context)
    return request_summary(
        api_base=api_base,
        api_key=api_key,
        model=model,
        messages=messages,
    )


def run_fast(
    input_value: str,
    *,
    output_root: Path | str,
    api_base: str = "",
    api_key: str = "",
    model: str = "glm-4.6v",
    window_sec: float = 90.0,
    language: str = "auto",
    asr_model: str = "small",
    device: str = "auto",
    compute_type: str = "int8",
    platform_profile: str = "auto",
    **_: Any,
) -> FastRunResult:
    begin = time.perf_counter()
    task_id = _build_task_id(input_value)
    paths = build_task_paths(output_root, task_id)
    source_kind = detect_source_kind(input_value)
    subtitle_probe: dict[str, Any] = {
        "attempted": False,
        "success": False,
        "provider": "yt-dlp",
        "language": "",
        "duration_sec": 0.0,
        "reason": "",
    }
    transcript_source = "asr"

    subtitle_hit = False
    if source_kind in {"youtube", "bilibili"}:
        probe = probe_subtitle(
            input_value,
            timeout_sec=5.0,
            cookies_from_browser=True,
            output_dir=paths.task_dir,
        )
        subtitle_probe = {
            "attempted": True,
            "success": probe.get("status") == "success",
            "provider": probe.get("provider", "yt-dlp"),
            "language": probe.get("language", ""),
            "duration_sec": probe.get("duration_sec", 0.0),
            "reason": probe.get("reason", ""),
        }
        subtitle_path = probe.get("subtitle_path") or ""
        if probe.get("status") == "success" and subtitle_path:
            transcript = subtitle_file_to_transcript(subtitle_path)
            write_json(paths.transcript_json, transcript.to_dict())
            transcribe_result = {
                "transcript_file": str(paths.transcript_json),
                "input_video": "",
                "output_dir": str(paths.task_dir),
                "engine": "subtitle",
                "provider": probe.get("provider", "yt-dlp"),
                "language": probe.get("language", ""),
                "subtitle_file": subtitle_path,
                "runtime_profile": {
                    "profile": "subtitle",
                    "device": "n/a",
                    "compute_type": "n/a",
                    "reason": "platform subtitle retrieval",
                },
            }
            transcript_source = "subtitle"
            subtitle_hit = True

    if not subtitle_hit:
        normalized = normalize_input_to_video(input_value, paths.task_dir)
        source_kind = normalized.source_kind
        try:
            transcribe_output = _transcribe_video(
                video_path=paths.video_path,
                transcript_path=paths.transcript_json,
                language=language,
                asr_model=asr_model,
                device=device,
                compute_type=compute_type,
                platform_profile=platform_profile,
            )
        except TypeError:
            transcribe_output = _transcribe_video(
                video_path=paths.video_path,
                transcript_path=paths.transcript_json,
            )
        if isinstance(transcribe_output, tuple):
            transcript, transcribe_result = transcribe_output
        else:
            transcript = transcribe_output
            transcribe_result = {
                "transcript_file": str(paths.transcript_json),
                "input_video": str(paths.video_path),
                "output_dir": str(paths.task_dir),
            }
            write_json(paths.transcript_json, transcript.to_dict())
        transcribe_result.setdefault(
            "runtime_profile",
            {
                "profile": "unknown",
                "device": device,
                "compute_type": compute_type,
                "reason": "not reported by backend",
            },
        )

    timeline = build_timeline(transcript.segments, window_sec=window_sec)
    write_json(
        paths.timeline_json,
        {
            "timeline": timeline,
            "meta": {
                "source_transcript": transcribe_result.get("transcript_file"),
                "window_sec": window_sec,
                "segments": len(transcript.segments),
                "items": len(timeline),
            },
        },
    )

    final_api_base, final_api_key = _api_credential(api_base, api_key)
    summary_source = "llm"
    fallback: dict[str, Any] | None = None

    if not (final_api_base and final_api_key):
        summary_source = "local_fallback"
        fallback = {
            "from": "fast",
            "to": "local_fallback",
            "reason": "Missing LLM API configuration: set --api-base/--api-key or OPENAI_BASE_URL/OPENAI_API_KEY",
        }
        summary_text = _local_fallback_markdown(transcript.text, timeline, fallback["reason"])
    else:
        try:
            summary_text = _request_summary_text(
                transcript_text=transcript.text,
                timeline=timeline,
                visual_context=None,
                api_base=final_api_base,
                api_key=final_api_key,
                model=model,
            )
        except LLMClientError as exc:
            summary_source = "local_fallback"
            fallback = {
                "from": "llm",
                "to": "local_fallback",
                "reason": str(exc),
            }
            summary_text = _local_fallback_markdown(transcript.text, timeline, str(exc))

    write_text(paths.summary_md, normalize_summary_markdown(summary_text))

    manifest = {
        "url": input_value,
        "mode": "fast",
        "selected_mode": "fast",
        "summary_source": summary_source,
        "task_root": str(paths.task_dir),
        "task_id": task_id,
        "summary_zh_md": str(paths.summary_md),
        "timeline_json": str(paths.timeline_json),
        "transcript_json": str(paths.transcript_json),
        "source_kind": source_kind,
        "transcript_source": transcript_source,
        "subtitle_probe": subtitle_probe,
        "transcribe": transcribe_result,
        "fallback": fallback,
        "timings_sec": {
            "total_sec": round(time.perf_counter() - begin, 3),
        },
    }
    write_json(paths.run_manifest_json, manifest)

    return FastRunResult(
        task_id=task_id,
        task_dir=paths.task_dir,
        video_path=paths.video_path,
        summary_md=paths.summary_md,
        timeline_json=paths.timeline_json,
        transcript_json=paths.transcript_json,
        run_manifest_json=paths.run_manifest_json,
        source_kind=source_kind,
        summary_source=summary_source,
        fallback=fallback,
    )
