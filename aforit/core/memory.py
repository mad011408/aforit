"""Long-term memory using vector storage for semantic search."""

from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any

from aforit.core.config import Config


class MemoryStore:
    """Persistent memory store with semantic search capabilities.

    Uses a simple local JSON-based store with TF-IDF-like scoring.
    Can be upgraded to use ChromaDB or other vector databases.
    """

    def __init__(self, config: Config):
        self.config = config
        self.store_path = config.data_dir / "memory.json"
        self.memories: list[dict[str, Any]] = []
        self._load()

    def _load(self):
        """Load memories from disk."""
        if self.store_path.exists():
            try:
                self.memories = json.loads(self.store_path.read_text())
            except (json.JSONDecodeError, IOError):
                self.memories = []

    def _save(self):
        """Persist memories to disk."""
        self.store_path.parent.mkdir(parents=True, exist_ok=True)
        self.store_path.write_text(json.dumps(self.memories, indent=2))

    async def store(self, query: str, response: str, metadata: dict | None = None):
        """Store a query-response pair in memory."""
        memory_id = hashlib.sha256(f"{query}{time.time()}".encode()).hexdigest()[:16]
        entry = {
            "id": memory_id,
            "query": query,
            "response": response,
            "content": f"{query} {response}",
            "timestamp": time.time(),
            "metadata": metadata or {},
            "access_count": 0,
        }
        self.memories.append(entry)

        # Keep memory bounded
        if len(self.memories) > 1000:
            self._prune()

        self._save()

    async def search(self, query: str, top_k: int = 5) -> list[dict[str, Any]]:
        """Search memories using keyword matching with TF-IDF-like scoring."""
        if not self.memories:
            return []

        query_terms = set(query.lower().split())
        scored = []

        for mem in self.memories:
            content_terms = set(mem["content"].lower().split())
            overlap = query_terms & content_terms
            if overlap:
                # Score based on term overlap, recency, and access frequency
                term_score = len(overlap) / max(len(query_terms), 1)
                recency_score = 1.0 / (1.0 + (time.time() - mem["timestamp"]) / 86400)
                access_score = 0.1 * mem.get("access_count", 0)
                total_score = term_score * 0.6 + recency_score * 0.3 + access_score * 0.1
                scored.append((total_score, mem))

        scored.sort(key=lambda x: x[0], reverse=True)

        # Update access counts for returned results
        results = []
        for score, mem in scored[:top_k]:
            mem["access_count"] = mem.get("access_count", 0) + 1
            results.append(mem)

        self._save()
        return results

    async def delete(self, memory_id: str) -> bool:
        """Delete a specific memory by ID."""
        before = len(self.memories)
        self.memories = [m for m in self.memories if m["id"] != memory_id]
        if len(self.memories) < before:
            self._save()
            return True
        return False

    async def clear(self):
        """Clear all memories."""
        self.memories.clear()
        self._save()

    def _prune(self):
        """Remove oldest, least-accessed memories when store gets too large."""
        # Score each memory for importance
        now = time.time()
        for mem in self.memories:
            age_days = (now - mem["timestamp"]) / 86400
            mem["_importance"] = mem.get("access_count", 0) - age_days * 0.1

        self.memories.sort(key=lambda m: m["_importance"], reverse=True)
        self.memories = self.memories[:800]

        # Clean up temp scoring field
        for mem in self.memories:
            mem.pop("_importance", None)

    @property
    def size(self) -> int:
        return len(self.memories)

    def get_stats(self) -> dict[str, Any]:
        """Return memory store statistics."""
        if not self.memories:
            return {"total": 0, "oldest": None, "newest": None}
        return {
            "total": len(self.memories),
            "oldest": self.memories[0]["timestamp"],
            "newest": self.memories[-1]["timestamp"],
            "avg_access_count": sum(m.get("access_count", 0) for m in self.memories)
            / len(self.memories),
        }
