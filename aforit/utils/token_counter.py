"""Token counting utilities for various LLM providers."""

from __future__ import annotations

from typing import Any


class TokenCounter:
    """Count tokens for different models and providers."""

    # Average characters per token for different model families
    CHARS_PER_TOKEN = {
        "gpt-4": 3.5,
        "gpt-3.5": 4.0,
        "claude": 3.5,
        "llama": 4.0,
        "default": 4.0,
    }

    def __init__(self, model: str = "gpt-4"):
        self.model = model
        self._tiktoken_enc = None

    def count(self, text: str) -> int:
        """Count tokens in text. Uses tiktoken if available, falls back to estimation."""
        try:
            return self._count_tiktoken(text)
        except (ImportError, KeyError):
            return self._count_estimate(text)

    def _count_tiktoken(self, text: str) -> int:
        """Precise counting using tiktoken."""
        import tiktoken

        if self._tiktoken_enc is None:
            try:
                self._tiktoken_enc = tiktoken.encoding_for_model(self.model)
            except KeyError:
                self._tiktoken_enc = tiktoken.get_encoding("cl100k_base")

        return len(self._tiktoken_enc.encode(text))

    def _count_estimate(self, text: str) -> int:
        """Estimate token count based on character ratios."""
        ratio = self.CHARS_PER_TOKEN.get(self.model.split("-")[0], 4.0)
        return max(1, int(len(text) / ratio))

    def count_messages(self, messages: list[dict[str, Any]]) -> int:
        """Count tokens in a list of chat messages."""
        total = 0
        for msg in messages:
            total += 4  # message overhead tokens
            total += self.count(msg.get("content", ""))
            total += self.count(msg.get("role", ""))
        total += 2  # priming tokens
        return total

    def truncate_to_limit(self, text: str, max_tokens: int) -> str:
        """Truncate text to fit within a token limit."""
        current = self.count(text)
        if current <= max_tokens:
            return text

        # Binary search for the right truncation point
        low, high = 0, len(text)
        while low < high:
            mid = (low + high + 1) // 2
            if self.count(text[:mid]) <= max_tokens:
                low = mid
            else:
                high = mid - 1

        return text[:low]

    def fits_in_context(self, messages: list[dict], context_window: int, reserve: int = 0) -> bool:
        """Check if messages fit within the context window."""
        return self.count_messages(messages) <= (context_window - reserve)
