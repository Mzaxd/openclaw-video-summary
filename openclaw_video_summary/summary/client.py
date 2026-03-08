from __future__ import annotations

import json
from urllib import error, request
from typing import Any


class LLMClientError(Exception):
    pass


def _normalize_base(api_base: str) -> str:
    base = (api_base or "").strip().rstrip("/")
    if not base:
        raise LLMClientError("api_base is empty")
    if base.endswith("/chat/completions"):
        return base
    if base.endswith("/v1"):
        return f"{base}/chat/completions"
    return f"{base}/v1/chat/completions"


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
            "temperature": 0.2,
        }
    ).encode("utf-8")
    req = request.Request(
        _normalize_base(api_base),
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )
    try:
        with request.urlopen(req, timeout=timeout_sec) as response:
            raw = response.read().decode("utf-8")
    except error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise LLMClientError(f"LLM request failed: HTTP {exc.code} {body}") from exc
    except error.URLError as exc:
        raise LLMClientError(f"LLM request failed: {exc.reason}") from exc
    except Exception as exc:
        raise LLMClientError(f"LLM request failed: {exc}") from exc

    try:
        body = json.loads(raw)
        choices = body.get("choices") or []
        first = choices[0] if choices else {}
        message = first.get("message") or {}
        content = message.get("content")
        if isinstance(content, str) and content.strip():
            return content.strip()
        if isinstance(content, list):
            text_chunks = []
            for item in content:
                if isinstance(item, dict) and item.get("type") == "text":
                    text = (item.get("text") or "").strip()
                    if text:
                        text_chunks.append(text)
            merged = "\n".join(text_chunks).strip()
            if merged:
                return merged
    except Exception as exc:
        raise LLMClientError(f"Invalid LLM response payload: {exc}") from exc

    raise LLMClientError("LLM response does not contain text content")
