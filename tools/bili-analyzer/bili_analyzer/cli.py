from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

from .core import AnalyzerError, ExitCode, analyze_frames_dir, prepare_video, transcribe_video
from .summarizer import summarize_video


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="bili-analyzer",
        description="Bilibili video preparation tool (download -> extract -> dedup)",
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose logs")

    sub = parser.add_subparsers(dest="command", required=True)

    p_prepare = sub.add_parser("prepare", help="Prepare video and frames")
    p_prepare.add_argument("url", help="Bilibili video URL")
    p_prepare.add_argument("-o", "--output", default="./tmp", help="Output root directory")
    p_prepare.add_argument("--fps", type=float, default=1.0, help="Frame extraction fps (default: 1.0)")
    p_prepare.add_argument(
        "--similarity",
        type=float,
        default=0.80,
        help="Similarity threshold in [0,1] for adjacent frame dedup (default: 0.80)",
    )
    p_prepare.add_argument("--no-dedup", action="store_true", help="Disable adjacent frame dedup")
    p_prepare.add_argument("--video-only", action="store_true", help="Only download video, skip frame extraction")
    p_prepare.add_argument(
        "--frames-only",
        action="store_true",
        help="Extract frames and remove downloaded video after processing",
    )
    p_prepare.add_argument(
        "--json-summary",
        action="store_true",
        help="Print concise summary JSON instead of full manifest payload",
    )

    p_analyze = sub.add_parser("analyze-frames", help="Analyze existing frame directory")
    p_analyze.add_argument("images_dir", help="Directory containing extracted frames")
    p_analyze.add_argument(
        "--json-summary",
        action="store_true",
        help="Print concise summary JSON",
    )

    p_transcribe = sub.add_parser("transcribe", help="Transcribe audio from a prepared video with ASR")
    p_transcribe.add_argument(
        "input_path",
        help="Path to video file, or prepare task directory containing video.mp4",
    )
    p_transcribe.add_argument(
        "-o",
        "--output",
        default=None,
        help="Output directory for transcript artifacts (default: alongside input video)",
    )
    p_transcribe.add_argument("--asr-model", default="small", help="ASR model size (default: small)")
    p_transcribe.add_argument("--language", default="zh", help="ASR language code (default: zh)")
    p_transcribe.add_argument("--device", default="auto", help="ASR device (auto/cpu/cuda, default: auto)")
    p_transcribe.add_argument(
        "--compute-type",
        default="int8",
        help="ASR compute type (default: int8)",
    )
    p_transcribe.add_argument(
        "--json-summary",
        action="store_true",
        help="Print concise summary JSON",
    )

    p_summarize = sub.add_parser("summarize", help="Generate Chinese video summary from URL")
    p_summarize.add_argument("url", help="Video URL")
    p_summarize.add_argument("-o", "--output", default="./tmp", help="Output root directory")
    p_summarize.add_argument(
        "--mode",
        choices=["fast", "fusion"],
        default="fast",
        help="Summarization mode (default: fast)",
    )
    p_summarize.add_argument(
        "--language",
        default="auto",
        help="ASR language code or auto (default: auto)",
    )
    p_summarize.add_argument("--asr-model", default="small", help="ASR model size (default: small)")
    p_summarize.add_argument("--device", default="auto", help="ASR device (default: auto)")
    p_summarize.add_argument("--compute-type", default="int8", help="ASR compute type (default: int8)")
    p_summarize.add_argument("--llm-model", default="glm-4.6v", help="LLM model name (default: glm-4.6v)")
    p_summarize.add_argument("--api-base", default=None, help="OpenAI compatible API base URL")
    p_summarize.add_argument("--api-key", default=None, help="OpenAI compatible API key")
    p_summarize.add_argument("--fps", type=float, default=0.5, help="Frame fps for fusion mode")
    p_summarize.add_argument(
        "--similarity",
        type=float,
        default=0.85,
        help="Frame dedup similarity in [0,1] for fusion mode",
    )
    p_summarize.add_argument(
        "--timeline-window-sec",
        type=float,
        default=90.0,
        help="Timeline merge window in seconds (default: 90)",
    )
    p_summarize.add_argument("--json-summary", action="store_true", help="Print concise summary JSON")

    return parser


