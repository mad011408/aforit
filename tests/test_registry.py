"""Tests for the Tool Registry."""

import pytest

from aforit.core.registry import ToolRegistry
from aforit.tools.base import BaseTool, ToolResult


class MockTool(BaseTool):
    name = "mock_tool"
    description = "A mock tool for testing"
    parameters = {"input": {"type": "string", "description": "Test input"}}
    required_params = ["input"]

    async def execute(self, input: str = "", **kwargs) -> ToolResult:
        return ToolResult(success=True, output=f"Processed: {input}")


class FailingTool(BaseTool):
    name = "failing_tool"
    description = "A tool that always fails"
    parameters = {}
    required_params = []

    async def execute(self, **kwargs) -> ToolResult:
        raise RuntimeError("Intentional failure")


class TestToolRegistry:
    def test_register_and_get(self):
        registry = ToolRegistry()
        tool = MockTool()
        registry.register(tool)
        assert registry.get("mock_tool") is tool
        assert registry.count == 1

    def test_unregister(self):
        registry = ToolRegistry()
        registry.register(MockTool())
        assert registry.unregister("mock_tool") is True
        assert registry.get("mock_tool") is None

    def test_list_tools(self):
        registry = ToolRegistry()
        registry.register(MockTool())
        tools = registry.list_tools()
        assert len(tools) == 1
        assert tools[0]["name"] == "mock_tool"

    def test_get_tool_schemas(self):
        registry = ToolRegistry()
        registry.register(MockTool())
        schemas = registry.get_tool_schemas()
        assert len(schemas) == 1
        assert schemas[0]["type"] == "function"
        assert schemas[0]["function"]["name"] == "mock_tool"

    @pytest.mark.asyncio
    async def test_execute(self):
        registry = ToolRegistry()
        registry.register(MockTool())
        result = await registry.execute("mock_tool", {"input": "hello"})
        assert result.success is True
        assert result.output == "Processed: hello"

    @pytest.mark.asyncio
    async def test_execute_unknown_tool(self):
        registry = ToolRegistry()
        result = await registry.execute("nonexistent", {})
        assert result.success is False
        assert "not found" in result.error

    @pytest.mark.asyncio
    async def test_execute_failing_tool(self):
        registry = ToolRegistry()
        registry.register(FailingTool())
        result = await registry.execute("failing_tool", {})
        assert result.success is False
        assert "RuntimeError" in result.error

    @pytest.mark.asyncio
    async def test_execute_missing_params(self):
        registry = ToolRegistry()
        registry.register(MockTool())
        result = await registry.execute("mock_tool", {})
        assert result.success is False
        assert "Missing required parameter" in result.error
