from __future__ import annotations

import shutil
import subprocess
import tempfile
import time
import os
from pathlib import Path
from typing import Any

from openclaw_video_summary.ingest.source import detect_source_kind

_SUBTITLE_SUFFIXES = (".vtt", ".srt", ".json3")


def _run_yt_dlp(cmd: list[str], timeout_sec: float) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=timeout_sec,
    )


def _looks_like_cookie_error(stderr: str) -> bool:
    text = (stderr or "").lower()
    markers = (
        "cookies-from-browser",
        "browser cookie",
        "keyring",
        "decrypt",
        "cookie",
    )
    return any(marker in text for marker in markers)


def _pick_subtitle_file(root: Path) -> Path | None:
    candidates = sorted(path for path in root.rglob("*") if path.suffix.lower() in _SUBTITLE_SUFFIXES)
    if not candidates:
        return None
    return candidates[0]


def _infer_language_from_filename(path: Path) -> str:
    # Common pattern: "<video-id>.<lang>.vtt"
    parts = path.name.split(".")
    if len(parts) >= 3:
        return parts[-2]
    return "unknown"


def _probe_with_mode(
    *,
    input_value: str,
    timeout_sec: float,
    output_dir: Path,
    browser: str | None,
) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="ocvs-sub-probe-") as td:
        temp_root = Path(td)
        cmd = [
            "yt-dlp",
            "--skip-download",
            "--no-part",
            "--no-warnings",
            "--write-subs",
            "--write-auto-subs",
            "--sub-langs",
            "all",
            "--sub-format",
            "vtt/srt/best",
            "-P",
            str(temp_root),
            "-o",
            "%(id)s.%(ext)s",
            input_value,
        ]
        if browser:
            cmd.extend(["--cookies-from-browser", browser])
        try:
            proc = _run_yt_dlp(cmd, timeout_sec)
        except subprocess.TimeoutExpired:
            return {"status": "timeout", "reason": f"subtitle probe timed out after {timeout_sec}s"}
        except Exception as exc:
            return {"status": "error", "reason": f"subtitle probe execution failed: {exc}"}

        if proc.returncode != 0:
            stderr = proc.stderr.strip() or proc.stdout.strip() or "yt-dlp failed"
            if browser and _looks_like_cookie_error(stderr):
                return {"status": "error", "reason": "cookies_from_browser_failed", "detail": stderr}
            return {"status": "error", "reason": f"yt_dlp_failed: {stderr}"}

        subtitle_path = _pick_subtitle_file(temp_root)
        if subtitle_path is None:
            return {"status": "miss", "reason": "no_subtitle_found"}

        output_dir.mkdir(parents=True, exist_ok=True)
        final_path = output_dir / f"subtitle{subtitle_path.suffix.lower()}"
        shutil.copy2(subtitle_path, final_path)
        return {
            "status": "success",
            "provider": "yt-dlp",
            "language": _infer_language_from_filename(subtitle_path),
            "subtitle_path": str(final_path),
            "reason": "",
        }


def _probe_with_cookies(
    *,
    input_value: str,
    timeout_sec: float,
    output_dir: Path,
) -> dict[str, Any]:
    browser_name = (os.environ.get("OCVS_COOKIES_BROWSER") or "chrome").strip()
    return _probe_with_mode(
        input_value=input_value,
        timeout_sec=timeout_sec,
        output_dir=output_dir,
        browser=browser_name,
    )


def _probe_without_cookies(
    *,
    input_value: str,
    timeout_sec: float,
    output_dir: Path,
) -> dict[str, Any]:
    return _probe_with_mode(
        input_value=input_value,
        timeout_sec=timeout_sec,
        output_dir=output_dir,
        browser=None,
    )


def probe_subtitle(
    input_value: str,
    *,
    timeout_sec: float = 5.0,
    cookies_from_browser: bool = True,
    output_dir: str | Path | None = None,
) -> dict[str, Any]:
    started = time.perf_counter()
    source_kind = detect_source_kind(input_value)
    result: dict[str, Any]

    if source_kind not in {"youtube", "bilibili"}:
        result = {
            "status": "miss",
            "provider": "yt-dlp",
            "language": "",
            "subtitle_path": "",
            "reason": "source_kind_not_supported",
        }
    elif shutil.which("yt-dlp") is None:
        result = {
            "status": "error",
            "provider": "yt-dlp",
            "language": "",
            "subtitle_path": "",
            "reason": "yt-dlp-not-found",
        }
    else:
        final_output_dir = Path(output_dir) if output_dir else Path(tempfile.mkdtemp(prefix="ocvs-sub-out-"))
        if cookies_from_browser:
            result = _probe_with_cookies(
                input_value=input_value,
                timeout_sec=timeout_sec,
                output_dir=final_output_dir,
            )
            if result.get("status") == "error" and result.get("reason") == "cookies_from_browser_failed":
                retried = _probe_without_cookies(
                    input_value=input_value,
                    timeout_sec=timeout_sec,
                    output_dir=final_output_dir,
                )
                if retried.get("status") == "success":
                    result = retried
                else:
                    result = {
                        "status": retried.get("status") or "error",
                        "provider": "yt-dlp",
                        "language": retried.get("language") or "",
                        "subtitle_path": retried.get("subtitle_path") or "",
                        "reason": retried.get("reason") or "subtitle_probe_failed_after_cookie_retry",
                    }
        else:
            result = _probe_without_cookies(
                input_value=input_value,
                timeout_sec=timeout_sec,
                output_dir=final_output_dir,
            )

    result.setdefault("provider", "yt-dlp")
    result.setdefault("language", "")
    result.setdefault("subtitle_path", "")
    result["duration_sec"] = round(time.perf_counter() - started, 3)
    return result
