from __future__ import annotations

import hashlib
import json
import logging
import shutil
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    from PIL import Image
except Exception:  # pragma: no cover - validated in runtime checks
    Image = None


LOGGER = logging.getLogger("bili_analyzer")


class ExitCode:
    OK = 0
    UNKNOWN = 1
    INVALID_ARGUMENT = 2
    DEPENDENCY_MISSING = 10
    DOWNLOAD_FAILED = 20
    EXTRACT_FAILED = 30
    DEDUP_FAILED = 40
    IO_ERROR = 50
    TRANSCRIBE_FAILED = 60
    SUMMARIZE_FAILED = 70


@dataclass
class AnalyzerError(Exception):
    message: str
    exit_code: int
    hint: str | None = None
    details: str | None = None

    def __str__(self) -> str:
        lines = [self.message]
        if self.hint:
            lines.append(f"Hint: {self.hint}")
        if self.details:
            lines.append(f"Details: {self.details}")
        return "\n".join(lines)


def _ensure_binary(name: str) -> None:
    if shutil.which(name):
        return
    raise AnalyzerError(
        message=f"Missing required dependency: {name}",
        exit_code=ExitCode.DEPENDENCY_MISSING,
        hint=f"Install `{name}` and make sure it is available in PATH.",
    )


def _ensure_pillow() -> None:
    if Image is not None:
        return
    raise AnalyzerError(
        message="Missing required Python dependency: Pillow",
        exit_code=ExitCode.DEPENDENCY_MISSING,
        hint="Run `pip install Pillow` or install with `pip install -e tools/bili-analyzer`.",
    )


def _run_cmd(cmd: list[str], failure_code: int, failure_message: str) -> float:
    LOGGER.info("Running: %s", " ".join(cmd))
    start = time.perf_counter()
    proc = subprocess.run(cmd, capture_output=True, text=True)
    elapsed = time.perf_counter() - start
    if proc.returncode == 0:
        return elapsed
    details = proc.stderr.strip() or proc.stdout.strip() or "No stderr output"
    raise AnalyzerError(
        message=failure_message,
        exit_code=failure_code,
        details=details,
    )


def _safe_slug_from_url(url: str) -> str:
    clean = url.strip()
    if not clean:
        raise AnalyzerError(
            message="Invalid input: url cannot be empty",
            exit_code=ExitCode.INVALID_ARGUMENT,
        )

    for prefix in ("BV", "av"):
        idx = clean.find(prefix)
        if idx >= 0:
            token = clean[idx : idx + 14]
            token = "".join(ch for ch in token if ch.isalnum())
            if len(token) >= 6:
                return f"bili-{token}"

    digest = hashlib.sha1(clean.encode("utf-8")).hexdigest()[:12]
    return f"bili-{digest}"


def _prepare_dirs(root: Path) -> tuple[Path, Path]:
    try:
        root.mkdir(parents=True, exist_ok=True)
        images_dir = root / "images"
        images_dir.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise AnalyzerError(
            message=f"Failed to create output directory: {root}",
            exit_code=ExitCode.IO_ERROR,
            details=str(exc),
        ) from exc
    return root, images_dir


def _download_video(url: str, video_path: Path) -> float:
    _ensure_binary("yt-dlp")
    cmd = [
        "yt-dlp",
        "--no-part",
        "--force-overwrites",
        "--merge-output-format",
        "mp4",
        "-o",
        str(video_path),
        url,
    ]
    return _run_cmd(cmd, ExitCode.DOWNLOAD_FAILED, "Failed to download video via yt-dlp")


def _extract_frames(video_path: Path, images_dir: Path, fps: float) -> float:
    _ensure_binary("ffmpeg")
    out_pattern = images_dir / "frame_%06d.jpg"
    cmd = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-i",
        str(video_path),
        "-vf",
        f"fps={fps}",
        "-q:v",
        "2",
        str(out_pattern),
    ]
    return _run_cmd(cmd, ExitCode.EXTRACT_FAILED, "Failed to extract frames via ffmpeg")


def _dhash_int(image_path: Path, hash_size: int = 8) -> int:
    _ensure_pillow()
    with Image.open(image_path) as img:
        gray = img.convert("L").resize((hash_size + 1, hash_size), Image.Resampling.LANCZOS)
        pixels = list(gray.getdata())

    result = 0
    width = hash_size + 1
    for row in range(hash_size):
        base = row * width
        for col in range(hash_size):
            left = pixels[base + col]
            right = pixels[base + col + 1]
            result = (result << 1) | (1 if left > right else 0)
    return result


def _hamming(a: int, b: int) -> int:
    return (a ^ b).bit_count()


