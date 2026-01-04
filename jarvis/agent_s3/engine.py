"""Minimal OpenAI-compatible engine for Agent-S S3 (self-hosted)."""
from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Any
from urllib import request
from urllib.error import HTTPError, URLError


class LMMEngine:
    pass


@dataclass
class EngineError(Exception):
    message: str
    status_code: int | None = None


class LMMEngineOpenAICompat(LMMEngine):
    def __init__(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
        model: str | None = None,
        rate_limit: int = -1,
        temperature: float | None = None,
        **_kwargs: Any,
    ) -> None:
        if not model:
            raise ValueError("model must be provided")
        if not base_url:
            raise ValueError("base_url must be provided for openai_compat")
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.temperature = temperature
        self.request_interval = 0 if rate_limit == -1 else 60.0 / rate_limit
        self._last_request_ts = 0.0

    def _sleep_rate_limit(self) -> None:
        if self.request_interval <= 0:
            return
        now = time.time()
        elapsed = now - self._last_request_ts
        if elapsed < self.request_interval:
            time.sleep(self.request_interval - elapsed)
        self._last_request_ts = time.time()

    def _make_url(self) -> str:
        if self.base_url.endswith("/v1/chat/completions"):
            return self.base_url
        return f"{self.base_url}/v1/chat/completions"

    def generate(
        self,
        messages: list[dict[str, Any]],
        temperature: float = 0.0,
        max_new_tokens: int | None = None,
        **kwargs: Any,
    ) -> str:
        self._sleep_rate_limit()
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature if self.temperature is None else self.temperature,
        }
        if max_new_tokens is not None:
            payload["max_tokens"] = max_new_tokens
        payload.update(kwargs)

        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        req = request.Request(
            self._make_url(),
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        try:
            with request.urlopen(req, timeout=60) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except HTTPError as exc:
            raise EngineError("openai_compat_http_error", exc.code) from exc
        except URLError as exc:
            raise EngineError("openai_compat_connection_error") from exc
        except Exception as exc:
            raise EngineError("openai_compat_unknown_error") from exc

        try:
            return data["choices"][0]["message"]["content"]
        except Exception as exc:
            raise EngineError("openai_compat_bad_response") from exc

    def generate_with_thinking(
        self,
        messages: list[dict[str, Any]],
        temperature: float = 0.0,
        max_new_tokens: int | None = None,
        **kwargs: Any,
    ) -> str:
        # No special thinking mode for openai_compat; fall back to generate.
        return self.generate(messages, temperature=temperature, max_new_tokens=max_new_tokens, **kwargs)


# Alias for compatibility with S3 naming
class LMMEnginevLLM(LMMEngineOpenAICompat):
    pass


class LMMEngineUnsupported(LMMEngine):
    def __init__(self, name: str) -> None:
        self.name = name

    def generate(self, *_args: Any, **_kwargs: Any) -> str:
        raise EngineError(f"engine_not_supported:{self.name}")
