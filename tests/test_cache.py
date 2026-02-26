"""Tests for caching utilities."""

import time
import pytest

from aforit.utils.cache import LRUCache, TTLCache, DiskCache


class TestLRUCache:
    def test_put_and_get(self):
        cache = LRUCache(max_size=10)
        cache.put("key1", "value1")
        assert cache.get("key1") == "value1"

    def test_get_missing(self):
        cache = LRUCache()
        assert cache.get("missing") is None
        assert cache.get("missing", "default") == "default"

    def test_eviction(self):
        cache = LRUCache(max_size=2)
        cache.put("a", 1)
        cache.put("b", 2)
        cache.put("c", 3)  # should evict "a"
        assert cache.get("a") is None
        assert cache.get("b") == 2
        assert cache.get("c") == 3

    def test_lru_order(self):
        cache = LRUCache(max_size=2)
        cache.put("a", 1)
        cache.put("b", 2)
        cache.get("a")  # makes "a" most recently used
        cache.put("c", 3)  # should evict "b"
        assert cache.get("a") == 1
        assert cache.get("b") is None

    def test_delete(self):
        cache = LRUCache()
        cache.put("key", "val")
        assert cache.delete("key") is True
        assert cache.get("key") is None

    def test_stats(self):
        cache = LRUCache()
        cache.put("a", 1)
        cache.get("a")
        cache.get("b")
        stats = cache.get_stats()
        assert stats["hits"] == 1
        assert stats["misses"] == 1


class TestTTLCache:
    def test_put_and_get(self):
        cache = TTLCache(ttl_seconds=10)
        cache.put("key", "value")
        assert cache.get("key") == "value"

    def test_expiration(self):
        cache = TTLCache(ttl_seconds=0.1)
        cache.put("key", "value")
        time.sleep(0.2)
        assert cache.get("key") is None

    def test_custom_ttl(self):
        cache = TTLCache(ttl_seconds=10)
        cache.put("short", "val", ttl=0.1)
        cache.put("long", "val", ttl=10)
        time.sleep(0.2)
        assert cache.get("short") is None
        assert cache.get("long") == "val"


class TestDiskCache:
    def test_put_and_get(self, tmp_path):
        cache = DiskCache(tmp_path)
        cache.put("key1", {"data": "value"})
        assert cache.get("key1") == {"data": "value"}

    def test_expiration(self, tmp_path):
        cache = DiskCache(tmp_path, ttl_seconds=0.1)
        cache.put("key1", "value")
        time.sleep(0.2)
        assert cache.get("key1") is None

    def test_delete(self, tmp_path):
        cache = DiskCache(tmp_path)
        cache.put("key1", "value")
        assert cache.delete("key1") is True
        assert cache.get("key1") is None

    def test_clear(self, tmp_path):
        cache = DiskCache(tmp_path)
        cache.put("a", 1)
        cache.put("b", 2)
        cache.clear()
        assert cache.size == 0
