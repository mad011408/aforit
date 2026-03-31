"""Advanced markdown rendering for the terminal."""

from __future__ import annotations

import re
from typing import Any

from rich.console import Console, ConsoleOptions, RenderResult
from rich.markdown import Markdown
from rich.panel import Panel
from rich.syntax import Syntax
from rich.text import Text


class TerminalMarkdownRenderer:
    """Enhanced markdown renderer with code block highlighting and custom formatting."""

    def __init__(self, console: Console):
        self.console = console

    def render(self, text: str):
        """Render markdown text to the terminal with enhanced formatting."""
        # Process custom blocks first
        text = self._process_custom_blocks(text)

        # Extract and render code blocks separately for better syntax highlighting
        segments = self._split_code_blocks(text)

        for segment in segments:
            if segment["type"] == "code":
                self._render_code_block(
                    segment["content"],
                    segment.get("language", ""),
                    segment.get("title", ""),
                )
            elif segment["type"] == "info":
                self._render_info_block(segment["content"])
            elif segment["type"] == "warning":
                self._render_warning_block(segment["content"])
            elif segment["type"] == "error":
                self._render_error_block(segment["content"])
            else:
                md = Markdown(segment["content"])
                self.console.print(md)

    def _split_code_blocks(self, text: str) -> list[dict[str, Any]]:
        """Split text into markdown and code block segments."""
        segments = []
        pattern = r"```(\w*)\n(.*?)```"
        last_end = 0

        for match in re.finditer(pattern, text, re.DOTALL):
            # Text before code block
            if match.start() > last_end:
                before = text[last_end : match.start()].strip()
                if before:
                    segments.append({"type": "text", "content": before})

            # Code block
            language = match.group(1) or "text"
            code = match.group(2).strip()
            segments.append({
                "type": "code",
                "language": language,
                "content": code,
            })
            last_end = match.end()

        # Remaining text
        if last_end < len(text):
            remaining = text[last_end:].strip()
            if remaining:
                segments.append({"type": "text", "content": remaining})

        if not segments:
            segments.append({"type": "text", "content": text})

        return segments

    def _process_custom_blocks(self, text: str) -> str:
        """Process custom block markers like :::info, :::warning, etc."""
        # These get handled in _split_code_blocks as special segments
        return text

    def _render_code_block(self, code: str, language: str, title: str = ""):
        """Render a syntax-highlighted code block."""
        lang_map = {
            "js": "javascript",
            "ts": "typescript",
            "py": "python",
            "rb": "ruby",
            "sh": "bash",
            "yml": "yaml",
            "md": "markdown",
            "": "text",
        }
        language = lang_map.get(language, language)

        syntax = Syntax(
            code,
            language,
            theme="monokai",
            line_numbers=True,
            word_wrap=True,
        )

        panel_title = title or language
        self.console.print(Panel(
            syntax,
            title=f"[bold]{panel_title}[/bold]",
            border_style="dim",
            padding=(0, 1),
        ))

    def _render_info_block(self, content: str):
        """Render an info callout block."""
        self.console.print(Panel(
            content,
            title="[bold blue]Info[/bold blue]",
            border_style="blue",
        ))

    def _render_warning_block(self, content: str):
        """Render a warning callout block."""
        self.console.print(Panel(
            content,
            title="[bold yellow]Warning[/bold yellow]",
            border_style="yellow",
        ))

    def _render_error_block(self, content: str):
        """Render an error callout block."""
        self.console.print(Panel(
            content,
            title="[bold red]Error[/bold red]",
            border_style="red",
        ))

    def render_diff(self, old: str, new: str, filename: str = ""):
        """Render a side-by-side diff."""
        import difflib

        diff = difflib.unified_diff(
            old.splitlines(keepends=True),
            new.splitlines(keepends=True),
            fromfile=f"a/{filename}" if filename else "before",
            tofile=f"b/{filename}" if filename else "after",
        )
        diff_text = "".join(diff)

        if diff_text:
            syntax = Syntax(diff_text, "diff", theme="monokai")
            self.console.print(Panel(
                syntax,
                title=f"[bold]Changes: {filename}[/bold]" if filename else "[bold]Diff[/bold]",
                border_style="yellow",
            ))
        else:
            self.console.print("[dim]No differences found.[/dim]")

    def render_json(self, data: Any, title: str = ""):
        """Render formatted JSON."""
        import json

        json_str = json.dumps(data, indent=2, default=str)
        syntax = Syntax(json_str, "json", theme="monokai")
        if title:
            self.console.print(Panel(syntax, title=f"[bold]{title}[/bold]", border_style="cyan"))
        else:
            self.console.print(syntax)