def _setup_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(level=level, format="[%(levelname)s] %(message)s")


def _summary_payload(command: str, result: dict) -> dict:
    if command == "prepare":
        frame_counts = result.get("frame_counts") or {}
        dedup = result.get("dedup") or {}
        return {
            "mode": result.get("mode"),
            "task_root": result.get("task_root"),
            "manifest": result.get("manifest"),
            "frame_counts": {
                "before_dedup": frame_counts.get("before_dedup"),
                "after_dedup": frame_counts.get("after_dedup"),
                "removed": frame_counts.get("removed", dedup.get("removed")),
            },
            "timings_sec": result.get("timings_sec"),
        }

    if command == "transcribe":
        return {
            "input_video": result.get("input_video"),
            "transcript_file": result.get("transcript_file"),
            "engine": result.get("engine"),
            "model": result.get("model"),
            "language": result.get("language"),
            "segment_count": result.get("segment_count"),
            "text_chars": result.get("text_chars"),
            "timings_sec": result.get("timings_sec"),
        }

    if command == "summarize":
        return {
            "mode": result.get("mode"),
            "task_root": result.get("task_root"),
            "summary_zh_md": result.get("summary_zh_md"),
            "timeline_json": result.get("timeline_json"),
            "summary_source": result.get("summary_source"),
            "fallback": result.get("fallback"),
            "manifest": result.get("manifest"),
            "timings_sec": result.get("timings_sec"),
        }

    return {
        "images_dir": result.get("images_dir"),
        "count": result.get("count"),
        "total_bytes": result.get("total_bytes"),
        "first": result.get("first"),
        "last": result.get("last"),
        "index_file": result.get("index_file"),
    }


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    _setup_logging(args.verbose)

    try:
        if args.command == "prepare":
            result = prepare_video(
                url=args.url,
                output=args.output,
                fps=args.fps,
                similarity=args.similarity,
                no_dedup=args.no_dedup,
                video_only=args.video_only,
                frames_only=args.frames_only,
            )
        elif args.command == "analyze-frames":
            result = analyze_frames_dir(Path(args.images_dir).expanduser().resolve())
        elif args.command == "transcribe":
            result = transcribe_video(
                input_path=args.input_path,
                output=args.output,
                asr_model=args.asr_model,
                language=args.language,
                device=args.device,
                compute_type=args.compute_type,
            )
        elif args.command == "summarize":
            result = summarize_video(
                url=args.url,
                output=args.output,
                mode=args.mode,
                language=args.language,
                asr_model=args.asr_model,
                device=args.device,
                compute_type=args.compute_type,
                llm_model=args.llm_model,
                api_base=args.api_base,
                api_key=args.api_key,
                fps=args.fps,
                similarity=args.similarity,
                timeline_window_sec=args.timeline_window_sec,
            )
        else:
            parser.error(f"Unsupported command: {args.command}")
            return ExitCode.INVALID_ARGUMENT

        payload = _summary_payload(args.command, result) if getattr(args, "json_summary", False) else result
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return ExitCode.OK
    except AnalyzerError as exc:
        print(str(exc), file=sys.stderr)
        return exc.exit_code
    except KeyboardInterrupt:
        print("Interrupted by user", file=sys.stderr)
        return ExitCode.UNKNOWN
    except Exception as exc:  # pragma: no cover - defensive fallback
        print(f"Unexpected error: {exc}", file=sys.stderr)
        return ExitCode.UNKNOWN


if __name__ == "__main__":
    raise SystemExit(main())
