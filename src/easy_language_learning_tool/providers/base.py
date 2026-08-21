from __future__ import annotations

import asyncio
import json
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Protocol

from pydantic import BaseModel, ConfigDict, Field


class ProviderError(RuntimeError):
    """Normalized provider error safe to display after secret redaction."""


class AuthenticationError(ProviderError):
    pass


class RateLimitError(ProviderError):
    pass


class ModelInfo(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str = Field(min_length=1)
    display_name: str


class TokenUsage(BaseModel):
    model_config = ConfigDict(frozen=True)

    input_tokens: int = 0
    output_tokens: int = 0


class ProviderResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    rows: list[dict[str, Any]]
    usage: TokenUsage = TokenUsage()
    raw_model: str | None = None


@dataclass(frozen=True)
class HttpResponse:
    status_code: int
    data: dict[str, Any]
    headers: dict[str, str]


class JsonHttpClient(Protocol):
    async def get(self, url: str, *, headers: dict[str, str] | None = None) -> HttpResponse: ...

    async def post(
        self,
        url: str,
        *,
        headers: dict[str, str] | None = None,
        payload: dict[str, Any],
    ) -> HttpResponse: ...


class HttpxJsonClient:
    def __init__(self, timeout_seconds: float = 60.0, max_attempts: int = 3) -> None:
        self.timeout_seconds = timeout_seconds
        self.max_attempts = max_attempts

    async def get(self, url: str, *, headers: dict[str, str] | None = None) -> HttpResponse:
        import httpx

        for attempt in range(self.max_attempts):
            try:
                async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                    response = await client.get(url, headers=headers)
                normalized = self._normalize(response)
                if not self._retryable(normalized.status_code) or attempt == self.max_attempts - 1:
                    return normalized
            except httpx.TransportError as error:
                if attempt == self.max_attempts - 1:
                    raise ProviderError("The provider connection failed after retries.") from error
            await asyncio.sleep(2**attempt)
        raise ProviderError("The provider connection failed after retries.")

    async def post(
        self,
        url: str,
        *,
        headers: dict[str, str] | None = None,
        payload: dict[str, Any],
    ) -> HttpResponse:
        import httpx

        for attempt in range(self.max_attempts):
            try:
                async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                    response = await client.post(url, headers=headers, json=payload)
                normalized = self._normalize(response)
                if not self._retryable(normalized.status_code) or attempt == self.max_attempts - 1:
                    return normalized
            except httpx.TransportError as error:
                if attempt == self.max_attempts - 1:
                    raise ProviderError("The provider connection failed after retries.") from error
            await asyncio.sleep(2**attempt)
        raise ProviderError("The provider connection failed after retries.")

    @staticmethod
    def _retryable(status_code: int) -> bool:
        return status_code == 429 or status_code in {500, 502, 503, 504}

    @staticmethod
    def _normalize(response: Any) -> HttpResponse:
        try:
            data = response.json()
        except Exception:
            data = {"error": {"message": response.text[:500]}}
        return HttpResponse(response.status_code, data, dict(response.headers))


def parse_json_text(text: str) -> dict[str, Any]:
    stripped = text.strip()
    if stripped.startswith("```"):
        lines = stripped.splitlines()
        stripped = "\n".join(lines[1:-1])
        if stripped.lstrip().startswith("json"):
            stripped = stripped.lstrip()[4:].lstrip()
    try:
        value = json.loads(stripped)
    except json.JSONDecodeError as error:
        raise ProviderError("The model did not return valid JSON.") from error
    if not isinstance(value, dict):
        raise ProviderError("The model response must be a JSON object.")
    return value


def require_success(response: HttpResponse) -> None:
    if 200 <= response.status_code < 300:
        return
    detail = response.data.get("error", response.data)
    if isinstance(detail, dict):
        message = str(detail.get("message", "Provider request failed."))
    else:
        message = str(detail)
    if response.status_code in {401, 403}:
        raise AuthenticationError(message)
    if response.status_code == 429:
        raise RateLimitError(message)
    raise ProviderError(f"Provider request failed ({response.status_code}): {message}")


class ProviderAdapter(ABC):
    provider_name: str

    def __init__(self, client: JsonHttpClient | None = None) -> None:
        self.client = client or HttpxJsonClient()

    @abstractmethod
    async def list_models(self) -> list[ModelInfo]: ...

    @abstractmethod
    async def generate(
        self, model: str, prompt: str, schema: dict[str, Any]
    ) -> ProviderResponse: ...
