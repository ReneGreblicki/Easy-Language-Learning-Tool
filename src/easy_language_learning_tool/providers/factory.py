from __future__ import annotations

from easy_language_learning_tool.domain.enums import Provider

from .anthropic import AnthropicProvider
from .base import JsonHttpClient, ProviderAdapter
from .gemini import GeminiProvider
from .ollama import OllamaProvider
from .openai import OpenAIProvider
from .openai_compatible import DeepSeekProvider, OpenAICompatibleProvider


def create_provider(
    provider: Provider,
    *,
    api_key: str = "",
    base_url: str = "",
    client: JsonHttpClient | None = None,
) -> ProviderAdapter:
    if provider is Provider.OPENAI:
        return OpenAIProvider(api_key, client)
    if provider is Provider.ANTHROPIC:
        return AnthropicProvider(api_key, client)
    if provider is Provider.GEMINI:
        return GeminiProvider(api_key, client)
    if provider is Provider.DEEPSEEK:
        return DeepSeekProvider(api_key, client)
    if provider is Provider.OLLAMA:
        return OllamaProvider(base_url or "http://localhost:11434", client)
    if provider is Provider.CUSTOM_COMPATIBLE:
        if not base_url:
            raise ValueError("A base URL is required for a custom compatible provider.")
        return OpenAICompatibleProvider(api_key, base_url, client, provider.value)
    raise ValueError(f"Unsupported provider: {provider}")
