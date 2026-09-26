"""Unit tests for OpenAI client 429 retry helper (no live network)."""

from __future__ import annotations

import json
import urllib.error
from io import BytesIO

from greencity.infrastructure.llm.openai_client import chat_completion


class _FakeResponse:
    def __init__(self, body: bytes):
        self._body = body

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return None

    def read(self) -> bytes:
        return self._body


def test_chat_completion_retries_on_429(monkeypatch) -> None:
    calls = {"n": 0}
    sleeps: list[float] = []

    def fake_urlopen(request, timeout=45):  # noqa: ANN001
        calls["n"] += 1
        if calls["n"] < 3:
            raise urllib.error.HTTPError(
                request.full_url,
                429,
                "Too Many Requests",
                hdrs={"Retry-After": "0"},  # type: ignore[arg-type]
                fp=BytesIO(
                    json.dumps(
                        {"error": {"type": "rate_limit_error", "code": "rate_limit_exceeded", "message": "slow down"}}
                    ).encode()
                ),
            )
        return _FakeResponse(
            json.dumps({"choices": [{"message": {"content": "  hello from llm  "}}]}).encode()
        )

    monkeypatch.setattr(
        "greencity.infrastructure.llm.openai_client.urllib.request.urlopen",
        fake_urlopen,
    )
    monkeypatch.setattr("greencity.infrastructure.llm.openai_client.time.sleep", sleeps.append)

    text = chat_completion(
        api_key="sk-test",
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": "hi"}],
        max_retries=4,
    )
    assert text == "hello from llm"
    assert calls["n"] == 3
    assert len(sleeps) == 2


def test_chat_completion_returns_none_without_key() -> None:
    assert chat_completion(api_key="", model="gpt-4o-mini", messages=[]) is None
