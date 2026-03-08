from __future__ import annotations

import hashlib
import json
import platform
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any


DEFAULT_DEVICE = "auto"
DEFAULT_COMPUTE_TYPE = "int8"


def _safe_slug_from_url(url: str) -> str:
    clean = (url or "").strip()
    if not clean:
        raise ValueError("url cannot be empty")
    for prefix in ("BV", "av"):
        idx = clean.find(prefix)
        if idx >= 0:
            token = clean[idx : idx + 14]
            token = "".join(ch for ch in token if ch.isalnum())
            if len(token) >= 6:
                return f"bili-{token}"
    digest = hashlib.sha1(clean.encode("utf-8")).hexdigest()[:12]
    return f"bili-{digest}"


def _resolve_video_input(input_path: Path) -> Path:
    if input_path.is_file():
        return input_path
    if input_path.is_dir():
        candidate = input_path / "video.mp4"
        if candidate.exists():
            return candidate
    raise ValueError(f"video input does not exist: {input_path}")


def _extract_audio_for_asr(video_path: Path, audio_path: Path) -> float:
    if shutil.which("ffmpeg") is None:
        raise RuntimeError("ffmpeg is required")
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
    started = time.perf_counter()
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        details = proc.stderr.strip() or proc.stdout.strip() or "ffmpeg failed"
        raise RuntimeError(details)
    return time.perf_counter() - started


def _transcribe_audio_faster_whisper(
    audio_path: Path,
    *,
    model_size: str,
    language: str | None,
    device: str,
    compute_type: str,
) -> dict[str, Any]:
    try:
        from faster_whisper import WhisperModel
    except Exception as exc:
        raise RuntimeError("Missing ASR dependency: faster-whisper") from exc

    model = WhisperModel(model_size, device=device, compute_type=compute_type)
    segments_iter, info = model.transcribe(str(audio_path), language=language)
    segments: list[dict[str, Any]] = []
    for segment in segments_iter:
        segments.append(
            {
                "start": round(float(segment.start), 3),
                "end": round(float(segment.end), 3),
                "text": (segment.text or "").strip(),
            }
        )
    full_text = "\n".join(item["text"] for item in segments if item["text"])
    return {
        "engine": "faster-whisper",
        "model": model_size,
        "language": getattr(info, "language", language or "auto"),
        "segments": segments,
        "segment_count": len(segments),
        "text": full_text,
    }


def _to_mlx_model_id(model_size: str) -> str:
    normalized = (model_size or "small").strip()
    if normalized.startswith("mlx-community/"):
        return normalized
    return f"mlx-community/whisper-{normalized}"


def _transcribe_audio_mlx_whisper(
    audio_path: Path,
    *,
    model_size: str,
    language: str | None,
) -> dict[str, Any]:
    try:
        import mlx_whisper
    except Exception as exc:
        raise RuntimeError("Missing ASR dependency: mlx-whisper") from exc

    model_id = _to_mlx_model_id(model_size)
    kwargs: dict[str, Any] = {
        "path_or_hf_repo": model_id,
    }
    if language:
        kwargs["language"] = language

    result: dict[str, Any] = mlx_whisper.transcribe(str(audio_path), **kwargs)

    raw_segments = list(result.get("segments") or [])
    segments: list[dict[str, Any]] = []
    for item in raw_segments:
        start = float(item.get("start") or 0.0)
        end = float(item.get("end") or start)
        text = str(item.get("text") or "").strip()
        if not text:
            continue
        segments.append({"start": round(start, 3), "end": round(end, 3), "text": text})

    full_text = str(result.get("text") or "").strip()
    if not full_text and segments:
        full_text = "\n".join(item["text"] for item in segments)

    return {
        "engine": "mlx-whisper",
        "model": model_id,
        "language": str(result.get("language") or language or "auto"),
        "segments": segments,
        "segment_count": len(segments),
        "text": full_text,
    }


