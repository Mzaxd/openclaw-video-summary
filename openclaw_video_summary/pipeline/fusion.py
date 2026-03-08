from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from openclaw_video_summary.pipeline.fast import FastRunResult, run_fast
from openclaw_video_summary.vision.analyze import VisualEvidence, VisionAnalyzer


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


class _UnconfiguredVisionAnalyzer(VisionAnalyzer):
    def analyze_video(self, video_path: str | Path) -> list[VisualEvidence]:
        raise RuntimeError(
            "Vision backend is not wired into run_fusion yet. Inject or monkeypatch _analyze_video in tests, "
            "or implement the real backend in a later task."
        )


_VISION_ANALYZER = _UnconfiguredVisionAnalyzer()


def _run_fast_pipeline(input_value: str, **kwargs: Any) -> FastRunResult:
    return run_fast(input_value, **kwargs)


def _analyze_video(video_path: Path) -> list[VisualEvidence]:
    return _VISION_ANALYZER.analyze_video(video_path)


def _load_manifest(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _write_text(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")


def _write_evidence(path: Path, evidence: list[VisualEvidence]) -> None:
    _write_json(
        path,
        {
            "items": [item.to_dict() for item in evidence],
            "count": len(evidence),
        },
    )


def _write_report(path: Path, evidence: list[VisualEvidence]) -> None:
    lines = ["# Fusion Report", "", "## Visual Evidence"]
    for item in evidence:
        lines.append(
            f"- {item.start:.3f}s - {item.end:.3f}s | {item.confidence} | {item.observation}"
        )
    _write_text(path, "\n".join(lines).strip() + "\n")


def run_fusion(
    input_value: str,
    *,
    output_root: Path | str,
    api_base: str = "",
    api_key: str = "",
    model: str = "glm-4.6v",
    window_sec: float = 90.0,
) -> FusionRunResult:
    fast_result = _run_fast_pipeline(
        input_value,
        output_root=output_root,
        api_base=api_base,
        api_key=api_key,
        model=model,
        window_sec=window_sec,
    )

    evidence_json = fast_result.task_dir / "evidence.json"
    fusion_report_md = fast_result.task_dir / "fusion_report.md"
    manifest = _load_manifest(fast_result.run_manifest_json)

    try:
        evidence = _analyze_video(fast_result.video_path)
        _write_evidence(evidence_json, evidence)
        _write_report(fusion_report_md, evidence)
        manifest["mode"] = "fusion"
        manifest["selected_mode"] = "fusion"
        manifest["evidence_items"] = len(evidence)
        manifest["fallback"] = None
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
