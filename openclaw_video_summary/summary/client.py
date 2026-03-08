from __future__ import annotations

import json
from typing import Any
from urllib import request


def request_summary(
    *,
    api_base: str,
    api_key: str,
    model: str,
    messages: list[dict[str, str]],
    timeout_sec: float = 60.0,
) -> str:
    payload = json.dumps(
        {
            "model": model,
            "messages": messages,
        }
    ).encode("utf-8")
    req = request.Request(
        f"{api_base.rstrip('/')}/chat/completions",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )
    with request.urlopen(req, timeout=timeout_sec) as response:
        body = json.loads(response.read().decode("utf-8"))
    return body["choices"][0]["message"]["content"]