def dedup_adjacent_frames(images_dir: Path, similarity: float) -> dict[str, Any]:
    if not (0 <= similarity <= 1):
        raise AnalyzerError(
            message=f"Invalid similarity value: {similarity}",
            exit_code=ExitCode.INVALID_ARGUMENT,
            hint="Use a value between 0 and 1.",
        )

    _ensure_pillow()

    try:
        frames = sorted([p for p in images_dir.iterdir() if p.suffix.lower() in {".jpg", ".jpeg", ".png"}])
        if not frames:
            return {"total": 0, "kept": 0, "removed": 0, "similarity": similarity}

        max_bits = 64
        max_distance = int(round((1.0 - similarity) * max_bits))

        kept = [frames[0]]
        kept_hash = _dhash_int(frames[0])
        removed: list[Path] = []

        for frame in frames[1:]:
            h = _dhash_int(frame)
            dist = _hamming(kept_hash, h)
            if dist <= max_distance:
                removed.append(frame)
                frame.unlink(missing_ok=True)
            else:
                kept.append(frame)
                kept_hash = h
    except AnalyzerError:
        raise
    except Exception as exc:
        raise AnalyzerError(
            message="Failed during adjacent frame dedup",
            exit_code=ExitCode.DEDUP_FAILED,
            details=str(exc),
        ) from exc

    return {
        "total": len(frames),
        "kept": len(kept),
        "removed": len(removed),
        "similarity": similarity,
        "max_hamming_distance": max_distance,
    }


def analyze_frames_dir(images_dir: Path) -> dict[str, Any]:
    if not images_dir.exists() or not images_dir.is_dir():
        raise AnalyzerError(
            message=f"images_dir does not exist or is not a directory: {images_dir}",
            exit_code=ExitCode.INVALID_ARGUMENT,
        )

    files = sorted(
        [
            p
            for p in images_dir.iterdir()
            if p.is_file() and p.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
        ]
    )

    stats = {
        "images_dir": str(images_dir),
        "count": len(files),
        "total_bytes": sum(p.stat().st_size for p in files),
        "first": files[0].name if files else None,
        "last": files[-1].name if files else None,
        "preview": [p.name for p in files[:20]],
    }

    index_path = images_dir / "frames_index.json"
    index_obj = {
        "stats": stats,
        "frames": [{"name": p.name, "size": p.stat().st_size} for p in files],
    }
    try:
        index_path.write_text(json.dumps(index_obj, ensure_ascii=False, indent=2), encoding="utf-8")
    except OSError as exc:
        raise AnalyzerError(
            message=f"Failed to write frame index file: {index_path}",
            exit_code=ExitCode.IO_ERROR,
            details=str(exc),
        ) from exc
    stats["index_file"] = str(index_path)
    return stats


def _resolve_video_input(input_path: Path) -> Path:
    if input_path.is_file():
        return input_path

    if input_path.is_dir():
        candidate = input_path / "video.mp4"
        if candidate.exists():
            return candidate

    raise AnalyzerError(
        message=f"video input does not exist: {input_path}",
        exit_code=ExitCode.INVALID_ARGUMENT,
        hint="Pass a video file path, or a prepare task directory containing video.mp4",
    )


def _extract_audio_for_asr(video_path: Path, audio_path: Path) -> float:
    _ensure_binary("ffmpeg")
    cmd = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-i",
        str(video_path),
        "-vn",
        "-ac",
        "1",
        "-ar",
        "16000",
        str(audio_path),
    ]
    return _run_cmd(cmd, ExitCode.EXTRACT_FAILED, "Failed to extract audio via ffmpeg")


def _transcribe_audio_faster_whisper(
    audio_path: Path,
    *,
    model_size: str,
    language: str,
    device: str,
    compute_type: str,
) -> dict[str, Any]:
    try:
        from faster_whisper import WhisperModel
    except Exception as exc:
        raise AnalyzerError(
            message="Missing ASR dependency: faster-whisper",
            exit_code=ExitCode.DEPENDENCY_MISSING,
            hint="Install with `python -m pip install 'faster-whisper>=1.0.0'`",
        ) from exc

    try:
        model = WhisperModel(model_size, device=device, compute_type=compute_type)
        segments_iter, info = model.transcribe(str(audio_path), language=language)
        segments = []
        for s in segments_iter:
            segments.append(
                {
                    "start": round(float(s.start), 3),
                    "end": round(float(s.end), 3),
                    "text": (s.text or "").strip(),
                }
            )
    except AnalyzerError:
        raise
    except Exception as exc:
        raise AnalyzerError(
            message="Failed during faster-whisper transcription",
            exit_code=ExitCode.TRANSCRIBE_FAILED,
            details=str(exc),
        ) from exc

    full_text = "\n".join(seg["text"] for seg in segments if seg["text"])
    return {
        "engine": "faster-whisper",
        "model": model_size,
        "language": getattr(info, "language", language),
        "segments": segments,
        "segment_count": len(segments),
        "text": full_text,
    }


