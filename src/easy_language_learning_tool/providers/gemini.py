from __future__ import annotations

from typing import Any
from urllib.parse import quote

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


class GeminiProvider(ProviderAdapter):
    provider_name = "Google Gemini"
    base_url = "https://generativelanguage.googleapis.com/v1beta"

    def __init__(self, api_key: str, client: JsonHttpClient | None = None) -> None:
        super().__init__(client)
        self.api_key = api_key

    async def list_models(self) -> list[ModelInfo]:
        response = await self.client.get(f"{self.base_url}/models?key={quote(self.api_key)}")
        require_success(response)
        result = []
        for item in response.data.get("models", []):
            methods = item.get("supportedGenerationMethods", [])
            if "generateContent" in methods:
                identifier = str(item["name"]).removeprefix("models/")
                result.append(
                    ModelInfo(id=identifier, display_name=str(item.get("displayName", identifier)))
                )
        return result

    async def generate(self, model: str, prompt: str, schema: dict[str, Any]) -> ProviderResponse:
        url = f"{self.base_url}/models/{quote(model, safe='')}:generateContent?key={quote(self.api_key)}"
        response = await self.client.post(
            url,
            payload={
                "contents": [{"role": "user", "parts": [{"text": prompt}]}],
                "generationConfig": {
                    "temperature": 0.4,
                    "responseMimeType": "application/json",
                    "responseJsonSchema": schema,
                },
            },
        )
        require_success(response)
        try:
            parts = response.data["candidates"][0]["content"]["parts"]
            text = "".join(str(part.get("text", "")) for part in parts)
        except (KeyError, IndexError, TypeError) as error:
            raise ProviderError("The Gemini response did not contain text.") from error
        parsed = parse_json_text(text)
        rows = parsed.get("rows")
        if not isinstance(rows, list):
            raise ProviderError("The Gemini JSON did not contain a rows array.")
        usage = response.data.get("usageMetadata", {})
        return ProviderResponse(
            rows=rows,
            usage=TokenUsage(
                input_tokens=int(usage.get("promptTokenCount", 0)),
                output_tokens=int(usage.get("candidatesTokenCount", 0)),
            ),
            raw_model=model,
        )
