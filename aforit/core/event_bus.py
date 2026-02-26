"""Event bus - pub/sub system for inter-component communication."""

from __future__ import annotations

import asyncio
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Callable, Coroutine
import time


@dataclass
class Event:
    """An event that can be published through the event bus."""

    type: str
    data: dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    source: str = ""


class EventBus:
    """Async event bus for loosely-coupled component communication.

    Usage:
        bus = EventBus()

        @bus.on("message.received")
        async def handle_message(event: Event):
            print(f"Got message: {event.data}")

        await bus.emit("message.received", {"content": "hello"})
    """

    def __init__(self):
        self._handlers: dict[str, list[Callable]] = defaultdict(list)
        self._once_handlers: dict[str, list[Callable]] = defaultdict(list)
        self._history: list[Event] = []
        self._max_history = 100

    def on(self, event_type: str):
        """Decorator to register a persistent event handler."""
        def decorator(func: Callable):
            self._handlers[event_type].append(func)
            return func
        return decorator

    def once(self, event_type: str):
        """Decorator to register a one-time event handler."""
        def decorator(func: Callable):
            self._once_handlers[event_type].append(func)
            return func
        return decorator

    def subscribe(self, event_type: str, handler: Callable):
        """Subscribe a handler to an event type."""
        self._handlers[event_type].append(handler)

    def unsubscribe(self, event_type: str, handler: Callable):
        """Unsubscribe a handler from an event type."""
        if handler in self._handlers[event_type]:
            self._handlers[event_type].remove(handler)

    async def emit(self, event_type: str, data: dict[str, Any] | None = None, source: str = ""):
        """Emit an event to all registered handlers."""
        event = Event(type=event_type, data=data or {}, source=source)

        # Track history
        self._history.append(event)
        if len(self._history) > self._max_history:
            self._history = self._history[-self._max_history:]

        # Call persistent handlers
        for handler in self._handlers.get(event_type, []):
            try:
                result = handler(event)
                if asyncio.iscoroutine(result):
                    await result
            except Exception:
                pass  # Don't let handler errors break the bus

        # Call and remove one-time handlers
        once_handlers = self._once_handlers.pop(event_type, [])
        for handler in once_handlers:
            try:
                result = handler(event)
                if asyncio.iscoroutine(result):
                    await result
            except Exception:
                pass

        # Also emit to wildcard handlers
        for handler in self._handlers.get("*", []):
            try:
                result = handler(event)
                if asyncio.iscoroutine(result):
                    await result
            except Exception:
                pass

    def get_history(self, event_type: str | None = None, limit: int = 20) -> list[Event]:
        """Get recent event history, optionally filtered by type."""
        if event_type:
            events = [e for e in self._history if e.type == event_type]
        else:
            events = self._history
        return events[-limit:]

    def clear_handlers(self, event_type: str | None = None):
        """Clear all handlers, optionally for a specific event type."""
        if event_type:
            self._handlers.pop(event_type, None)
            self._once_handlers.pop(event_type, None)
        else:
            self._handlers.clear()
            self._once_handlers.clear()

    @property
    def registered_events(self) -> list[str]:
        return list(set(list(self._handlers.keys()) + list(self._once_handlers.keys())))
