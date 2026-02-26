"""Diff engine - compute and apply text diffs."""

from __future__ import annotations

import difflib
from dataclasses import dataclass
from typing import Any


@dataclass
class DiffHunk:
    """A single hunk in a diff."""

    old_start: int
    old_count: int
    new_start: int
    new_count: int
    lines: list[str]

    @property
    def additions(self) -> int:
        return sum(1 for l in self.lines if l.startswith("+") and not l.startswith("+++"))

    @property
    def deletions(self) -> int:
        return sum(1 for l in self.lines if l.startswith("-") and not l.startswith("---"))


@dataclass
class DiffResult:
    """Result of a diff operation."""

    hunks: list[DiffHunk]
    old_file: str
    new_file: str
    unified_diff: str

    @property
    def total_additions(self) -> int:
        return sum(h.additions for h in self.hunks)

    @property
    def total_deletions(self) -> int:
        return sum(h.deletions for h in self.hunks)

    @property
    def is_empty(self) -> bool:
        return len(self.hunks) == 0

    def summary(self) -> str:
        return (
            f"{len(self.hunks)} hunks, "
            f"+{self.total_additions} -{self.total_deletions}"
        )


class DiffEngine:
    """Compute diffs between text content."""

    @staticmethod
    def unified_diff(
        old_text: str,
        new_text: str,
        old_name: str = "before",
        new_name: str = "after",
        context_lines: int = 3,
    ) -> DiffResult:
        """Generate a unified diff between two strings."""
        old_lines = old_text.splitlines(keepends=True)
        new_lines = new_text.splitlines(keepends=True)

        diff_lines = list(difflib.unified_diff(
            old_lines,
            new_lines,
            fromfile=old_name,
            tofile=new_name,
            n=context_lines,
        ))

        hunks = DiffEngine._parse_hunks(diff_lines)
        unified = "".join(diff_lines)

        return DiffResult(
            hunks=hunks,
            old_file=old_name,
            new_file=new_name,
            unified_diff=unified,
        )

    @staticmethod
    def _parse_hunks(diff_lines: list[str]) -> list[DiffHunk]:
        """Parse unified diff output into hunks."""
        hunks = []
        current_lines: list[str] = []
        old_start = new_start = old_count = new_count = 0

        for line in diff_lines:
            if line.startswith("@@"):
                if current_lines:
                    hunks.append(DiffHunk(old_start, old_count, new_start, new_count, current_lines))
                    current_lines = []

                # Parse hunk header: @@ -old_start,old_count +new_start,new_count @@
                parts = line.split()
                old_part = parts[1]  # -start,count
                new_part = parts[2]  # +start,count

                old_vals = old_part[1:].split(",")
                new_vals = new_part[1:].split(",")

                old_start = int(old_vals[0])
                old_count = int(old_vals[1]) if len(old_vals) > 1 else 1
                new_start = int(new_vals[0])
                new_count = int(new_vals[1]) if len(new_vals) > 1 else 1

            elif line.startswith("---") or line.startswith("+++"):
                continue
            else:
                current_lines.append(line)

        if current_lines:
            hunks.append(DiffHunk(old_start, old_count, new_start, new_count, current_lines))

        return hunks

    @staticmethod
    def apply_patch(original: str, diff_result: DiffResult) -> str:
        """Apply a diff patch to the original text."""
        lines = original.splitlines(keepends=True)

        offset = 0
        for hunk in diff_result.hunks:
            start = hunk.old_start - 1 + offset
            removed = 0
            added = 0

            new_lines = []
            for line in hunk.lines:
                if line.startswith("-"):
                    removed += 1
                elif line.startswith("+"):
                    new_lines.append(line[1:])
                    added += 1
                elif line.startswith(" "):
                    new_lines.append(line[1:])

            lines[start : start + hunk.old_count] = new_lines
            offset += added - removed

        return "".join(lines)

    @staticmethod
    def similarity_ratio(text_a: str, text_b: str) -> float:
        """Calculate the similarity ratio between two texts (0.0 to 1.0)."""
        return difflib.SequenceMatcher(None, text_a, text_b).ratio()

    @staticmethod
    def find_closest_match(target: str, candidates: list[str], cutoff: float = 0.6) -> str | None:
        """Find the closest matching string from a list."""
        matches = difflib.get_close_matches(target, candidates, n=1, cutoff=cutoff)
        return matches[0] if matches else None
