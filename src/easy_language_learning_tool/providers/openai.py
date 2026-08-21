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


class OpenAIProvider(ProviderAdapter):
    provider_name = "OpenAI"
    base_url = "https://api.openai.com/v1"

    def __init__(self, api_key: str, client: JsonHttpClient | None = None) -> None:
        super().__init__(client)
        self.api_key = api_key

    @property
    def headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}

    async def list_models(self) -> list[ModelInfo]:
        response = await self.client.get(f"{self.base_url}/models", headers=self.headers)
        require_success(response)
        models = response.data.get("data", [])
        return sorted(
            [ModelInfo(id=str(item["id"]), display_name=str(item["id"])) for item in models],
            key=lambda item: item.id,
        )

    async def generate(self, model: str, prompt: str, schema: dict[str, Any]) -> ProviderResponse:
        response = await self.client.post(
            f"{self.base_url}/responses",
            headers=self.headers,
            payload={
                "model": model,
                "input": prompt,
                "text": {
                    "format": {
                        "type": "json_schema",
                        "name": "language_rows",
                        "strict": True,
                        "schema": schema,
                    }
                },
            },
        )
        require_success(response)
        text = response.data.get("output_text")
        if not text:
            for item in response.data.get("output", []):
                for content in item.get("content", []):
                    if content.get("type") == "output_text":
                        text = content.get("text")
                        break
        if not text:
            raise ProviderError("The OpenAI response did not contain output text.")
        parsed = parse_json_text(str(text))
        rows = parsed.get("rows")
        if not isinstance(rows, list):
            raise ProviderError("The OpenAI JSON did not contain a rows array.")
        usage = response.data.get("usage", {})
        return ProviderResponse(
            rows=rows,
            usage=TokenUsage(
                input_tokens=int(usage.get("input_tokens", 0)),
                output_tokens=int(usage.get("output_tokens", 0)),
            ),
            raw_model=str(response.data.get("model", model)),
        )
