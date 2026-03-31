"""Model router - intelligent routing between LLM providers with fallback."""

from __future__ import annotations

import time
from typing import Any, AsyncIterator

from aforit.core.config import Config
from aforit.llm.base import BaseLLMProvider, LLMResponse


# Model name to provider mapping
MODEL_PROVIDER_MAP = {
    "gpt-4": "openai",
    "gpt-4-turbo": "openai",
    "gpt-4o": "openai",
    "gpt-4o-mini": "openai",
    "gpt-3.5-turbo": "openai",
    "o1-preview": "openai",
    "o1-mini": "openai",
    "claude-sonnet-4-20250514": "anthropic",
    "claude-3-5-sonnet-20241022": "anthropic",
    "claude-3-opus-20240229": "anthropic",
    "claude-3-haiku-20240307": "anthropic",
    "llama3": "local",
    "codellama": "local",
    "mistral": "local",
    "mixtral": "local",
    "deepseek-coder": "local",
}

# Fallback chains
FALLBACK_CHAINS = {
    "openai": ["anthropic", "local"],
    "anthropic": ["openai", "local"],
    "local": ["openai", "anthropic"],
}


class ModelRouter:
    """Routes requests to the appropriate LLM provider with fallback support."""

    def __init__(self, config: Config):
        self.config = config
        self._providers: dict[str, BaseLLMProvider] = {}
        self._init_providers()
        self._request_count = 0
        self._error_count: dict[str, int] = {}
        self._last_request_time: dict[str, float] = {}

    def _init_providers(self):
        """Initialize available providers based on configuration."""
        if self.config.openai_api_key:
            from aforit.llm.openai_provider import OpenAIProvider
            self._providers["openai"] = OpenAIProvider(self.config.openai_api_key)

        if self.config.anthropic_api_key:
            from aforit.llm.anthropic_provider import AnthropicProvider
            self._providers["anthropic"] = AnthropicProvider(self.config.anthropic_api_key)

        # Always try to add local provider
        from aforit.llm.local_provider import LocalProvider
        self._providers["local"] = LocalProvider()

    def _get_provider_for_model(self, model: str | None = None) -> tuple[str, BaseLLMProvider]:
        """Determine which provider to use for a given model."""
        model = model or self.config.model_name
        provider_name = MODEL_PROVIDER_MAP.get(model)

        if provider_name and provider_name in self._providers:
            return model, self._providers[provider_name]

        # Try fallback chain
        if provider_name:
            for fallback in FALLBACK_CHAINS.get(provider_name, []):
                if fallback in self._providers:
                    fallback_model = self._get_default_model(fallback)
                    return fallback_model, self._providers[fallback]

        # Last resort: use whatever is available
        for name, provider in self._providers.items():
            return self._get_default_model(name), provider

        raise RuntimeError("No LLM providers available. Set OPENAI_API_KEY or ANTHROPIC_API_KEY.")

    def _get_default_model(self, provider_name: str) -> str:
        """Get the default model for a provider."""
        defaults = {
            "openai": "gpt-4o",
            "anthropic": "claude-sonnet-4-20250514",
            "local": "llama3",
        }
        return defaults.get(provider_name, "gpt-4")

    async def complete(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict] | None = None,
        model: str | None = None,
        **kwargs,
    ) -> LLMResponse:
        """Send a completion request with automatic fallback."""
        model_name, provider = self._get_provider_for_model(model)

        try:
            self._request_count += 1
            response = await provider.complete(
                messages,
                tools=tools,
                model=model_name,
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens,
                **kwargs,
            )
            return response
        except Exception as e:
            # Try fallback
            provider_name = MODEL_PROVIDER_MAP.get(model_name, "")
            self._error_count[provider_name] = self._error_count.get(provider_name, 0) + 1

            for fallback_name in FALLBACK_CHAINS.get(provider_name, []):
                if fallback_name in self._providers:
                    fallback_model = self._get_default_model(fallback_name)
                    try:
                        return await self._providers[fallback_name].complete(
                            messages,
                            tools=tools,
                            model=fallback_model,
                            temperature=self.config.temperature,
                            max_tokens=self.config.max_tokens,
                            **kwargs,
                        )
                    except Exception:
                        continue
            raise

    async def stream(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict] | None = None,
        model: str | None = None,
        **kwargs,
    ) -> AsyncIterator[dict[str, Any]]:
        """Stream a completion with automatic fallback."""
        model_name, provider = self._get_provider_for_model(model)

        try:
            self._request_count += 1
            async for chunk in provider.stream(
                messages,
                tools=tools,
                model=model_name,
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens,
                **kwargs,
            ):
                yield chunk
        except Exception:
            # Try fallback providers
            provider_name = MODEL_PROVIDER_MAP.get(model_name, "")
            for fallback_name in FALLBACK_CHAINS.get(provider_name, []):
                if fallback_name in self._providers:
                    fallback_model = self._get_default_model(fallback_name)
                    try:
                        async for chunk in self._providers[fallback_name].stream(
                            messages,
                            tools=tools,
                            model=fallback_model,
                            **kwargs,
                        ):
                            yield chunk
                        return
                    except Exception:
                        continue
            raise

    def get_stats(self) -> dict[str, Any]:
        """Get router statistics."""
        return {
            "total_requests": self._request_count,
            "errors": dict(self._error_count),
            "available_providers": list(self._providers.keys()),
            "current_model": self.config.model_name,
        }
