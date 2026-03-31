"""Reusable UI components - spinners, progress bars, prompts."""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator

from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.progress import (
    Progress,
    SpinnerColumn,
    TextColumn,
    BarColumn,
    TaskProgressColumn,
    TimeRemainingColumn,
)
from rich.spinner import Spinner
from rich.table import Table
from rich.text import Text


class SpinnerContext:
    """A context manager that shows a spinner while work is being done."""

    def __init__(self, console: Console, message: str = "Working...", style: str = "cyan"):
        self.console = console
        self.message = message
        self.style = style
        self._live: Live | None = None

    async def __aenter__(self):
        spinner = Spinner("dots", text=Text(self.message, style=self.style))
        self._live = Live(spinner, console=self.console, refresh_per_second=10)
        self._live.__enter__()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._live:
            self._live.__exit__(exc_type, exc_val, exc_tb)

    def update(self, message: str):
        """Update the spinner message."""
        if self._live:
            spinner = Spinner("dots", text=Text(message, style=self.style))
            self._live.update(spinner)


class ProgressTracker:
    """Track progress of multi-step operations."""

    def __init__(self, console: Console):
        self.console = console
        self.progress = Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            TimeRemainingColumn(),
            console=console,
        )

    def __enter__(self):
        self.progress.__enter__()
        return self

    def __exit__(self, *args):
        self.progress.__exit__(*args)

    def add_task(self, description: str, total: int = 100) -> int:
        """Add a new task to track."""
        return self.progress.add_task(description, total=total)

    def update(self, task_id: int, advance: int = 1, description: str = ""):
        """Update task progress."""
        kwargs: dict[str, Any] = {"advance": advance}
        if description:
            kwargs["description"] = description
        self.progress.update(task_id, **kwargs)

    def complete(self, task_id: int):
        """Mark a task as complete."""
        self.progress.update(task_id, completed=self.progress.tasks[task_id].total)


class SelectionMenu:
    """Interactive selection menu."""

    def __init__(self, console: Console, title: str = "Select an option"):
        self.console = console
        self.title = title
        self.options: list[dict[str, Any]] = []

    def add_option(self, label: str, value: Any = None, description: str = ""):
        """Add an option to the menu."""
        self.options.append({
            "label": label,
            "value": value or label,
            "description": description,
        })

    def show(self) -> Any:
        """Display the menu and get user selection."""
        self.console.print(f"\n[bold cyan]{self.title}[/bold cyan]")

        table = Table(show_header=False, box=None, padding=(0, 2))
        table.add_column("Num", style="bold yellow", width=4)
        table.add_column("Option", style="cyan")
        table.add_column("Description", style="dim")

        for i, opt in enumerate(self.options, 1):
            table.add_row(str(i), opt["label"], opt["description"])

        self.console.print(table)

        while True:
            try:
                choice = self.console.input("\n[bold green]Choice: [/bold green]")
                idx = int(choice) - 1
                if 0 <= idx < len(self.options):
                    return self.options[idx]["value"]
                self.console.print("[red]Invalid choice. Try again.[/red]")
            except (ValueError, EOFError):
                self.console.print("[red]Enter a number.[/red]")


class ConfirmPrompt:
    """Yes/No confirmation prompt."""

    def __init__(self, console: Console, message: str, default: bool = False):
        self.console = console
        self.message = message
        self.default = default

    def ask(self) -> bool:
        """Show the prompt and get a response."""
        default_hint = "[Y/n]" if self.default else "[y/N]"
        try:
            response = self.console.input(
                f"[bold yellow]{self.message}[/bold yellow] {default_hint} "
            )
            if not response:
                return self.default
            return response.lower().startswith("y")
        except EOFError:
            return self.default


class StatusBar:
    """A status bar that shows at the bottom of output."""

    def __init__(self, console: Console):
        self.console = console
        self._items: dict[str, str] = {}

    def set(self, key: str, value: str):
        """Set a status bar item."""
        self._items[key] = value

    def remove(self, key: str):
        """Remove a status bar item."""
        self._items.pop(key, None)

    def render(self) -> Text:
        """Render the status bar."""
        text = Text()
        for i, (key, value) in enumerate(self._items.items()):
            if i > 0:
                text.append(" | ", style="dim")
            text.append(f"{key}: ", style="bold dim")
            text.append(value, style="dim")
        return text

    def print(self):
        """Print the status bar."""
        self.console.print(self.render())
