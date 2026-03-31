"""Base tool interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ToolResult:
    """Result from a tool execution."""

    success: bool
    output: str
    error: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


class BaseTool(ABC):
    """Abstract base class for all tools."""

    name: str = "base_tool"
    description: str = "Base tool"
    parameters: dict[str, Any] = {}
    required_params: list[str] = []
    timeout: float = 30.0

    def validate(self, arguments: dict[str, Any]) -> str | None:
        """Validate arguments. Returns error string or None if valid."""
        for param in self.required_params:
            if param not in arguments:
                return f"Missing required parameter: {param}"
        return None

    @abstractmethod
    async def execute(self, **kwargs) -> ToolResult:
        """Execute the tool with given arguments."""
        ...

    def get_schema(self) -> dict[str, Any]:
        """Get the tool schema for LLM function calling."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": self.parameters,
                    "required": self.required_params,
                },
            },
        }
