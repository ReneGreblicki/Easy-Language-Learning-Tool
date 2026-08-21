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


class OllamaProvider(ProviderAdapter):
    provider_name = "Ollama"

    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        client: JsonHttpClient | None = None,
    ) -> None:
        super().__init__(client)
        self.base_url = base_url.rstrip("/")

    async def list_models(self) -> list[ModelInfo]:
        response = await self.client.get(f"{self.base_url}/api/tags")
        require_success(response)
        return [
            ModelInfo(id=str(item["name"]), display_name=str(item.get("name", "")))
            for item in response.data.get("models", [])
        ]

    async def generate(self, model: str, prompt: str, schema: dict[str, Any]) -> ProviderResponse:
        response = await self.client.post(
            f"{self.base_url}/api/chat",
            payload={
                "model": model,
                "stream": False,
                "format": schema,
                "options": {"temperature": 0.4},
                "messages": [{"role": "user", "content": prompt}],
            },
        )
        require_success(response)
        try:
            text = str(response.data["message"]["content"])
        except (KeyError, TypeError) as error:
            raise ProviderError("The Ollama response did not contain message content.") from error
        parsed = parse_json_text(text)
        rows = parsed.get("rows")
        if not isinstance(rows, list):
            raise ProviderError("The Ollama JSON did not contain a rows array.")
        return ProviderResponse(
            rows=rows,
            usage=TokenUsage(
                input_tokens=int(response.data.get("prompt_eval_count", 0)),
                output_tokens=int(response.data.get("eval_count", 0)),
            ),
            raw_model=str(response.data.get("model", model)),
        )
