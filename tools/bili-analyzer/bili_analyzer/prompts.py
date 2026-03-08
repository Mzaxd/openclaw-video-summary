from __future__ import annotations

import json
from typing import Any


def _safe_text(text: str, limit: int) -> str:
    text = (text or "").strip()
    if len(text) <= limit:
        return text
    return text[:limit] + "\n...[truncated]..."


def build_summary_messages(
    *,
    transcript_text: str,
    timeline: list[dict[str, Any]],
    visual_context: dict[str, Any] | None = None,
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
        visual_json = json.dumps(visual_context, ensure_ascii=False)

    user_content = (
        "请基于以下视频转写内容生成中文总结。\n"
        "要求：\n"
        "1) 无论原视频是中文或英文，最终输出必须为中文。\n"
        "2) 使用 Markdown。\n"
        "3) 包含以下部分：\n"
        "   - 一句话总结\n"
        "   - 核心要点（3-8条）\n"
        "   - 时间线解读（按阶段）\n"
        "   - 可执行建议（如适用）\n"
        "4) 不要杜撰未出现的信息。\n\n"
        f"视觉上下文（可选）：\n{visual_json}\n\n"
        f"时间线摘要（前20段）：\n{json.dumps(timeline_brief, ensure_ascii=False, indent=2)}\n\n"
        f"转写全文（可能截断）：\n{_safe_text(transcript_text, 12000)}\n"
    )

    return [
        {
            "role": "system",
            "content": "你是严谨的视频内容分析助手，擅长将中英文视频内容统一整理为高质量中文总结。",
        },
        {
            "role": "user",
            "content": user_content,
        },
    ]
