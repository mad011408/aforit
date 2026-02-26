"""Middleware system - intercept and transform messages in the pipeline."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Callable


class Middleware(ABC):
    """Base class for middleware that can intercept messages."""

    name: str = "base"
    priority: int = 0  # Lower = runs first

    @abstractmethod
    async def process_input(self, message: str, context: dict[str, Any]) -> str:
        """Process user input before it reaches the LLM."""
        return message

    @abstractmethod
    async def process_output(self, response: str, context: dict[str, Any]) -> str:
        """Process LLM output before it reaches the user."""
        return response


class MiddlewareChain:
    """Chain of middleware processors."""

    def __init__(self):
        self._middleware: list[Middleware] = []

    def add(self, middleware: Middleware):
        """Add middleware to the chain."""
        self._middleware.append(middleware)
        self._middleware.sort(key=lambda m: m.priority)

    def remove(self, name: str) -> bool:
        before = len(self._middleware)
        self._middleware = [m for m in self._middleware if m.name != name]
        return len(self._middleware) < before

    async def process_input(self, message: str, context: dict[str, Any] | None = None) -> str:
        ctx = context or {}
        for mw in self._middleware:
            message = await mw.process_input(message, ctx)
        return message

    async def process_output(self, response: str, context: dict[str, Any] | None = None) -> str:
        ctx = context or {}
        for mw in reversed(self._middleware):
            response = await mw.process_output(response, ctx)
        return response


class ContentFilterMiddleware(Middleware):
    """Filter sensitive content from inputs and outputs."""

    name = "content_filter"
    priority = 10

    def __init__(self, blocked_patterns: list[str] | None = None):
        self.blocked_patterns = blocked_patterns or []

    async def process_input(self, message: str, context: dict[str, Any]) -> str:
        for pattern in self.blocked_patterns:
            if pattern.lower() in message.lower():
                return "[Content filtered]"
        return message

    async def process_output(self, response: str, context: dict[str, Any]) -> str:
        return response


class LoggingMiddleware(Middleware):
    """Log all messages passing through the pipeline."""

    name = "logging"
    priority = 0

    def __init__(self):
        self.log: list[dict[str, Any]] = []

    async def process_input(self, message: str, context: dict[str, Any]) -> str:
        self.log.append({"direction": "input", "content": message[:200]})
        return message

    async def process_output(self, response: str, context: dict[str, Any]) -> str:
        self.log.append({"direction": "output", "content": response[:200]})
        return response


class PromptInjectionGuard(Middleware):
    """Detect and prevent prompt injection attempts."""

    name = "injection_guard"
    priority = 5

    SUSPICIOUS_PATTERNS = [
        "ignore previous instructions",
        "ignore all instructions",
        "disregard your instructions",
        "new instructions:",
        "system prompt:",
        "you are now",
        "pretend to be",
        "jailbreak",
    ]

    async def process_input(self, message: str, context: dict[str, Any]) -> str:
        msg_lower = message.lower()
        for pattern in self.SUSPICIOUS_PATTERNS:
            if pattern in msg_lower:
                context["injection_detected"] = True
                return message  # Still pass through, but flag it
        return message

    async def process_output(self, response: str, context: dict[str, Any]) -> str:
        return response


class AutoCorrectMiddleware(Middleware):
    """Auto-correct common command typos."""

    name = "autocorrect"
    priority = 20

    CORRECTIONS = {
        "/hepl": "/help",
        "/hlep": "/help",
        "/quiit": "/quit",
        "/exti": "/exit",
        "/clera": "/clear",
        "/hisotry": "/history",
    }

    async def process_input(self, message: str, context: dict[str, Any]) -> str:
        stripped = message.strip().lower()
        if stripped in self.CORRECTIONS:
            return self.CORRECTIONS[stripped]
        return message

    async def process_output(self, response: str, context: dict[str, Any]) -> str:
        return response
