from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from openclaw_video_summary.pipeline.fast import FastRunResult, run_fast
from openclaw_video_summary.pipeline.fusion import FusionRunResult, _run_fusion_from_fast_result
from openclaw_video_summary.pipeline.manifest import update_manifest
from openclaw_video_summary.common.fileio import read_json


VISUAL_PATTERNS = [
    re.compile(pattern)
    for pattern in (
        r"画面|镜头|字幕|动画|图表|表格|截图|示意图|流程图",
        r"界面|页面|屏幕|菜单|按钮|设置|左边|右边|上方|下方",
        r"点击|打开|选择|输入|拖动|安装|演示|教程|步骤|操作",
        r"可以看到|如图|这里|这边|对比|展示|切换",
    )
]


@dataclass(frozen=True)
class AutoRunResult:
    task_id: str
    task_dir: Path
    video_path: Path
    summary_md: Path
    timeline_json: Path
    transcript_json: Path
    run_manifest_json: Path
    selected_mode: str
    source_kind: str
    selection_reason: str
    selection_signals: list[str]
    summary_source: str | None = None
    fallback: dict[str, Any] | None = None
    evidence_json: Path | None = None
    fusion_report_md: Path | None = None
    mode: str = "auto"


def _run_fast_pipeline(input_value: str, **kwargs: Any) -> FastRunResult:
    return run_fast(input_value, **kwargs)


def _run_fusion_from_fast(
    fast_result: FastRunResult,
    *,
    api_base: str,
    api_key: str,
    model: str,
    chunk_sec: float,
) -> FusionRunResult:
    return _run_fusion_from_fast_result(
        fast_result,
        api_base=api_base,
        api_key=api_key,
        model=model,
        chunk_sec=chunk_sec,
    )


def _visual_score(text: str) -> tuple[int, list[str]]:
    score = 0
    signals: list[str] = []
    for index, pattern in enumerate(VISUAL_PATTERNS, start=1):
        hits = len(pattern.findall(text))
        if hits:
            score += min(hits, 3)
            signals.append(f"pattern_{index}_hits={hits}")
    return score, signals


def _choose_mode(
    *,
    transcript_payload: dict[str, Any],
    timeline_payload: dict[str, Any],
) -> tuple[str, str, list[str]]:
    transcript_text = str(transcript_payload.get("text") or "")
    timeline_items = list(timeline_payload.get("timeline") or [])
    timeline_text = "\n".join(str(item.get("summary") or "") for item in timeline_items[:12])
    combined = f"{transcript_text}\n{timeline_text}"
    score, signals = _visual_score(combined)

    if len(timeline_items) >= 6:
        score += 1
        signals.append(f"timeline_items={len(timeline_items)}")

    if score >= 4:
        return (
            "fusion",
            "detected strong visual or operational cues in transcript/timeline",
            signals,
        )

    return (
        "fast",
        "transcript looks primarily verbal; visual evidence likely low-value",
        signals or ["no_strong_visual_cues"],
    )


def _normalize_from_fast(
    fast_result: FastRunResult,
    *,
    selection_reason: str,
    selection_signals: list[str],
) -> AutoRunResult:
    return AutoRunResult(
        task_id=fast_result.task_id,
        task_dir=fast_result.task_dir,
        video_path=fast_result.video_path,
        summary_md=fast_result.summary_md,
        timeline_json=fast_result.timeline_json,
        transcript_json=fast_result.transcript_json,
        run_manifest_json=fast_result.run_manifest_json,
        selected_mode="fast",
        source_kind=fast_result.source_kind,
        selection_reason=selection_reason,
        selection_signals=selection_signals,
        summary_source=fast_result.summary_source,
        fallback=fast_result.fallback,
    )


def _normalize_from_fusion(
    fusion_result: FusionRunResult,
    *,
    selected_mode: str,
    selection_reason: str,
    selection_signals: list[str],
    summary_source: str | None,
    fallback: dict[str, Any] | None,
) -> AutoRunResult:
    return AutoRunResult(
        task_id=fusion_result.task_id,
        task_dir=fusion_result.task_dir,
        video_path=fusion_result.video_path,
        summary_md=fusion_result.summary_md,
        timeline_json=fusion_result.timeline_json,
        transcript_json=fusion_result.transcript_json,
        run_manifest_json=fusion_result.run_manifest_json,
        selected_mode=selected_mode,
        source_kind=fusion_result.source_kind,
        selection_reason=selection_reason,
        selection_signals=selection_signals,
        summary_source=summary_source,
        fallback=fallback,
        evidence_json=fusion_result.evidence_json,
        fusion_report_md=fusion_result.fusion_report_md,
    )


def _auto_selection_payload(
    decision: str,
    reason: str,
    signals: list[str],
) -> dict[str, Any]:
    return {
        "auto_selection": {
            "decision": decision,
            "reason": reason,
            "signals": signals,
        }
    }


def run_auto(
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
) -> AutoRunResult:
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

    transcript_payload = read_json(fast_result.transcript_json)
    timeline_payload = read_json(fast_result.timeline_json)
    target_mode, selection_reason, selection_signals = _choose_mode(
        transcript_payload=transcript_payload,
        timeline_payload=timeline_payload,
    )

    if target_mode == "fast":
        update_manifest(
            fast_result.run_manifest_json,
            mode="auto",
            selected_mode="fast",
            fallback=fast_result.fallback,
            extra=_auto_selection_payload("fast", selection_reason, selection_signals),
        )
        return _normalize_from_fast(
            fast_result,
            selection_reason=selection_reason,
            selection_signals=selection_signals,
        )

    fusion_result = _run_fusion_from_fast(
        fast_result,
        api_base=api_base,
        api_key=api_key,
        model=model,
        chunk_sec=chunk_sec,
    )
    fusion_manifest = read_json(fusion_result.run_manifest_json)
    manifest = update_manifest(
        fusion_result.run_manifest_json,
        mode="auto",
        selected_mode=str(fusion_manifest.get("selected_mode") or "fusion"),
        fallback=fusion_manifest.get("fallback"),
        extra=_auto_selection_payload(target_mode, selection_reason, selection_signals),
    )
    selected_mode = str(manifest.get("selected_mode") or "fusion")
    return _normalize_from_fusion(
        fusion_result,
        selected_mode=selected_mode,
        selection_reason=selection_reason,
        selection_signals=selection_signals,
        summary_source=manifest.get("summary_source"),
        fallback=manifest.get("fallback"),
    )
