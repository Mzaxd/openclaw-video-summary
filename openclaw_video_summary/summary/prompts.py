from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any


SYSTEM_PROMPT = (
    "你是严谨的视频内容分析助手。"
    "你擅长把长视频整理成信息密度高、结构清楚、观点明确的中文总结。"
    "你不会泛泛而谈，也不会只做表面改写。"
)


def _safe_text(text: str, limit: int) -> str:
    text = (text or "").strip()
    if len(text) <= limit:
        return text
    return text[:limit] + "\n...[truncated]..."


def normalize_summary_markdown(text: str) -> str:
    body = (text or "").strip()
    fenced = re.match(r"^```[a-zA-Z0-9_-]*\n([\s\S]*?)\n```$", body)
    if fenced:
        body = fenced.group(1).strip()
    return body.strip() + ("\n" if body.strip() else "")


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _default_template_path() -> Path:
    return Path(__file__).with_name("summary_prompt.default.md")


def resolve_summary_template_path() -> Path:
    explicit = (os.environ.get("OCVS_SUMMARY_TEMPLATE_FILE") or "").strip()
    if explicit:
        return Path(explicit).expanduser()

    repo_local = _repo_root() / "summary_prompt.local.md"
    if repo_local.exists():
        return repo_local

    user_global = Path.home() / ".config" / "openclaw-video-summary" / "summary_prompt.md"
    if user_global.exists():
        return user_global

    return _default_template_path()


def _load_summary_template() -> str:
    path = resolve_summary_template_path()
    return path.read_text(encoding="utf-8")


def _render_summary_template(
    *,
    transcript_text: str,
    timeline_brief: list[dict[str, Any]],
    visual_json: str,
) -> str:
    template = _load_summary_template()
    replacements = {
        "{{visual_context}}": visual_json,
        "{{timeline_brief}}": json.dumps(timeline_brief, ensure_ascii=False, indent=2),
        "{{transcript_text}}": _safe_text(transcript_text, 18000),
    }
    rendered = template
    for needle, value in replacements.items():
        rendered = rendered.replace(needle, value)
    return rendered.strip()


def build_summary_messages(
    transcript_text: str,
    timeline: list[dict[str, Any]],
    visual_context: dict[str, Any] | None,
) -> list[dict[str, str]]:
    timeline_brief = []
    for item in timeline[:20]:
        timeline_brief.append(
            {
                "start": item.get("start"),
                "end": item.get("end"),
                "summary": item.get("summary"),
            }
        )

    visual_json = "无"
    if visual_context:
        visual_json = json.dumps(visual_context, ensure_ascii=False, indent=2)

    user_content = _render_summary_template(
        transcript_text=transcript_text,
        timeline_brief=timeline_brief,
        visual_json=visual_json,
    )
    return [
        {
            "role": "system",
            "content": SYSTEM_PROMPT,
        },
        {
            "role": "user",
            "content": user_content,
        },
    ]
