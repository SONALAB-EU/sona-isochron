"""Minimal client for an OpenAI-compatible /chat/completions endpoint."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

import httpx

from isochron.config import LLMConfig

RETRY_STATUS = {408, 409, 429, 500, 502, 503, 504}


class LLMError(RuntimeError):
    pass


@dataclass
class ChatResult:
    text: str
    model: str
    finish_reason: str | None
    usage: dict[str, Any]
    raw: dict[str, Any]


class ChatClient:
    def __init__(
        self,
        config: LLMConfig | None = None,
        timeout: float = 60.0,
        max_retries: int = 3,
        backoff: float = 2.0,
    ) -> None:
        self.config = config or LLMConfig.from_env()
        self.max_retries = max_retries
        self.backoff = backoff
        self._http = httpx.Client(
            base_url=self.config.base_url,
            timeout=timeout,
            headers={"Authorization": f"Bearer {self.config.api_key}"},
        )

    def chat(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.0,
        max_tokens: int | None = None,
        seed: int | None = None,
        **extra: Any,
    ) -> ChatResult:
        body: dict[str, Any] = {
            "model": self.config.name,
            "messages": messages,
            "temperature": temperature,
            **extra,
        }
        if max_tokens is not None:
            body["max_tokens"] = max_tokens
        if seed is not None:
            body["seed"] = seed

        last_error: Exception | None = None
        for attempt in range(self.max_retries + 1):
            if attempt:
                time.sleep(self.backoff * 2 ** (attempt - 1))
            try:
                resp = self._http.post("/chat/completions", json=body)
            except httpx.TransportError as e:
                last_error = e
                continue
            if resp.status_code in RETRY_STATUS:
                last_error = LLMError(f"HTTP {resp.status_code}: {resp.text[:500]}")
                continue
            if resp.is_error:
                raise LLMError(f"HTTP {resp.status_code}: {resp.text[:500]}")
            data = resp.json()
            try:
                choice = data["choices"][0]
                text = choice["message"]["content"] or ""
            except (KeyError, IndexError, TypeError) as e:
                raise LLMError(f"unexpected response shape: {str(data)[:500]}") from e
            return ChatResult(
                text=text,
                model=data.get("model", self.config.name),
                finish_reason=choice.get("finish_reason"),
                usage=data.get("usage") or {},
                raw=data,
            )
        raise LLMError(f"gave up after {self.max_retries + 1} attempts: {last_error}")

    def close(self) -> None:
        self._http.close()

    def __enter__(self) -> ChatClient:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()
