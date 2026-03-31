"""Rich terminal UI for the Aforit agent."""

from __future__ import annotations

import asyncio
from typing import Any

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table
from rich.text import Text
from rich.live import Live
from rich.spinner import Spinner
from rich.theme import Theme

from aforit.core.config import Config
from aforit.ui.themes import get_theme, THEMES


class TerminalUI:
    """Rich terminal interface for the AI agent."""

    def __init__(self, config: Config):
        self.config = config
        theme = get_theme(config.theme_name)
        self.console = Console(theme=theme)
        self._stream_buffer = ""
        self._live: Live | None = None

    def print_welcome(self):
        """Print the welcome banner."""
        banner = Text()
        banner.append("  ___  ", style="bold cyan")
        banner.append("  __            _ _   \n", style="bold cyan")
        banner.append(" / _ \\ ", style="bold cyan")
        banner.append(" / _| ___  _ __(_) |_ \n", style="bold cyan")
        banner.append("| |_| |", style="bold cyan")
        banner.append("| |_ / _ \\| '__| | __|\n", style="bold cyan")
        banner.append("|  _  |", style="bold cyan")
        banner.append("|  _| (_) | |  | | |_ \n", style="bold cyan")
        banner.append("|_| |_|", style="bold cyan")
        banner.append("|_|  \\___/|_|  |_|\\__|\n", style="bold cyan")

        self.console.print()
        self.console.print(Panel(
            banner,
            title="[bold white]Aforit Terminal AI Agent[/bold white]",
            subtitle=f"[dim]v1.0.0 | Model: {self.config.model_name}[/dim]",
            border_style="cyan",
            padding=(1, 2),
        ))
        self.console.print(
            "[dim]Type [bold]/help[/bold] for commands, "
            "[bold]/quit[/bold] to exit[/dim]\n"
        )

    def print_goodbye(self):
        """Print goodbye message."""
        self.console.print("\n[bold cyan]Session ended. Goodbye![/bold cyan]\n")

    async def get_input(self) -> str:
        """Get user input with a styled prompt."""
        try:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None, lambda: self.console.input("[bold green]> [/bold green]")
            )
            return result.strip()
        except EOFError:
            return "/quit"

    def print_stream(self, chunk: str):
        """Print a streaming chunk of the response."""
        self._stream_buffer += chunk
        self.console.print(chunk, end="", highlight=False)

    def print_stream_end(self):
        """End streaming output."""
        self.console.print()
        self._stream_buffer = ""

    def print_error(self, message: str):
        """Print an error message."""
        self.console.print(f"\n[bold red]Error:[/bold red] {message}\n")

    def print_info(self, message: str):
        """Print an info message."""
        self.console.print(f"[bold blue]Info:[/bold blue] {message}")

    def print_success(self, message: str):
        """Print a success message."""
        self.console.print(f"[bold green]Success:[/bold green] {message}")

    def print_warning(self, message: str):
        """Print a warning message."""
        self.console.print(f"[bold yellow]Warning:[/bold yellow] {message}")

    def print_code(self, code: str, language: str = "python"):
        """Print syntax-highlighted code."""
        syntax = Syntax(code, language, theme="monokai", line_numbers=True)
        self.console.print(syntax)

    def print_markdown(self, text: str):
        """Print rendered markdown."""
        md = Markdown(text)
        self.console.print(md)

    def print_help(self, tools: list[dict]):
        """Print help information."""
        self.console.print("\n[bold cyan]Available Commands:[/bold cyan]")
        commands = {
            "/help": "Show this help message",
            "/clear": "Clear conversation history",
            "/history": "Show conversation history",
            "/model": "Show current model",
            "/tools": "List available tools",
            "/memory": "Show memory status",
            "/export <file>": "Export session to file",
            "/theme <name>": "Change color theme",
            "/quit": "Exit the agent",
        }
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Command", style="cyan")
        table.add_column("Description")
        for cmd, desc in commands.items():
            table.add_row(cmd, desc)
        self.console.print(table)

    def print_tools(self, tools: list[dict]):
        """Print available tools."""
        self.console.print("\n[bold cyan]Available Tools:[/bold cyan]")
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Tool", style="cyan")
        table.add_column("Description")
        for tool in tools:
            table.add_row(tool["name"], tool["description"])
        self.console.print(table)

    def print_history(self, messages: list):
        """Print conversation history."""
        self.console.print("\n[bold cyan]Conversation History:[/bold cyan]")
        for msg in messages:
            role = msg.role
            style = {
                "user": "green",
                "assistant": "cyan",
                "system": "yellow",
                "tool": "magenta",
            }.get(role, "white")
            content = msg.content[:200]
            if len(msg.content) > 200:
                content += "..."
            self.console.print(f"[bold {style}]{role}:[/bold {style}] {content}")
        self.console.print()

    def set_theme(self, theme_name: str):
        """Switch the color theme."""
        if theme_name not in THEMES:
            self.print_error(f"Unknown theme: {theme_name}. Available: {', '.join(THEMES.keys())}")
            return
        theme = get_theme(theme_name)
        self.console = Console(theme=theme)
        self.print_success(f"Theme changed to: {theme_name}")

    def print_table(self, headers: list[str], rows: list[list[str]], title: str = ""):
        """Print a formatted table."""
        table = Table(title=title, show_header=True, header_style="bold magenta")
        for header in headers:
            table.add_column(header)
        for row in rows:
            table.add_row(*[str(v) for v in row])
        self.console.print(table)

    def print_panel(self, content: str, title: str = "", style: str = "cyan"):
        """Print content in a panel."""
        self.console.print(Panel(content, title=title, border_style=style))
