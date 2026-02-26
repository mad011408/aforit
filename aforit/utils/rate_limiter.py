"""Rate limiter - token bucket and sliding window implementations."""

from __future__ import annotations

import asyncio
import time
from collections import deque
from dataclasses import dataclass, field


@dataclass
class RateLimitState:
    """State for rate limit tracking."""

    tokens: float = 0.0
    last_refill: float = field(default_factory=time.time)
    request_timestamps: deque = field(default_factory=deque)


class TokenBucketLimiter:
    """Token bucket rate limiter.

    Allows bursts up to bucket_size, refilling at rate tokens per second.
    """

    def __init__(self, rate: float, bucket_size: int):
        self.rate = rate  # tokens per second
        self.bucket_size = bucket_size
        self._state = RateLimitState(tokens=float(bucket_size))
        self._lock = asyncio.Lock()

    async def acquire(self, tokens: int = 1) -> float:
        """Acquire tokens. Returns wait time if throttled, 0.0 if immediate."""
        async with self._lock:
            self._refill()

            if self._state.tokens >= tokens:
                self._state.tokens -= tokens
                return 0.0

            # Calculate wait time
            deficit = tokens - self._state.tokens
            wait_time = deficit / self.rate
            await asyncio.sleep(wait_time)
            self._refill()
            self._state.tokens -= tokens
            return wait_time

    def _refill(self):
        """Refill tokens based on elapsed time."""
        now = time.time()
        elapsed = now - self._state.last_refill
        self._state.tokens = min(
            self.bucket_size,
            self._state.tokens + elapsed * self.rate,
        )
        self._state.last_refill = now

    @property
    def available_tokens(self) -> float:
        self._refill()
        return self._state.tokens


class SlidingWindowLimiter:
    """Sliding window rate limiter.

    Limits to max_requests within window_seconds.
    """

    def __init__(self, max_requests: int, window_seconds: float):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._timestamps: deque[float] = deque()
        self._lock = asyncio.Lock()

    async def acquire(self) -> float:
        """Try to acquire a slot. Returns wait time, 0.0 if immediate."""
        async with self._lock:
            now = time.time()
            cutoff = now - self.window_seconds

            # Remove old timestamps
            while self._timestamps and self._timestamps[0] < cutoff:
                self._timestamps.popleft()

            if len(self._timestamps) < self.max_requests:
                self._timestamps.append(now)
                return 0.0

            # Need to wait
            oldest = self._timestamps[0]
            wait_time = oldest + self.window_seconds - now
            if wait_time > 0:
                await asyncio.sleep(wait_time)

            # Clean up and add
            now = time.time()
            cutoff = now - self.window_seconds
            while self._timestamps and self._timestamps[0] < cutoff:
                self._timestamps.popleft()
            self._timestamps.append(now)
            return wait_time

    @property
    def current_count(self) -> int:
        now = time.time()
        cutoff = now - self.window_seconds
        while self._timestamps and self._timestamps[0] < cutoff:
            self._timestamps.popleft()
        return len(self._timestamps)

    @property
    def is_limited(self) -> bool:
        return self.current_count >= self.max_requests


class CompositeRateLimiter:
    """Combines multiple rate limiters (e.g., requests + tokens per minute)."""

    def __init__(self):
        self._limiters: dict[str, TokenBucketLimiter | SlidingWindowLimiter] = {}

    def add_limiter(self, name: str, limiter: TokenBucketLimiter | SlidingWindowLimiter):
        self._limiters[name] = limiter

    async def acquire(self, tokens: dict[str, int] | None = None) -> float:
        """Acquire from all limiters. Returns total wait time."""
        total_wait = 0.0
        for name, limiter in self._limiters.items():
            if isinstance(limiter, TokenBucketLimiter):
                t = tokens.get(name, 1) if tokens else 1
                wait = await limiter.acquire(t)
            else:
                wait = await limiter.acquire()
            total_wait += wait
        return total_wait

    def get_status(self) -> dict[str, Any]:
        """Get status of all limiters."""
        from typing import Any
        status: dict[str, Any] = {}
        for name, limiter in self._limiters.items():
            if isinstance(limiter, TokenBucketLimiter):
                status[name] = {"available": limiter.available_tokens}
            else:
                status[name] = {
                    "current": limiter.current_count,
                    "limited": limiter.is_limited,
                }
        return status
