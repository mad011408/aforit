"""Color themes for the terminal UI."""

from __future__ import annotations

from rich.theme import Theme


THEMES: dict[str, dict[str, str]] = {
    "monokai": {
        "info": "bold cyan",
        "warning": "bold yellow",
        "error": "bold red",
        "success": "bold green",
        "prompt": "bold green",
        "response": "white",
        "code": "bright_green",
        "heading": "bold magenta",
        "dim": "dim white",
        "accent": "bold cyan",
        "highlight": "bold yellow on grey23",
    },
    "dracula": {
        "info": "bold #8be9fd",
        "warning": "bold #f1fa8c",
        "error": "bold #ff5555",
        "success": "bold #50fa7b",
        "prompt": "bold #bd93f9",
        "response": "#f8f8f2",
        "code": "#50fa7b",
        "heading": "bold #ff79c6",
        "dim": "dim #6272a4",
        "accent": "bold #bd93f9",
        "highlight": "bold #f1fa8c on #44475a",
    },
    "nord": {
        "info": "bold #88c0d0",
        "warning": "bold #ebcb8b",
        "error": "bold #bf616a",
        "success": "bold #a3be8c",
        "prompt": "bold #81a1c1",
        "response": "#d8dee9",
        "code": "#a3be8c",
        "heading": "bold #b48ead",
        "dim": "dim #4c566a",
        "accent": "bold #81a1c1",
        "highlight": "bold #ebcb8b on #3b4252",
    },
    "solarized": {
        "info": "bold #268bd2",
        "warning": "bold #b58900",
        "error": "bold #dc322f",
        "success": "bold #859900",
        "prompt": "bold #2aa198",
        "response": "#839496",
        "code": "#859900",
        "heading": "bold #6c71c4",
        "dim": "dim #586e75",
        "accent": "bold #2aa198",
        "highlight": "bold #b58900 on #073642",
    },
    "gruvbox": {
        "info": "bold #83a598",
        "warning": "bold #fabd2f",
        "error": "bold #fb4934",
        "success": "bold #b8bb26",
        "prompt": "bold #fe8019",
        "response": "#ebdbb2",
        "code": "#b8bb26",
        "heading": "bold #d3869b",
        "dim": "dim #928374",
        "accent": "bold #fe8019",
        "highlight": "bold #fabd2f on #3c3836",
    },
    "catppuccin": {
        "info": "bold #89dceb",
        "warning": "bold #f9e2af",
        "error": "bold #f38ba8",
        "success": "bold #a6e3a1",
        "prompt": "bold #cba6f7",
        "response": "#cdd6f4",
        "code": "#a6e3a1",
        "heading": "bold #f5c2e7",
        "dim": "dim #6c7086",
        "accent": "bold #cba6f7",
        "highlight": "bold #f9e2af on #313244",
    },
    "matrix": {
        "info": "bold bright_green",
        "warning": "bold yellow",
        "error": "bold red",
        "success": "bold bright_green",
        "prompt": "bold green",
        "response": "green",
        "code": "bright_green",
        "heading": "bold bright_green",
        "dim": "dim green",
        "accent": "bold bright_green",
        "highlight": "bold white on dark_green",
    },
    "minimal": {
        "info": "bold white",
        "warning": "bold white",
        "error": "bold white",
        "success": "bold white",
        "prompt": "bold white",
        "response": "white",
        "code": "white",
        "heading": "bold white",
        "dim": "dim white",
        "accent": "bold white",
        "highlight": "bold white",
    },
}


def get_theme(name: str) -> Theme:
    """Get a Rich Theme by name."""
    theme_data = THEMES.get(name, THEMES["monokai"])
    return Theme(theme_data)


def list_themes() -> list[str]:
    """List all available theme names."""
    return list(THEMES.keys())
