from __future__ import annotations

from typing import Any

from .base import (
    JsonHttpClient,
    ModelInfo,
    ProviderAdapter,
    ProviderError,
    ProviderResponse,
    TokenUsage,
    parse_json_text,
    require_success,
)


class OpenAICompatibleProvider(ProviderAdapter):
    provider_name = "OpenAI-compatible"

    def __init__(
        self,
        api_key: str,
        base_url: str,
        client: JsonHttpClient | None = None,
        provider_name: str | None = None,
    ) -> None:
        super().__init__(client)
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        if provider_name:
            self.provider_name = provider_name

    @property
    def headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}

    async def list_models(self) -> list[ModelInfo]:
        response = await self.client.get(f"{self.base_url}/models", headers=self.headers)
        require_success(response)
        values = response.data.get("data", [])
        return sorted(
            [ModelInfo(id=str(item["id"]), display_name=str(item["id"])) for item in values],
            key=lambda item: item.id,
        )

    async def generate(self, model: str, prompt: str, schema: dict[str, Any]) -> ProviderResponse:
        response = await self.client.post(
            f"{self.base_url}/chat/completions",
            headers=self.headers,
            payload={
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "response_format": {"type": "json_object"},
                "temperature": 0.4,
            },
        )
        require_success(response)
        try:
            text = response.data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as error:
            raise ProviderError("The provider response did not contain message content.") from error
        parsed = parse_json_text(str(text))
        usage = response.data.get("usage", {})
        rows = parsed.get("rows")
        if not isinstance(rows, list):
            raise ProviderError("The provider JSON did not contain a rows array.")
        return ProviderResponse(
            rows=rows,
            usage=TokenUsage(
                input_tokens=int(usage.get("prompt_tokens", 0)),
                output_tokens=int(usage.get("completion_tokens", 0)),
            ),
            raw_model=str(response.data.get("model", model)),
        )


class DeepSeekProvider(OpenAICompatibleProvider):
    provider_name = "DeepSeek"

    def __init__(self, api_key: str, client: JsonHttpClient | None = None) -> None:
        super().__init__(api_key, "https://api.deepseek.com", client, self.provider_name)
