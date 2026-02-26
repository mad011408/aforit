"""Tests for the Memory module."""

import pytest

from aforit.core.config import Config
from aforit.core.memory import MemoryStore


@pytest.fixture
def memory(tmp_path):
    config = Config(data_dir=tmp_path)
    return MemoryStore(config)


class TestMemoryStore:
    @pytest.mark.asyncio
    async def test_store_and_search(self, memory):
        await memory.store("python list comprehension", "Use [x for x in items]")
        results = await memory.search("python list")
        assert len(results) > 0
        assert "list comprehension" in results[0]["query"]

    @pytest.mark.asyncio
    async def test_empty_search(self, memory):
        results = await memory.search("anything")
        assert results == []

    @pytest.mark.asyncio
    async def test_delete(self, memory):
        await memory.store("test query", "test response")
        mem_id = memory.memories[0]["id"]
        assert await memory.delete(mem_id) is True
        assert memory.size == 0

    @pytest.mark.asyncio
    async def test_clear(self, memory):
        await memory.store("q1", "r1")
        await memory.store("q2", "r2")
        await memory.clear()
        assert memory.size == 0

    @pytest.mark.asyncio
    async def test_stats(self, memory):
        stats = memory.get_stats()
        assert stats["total"] == 0

        await memory.store("q1", "r1")
        stats = memory.get_stats()
        assert stats["total"] == 1

    @pytest.mark.asyncio
    async def test_persistence(self, tmp_path):
        config = Config(data_dir=tmp_path)
        mem1 = MemoryStore(config)
        await mem1.store("persist test", "persist value")

        # Create new instance, should load from disk
        mem2 = MemoryStore(config)
        assert mem2.size == 1
