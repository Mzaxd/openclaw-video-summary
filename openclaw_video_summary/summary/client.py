from __future__ import annotations

import base64
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


def _request_text(
    *,
    api_base: str,
    api_key: str,
    payload: dict[str, Any],
    timeout_sec: float = 60.0,
) -> str:
    req = request.Request(
        _normalize_base(api_base),
        data=json.dumps(payload).encode("utf-8"),
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


def request_summary(
    *,
    api_base: str,
    api_key: str,
    model: str,
    messages: list[dict[str, Any]],
    timeout_sec: float = 60.0,
) -> str:
    return _request_text(
        api_base=api_base,
        api_key=api_key,
        payload={
            "model": model,
            "messages": messages,
            "temperature": 0.2,
        },
        timeout_sec=timeout_sec,
    )


def request_video_analysis(
    *,
    api_base: str,
    api_key: str,
    model: str,
    video_path: str,
    prompt: str,
    timeout_sec: float = 180.0,
) -> str:
    with open(video_path, "rb") as handle:
        video_bytes = base64.b64encode(handle.read()).decode("ascii")
    data_uri = f"data:video/mp4;base64,{video_bytes}"
    attempts = [
        {
            "model": model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "input_video", "input_video": {"data": data_uri}},
                    ],
                }
            ],
            "temperature": 0.1,
        },
        {
            "model": model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "video_url", "video_url": {"url": data_uri}},
                    ],
                }
            ],
            "temperature": 0.1,
        },
    ]

    last_error: Exception | None = None
    for payload in attempts:
        try:
            return _request_text(
                api_base=api_base,
                api_key=api_key,
                payload=payload,
                timeout_sec=timeout_sec,
            )
        except LLMClientError as exc:
            last_error = exc

    raise LLMClientError(str(last_error) if last_error else "video analysis request failed")
