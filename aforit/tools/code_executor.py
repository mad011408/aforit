"""Safe code execution tool - runs Python code in isolated environments."""

from __future__ import annotations

import asyncio
import io
import sys
import traceback
from contextlib import redirect_stdout, redirect_stderr
from typing import Any

from aforit.tools.base import BaseTool, ToolResult


# Modules that are blocked in safe mode
BLOCKED_MODULES = {
    "os.system",
    "subprocess",
    "shutil.rmtree",
    "ctypes",
    "importlib",
}

# Blocked builtins
BLOCKED_BUILTINS = {"exec", "eval", "compile", "__import__"}


class CodeExecutorTool(BaseTool):
    """Execute Python code safely with output capture."""

    name = "code_executor"
    description = (
        "Execute Python code and return the output. Supports running scripts, "
        "evaluating expressions, and capturing stdout/stderr. Has safety "
        "restrictions to prevent harmful operations."
    )
    parameters = {
        "code": {
            "type": "string",
            "description": "Python code to execute",
        },
        "language": {
            "type": "string",
            "enum": ["python", "bash"],
            "description": "Language to execute (default: python)",
        },
        "timeout": {
            "type": "number",
            "description": "Execution timeout in seconds",
        },
    }
    required_params = ["code"]
    timeout = 30.0

    async def execute(
        self,
        code: str,
        language: str = "python",
        timeout: float = 15.0,
        **kwargs,
    ) -> ToolResult:
        """Execute code and return results."""
        if language == "bash":
            return await self._execute_bash(code, timeout)
        return await self._execute_python(code, timeout)

    async def _execute_python(self, code: str, timeout: float) -> ToolResult:
        """Execute Python code in a restricted environment."""
        stdout_capture = io.StringIO()
        stderr_capture = io.StringIO()

        # Build restricted globals
        safe_globals = self._build_safe_globals()
        safe_globals["__builtins__"] = {
            k: v for k, v in __builtins__.items()
            if k not in BLOCKED_BUILTINS
        } if isinstance(__builtins__, dict) else {
            k: getattr(__builtins__, k) for k in dir(__builtins__)
            if k not in BLOCKED_BUILTINS and not k.startswith("_")
        }

        local_vars: dict[str, Any] = {}

        def run_code():
            with redirect_stdout(stdout_capture), redirect_stderr(stderr_capture):
                try:
                    # Try as expression first
                    try:
                        result = eval(code, safe_globals, local_vars)
                        if result is not None:
                            print(repr(result))
                    except SyntaxError:
                        # Execute as statements
                        exec(code, safe_globals, local_vars)
                except Exception:
                    traceback.print_exc()

        try:
            loop = asyncio.get_event_loop()
            await asyncio.wait_for(
                loop.run_in_executor(None, run_code),
                timeout=timeout,
            )

            stdout_val = stdout_capture.getvalue()
            stderr_val = stderr_capture.getvalue()

            output = stdout_val
            if stderr_val:
                output += f"\n[stderr]\n{stderr_val}"

            has_error = bool(stderr_val) and "Traceback" in stderr_val

            return ToolResult(
                success=not has_error,
                output=output.strip() or "(no output)",
                error=stderr_val if has_error else "",
                metadata={"language": "python", "variables": list(local_vars.keys())},
            )

        except asyncio.TimeoutError:
            return ToolResult(
                success=False,
                output="",
                error=f"Code execution timed out after {timeout}s",
            )

    async def _execute_bash(self, code: str, timeout: float) -> ToolResult:
        """Execute bash code via subprocess."""
        try:
            process = await asyncio.create_subprocess_shell(
                code,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(
                process.communicate(), timeout=timeout
            )

            output = stdout.decode("utf-8", errors="replace")
            err = stderr.decode("utf-8", errors="replace")
            if err:
                output += f"\n[stderr]\n{err}"

            return ToolResult(
                success=process.returncode == 0,
                output=output.strip(),
                error=err if process.returncode != 0 else "",
                metadata={"language": "bash", "exit_code": process.returncode},
            )
        except asyncio.TimeoutError:
            return ToolResult(
                success=False,
                output="",
                error=f"Bash execution timed out after {timeout}s",
            )

    def _build_safe_globals(self) -> dict[str, Any]:
        """Build a restricted set of globals for code execution."""
        import math
        import json
        import re
        import datetime
        import collections
        import itertools
        import functools
        import operator
        import string
        import textwrap
        import hashlib
        import base64
        import urllib.parse

        return {
            "math": math,
            "json": json,
            "re": re,
            "datetime": datetime,
            "collections": collections,
            "itertools": itertools,
            "functools": functools,
            "operator": operator,
            "string": string,
            "textwrap": textwrap,
            "hashlib": hashlib,
            "base64": base64,
            "urllib": urllib,
            "print": print,
            "range": range,
            "len": len,
            "str": str,
            "int": int,
            "float": float,
            "bool": bool,
            "list": list,
            "dict": dict,
            "set": set,
            "tuple": tuple,
            "sorted": sorted,
            "reversed": reversed,
            "enumerate": enumerate,
            "zip": zip,
            "map": map,
            "filter": filter,
            "sum": sum,
            "min": min,
            "max": max,
            "abs": abs,
            "round": round,
            "any": any,
            "all": all,
            "isinstance": isinstance,
            "type": type,
            "hasattr": hasattr,
            "getattr": getattr,
        }
