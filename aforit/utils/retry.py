"""Retry utilities with exponential backoff and jitter."""

from __future__ import annotations

import asyncio
import random
import time
from functools import wraps
from typing import Any, Callable, Type


class RetryConfig:
    """Configuration for retry behavior."""

    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        jitter: bool = True,
        retryable_exceptions: tuple[Type[Exception], ...] = (Exception,),
        on_retry: Callable[[int, Exception, float], None] | None = None,
    ):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter
        self.retryable_exceptions = retryable_exceptions
        self.on_retry = on_retry

    def calculate_delay(self, attempt: int) -> float:
        """Calculate the delay for a given attempt number."""
        delay = self.base_delay * (self.exponential_base ** attempt)
        delay = min(delay, self.max_delay)
        if self.jitter:
            delay = delay * (0.5 + random.random() * 0.5)
        return delay


async def retry_async(
    func: Callable,
    *args,
    config: RetryConfig | None = None,
    **kwargs,
) -> Any:
    """Execute an async function with retry logic."""
    config = config or RetryConfig()
    last_exception = None

    for attempt in range(config.max_retries + 1):
        try:
            return await func(*args, **kwargs)
        except config.retryable_exceptions as e:
            last_exception = e

            if attempt >= config.max_retries:
                break

            delay = config.calculate_delay(attempt)
            if config.on_retry:
                config.on_retry(attempt + 1, e, delay)

            await asyncio.sleep(delay)

    raise last_exception


def retry_sync(
    func: Callable,
    *args,
    config: RetryConfig | None = None,
    **kwargs,
) -> Any:
    """Execute a sync function with retry logic."""
    config = config or RetryConfig()
    last_exception = None

    for attempt in range(config.max_retries + 1):
        try:
            return func(*args, **kwargs)
        except config.retryable_exceptions as e:
            last_exception = e

            if attempt >= config.max_retries:
                break

            delay = config.calculate_delay(attempt)
            if config.on_retry:
                config.on_retry(attempt + 1, e, delay)

            time.sleep(delay)

    raise last_exception


def with_retry(config: RetryConfig | None = None):
    """Decorator for adding retry behavior to async functions.

    Usage:
        @with_retry(RetryConfig(max_retries=3))
        async def flaky_api_call():
            ...
    """
    config_ = config or RetryConfig()

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            return await retry_async(func, *args, config=config_, **kwargs)
        return wrapper
    return decorator


def with_retry_sync(config: RetryConfig | None = None):
    """Decorator for adding retry behavior to sync functions."""
    config_ = config or RetryConfig()

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            return retry_sync(func, *args, config=config_, **kwargs)
        return wrapper
    return decorator
