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


class AnthropicProvider(ProviderAdapter):
    provider_name = "Anthropic"
    base_url = "https://api.anthropic.com/v1"

    def __init__(self, api_key: str, client: JsonHttpClient | None = None) -> None:
        super().__init__(client)
        self.api_key = api_key

    @property
    def headers(self) -> dict[str, str]:
        return {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        }

    async def list_models(self) -> list[ModelInfo]:
        response = await self.client.get(f"{self.base_url}/models", headers=self.headers)
        require_success(response)
        return [
            ModelInfo(id=str(item["id"]), display_name=str(item.get("display_name", item["id"])))
            for item in response.data.get("data", [])
        ]

    async def generate(self, model: str, prompt: str, schema: dict[str, Any]) -> ProviderResponse:
        schema_instruction = f"Return only JSON matching this schema: {schema}"
        response = await self.client.post(
            f"{self.base_url}/messages",
            headers=self.headers,
            payload={
                "model": model,
                "max_tokens": 8_192,
                "temperature": 0.4,
                "system": schema_instruction,
                "messages": [{"role": "user", "content": prompt}],
            },
        )
        require_success(response)
        blocks = response.data.get("content", [])
        text = "".join(
            str(block.get("text", "")) for block in blocks if block.get("type") == "text"
        )
        if not text:
            raise ProviderError("The Anthropic response did not contain text.")
        parsed = parse_json_text(text)
        rows = parsed.get("rows")
        if not isinstance(rows, list):
            raise ProviderError("The Anthropic JSON did not contain a rows array.")
        usage = response.data.get("usage", {})
        return ProviderResponse(
            rows=rows,
            usage=TokenUsage(
                input_tokens=int(usage.get("input_tokens", 0)),
                output_tokens=int(usage.get("output_tokens", 0)),
            ),
            raw_model=str(response.data.get("model", model)),
        )
