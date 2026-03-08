from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from openclaw_video_summary.pipeline.fast import FastRunResult, _api_credential, run_fast
from openclaw_video_summary.summary.client import LLMClientError, request_summary, request_video_analysis
from openclaw_video_summary.summary.prompts import build_summary_messages, normalize_summary_markdown
from openclaw_video_summary.vision.analyze import VisualEvidence


@dataclass(frozen=True)
class FusionRunResult:
    task_id: str
    task_dir: Path
    video_path: Path
    summary_md: Path
    timeline_json: Path
    transcript_json: Path
    run_manifest_json: Path
    evidence_json: Path
    fusion_report_md: Path
    source_kind: str
    fallback: dict[str, str] | None = None
    mode: str = "fusion"


@dataclass(frozen=True)
class VideoChunk:
    index: int
    start: float
    end: float
    path: Path
    asr_preview: str


def _run_fast_pipeline(input_value: str, **kwargs: Any) -> FastRunResult:
    return run_fast(input_value, **kwargs)


def _load_manifest(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_transcript(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _write_text(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")


def _probe_duration(video_path: Path) -> float:
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        str(video_path),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        details = proc.stderr.strip() or proc.stdout.strip() or "ffprobe failed"
        raise RuntimeError(details)
    try:
        return float((proc.stdout or "0").strip())
    except ValueError as exc:
        raise RuntimeError(f"Invalid ffprobe duration for {video_path.name}") from exc


def _build_asr_preview(segments: list[dict[str, Any]], start: float, end: float) -> str:
    lines: list[str] = []
    for segment in segments:
        seg_start = float(segment.get("start") or 0.0)
        seg_end = float(segment.get("end") or seg_start)
        if seg_end <= start or seg_start >= end:
            continue
        text = str(segment.get("text") or "").strip()
        if not text:
            continue
        minutes = int(seg_start // 60)
        seconds = int(seg_start % 60)
        lines.append(f"{minutes:02d}:{seconds:02d} {text}")
        if len(lines) >= 8:
            break
    return "\n".join(lines)


def _split_video_chunks(
    video_path: Path,
    *,
    chunks_dir: Path,
    chunk_sec: float,
    transcript_segments: list[dict[str, Any]],
) -> list[VideoChunk]:
    chunks_dir.mkdir(parents=True, exist_ok=True)
    segment_pattern = chunks_dir / "chunk_%02d.mp4"
    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(video_path),
        "-map",
        "0",
        "-c",
        "copy",
        "-f",
        "segment",
        "-segment_time",
        str(chunk_sec),
        "-reset_timestamps",
        "1",
        str(segment_pattern),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        details = proc.stderr.strip() or proc.stdout.strip() or "ffmpeg segment failed"
        raise RuntimeError(details)

    chunk_paths = sorted(chunks_dir.glob("chunk_*.mp4"))
    if not chunk_paths:
        raise RuntimeError("ffmpeg did not produce any video chunks")

    chunks: list[VideoChunk] = []
    current_start = 0.0
    for index, chunk_path in enumerate(chunk_paths):
        duration = max(_probe_duration(chunk_path), 0.0)
        current_end = current_start + duration
        chunks.append(
            VideoChunk(
                index=index,
                start=round(current_start, 3),
                end=round(current_end, 3),
                path=chunk_path,
                asr_preview=_build_asr_preview(transcript_segments, current_start, current_end),
            )
        )
        current_start = current_end
    return chunks


def _build_chunk_prompt(chunk: VideoChunk) -> str:
    return (
        "请分析这个视频片段，输出中文，保持简洁但具体。\n"
        "要求：\n"
        "1) 先写“画面内容摘要”。\n"
        "2) 再写“画面与口播一致性”：高/中/低。\n"
        "3) 再写“关键画面证据”：列出1-3条。\n"
        "4) 不要复述太多口播，不要编造未出现的画面。\n\n"
        f"片段时间：{chunk.start:.1f}s - {chunk.end:.1f}s\n"
        f"对应口播预览：\n{chunk.asr_preview or '（该时间段无明显口播）'}\n"
    )


def _analyze_chunk(
    chunk: VideoChunk,
    *,
    api_base: str,
    api_key: str,
    model: str,
) -> VisualEvidence:
    analysis = request_video_analysis(
        api_base=api_base,
        api_key=api_key,
        model=model,
        video_path=str(chunk.path),
        prompt=_build_chunk_prompt(chunk),
    )
    confidence = "high" if analysis.strip() else "low"
    return VisualEvidence(
        start=chunk.start,
        end=chunk.end,
        observation=(analysis or "").strip() or "（视频分析未返回内容）",
        confidence=confidence,
        metadata={
            "chunk_index": chunk.index,
            "chunk_path": str(chunk.path),
            "asr_preview": chunk.asr_preview,
        },
    )


def _analyze_chunks(
    chunks: list[VideoChunk],
    *,
    api_base: str,
    api_key: str,
    model: str,
) -> list[VisualEvidence]:
    evidence: list[VisualEvidence] = []
    for chunk in chunks:
        evidence.append(
            _analyze_chunk(
                chunk,
                api_base=api_base,
                api_key=api_key,
                model=model,
            )
        )
    return evidence


def _write_evidence(path: Path, evidence: list[VisualEvidence]) -> None:
    items = []
    for item in evidence:
        payload = item.to_dict()
        payload["chunk"] = (item.metadata or {}).get("chunk_index")
        payload["video_analysis"] = item.observation
        items.append(payload)
    _write_json(path, {"items": items, "count": len(items)})


def _write_report(path: Path, evidence: list[VisualEvidence]) -> None:
    lines = ["# B站视频多模态融合分析报告", "", "## 分段画面证据"]
    for item in evidence:
        metadata = item.metadata or {}
        chunk_index = metadata.get("chunk_index")
        chunk_title = f"片段 {int(chunk_index) + 1}" if isinstance(chunk_index, int) else "片段"
        lines.extend(
            [
                "",
                f"### {chunk_title}：{item.start:.1f}s ~ {item.end:.1f}s",
                "",
                "**口播预览**：",
                metadata.get("asr_preview") or "（该片段无明显口播）",
                "",
                "**画面分析**：",
                item.observation or "（未返回画面分析）",
            ]
        )
    _write_text(path, "\n".join(lines).strip() + "\n")


def _load_timeline(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return list(payload.get("timeline") or [])


def _build_visual_context(
    *,
    evidence: list[VisualEvidence],
    chunk_sec: float,
) -> dict[str, Any]:
    items: list[dict[str, Any]] = []
    for item in evidence:
        metadata = item.metadata or {}
        items.append(
            {
                "chunk": metadata.get("chunk_index"),
                "start": item.start,
                "end": item.end,
                "asr_preview": metadata.get("asr_preview") or "",
                "video_analysis": item.observation,
            }
        )
    return {
        "mode": "fusion",
        "chunk_sec": chunk_sec,
        "evidence_count": len(items),
        "evidence": items,
    }


def _rewrite_summary_with_evidence(
    *,
    summary_md: Path,
    transcript_payload: dict[str, Any],
    timeline: list[dict[str, Any]],
    evidence: list[VisualEvidence],
    api_base: str,
    api_key: str,
    model: str,
    chunk_sec: float,
) -> str:
    messages = build_summary_messages(
        str(transcript_payload.get("text") or ""),
        timeline,
        _build_visual_context(evidence=evidence, chunk_sec=chunk_sec),
    )
    content = request_summary(
        api_base=api_base,
        api_key=api_key,
        model=model,
        messages=messages,
    )
    normalized = normalize_summary_markdown(content)
    summary_md.write_text(normalized, encoding="utf-8")
    return normalized


def _run_fusion_from_fast_result(
    fast_result: FastRunResult,
    *,
    api_base: str = "",
    api_key: str = "",
    model: str = "glm-4.6v",
    chunk_sec: float = 180.0,
) -> FusionRunResult:
    evidence_json = fast_result.task_dir / "evidence.json"
    fusion_report_md = fast_result.task_dir / "fusion_report.md"
    manifest = _load_manifest(fast_result.run_manifest_json)
    final_api_base, final_api_key = _api_credential(api_base, api_key)

    try:
        transcript_payload = _load_transcript(fast_result.transcript_json)
        timeline = _load_timeline(fast_result.timeline_json)
        chunks = _split_video_chunks(
            fast_result.video_path,
            chunks_dir=fast_result.task_dir / "chunks",
            chunk_sec=chunk_sec,
            transcript_segments=list(transcript_payload.get("segments") or []),
        )
        if not final_api_base or not final_api_key:
            raise RuntimeError(
                "fusion mode requires LLM API configuration for chunk video analysis"
            )
        evidence = _analyze_chunks(
            chunks,
            api_base=final_api_base,
            api_key=final_api_key,
            model=model,
        )
        if not evidence:
            raise RuntimeError("fusion mode requires at least one analyzed chunk")
        _write_evidence(evidence_json, evidence)
        _write_report(fusion_report_md, evidence)
        summary_source = manifest.get("summary_source") or "llm"
        summary_fallback = None
        try:
            _rewrite_summary_with_evidence(
                summary_md=fast_result.summary_md,
                transcript_payload=transcript_payload,
                timeline=timeline,
                evidence=evidence,
                api_base=final_api_base,
                api_key=final_api_key,
                model=model,
                chunk_sec=chunk_sec,
            )
            summary_source = "llm_fusion"
        except LLMClientError as exc:
            summary_fallback = {
                "from": "fusion_summary",
                "to": "fast_summary",
                "reason": str(exc),
            }
        manifest["mode"] = "fusion"
        manifest["selected_mode"] = "fusion"
        manifest["summary_source"] = summary_source
        manifest["chunk_sec"] = chunk_sec
        manifest["chunk_count"] = len(chunks)
        manifest["chunks_dir"] = str(fast_result.task_dir / "chunks")
        manifest["evidence_items"] = len(evidence)
        manifest["fallback"] = None
        manifest["summary_fallback"] = summary_fallback
        _write_json(fast_result.run_manifest_json, manifest)
        fallback = None
    except Exception as exc:
        fallback = {
            "from": "fusion",
            "to": "fast",
            "reason": str(exc),
        }
        manifest["mode"] = "fusion"
        manifest["selected_mode"] = "fast"
        manifest["chunk_sec"] = chunk_sec
        manifest["fallback"] = fallback
        manifest["evidence_items"] = 0
        _write_json(fast_result.run_manifest_json, manifest)

    return FusionRunResult(
        task_id=fast_result.task_id,
        task_dir=fast_result.task_dir,
        video_path=fast_result.video_path,
        summary_md=fast_result.summary_md,
        timeline_json=fast_result.timeline_json,
        transcript_json=fast_result.transcript_json,
        run_manifest_json=fast_result.run_manifest_json,
        evidence_json=evidence_json,
        fusion_report_md=fusion_report_md,
        source_kind=fast_result.source_kind,
        fallback=fallback,
    )


def run_fusion(
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
    chunk_sec: float = 180.0,
    **_: Any,
) -> FusionRunResult:
    fast_result = _run_fast_pipeline(
        input_value,
        output_root=output_root,
        api_base=api_base,
        api_key=api_key,
        model=model,
        window_sec=window_sec,
        language=language,
        asr_model=asr_model,
        device=device,
        compute_type=compute_type,
    )
    return _run_fusion_from_fast_result(
        fast_result,
        api_base=api_base,
        api_key=api_key,
        model=model,
        chunk_sec=chunk_sec,
    )