def transcribe_video(
    *,
    input_path: str,
    output: str | None = None,
    asr_model: str = "small",
    language: str = "zh",
    device: str = "auto",
    compute_type: str = "int8",
) -> dict[str, Any]:
    source = Path(input_path).expanduser().resolve()
    video_path = _resolve_video_input(source)

    out_root = Path(output).expanduser().resolve() if output else video_path.parent
    out_root.mkdir(parents=True, exist_ok=True)

    audio_path = out_root / "audio_16k.wav"
    transcript_path = out_root / "transcript.json"

    timings: dict[str, float] = {}
    total_start = time.perf_counter()

    timings["audio_extract_sec"] = round(_extract_audio_for_asr(video_path, audio_path), 3)

    transcribe_start = time.perf_counter()
    transcription = _transcribe_audio_faster_whisper(
        audio_path,
        model_size=asr_model,
        language=language,
        device=device,
        compute_type=compute_type,
    )
    timings["transcribe_sec"] = round(time.perf_counter() - transcribe_start, 3)
    timings["total_sec"] = round(time.perf_counter() - total_start, 3)

    result = {
        "input_video": str(video_path),
        "output_dir": str(out_root),
        "audio_file": str(audio_path),
        "transcript_file": str(transcript_path),
        "engine": transcription["engine"],
        "model": transcription["model"],
        "language": transcription["language"],
        "segment_count": transcription["segment_count"],
        "text_chars": len(transcription["text"]),
        "timings_sec": timings,
    }

    try:
        transcript_payload = {
            "meta": result,
            "text": transcription["text"],
            "segments": transcription["segments"],
        }
        transcript_path.write_text(json.dumps(transcript_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    except OSError as exc:
        raise AnalyzerError(
            message=f"Failed to write transcript file: {transcript_path}",
            exit_code=ExitCode.IO_ERROR,
            details=str(exc),
        ) from exc

    return result


def prepare_video(
    *,
    url: str,
    output: str,
    fps: float = 1.0,
    similarity: float = 0.80,
    no_dedup: bool = False,
    video_only: bool = False,
    frames_only: bool = False,
) -> dict[str, Any]:
    if fps <= 0:
        raise AnalyzerError(
            message=f"Invalid fps value: {fps}",
            exit_code=ExitCode.INVALID_ARGUMENT,
            hint="fps must be > 0.",
        )
    if not (0 <= similarity <= 1):
        raise AnalyzerError(
            message=f"Invalid similarity value: {similarity}",
            exit_code=ExitCode.INVALID_ARGUMENT,
            hint="similarity must be in [0,1].",
        )
    if video_only and frames_only:
        raise AnalyzerError(
            message="Invalid flag combination: --video-only and --frames-only cannot be used together",
            exit_code=ExitCode.INVALID_ARGUMENT,
        )

    task_dir_name = _safe_slug_from_url(url)
    task_root = Path(output).expanduser().resolve() / task_dir_name
    task_root, images_dir = _prepare_dirs(task_root)

    video_path = task_root / "video.mp4"
    total_start = time.perf_counter()
    timings: dict[str, float] = {}

    timings["download_sec"] = round(_download_video(url, video_path), 3)

    result: dict[str, Any] = {
        "task_root": str(task_root),
        "video": str(video_path),
        "fps": fps,
        "similarity": similarity,
        "dedup_enabled": not no_dedup,
        "timings_sec": timings,
    }

    if video_only:
        result["mode"] = "video_only"
    else:
        timings["extract_sec"] = round(_extract_frames(video_path, images_dir, fps), 3)

        analyze_before_start = time.perf_counter()
        frame_stats = analyze_frames_dir(images_dir)
        timings["analyze_before_dedup_sec"] = round(time.perf_counter() - analyze_before_start, 3)

        result["mode"] = "video_and_frames"
        result["frames"] = frame_stats
        result["frame_counts"] = {
            "before_dedup": frame_stats["count"],
            "after_dedup": frame_stats["count"],
        }

        if not no_dedup:
            dedup_start = time.perf_counter()
            dedup_stats = dedup_adjacent_frames(images_dir, similarity)
            timings["dedup_sec"] = round(time.perf_counter() - dedup_start, 3)

            analyze_after_start = time.perf_counter()
            frame_stats = analyze_frames_dir(images_dir)
            timings["analyze_after_dedup_sec"] = round(time.perf_counter() - analyze_after_start, 3)

            result["dedup"] = dedup_stats
            result["frames"] = frame_stats
            result["frame_counts"] = {
                "before_dedup": dedup_stats["total"],
                "after_dedup": dedup_stats["kept"],
                "removed": dedup_stats["removed"],
            }

        if frames_only:
            try:
                video_path.unlink(missing_ok=True)
            except OSError as exc:
                LOGGER.warning("Unable to remove video for --frames-only: %s", exc)
            result["video"] = None
            result["mode"] = "frames_only"

    timings["total_sec"] = round(time.perf_counter() - total_start, 3)

    manifest_path = task_root / "prepare_manifest.json"
    try:
        manifest_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    except OSError as exc:
        raise AnalyzerError(
            message=f"Failed to write manifest file: {manifest_path}",
            exit_code=ExitCode.IO_ERROR,
            details=str(exc),
        ) from exc
    result["manifest"] = str(manifest_path)
    return result
