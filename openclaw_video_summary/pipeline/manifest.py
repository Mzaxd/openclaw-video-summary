from __future__ import annotations

from pathlib import Path
from typing import Any

from openclaw_video_summary.common.fileio import read_json, write_json


def update_manifest(
    manifest_path: Path,
    *,
    mode: str,
    selected_mode: str,
    fallback: dict[str, Any] | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    manifest = read_json(manifest_path)
    manifest["mode"] = mode
    manifest["selected_mode"] = selected_mode
    manifest["fallback"] = fallback
    if extra:
        manifest.update(extra)
    write_json(manifest_path, manifest)
    return manifest

