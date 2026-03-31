"""Tool registry - manages tool registration and execution."""

from __future__ import annotations

import asyncio
from typing import Any

from aforit.tools.base import BaseTool, ToolResult


class ToolRegistry:
    """Central registry for all available tools."""

    def __init__(self):
        self._tools: dict[str, BaseTool] = {}

    def register(self, tool: BaseTool):
        """Register a tool instance."""
        self._tools[tool.name] = tool

    def unregister(self, name: str) -> bool:
        """Remove a tool from the registry."""
        if name in self._tools:
            del self._tools[name]
            return True
        return False

    def get(self, name: str) -> BaseTool | None:
        """Get a tool by name."""
        return self._tools.get(name)

    def list_tools(self) -> list[dict[str, Any]]:
        """List all registered tools with their descriptions."""
        return [
            {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.parameters,
            }
            for tool in self._tools.values()
        ]

    def get_tool_schemas(self) -> list[dict[str, Any]]:
        """Get tool schemas in OpenAI function-calling format."""
        schemas = []
        for tool in self._tools.values():
            schemas.append({
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": {
                        "type": "object",
                        "properties": tool.parameters,
                        "required": tool.required_params,
                    },
                },
            })
        return schemas

    async def execute(self, name: str, arguments: dict[str, Any]) -> ToolResult:
        """Execute a tool by name with given arguments."""
        tool = self._tools.get(name)
        if not tool:
            return ToolResult(
                success=False,
                output="",
                error=f"Tool '{name}' not found. Available: {list(self._tools.keys())}",
            )

        try:
            # Validate arguments
            validation_error = tool.validate(arguments)
            if validation_error:
                return ToolResult(success=False, output="", error=validation_error)

            # Execute with timeout
            result = await asyncio.wait_for(
                tool.execute(**arguments),
                timeout=tool.timeout,
            )
            return result

        except asyncio.TimeoutError:
            return ToolResult(
                success=False,
                output="",
                error=f"Tool '{name}' timed out after {tool.timeout}s",
            )
        except Exception as e:
            return ToolResult(
                success=False,
                output="",
                error=f"Tool '{name}' failed: {type(e).__name__}: {str(e)}",
            )

    @property
    def count(self) -> int:
        return len(self._tools)