def _is_apple_silicon_macos() -> bool:
    return platform.system().lower() == "darwin" and platform.machine().lower() in {"arm64", "aarch64"}


def _normalize_profile(platform_profile: str) -> str:
    profile = (platform_profile or "auto").strip().lower()
    if profile in {"auto", "apple_silicon", "nvidia", "intel", "amd", "cpu"}:
        return profile
    return "auto"


def _resolve_faster_params(platform_profile: str) -> tuple[str, str]:
    profile = _normalize_profile(platform_profile)
    if profile == "nvidia":
        return "cuda", "float16"
    if profile in {"cpu", "intel", "amd"}:
        return "cpu", "int8"
    return DEFAULT_DEVICE, DEFAULT_COMPUTE_TYPE


def _should_prefer_mlx(platform_profile: str, explicit_device: bool, explicit_compute_type: bool) -> bool:
    if explicit_device or explicit_compute_type:
        return False
    profile = _normalize_profile(platform_profile)
    return profile == "apple_silicon" or (profile == "auto" and _is_apple_silicon_macos())


def transcribe_video(
    *,
    input_path: str,
    output: str | None = None,
    asr_model: str = "small",
    language: str | None = "zh",
    device: str | None = None,
    compute_type: str | None = None,
    platform_profile: str = "auto",
) -> dict[str, Any]:
    source = Path(input_path).expanduser().resolve()
    video_path = _resolve_video_input(source)
    out_root = Path(output).expanduser().resolve() if output else video_path.parent
    out_root.mkdir(parents=True, exist_ok=True)

    audio_path = out_root / "audio_16k.wav"
    transcript_path = out_root / "transcript.json"

    explicit_device = bool(device and device.strip())
    explicit_compute_type = bool(compute_type and compute_type.strip())
    fallback_device, fallback_compute_type = _resolve_faster_params(platform_profile)
    resolved_device = (device or fallback_device or DEFAULT_DEVICE).strip()
    resolved_compute_type = (compute_type or fallback_compute_type or DEFAULT_COMPUTE_TYPE).strip()

    started = time.perf_counter()
    audio_extract_sec = _extract_audio_for_asr(video_path, audio_path)
    transcribe_started = time.perf_counter()

    fallback: dict[str, Any] | None = None
    runtime_profile = _normalize_profile(platform_profile)

    if _should_prefer_mlx(platform_profile, explicit_device, explicit_compute_type):
        try:
            transcription = _transcribe_audio_mlx_whisper(
                audio_path,
                model_size=asr_model,
                language=language,
            )
            runtime_profile = "apple_silicon_mlx"
        except Exception as exc:
            fallback = {
                "from": "mlx-whisper",
                "to": "faster-whisper",
                "reason": str(exc),
            }
            transcription = _transcribe_audio_faster_whisper(
                audio_path,
                model_size=asr_model,
                language=language,
                device="cpu",
                compute_type="int8",
            )
            runtime_profile = "apple_silicon_fallback_cpu"
            resolved_device = "cpu"
            resolved_compute_type = "int8"
    else:
        transcription = _transcribe_audio_faster_whisper(
            audio_path,
            model_size=asr_model,
            language=language,
            device=resolved_device,
            compute_type=resolved_compute_type,
        )

    transcribe_sec = time.perf_counter() - transcribe_started
    total_sec = time.perf_counter() - started

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
        "runtime_profile": runtime_profile,
        "platform_profile": _normalize_profile(platform_profile),
        "device": resolved_device,
        "compute_type": resolved_compute_type,
        "fallback": fallback,
        "timings_sec": {
            "audio_extract_sec": round(audio_extract_sec, 3),
            "transcribe_sec": round(transcribe_sec, 3),
            "total_sec": round(total_sec, 3),
        },
    }
    transcript_payload = {
        "meta": result,
        "text": transcription["text"],
        "segments": transcription["segments"],
    }
    transcript_path.write_text(json.dumps(transcript_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return result
