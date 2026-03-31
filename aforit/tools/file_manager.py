"""File management tool - read, write, search, and manipulate files."""

from __future__ import annotations

import glob
import os
import shutil
from pathlib import Path
from typing import Any

from aforit.tools.base import BaseTool, ToolResult


class FileManagerTool(BaseTool):
    """Tool for file system operations."""

    name = "file_manager"
    description = (
        "Manage files and directories. Supports read, write, list, search, "
        "copy, move, delete, and tree operations."
    )
    parameters = {
        "action": {
            "type": "string",
            "enum": ["read", "write", "append", "list", "search", "tree", "copy", "move", "delete", "info", "mkdir"],
            "description": "The file operation to perform",
        },
        "path": {
            "type": "string",
            "description": "File or directory path",
        },
        "content": {
            "type": "string",
            "description": "Content to write (for write/append actions)",
        },
        "pattern": {
            "type": "string",
            "description": "Search pattern (glob or text)",
        },
        "destination": {
            "type": "string",
            "description": "Destination path (for copy/move)",
        },
        "recursive": {
            "type": "boolean",
            "description": "Whether to operate recursively",
            "default": False,
        },
    }
    required_params = ["action", "path"]
    timeout = 30.0

    async def execute(self, action: str, path: str, **kwargs) -> ToolResult:
        """Execute a file operation."""
        handlers = {
            "read": self._read,
            "write": self._write,
            "append": self._append,
            "list": self._list,
            "search": self._search,
            "tree": self._tree,
            "copy": self._copy,
            "move": self._move,
            "delete": self._delete,
            "info": self._info,
            "mkdir": self._mkdir,
        }

        handler = handlers.get(action)
        if not handler:
            return ToolResult(success=False, output="", error=f"Unknown action: {action}")

        try:
            return await handler(path, **kwargs)
        except PermissionError:
            return ToolResult(success=False, output="", error=f"Permission denied: {path}")
        except Exception as e:
            return ToolResult(success=False, output="", error=str(e))

    async def _read(self, path: str, **kwargs) -> ToolResult:
        p = Path(path)
        if not p.exists():
            return ToolResult(success=False, output="", error=f"File not found: {path}")
        if not p.is_file():
            return ToolResult(success=False, output="", error=f"Not a file: {path}")

        content = p.read_text(errors="replace")
        lines = content.split("\n")
        numbered = "\n".join(f"{i+1:4d} | {line}" for i, line in enumerate(lines))
        return ToolResult(
            success=True,
            output=numbered,
            metadata={"lines": len(lines), "size": p.stat().st_size},
        )

    async def _write(self, path: str, content: str = "", **kwargs) -> ToolResult:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content)
        return ToolResult(
            success=True,
            output=f"Written {len(content)} bytes to {path}",
            metadata={"bytes_written": len(content)},
        )

    async def _append(self, path: str, content: str = "", **kwargs) -> ToolResult:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "a") as f:
            f.write(content)
        return ToolResult(success=True, output=f"Appended {len(content)} bytes to {path}")

    async def _list(self, path: str, recursive: bool = False, **kwargs) -> ToolResult:
        p = Path(path)
        if not p.exists():
            return ToolResult(success=False, output="", error=f"Directory not found: {path}")

        if recursive:
            entries = sorted(str(e.relative_to(p)) for e in p.rglob("*"))
        else:
            entries = sorted(
                f"{'[DIR]  ' if e.is_dir() else '[FILE] '}{e.name}"
                for e in sorted(p.iterdir())
            )

        output = "\n".join(entries)
        return ToolResult(success=True, output=output, metadata={"count": len(entries)})

    async def _search(self, path: str, pattern: str = "", **kwargs) -> ToolResult:
        p = Path(path)
        if not p.exists():
            return ToolResult(success=False, output="", error=f"Path not found: {path}")

        results = []

        # Search file contents
        if p.is_file():
            content = p.read_text(errors="replace")
            for i, line in enumerate(content.split("\n"), 1):
                if pattern.lower() in line.lower():
                    results.append(f"{path}:{i}: {line.strip()}")
        else:
            # Search in directory
            for fp in p.rglob("*"):
                if fp.is_file():
                    try:
                        content = fp.read_text(errors="replace")
                        for i, line in enumerate(content.split("\n"), 1):
                            if pattern.lower() in line.lower():
                                results.append(f"{fp}:{i}: {line.strip()}")
                    except (UnicodeDecodeError, PermissionError):
                        continue

        output = "\n".join(results[:100])
        if len(results) > 100:
            output += f"\n... and {len(results) - 100} more matches"
        return ToolResult(success=True, output=output, metadata={"matches": len(results)})

    async def _tree(self, path: str, **kwargs) -> ToolResult:
        p = Path(path)
        if not p.exists():
            return ToolResult(success=False, output="", error=f"Path not found: {path}")

        lines = [str(p)]
        self._build_tree(p, lines, prefix="")
        return ToolResult(success=True, output="\n".join(lines[:200]))

    def _build_tree(self, path: Path, lines: list[str], prefix: str, depth: int = 0):
        if depth > 5:
            return
        try:
            entries = sorted(path.iterdir(), key=lambda e: (not e.is_dir(), e.name))
        except PermissionError:
            return

        for i, entry in enumerate(entries):
            is_last = i == len(entries) - 1
            connector = "--- " if is_last else "|-- "
            lines.append(f"{prefix}{connector}{entry.name}")
            if entry.is_dir():
                extension = "    " if is_last else "|   "
                self._build_tree(entry, lines, prefix + extension, depth + 1)

    async def _copy(self, path: str, destination: str = "", **kwargs) -> ToolResult:
        if not destination:
            return ToolResult(success=False, output="", error="Destination required for copy")
        src = Path(path)
        dst = Path(destination)
        if src.is_dir():
            shutil.copytree(str(src), str(dst))
        else:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(str(src), str(dst))
        return ToolResult(success=True, output=f"Copied {path} -> {destination}")

    async def _move(self, path: str, destination: str = "", **kwargs) -> ToolResult:
        if not destination:
            return ToolResult(success=False, output="", error="Destination required for move")
        shutil.move(path, destination)
        return ToolResult(success=True, output=f"Moved {path} -> {destination}")

    async def _delete(self, path: str, **kwargs) -> ToolResult:
        p = Path(path)
        if not p.exists():
            return ToolResult(success=False, output="", error=f"Path not found: {path}")
        if p.is_dir():
            shutil.rmtree(str(p))
        else:
            p.unlink()
        return ToolResult(success=True, output=f"Deleted {path}")

    async def _info(self, path: str, **kwargs) -> ToolResult:
        p = Path(path)
        if not p.exists():
            return ToolResult(success=False, output="", error=f"Path not found: {path}")
        stat = p.stat()
        info = {
            "path": str(p.absolute()),
            "type": "directory" if p.is_dir() else "file",
            "size": stat.st_size,
            "modified": stat.st_mtime,
            "permissions": oct(stat.st_mode),
        }
        if p.is_file():
            info["extension"] = p.suffix
            info["lines"] = len(p.read_text(errors="replace").split("\n"))
        output = "\n".join(f"{k}: {v}" for k, v in info.items())
        return ToolResult(success=True, output=output, metadata=info)

    async def _mkdir(self, path: str, **kwargs) -> ToolResult:
        Path(path).mkdir(parents=True, exist_ok=True)
        return ToolResult(success=True, output=f"Created directory: {path}")
