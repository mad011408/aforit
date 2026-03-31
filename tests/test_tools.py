"""Tests for built-in tools."""

import os
import pytest
from pathlib import Path

from aforit.tools.file_manager import FileManagerTool
from aforit.tools.shell_tool import ShellTool
from aforit.tools.code_executor import CodeExecutorTool


class TestFileManagerTool:
    @pytest.fixture
    def tool(self):
        return FileManagerTool()

    @pytest.mark.asyncio
    async def test_write_and_read(self, tool, tmp_path):
        test_file = str(tmp_path / "test.txt")
        result = await tool.execute(action="write", path=test_file, content="Hello World")
        assert result.success is True

        result = await tool.execute(action="read", path=test_file)
        assert result.success is True
        assert "Hello World" in result.output

    @pytest.mark.asyncio
    async def test_list_directory(self, tool, tmp_path):
        (tmp_path / "file1.txt").write_text("a")
        (tmp_path / "file2.txt").write_text("b")
        result = await tool.execute(action="list", path=str(tmp_path))
        assert result.success is True
        assert "file1.txt" in result.output
        assert "file2.txt" in result.output

    @pytest.mark.asyncio
    async def test_search(self, tool, tmp_path):
        test_file = tmp_path / "search_test.py"
        test_file.write_text("def hello_world():\n    print('hello')\n")
        result = await tool.execute(action="search", path=str(test_file), pattern="hello")
        assert result.success is True
        assert "hello" in result.output

    @pytest.mark.asyncio
    async def test_info(self, tool, tmp_path):
        test_file = tmp_path / "info_test.txt"
        test_file.write_text("content")
        result = await tool.execute(action="info", path=str(test_file))
        assert result.success is True
        assert "file" in result.output

    @pytest.mark.asyncio
    async def test_mkdir(self, tool, tmp_path):
        new_dir = str(tmp_path / "new" / "nested" / "dir")
        result = await tool.execute(action="mkdir", path=new_dir)
        assert result.success is True
        assert Path(new_dir).exists()

    @pytest.mark.asyncio
    async def test_read_nonexistent(self, tool):
        result = await tool.execute(action="read", path="/nonexistent/file.txt")
        assert result.success is False


class TestShellTool:
    @pytest.fixture
    def tool(self):
        return ShellTool(safe_mode=True)

    @pytest.mark.asyncio
    async def test_simple_command(self, tool):
        result = await tool.execute(command="echo 'hello'")
        assert result.success is True
        assert "hello" in result.output

    @pytest.mark.asyncio
    async def test_blocked_command(self, tool):
        result = await tool.execute(command="rm -rf /")
        assert result.success is False
        assert "blocked" in result.error.lower() or "safety" in result.error.lower()

    @pytest.mark.asyncio
    async def test_cwd(self, tool, tmp_path):
        result = await tool.execute(command="pwd", cwd=str(tmp_path))
        assert result.success is True
        assert str(tmp_path) in result.output


class TestCodeExecutorTool:
    @pytest.fixture
    def tool(self):
        return CodeExecutorTool()

    @pytest.mark.asyncio
    async def test_simple_expression(self, tool):
        result = await tool.execute(code="2 + 2")
        assert result.success is True
        assert "4" in result.output

    @pytest.mark.asyncio
    async def test_print_output(self, tool):
        result = await tool.execute(code="print('Hello from code executor')")
        assert result.success is True
        assert "Hello from code executor" in result.output

    @pytest.mark.asyncio
    async def test_multi_line(self, tool):
        code = "x = [1, 2, 3]\nprint(sum(x))"
        result = await tool.execute(code=code)
        assert result.success is True
        assert "6" in result.output

    @pytest.mark.asyncio
    async def test_error_handling(self, tool):
        result = await tool.execute(code="1/0")
        assert "ZeroDivisionError" in result.output or "ZeroDivisionError" in result.error
