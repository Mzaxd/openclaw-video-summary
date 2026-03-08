from __future__ import annotations

import json
from typing import Any


def build_summary_messages(
    transcript_text: str,
    timeline: list[dict[str, Any]],
    visual_context: dict[str, Any] | None,
) -> list[dict[str, str]]:
    system_prompt = (
        "你是一个视频总结助手。"
        "无论输入是什么语言，都必须输出结构化中文总结。"
        "总结应以转写与时间线为主，若提供画面证据，只能作为补充。"
    )
    user_prompt = {
        "transcript_text": transcript_text,
        "timeline": timeline,
        "visual_context": visual_context,
    }
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": json.dumps(user_prompt, ensure_ascii=False, indent=2)},
    ]
