from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from openclaw_video_summary.pipeline.auto import run_auto
from openclaw_video_summary.pipeline.fast import run_fast
from openclaw_video_summary.pipeline.fusion import run_fusion
from openclaw_video_summary.pipeline.quality import run_quality


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="openclaw-video-summary",
        description="Skill-first video summarization for OpenClaw",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    summarize = subparsers.add_parser("summarize", help="Summarize a video input")
    summarize.add_argument("input_value", help="Video URL or local file path")
    summarize.add_argument("-o", "--output-root", "--output", dest="output_root", default="./tmp", help="Directory for run artifacts")
    summarize.add_argument(
        "--mode",
        choices=["auto", "fast", "fusion", "quality"],
        default="auto",
        help="Pipeline mode",
    )
    summarize.add_argument("--language", default="auto", help="ASR language code or auto (default: auto)")
    summarize.add_argument("--asr-model", default="small", help="ASR model size (default: small)")
    summarize.add_argument("--device", default="auto", help="ASR device (default: auto)")
    summarize.add_argument("--compute-type", default="int8", help="ASR compute type (default: int8)")
    summarize.add_argument("--api-base", default="", help="OpenAI-compatible API base URL")
    summarize.add_argument("--api-key", default="", help="OpenAI-compatible API key")
    summarize.add_argument("--model", "--llm-model", dest="model", default="glm-4.6v", help="Model name")
    summarize.add_argument("--chunk-sec", type=float, default=180.0, help="Chunk size in seconds for fusion mode")
    summarize.add_argument(
        "--window-sec",
        "--timeline-window-sec",
        type=float,
        default=90.0,
        dest="window_sec",
        help="Timeline window size in seconds",
    )
    summarize.add_argument(
        "--json-summary",
        action="store_true",
        help="Print concise JSON result",
    )

    return parser


def _serialize_result(result: Any, mode: str) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "mode": mode,
        "task_id": getattr(result, "task_id", None),
        "task_dir": str(getattr(result, "task_dir", "")),
        "video_path": str(getattr(result, "video_path", "")),
        "summary_md": str(getattr(result, "summary_md", "")),
        "summary_zh_md": str(getattr(result, "summary_md", "")),
        "timeline_json": str(getattr(result, "timeline_json", "")),
        "transcript_json": str(getattr(result, "transcript_json", "")),
        "run_manifest_json": str(getattr(result, "run_manifest_json", "")),
        "manifest": str(getattr(result, "run_manifest_json", "")),
        "source_kind": getattr(result, "source_kind", None),
        "summary_source": getattr(result, "summary_source", None),
    }

    if hasattr(result, "selected_mode"):
        payload["selected_mode"] = getattr(result, "selected_mode")
    if hasattr(result, "selection_reason"):
        payload["selection_reason"] = getattr(result, "selection_reason")
    if hasattr(result, "selection_signals"):
        payload["selection_signals"] = getattr(result, "selection_signals")
    if hasattr(result, "fallback"):
        payload["fallback"] = getattr(result, "fallback")
    if hasattr(result, "evidence_json"):
        payload["evidence_json"] = str(getattr(result, "evidence_json"))
    if hasattr(result, "fusion_report_md"):
        payload["fusion_report_md"] = str(getattr(result, "fusion_report_md"))

    return payload


def _run_summarize(args: argparse.Namespace) -> dict[str, Any]:
    run_kwargs = {
        "output_root": Path(args.output_root),
        "api_base": args.api_base,
        "api_key": args.api_key,
        "model": args.model,
        "window_sec": args.window_sec,
        "language": args.language,
        "asr_model": args.asr_model,
        "device": args.device,
        "compute_type": args.compute_type,
        "chunk_sec": args.chunk_sec,
    }

    if args.mode == "auto":
        result = run_auto(args.input_value, **run_kwargs)
    elif args.mode == "fast":
        result = run_fast(args.input_value, **run_kwargs)
    elif args.mode == "fusion":
        result = run_fusion(args.input_value, **run_kwargs)
    else:
        result = run_quality(args.input_value, **run_kwargs)

    return _serialize_result(result, args.mode)


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.command != "summarize":
        parser.error(f"unsupported command: {args.command}")

    payload = _run_summarize(args)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
