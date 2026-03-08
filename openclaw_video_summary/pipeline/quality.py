from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from openclaw_video_summary.common.fileio import read_json
from openclaw_video_summary.pipeline.fast import FastRunResult, run_fast
from openclaw_video_summary.pipeline.fusion import FusionRunResult, run_fusion
from openclaw_video_summary.pipeline.manifest import update_manifest


@dataclass(frozen=True)
class QualityRunResult:
    task_id: str
    task_dir: Path
    video_path: Path
    summary_md: Path
    timeline_json: Path
    transcript_json: Path
    run_manifest_json: Path
    selected_mode: str
    source_kind: str
    fallback: dict[str, str] | None = None
    mode: str = "quality"


def _run_fusion_pipeline(input_value: str, **kwargs: Any) -> FusionRunResult:
    return run_fusion(input_value, **kwargs)


def _run_fast_pipeline(input_value: str, **kwargs: Any) -> FastRunResult:
    return run_fast(input_value, **kwargs)


def _run_quality_enhancement(result: FusionRunResult) -> dict[str, Any]:
    raise RuntimeError(
        "Quality enhancement is not wired into run_quality yet. Inject or monkeypatch "
        "_run_quality_enhancement in tests, or implement the real backend in a later task."
    )


def _normalize_from_fast(
    fast_result: FastRunResult,
    *,
    fallback: dict[str, str] | None,
) -> QualityRunResult:
    return QualityRunResult(
        task_id=fast_result.task_id,
        task_dir=fast_result.task_dir,
        video_path=fast_result.video_path,
        summary_md=fast_result.summary_md,
        timeline_json=fast_result.timeline_json,
        transcript_json=fast_result.transcript_json,
        run_manifest_json=fast_result.run_manifest_json,
        selected_mode="fast",
        source_kind=fast_result.source_kind,
        fallback=fallback,
    )


def _normalize_from_fusion(
    fusion_result: FusionRunResult,
    *,
    selected_mode: str,
    fallback: dict[str, str] | None,
) -> QualityRunResult:
    return QualityRunResult(
        task_id=fusion_result.task_id,
        task_dir=fusion_result.task_dir,
        video_path=fusion_result.video_path,
        summary_md=fusion_result.summary_md,
        timeline_json=fusion_result.timeline_json,
        transcript_json=fusion_result.transcript_json,
        run_manifest_json=fusion_result.run_manifest_json,
        selected_mode=selected_mode,
        source_kind=fusion_result.source_kind,
        fallback=fallback,
    )


def run_quality(
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
) -> QualityRunResult:
    pipeline_kwargs = {
        "output_root": output_root,
        "api_base": api_base,
        "api_key": api_key,
        "model": model,
        "window_sec": window_sec,
        "language": language,
        "asr_model": asr_model,
        "device": device,
        "compute_type": compute_type,
        "chunk_sec": chunk_sec,
    }

    try:
        fusion_result = _run_fusion_pipeline(input_value, **pipeline_kwargs)
    except Exception as exc:
        fast_result = _run_fast_pipeline(input_value, **pipeline_kwargs)
        fallback = {
            "from": "quality",
            "to": "fast",
            "reason": str(exc),
        }
        update_manifest(
            fast_result.run_manifest_json,
            mode="quality",
            selected_mode="fast",
            fallback=fallback,
        )
        return _normalize_from_fast(
            fast_result,
            fallback=fallback,
        )

    manifest = read_json(fusion_result.run_manifest_json)
    fusion_selected_mode = str(manifest.get("selected_mode") or "fusion")

    if fusion_selected_mode == "fast":
        fallback = {
            "from": "quality",
            "to": "fast",
            "reason": "fusion pipeline downgraded to fast",
        }
        update_manifest(
            fusion_result.run_manifest_json,
            mode="quality",
            selected_mode="fast",
            fallback=fallback,
        )
        return _normalize_from_fusion(
            fusion_result,
            selected_mode="fast",
            fallback=fallback,
        )

    try:
        enhancement = _run_quality_enhancement(fusion_result)
        update_manifest(
            fusion_result.run_manifest_json,
            mode="quality",
            selected_mode="quality",
            fallback=None,
            extra={"quality": enhancement},
        )
        return _normalize_from_fusion(
            fusion_result,
            selected_mode="quality",
            fallback=None,
        )
    except Exception as exc:
        fallback = {
            "from": "quality",
            "to": "fusion",
            "reason": str(exc),
        }
        update_manifest(
            fusion_result.run_manifest_json,
            mode="quality",
            selected_mode="fusion",
            fallback=fallback,
        )
        return _normalize_from_fusion(
            fusion_result,
            selected_mode="fusion",
            fallback=fallback,
        )
