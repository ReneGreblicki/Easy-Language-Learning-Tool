from __future__ import annotations

import asyncio
import sys
import types
import unittest
from typing import Any
from unittest.mock import AsyncMock, patch

from easy_language_learning_tool.domain.enums import Provider
from easy_language_learning_tool.providers.base import (
    AuthenticationError,
    HttpResponse,
    HttpxJsonClient,
    ProviderError,
    RateLimitError,
    parse_json_text,
    require_success,
)
from easy_language_learning_tool.providers.factory import create_provider


class FakeClient:
    def __init__(self, get_response: HttpResponse, post_response: HttpResponse) -> None:
        self.get_response = get_response
        self.post_response = post_response
        self.last_post: tuple[str, dict[str, str] | None, dict[str, Any]] | None = None

    async def get(self, url: str, *, headers: dict[str, str] | None = None) -> HttpResponse:
        return self.get_response

    async def post(
        self,
        url: str,
        *,
        headers: dict[str, str] | None = None,
        payload: dict[str, Any],
    ) -> HttpResponse:
        self.last_post = (url, headers, payload)
        return self.post_response


class ProviderContractTests(unittest.TestCase):
    def test_all_approved_provider_factories_exist(self) -> None:
        client = FakeClient(HttpResponse(200, {}, {}), HttpResponse(200, {}, {}))
        for provider in Provider:
            kwargs: dict[str, object] = {"api_key": "test", "client": client}
            if provider is Provider.CUSTOM_COMPATIBLE:
                kwargs["base_url"] = "https://example.invalid/v1"
            adapter = create_provider(provider, **kwargs)
            self.assertEqual(adapter.provider_name, provider.value)

    def test_deepseek_lists_models_and_normalizes_generation(self) -> None:
        client = FakeClient(
            HttpResponse(200, {"data": [{"id": "deepseek-v4-flash"}]}, {}),
            HttpResponse(
                200,
                {
                    "model": "deepseek-v4-flash",
                    "choices": [{"message": {"content": '{"rows":[{"row_number":1}]}'}}],
                    "usage": {"prompt_tokens": 10, "completion_tokens": 5},
                },
                {},
            ),
        )
        adapter = create_provider(Provider.DEEPSEEK, api_key="secret", client=client)
        models = asyncio.run(adapter.list_models())
        response = asyncio.run(adapter.generate(models[0].id, "prompt", {"type": "object"}))
        self.assertEqual(models[0].id, "deepseek-v4-flash")
        self.assertEqual(response.rows, [{"row_number": 1}])
        self.assertEqual(response.usage.output_tokens, 5)
        assert client.last_post is not None
        self.assertEqual(client.last_post[0], "https://api.deepseek.com/chat/completions")

    def test_ollama_requires_no_api_key(self) -> None:
        client = FakeClient(
            HttpResponse(200, {"models": [{"name": "gemma4"}]}, {}),
            HttpResponse(
                200,
                {"model": "gemma4", "message": {"content": '{"rows":[]}'}, "eval_count": 2},
                {},
            ),
        )
        adapter = create_provider(Provider.OLLAMA, client=client)
        self.assertEqual(asyncio.run(adapter.list_models())[0].id, "gemma4")
        response = asyncio.run(adapter.generate("gemma4", "prompt", {"type": "object"}))
        self.assertEqual(response.rows, [])

    def test_openai_contract(self) -> None:
        client = FakeClient(
            HttpResponse(200, {"data": [{"id": "gpt-test"}]}, {}),
            HttpResponse(
                200,
                {
                    "model": "gpt-test",
                    "output_text": '{"rows":[{"row_number":1}]}',
                    "usage": {"input_tokens": 12, "output_tokens": 7},
                },
                {},
            ),
        )
        adapter = create_provider(Provider.OPENAI, api_key="secret", client=client)
        self.assertEqual(asyncio.run(adapter.list_models())[0].id, "gpt-test")
        response = asyncio.run(adapter.generate("gpt-test", "prompt", {"type": "object"}))
        self.assertEqual(response.usage.input_tokens, 12)
        assert client.last_post is not None
        self.assertEqual(client.last_post[0], "https://api.openai.com/v1/responses")

    def test_anthropic_contract(self) -> None:
        client = FakeClient(
            HttpResponse(200, {"data": [{"id": "claude-test", "display_name": "Claude"}]}, {}),
            HttpResponse(
                200,
                {
                    "model": "claude-test",
                    "content": [{"type": "text", "text": '{"rows":[]}'}],
                    "usage": {"input_tokens": 3, "output_tokens": 2},
                },
                {},
            ),
        )
        adapter = create_provider(Provider.ANTHROPIC, api_key="secret", client=client)
        self.assertEqual(asyncio.run(adapter.list_models())[0].display_name, "Claude")
        response = asyncio.run(adapter.generate("claude-test", "prompt", {"type": "object"}))
        self.assertEqual(response.usage.output_tokens, 2)

    def test_gemini_contract(self) -> None:
        client = FakeClient(
            HttpResponse(
                200,
                {
                    "models": [
                        {
                            "name": "models/gemini-test",
                            "displayName": "Gemini Test",
                            "supportedGenerationMethods": ["generateContent"],
                        },
                        {"name": "models/embed", "supportedGenerationMethods": ["embedContent"]},
                    ]
                },
                {},
            ),
            HttpResponse(
                200,
                {
                    "candidates": [{"content": {"parts": [{"text": '{"rows":[]}'}]}}],
                    "usageMetadata": {"promptTokenCount": 4, "candidatesTokenCount": 2},
                },
                {},
            ),
        )
        adapter = create_provider(Provider.GEMINI, api_key="secret", client=client)
        self.assertEqual(asyncio.run(adapter.list_models())[0].id, "gemini-test")
        response = asyncio.run(adapter.generate("gemini-test", "prompt", {"type": "object"}))
        self.assertEqual(response.usage.input_tokens, 4)

    def test_normalized_errors_and_json_fences(self) -> None:
        self.assertEqual(parse_json_text('```json\n{"rows": []}\n```'), {"rows": []})
        with self.assertRaises(ProviderError):
            parse_json_text("[]")
        with self.assertRaises(AuthenticationError):
            require_success(HttpResponse(401, {"error": {"message": "bad key"}}, {}))
        with self.assertRaises(RateLimitError):
            require_success(HttpResponse(429, {"error": {"message": "slow down"}}, {}))
        with self.assertRaises(ProviderError):
            require_success(HttpResponse(500, {"error": "unavailable"}, {}))

    def test_http_client_retries_transient_get_and_post(self) -> None:
        class FakeResponse:
            def __init__(self, status_code: int) -> None:
                self.status_code = status_code
                self.headers: dict[str, str] = {}
                self.text = ""

            def json(self) -> dict[str, object]:
                return {"ok": self.status_code == 200}

        class FakeAsyncClient:
            statuses = [503, 200, 429, 200]

            def __init__(self, **_kwargs: object) -> None:
                pass

            async def __aenter__(self) -> FakeAsyncClient:
                return self

            async def __aexit__(self, *_args: object) -> None:
                pass

            async def get(self, *_args: object, **_kwargs: object) -> FakeResponse:
                return FakeResponse(self.statuses.pop(0))

            async def post(self, *_args: object, **_kwargs: object) -> FakeResponse:
                return FakeResponse(self.statuses.pop(0))

        fake_httpx = types.SimpleNamespace(
            AsyncClient=FakeAsyncClient,
            TransportError=RuntimeError,
        )
        with (
            patch.dict(sys.modules, {"httpx": fake_httpx}),
            patch("easy_language_learning_tool.providers.base.asyncio.sleep", new=AsyncMock()),
        ):
            client = HttpxJsonClient(max_attempts=3)
            self.assertEqual(asyncio.run(client.get("https://example.invalid")).status_code, 200)
            self.assertEqual(
                asyncio.run(client.post("https://example.invalid", payload={})).status_code,
                200,
            )


if __name__ == "__main__":
    unittest.main()
