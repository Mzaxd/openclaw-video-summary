from __future__ import annotations

from typing import Any


def _strip_markdown_title(summary_md: str) -> str:
    lines = [line.rstrip() for line in summary_md.strip().splitlines()]
    if lines and lines[0].startswith("#"):
        lines = lines[1:]
    body = "\n".join(lines).strip()
    return body or summary_md.strip()


def _format_timeline_items(timeline_items: list[dict[str, Any]]) -> list[str]:
    lines: list[str] = []
    for item in timeline_items[:5]:
        start = item.get("start", 0)
        end = item.get("end", 0)
        summary = str(item.get("summary") or item.get("text") or "").strip()
        lines.append(f"- {start}s - {end}s: {summary}")
    return lines or ["- 无时间线摘录"]


def _format_evidence_items(evidence_items: list[dict[str, Any]]) -> list[str]:
    lines: list[str] = []
    for item in evidence_items[:5]:
        observation = str(item.get("observation") or item.get("summary") or "").strip()
        confidence = str(item.get("confidence") or "").strip()
        suffix = f" ({confidence})" if confidence else ""
        lines.append(f"- {observation}{suffix}")
    return lines or ["- 无画面证据"]


def format_skill_response(
    *,
    summary_md: str,
    timeline_items: list[dict[str, Any]],
    evidence_items: list[dict[str, Any]],
    task_dir: str,
    artifact_paths: dict[str, str] | None = None,
) -> str:
    lines = [
        "## 中文总结",
        _strip_markdown_title(summary_md),
        "",
        "## 时间线",
        *_format_timeline_items(timeline_items),
        "",
        "## 关键证据",
        *_format_evidence_items(evidence_items),
        "",
        "## 产物路径",
        f"- task_dir: {task_dir}",
    ]

    for name, path in sorted((artifact_paths or {}).items()):
        lines.append(f"- {name}: {path}")

    return "\n".join(lines).strip() + "\n"
