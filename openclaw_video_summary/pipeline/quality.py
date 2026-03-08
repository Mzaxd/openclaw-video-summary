from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from openclaw_video_summary.pipeline.fast import FastRunResult, run_fast
from openclaw_video_summary.pipeline.fusion import FusionRunResult, run_fusion


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


def _load_manifest(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


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
) -> QualityRunResult:
    pipeline_kwargs = {
        "output_root": output_root,
        "api_base": api_base,
        "api_key": api_key,
        "model": model,
        "window_sec": window_sec,
    }

    try:
        fusion_result = _run_fusion_pipeline(input_value, **pipeline_kwargs)
    except Exception as exc:
        fast_result = _run_fast_pipeline(input_value, **pipeline_kwargs)
        manifest = _load_manifest(fast_result.run_manifest_json)
        fallback = {
            "from": "quality",
            "to": "fast",
            "reason": str(exc),
        }
        manifest["mode"] = "quality"
        manifest["selected_mode"] = "fast"
        manifest["fallback"] = fallback
        _write_json(fast_result.run_manifest_json, manifest)
        return _normalize_from_fast(
            fast_result,
            fallback=fallback,
        )

    manifest = _load_manifest(fusion_result.run_manifest_json)
    fusion_selected_mode = str(manifest.get("selected_mode") or "fusion")

    if fusion_selected_mode == "fast":
        fallback = {
            "from": "quality",
            "to": "fast",
            "reason": "fusion pipeline downgraded to fast",
        }
        manifest["mode"] = "quality"
        manifest["selected_mode"] = "fast"
        manifest["fallback"] = fallback
        _write_json(fusion_result.run_manifest_json, manifest)
        return _normalize_from_fusion(
            fusion_result,
            selected_mode="fast",
            fallback=fallback,
        )

    try:
        enhancement = _run_quality_enhancement(fusion_result)
        manifest["mode"] = "quality"
        manifest["selected_mode"] = "quality"
        manifest["fallback"] = None
        manifest["quality"] = enhancement
        _write_json(fusion_result.run_manifest_json, manifest)
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
        manifest["mode"] = "quality"
        manifest["selected_mode"] = "fusion"
        manifest["fallback"] = fallback
        _write_json(fusion_result.run_manifest_json, manifest)
        return _normalize_from_fusion(
            fusion_result,
            selected_mode="fusion",
            fallback=fallback,
        )
