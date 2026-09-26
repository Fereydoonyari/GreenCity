"""Shared OpenAI Chat Completions helper with 429 backoff."""

from __future__ import annotations

import json
import logging
import time
import urllib.error
import urllib.request
from typing import Any

_log = logging.getLogger(__name__)


def chat_completion(
    *,
    api_key: str,
    model: str,
    messages: list[dict[str, str]],
    temperature: float = 0.3,
    max_tokens: int = 220,
    timeout_s: float = 45.0,
    max_retries: int = 4,
) -> str | None:
    """Call OpenAI chat completions; retry on 429; return text or ``None``."""

    key = api_key.strip()
    if not key:
        return None

    body: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    data = json.dumps(body).encode("utf-8")
    last_error: Exception | None = None

    for attempt in range(max(1, max_retries)):
        request = urllib.request.Request(
            "https://api.openai.com/v1/chat/completions",
            data=data,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {key}",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=timeout_s) as response:  # noqa: S310
                payload = json.loads(response.read().decode("utf-8"))
            text = payload["choices"][0]["message"]["content"]
            if isinstance(text, str) and text.strip():
                return text.strip()
            return None
        except urllib.error.HTTPError as exc:
            try:
                err_body = exc.read().decode("utf-8", errors="replace")
            except Exception:  # noqa: BLE001
                err_body = ""
            err_type = err_code = ""
            try:
                err_obj = (json.loads(err_body).get("error") or {}) if err_body else {}
                err_type = str(err_obj.get("type") or "")
                err_code = str(err_obj.get("code") or "")
            except json.JSONDecodeError:
                pass
            last_error = exc
            if exc.code == 429 and attempt + 1 < max_retries:
                retry_after = exc.headers.get("Retry-After") if exc.headers else None
                try:
                    delay = float(retry_after) if retry_after else 1.5 * (2**attempt)
                except ValueError:
                    delay = 1.5 * (2**attempt)
                delay = min(max(delay, 0.5), 20.0)
                _log.warning(
                    "OpenAI 429 (type=%s code=%s); retry %s/%s in %.1fs",
                    err_type or "?",
                    err_code or "?",
                    attempt + 1,
                    max_retries,
                    delay,
                )
                time.sleep(delay)
                continue
            _log.warning(
                "OpenAI HTTP %s (type=%s code=%s); giving up (%s)",
                exc.code,
                err_type or "?",
                err_code or "?",
                (err_body[:200] if err_body else exc),
            )
            return None
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, KeyError, IndexError, TypeError) as exc:
            last_error = exc
            _log.warning("OpenAI request failed; giving up (%s)", exc)
            return None

    if last_error is not None:
        _log.warning("OpenAI unavailable after retries (%s)", last_error)
    return None
