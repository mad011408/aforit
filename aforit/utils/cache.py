"""Caching utilities - in-memory LRU, disk cache, and TTL cache."""

from __future__ import annotations

import hashlib
import json
import time
from collections import OrderedDict
from pathlib import Path
from typing import Any, Callable


class LRUCache:
    """Thread-safe LRU (Least Recently Used) cache."""

    def __init__(self, max_size: int = 128):
        self.max_size = max_size
        self._cache: OrderedDict[str, Any] = OrderedDict()
        self._hits = 0
        self._misses = 0

    def get(self, key: str, default: Any = None) -> Any:
        """Get a value, moving it to the end (most recent)."""
        if key in self._cache:
            self._hits += 1
            self._cache.move_to_end(key)
            return self._cache[key]
        self._misses += 1
        return default

    def put(self, key: str, value: Any):
        """Store a value, evicting the oldest if at capacity."""
        if key in self._cache:
            self._cache.move_to_end(key)
        self._cache[key] = value
        if len(self._cache) > self.max_size:
            self._cache.popitem(last=False)

    def delete(self, key: str) -> bool:
        if key in self._cache:
            del self._cache[key]
            return True
        return False

    def clear(self):
        self._cache.clear()

    @property
    def size(self) -> int:
        return len(self._cache)

    @property
    def hit_rate(self) -> float:
        total = self._hits + self._misses
        return self._hits / total if total > 0 else 0.0

    def get_stats(self) -> dict[str, Any]:
        return {
            "size": self.size,
            "max_size": self.max_size,
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": f"{self.hit_rate:.1%}",
        }


class TTLCache:
    """Cache with time-to-live expiration."""

    def __init__(self, ttl_seconds: float = 300, max_size: int = 256):
        self.ttl = ttl_seconds
        self.max_size = max_size
        self._cache: dict[str, tuple[float, Any]] = {}

    def get(self, key: str, default: Any = None) -> Any:
        entry = self._cache.get(key)
        if entry is None:
            return default
        expires_at, value = entry
        if time.time() > expires_at:
            del self._cache[key]
            return default
        return value

    def put(self, key: str, value: Any, ttl: float | None = None):
        self._evict_expired()
        expires_at = time.time() + (ttl or self.ttl)
        self._cache[key] = (expires_at, value)
        if len(self._cache) > self.max_size:
            # Remove the entry expiring soonest
            oldest_key = min(self._cache, key=lambda k: self._cache[k][0])
            del self._cache[oldest_key]

    def delete(self, key: str) -> bool:
        if key in self._cache:
            del self._cache[key]
            return True
        return False

    def clear(self):
        self._cache.clear()

    def _evict_expired(self):
        now = time.time()
        expired = [k for k, (exp, _) in self._cache.items() if now > exp]
        for k in expired:
            del self._cache[k]

    @property
    def size(self) -> int:
        self._evict_expired()
        return len(self._cache)


class DiskCache:
    """Persistent disk-based cache."""

    def __init__(self, cache_dir: Path, ttl_seconds: float = 3600):
        self.cache_dir = cache_dir
        self.ttl = ttl_seconds
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _key_to_path(self, key: str) -> Path:
        hashed = hashlib.sha256(key.encode()).hexdigest()
        return self.cache_dir / f"{hashed}.json"

    def get(self, key: str, default: Any = None) -> Any:
        path = self._key_to_path(key)
        if not path.exists():
            return default
        try:
            data = json.loads(path.read_text())
            if time.time() > data.get("expires_at", 0):
                path.unlink(missing_ok=True)
                return default
            return data["value"]
        except (json.JSONDecodeError, IOError, KeyError):
            path.unlink(missing_ok=True)
            return default

    def put(self, key: str, value: Any, ttl: float | None = None):
        path = self._key_to_path(key)
        data = {
            "key": key,
            "value": value,
            "created_at": time.time(),
            "expires_at": time.time() + (ttl or self.ttl),
        }
        path.write_text(json.dumps(data, default=str))

    def delete(self, key: str) -> bool:
        path = self._key_to_path(key)
        if path.exists():
            path.unlink()
            return True
        return False

    def clear(self):
        for p in self.cache_dir.glob("*.json"):
            p.unlink(missing_ok=True)

    def evict_expired(self) -> int:
        """Remove all expired entries. Returns count of evicted entries."""
        now = time.time()
        count = 0
        for p in self.cache_dir.glob("*.json"):
            try:
                data = json.loads(p.read_text())
                if now > data.get("expires_at", 0):
                    p.unlink()
                    count += 1
            except (json.JSONDecodeError, IOError):
                p.unlink(missing_ok=True)
                count += 1
        return count

    @property
    def size(self) -> int:
        return len(list(self.cache_dir.glob("*.json")))


def cached(cache: LRUCache | TTLCache, key_fn: Callable[..., str] | None = None):
    """Decorator to cache function results.

    Usage:
        my_cache = LRUCache(max_size=100)

        @cached(my_cache)
        def expensive_function(x, y):
            return x + y
    """
    def decorator(func: Callable) -> Callable:
        def wrapper(*args, **kwargs):
            if key_fn:
                cache_key = key_fn(*args, **kwargs)
            else:
                cache_key = f"{func.__name__}:{args}:{kwargs}"

            result = cache.get(cache_key)
            if result is not None:
                return result

            result = func(*args, **kwargs)
            cache.put(cache_key, result)
            return result
        return wrapper
    return decorator
