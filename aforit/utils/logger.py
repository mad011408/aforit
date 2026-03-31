"""Colored logging with Rich integration."""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.logging import RichHandler
from rich.text import Text


# Global log directory
LOG_DIR = Path.home() / ".aforit" / "logs"


class AgentLogger:
    """Configurable logger with rich terminal output and file logging."""

    def __init__(
        self,
        name: str = "aforit",
        level: str = "INFO",
        log_file: bool = True,
        console: Console | None = None,
    ):
        self.name = name
        self.logger = logging.getLogger(name)
        self.logger.setLevel(getattr(logging, level.upper(), logging.INFO))
        self.logger.handlers.clear()

        # Rich console handler
        console = console or Console(stderr=True)
        rich_handler = RichHandler(
            console=console,
            show_time=True,
            show_path=False,
            markup=True,
            rich_tracebacks=True,
            tracebacks_show_locals=True,
        )
        rich_handler.setLevel(getattr(logging, level.upper(), logging.INFO))
        self.logger.addHandler(rich_handler)

        # File handler
        if log_file:
            LOG_DIR.mkdir(parents=True, exist_ok=True)
            file_handler = logging.FileHandler(LOG_DIR / f"{name}.log")
            file_handler.setLevel(logging.DEBUG)
            file_formatter = logging.Formatter(
                "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
            file_handler.setFormatter(file_formatter)
            self.logger.addHandler(file_handler)

    def debug(self, msg: str, **kwargs):
        self.logger.debug(msg, **kwargs)

    def info(self, msg: str, **kwargs):
        self.logger.info(msg, **kwargs)

    def warning(self, msg: str, **kwargs):
        self.logger.warning(msg, **kwargs)

    def error(self, msg: str, **kwargs):
        self.logger.error(msg, **kwargs)

    def critical(self, msg: str, **kwargs):
        self.logger.critical(msg, **kwargs)

    def exception(self, msg: str, **kwargs):
        self.logger.exception(msg, **kwargs)

    def set_level(self, level: str):
        self.logger.setLevel(getattr(logging, level.upper(), logging.INFO))


# Module-level convenience instance
_default_logger: AgentLogger | None = None


def get_logger(name: str = "aforit", level: str = "INFO") -> AgentLogger:
    """Get or create a logger instance."""
    global _default_logger
    if _default_logger is None or _default_logger.name != name:
        _default_logger = AgentLogger(name=name, level=level)
    return _default_logger
