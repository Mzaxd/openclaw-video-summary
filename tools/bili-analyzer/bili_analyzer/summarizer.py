from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

from .core import AnalyzerError, ExitCode, analyze_frames_dir, prepare_video, transcribe_video
from .llm_client import LLMClientError, chat_completion
from .prompts import build_summary_messages
from .timeline import build_timeline


def _load_transcript_payload(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise AnalyzerError(
            message=f"Failed to read transcript file: {path}",
            exit_code=ExitCode.IO_ERROR,
            details=str(exc),
        ) from exc
    except json.JSONDecodeError as exc:
        raise AnalyzerError(
            message=f"Invalid transcript JSON format: {path}",
            exit_code=ExitCode.SUMMARIZE_FAILED,
            details=str(exc),
        ) from exc


def _save_json(path: Path, payload: dict[str, Any]) -> None:
    try:
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    except OSError as exc:
        raise AnalyzerError(
            message=f"Failed to write JSON file: {path}",
            exit_code=ExitCode.IO_ERROR,
            details=str(exc),
        ) from exc


def _save_text(path: Path, text: str) -> None:
    try:
        path.write_text(text, encoding="utf-8")
    except OSError as exc:
        raise AnalyzerError(
            message=f"Failed to write text file: {path}",
            exit_code=ExitCode.IO_ERROR,
            details=str(exc),
        ) from exc


def _api_credential(api_base: str | None, api_key: str | None) -> tuple[str, str]:
    final_base = (api_base or os.environ.get("OPENAI_BASE_URL") or "").strip()
    final_key = (api_key or os.environ.get("OPENAI_API_KEY") or "").strip()
    return final_base, final_key


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


def _call_llm_summary(
    *,
    transcript_text: str,
    timeline: list[dict[str, Any]],
    visual_context: dict[str, Any] | None,
    api_base: str,
    api_key: str,
    llm_model: str,
) -> str:
    messages = build_summary_messages(
        transcript_text=transcript_text,
        timeline=timeline,
        visual_context=visual_context,
    )
    try:
        return chat_completion(
            api_base=api_base,
            api_key=api_key,
            model=llm_model,
            messages=messages,
        )
    except LLMClientError as exc:
        raise AnalyzerError(
            message="LLM summary generation failed",
            exit_code=ExitCode.SUMMARIZE_FAILED,
            details=str(exc),
        ) from exc


def summarize_video(
    *,
    url: str,
    output: str = "./tmp",
    mode: str = "fast",
    language: str = "auto",
    asr_model: str = "small",
    device: str = "auto",
    compute_type: str = "int8",
    llm_model: str = "glm-4.6v",
    api_base: str | None = None,
    api_key: str | None = None,
    fps: float = 0.5,
    similarity: float = 0.85,
    timeline_window_sec: float = 90.0,
) -> dict[str, Any]:
    if mode not in {"fast", "fusion"}:
        raise AnalyzerError(
            message=f"Invalid mode: {mode}",
            exit_code=ExitCode.INVALID_ARGUMENT,
            hint="Use mode in: fast, fusion",
        )

    final_api_base, final_api_key = _api_credential(api_base, api_key)
    begin = time.perf_counter()

    prepare_kwargs: dict[str, Any] = {
        "url": url,
        "output": output,
        "fps": fps,
        "similarity": similarity,
        "no_dedup": False,
    }
    if mode == "fast":
        prepare_kwargs["video_only"] = True
        prepare_kwargs["frames_only"] = False
    else:
        prepare_kwargs["video_only"] = False
        prepare_kwargs["frames_only"] = False

    prepare_result = prepare_video(**prepare_kwargs)
    task_root = Path(prepare_result["task_root"])

    asr_language = None if language == "auto" else language
    transcribe_result = transcribe_video(
        input_path=str(task_root),
        output=str(task_root),
        asr_model=asr_model,
        language=asr_language,
        device=device,
        compute_type=compute_type,
    )

    transcript_payload = _load_transcript_payload(Path(transcribe_result["transcript_file"]))
    transcript_text = (transcript_payload.get("text") or "").strip()
    segments = transcript_payload.get("segments") or []

    timeline_items = build_timeline(segments, window_sec=timeline_window_sec)
    timeline_path = task_root / "timeline.json"
    _save_json(
        timeline_path,
        {
            "timeline": timeline_items,
            "meta": {
                "source_transcript": transcribe_result.get("transcript_file"),
                "window_sec": timeline_window_sec,
                "segments": len(segments),
                "items": len(timeline_items),
            },
        },
    )

    fallback: dict[str, Any] | None = None
    summary_source = "llm"
    visual_context: dict[str, Any] | None = None

    llm_enabled = bool(final_api_base and final_api_key)
    if not llm_enabled:
        summary_source = "local_fallback"
        fallback = {
            "from": mode,
            "to": "local_fallback",
            "reason": "Missing LLM API configuration: set --api-base/--api-key or OPENAI_BASE_URL/OPENAI_API_KEY",
        }
        summary_md = _local_fallback_markdown(transcript_text, timeline_items, fallback["reason"])
    else:
        try:
            if mode == "fusion":
                if os.environ.get("BILI_FORCE_FUSION_FAIL") == "1":
                    raise RuntimeError("BILI_FORCE_FUSION_FAIL=1")
                images_dir = task_root / "images"
                if not images_dir.exists():
                    raise RuntimeError("fusion mode requires extracted frames")
                frame_stats = analyze_frames_dir(images_dir)
                visual_context = {
                    "frame_count": frame_stats.get("count", 0),
                    "sample_frames": (frame_stats.get("preview") or [])[:8],
                }

            summary_md = _call_llm_summary(
                transcript_text=transcript_text,
                timeline=timeline_items,
                visual_context=visual_context,
                api_base=final_api_base,
                api_key=final_api_key,
                llm_model=llm_model,
            )
        except Exception as first_exc:
            if mode == "fusion":
                fallback = {
                    "from": "fusion",
                    "to": "fast",
                    "reason": str(first_exc),
                }
                try:
                    summary_md = _call_llm_summary(
                        transcript_text=transcript_text,
                        timeline=timeline_items,
                        visual_context=None,
                        api_base=final_api_base,
                        api_key=final_api_key,
                        llm_model=llm_model,
                    )
                except Exception as llm_exc:
                    summary_source = "local_fallback"
                    fallback["llm_error"] = str(llm_exc)
                    summary_md = _local_fallback_markdown(transcript_text, timeline_items, str(llm_exc))
            else:
                summary_source = "local_fallback"
                fallback = {"from": "llm", "to": "local_fallback", "reason": str(first_exc)}
                summary_md = _local_fallback_markdown(transcript_text, timeline_items, str(first_exc))

    summary_path = task_root / "summary_zh.md"
    _save_text(summary_path, summary_md.strip() + "\n")

    manifest = {
        "url": url,
        "mode": mode,
        "summary_source": summary_source,
        "task_root": str(task_root),
        "summary_zh_md": str(summary_path),
        "timeline_json": str(timeline_path),
        "prepare": prepare_result,
        "transcribe": transcribe_result,
        "fallback": fallback,
        "timings_sec": {
            "total_sec": round(time.perf_counter() - begin, 3),
        },
    }
    manifest_path = task_root / "summarize_manifest.json"
    _save_json(manifest_path, manifest)
    manifest["manifest"] = str(manifest_path)
    return manifest
