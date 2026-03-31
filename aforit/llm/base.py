"""Base LLM provider interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, AsyncIterator


@dataclass
class LLMResponse:
    """Structured response from an LLM provider."""

    content: str = ""
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    finish_reason: str = ""
    usage: dict[str, int] = field(default_factory=dict)
    model: str = ""
    raw: Any = None


class BaseLLMProvider(ABC):
    """Abstract base class for LLM providers."""

    name: str = "base"
    supports_streaming: bool = True
    supports_tools: bool = True
    supports_vision: bool = False

    @abstractmethod
    async def complete(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict] | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        **kwargs,
    ) -> LLMResponse:
        """Send a completion request and get the full response."""
        ...

    @abstractmethod
    async def stream(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict] | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        **kwargs,
    ) -> AsyncIterator[dict[str, Any]]:
        """Stream a completion response chunk by chunk."""
        ...

    @abstractmethod
    def count_tokens(self, text: str) -> int:
        """Count tokens in a string."""
        ...

    @abstractmethod
    def get_available_models(self) -> list[str]:
        """List models available from this provider."""
        ...

    def supports_model(self, model_name: str) -> bool:
        """Check if this provider supports a given model."""
        return model_name in self.get_available_models()
