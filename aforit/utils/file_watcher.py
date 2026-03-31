"""File watcher - monitor file system changes."""

from __future__ import annotations

import asyncio
import hashlib
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable


@dataclass
class FileChange:
    """Represents a detected file change."""

    path: Path
    change_type: str  # created, modified, deleted
    timestamp: float = field(default_factory=time.time)
    old_hash: str = ""
    new_hash: str = ""


class FileWatcher:
    """Watch for file system changes using polling.

    A lightweight alternative to watchdog that works across platforms
    without native dependencies.
    """

    def __init__(
        self,
        paths: list[str | Path],
        patterns: list[str] | None = None,
        ignore_patterns: list[str] | None = None,
        poll_interval: float = 1.0,
    ):
        self.paths = [Path(p) for p in paths]
        self.patterns = patterns or ["*"]
        self.ignore_patterns = ignore_patterns or [
            "*.pyc", "__pycache__", ".git", "node_modules", ".DS_Store"
        ]
        self.poll_interval = poll_interval
        self._file_hashes: dict[str, str] = {}
        self._callbacks: list[Callable[[FileChange], Any]] = []
        self._running = False

    def on_change(self, callback: Callable[[FileChange], Any]):
        """Register a callback for file changes."""
        self._callbacks.append(callback)

    def _hash_file(self, path: Path) -> str:
        """Get a hash of a file's contents."""
        try:
            return hashlib.md5(path.read_bytes()).hexdigest()
        except (IOError, PermissionError):
            return ""

    def _should_watch(self, path: Path) -> bool:
        """Check if a path should be watched based on patterns."""
        name = path.name

        # Check ignore patterns
        for pattern in self.ignore_patterns:
            if path.match(pattern) or name == pattern:
                return False

        # Check include patterns
        if self.patterns == ["*"]:
            return True
        return any(path.match(p) for p in self.patterns)

    def _scan(self) -> dict[str, str]:
        """Scan all watched paths and return file hashes."""
        hashes = {}
        for watch_path in self.paths:
            if watch_path.is_file():
                if self._should_watch(watch_path):
                    hashes[str(watch_path)] = self._hash_file(watch_path)
            elif watch_path.is_dir():
                for p in watch_path.rglob("*"):
                    if p.is_file() and self._should_watch(p):
                        hashes[str(p)] = self._hash_file(p)
        return hashes

    def _detect_changes(self, new_hashes: dict[str, str]) -> list[FileChange]:
        """Compare old and new hashes to detect changes."""
        changes = []

        # Check for new and modified files
        for path, new_hash in new_hashes.items():
            old_hash = self._file_hashes.get(path)
            if old_hash is None:
                changes.append(FileChange(
                    path=Path(path),
                    change_type="created",
                    new_hash=new_hash,
                ))
            elif old_hash != new_hash:
                changes.append(FileChange(
                    path=Path(path),
                    change_type="modified",
                    old_hash=old_hash,
                    new_hash=new_hash,
                ))

        # Check for deleted files
        for path in self._file_hashes:
            if path not in new_hashes:
                changes.append(FileChange(
                    path=Path(path),
                    change_type="deleted",
                    old_hash=self._file_hashes[path],
                ))

        return changes

    async def start(self):
        """Start watching for changes."""
        self._running = True
        self._file_hashes = self._scan()

        while self._running:
            await asyncio.sleep(self.poll_interval)
            new_hashes = self._scan()
            changes = self._detect_changes(new_hashes)
            self._file_hashes = new_hashes

            for change in changes:
                for callback in self._callbacks:
                    try:
                        result = callback(change)
                        if asyncio.iscoroutine(result):
                            await result
                    except Exception:
                        pass

    def stop(self):
        """Stop watching."""
        self._running = False

    def get_watched_files(self) -> list[str]:
        """Get list of currently watched files."""
        return list(self._file_hashes.keys())
