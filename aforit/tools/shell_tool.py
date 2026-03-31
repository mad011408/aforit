"""Shell command execution tool with safety controls."""

from __future__ import annotations

import asyncio
import os
import shlex
from typing import Any

from aforit.tools.base import BaseTool, ToolResult


# Commands that are always blocked
BLOCKED_COMMANDS = {
    "rm -rf /",
    "rm -rf /*",
    "mkfs",
    "dd if=/dev/zero",
    ":(){ :|:& };:",
    "chmod -R 777 /",
    "shutdown",
    "reboot",
    "halt",
    "init 0",
    "init 6",
}

# Patterns that trigger a warning
DANGEROUS_PATTERNS = [
    "rm -rf",
    "sudo rm",
    "chmod 777",
    "> /dev/sd",
    "format c:",
    "del /f /s /q",
    "DROP TABLE",
    "DROP DATABASE",
    "DELETE FROM",
    "TRUNCATE",
]


class ShellTool(BaseTool):
    """Execute shell commands with safety controls."""

    name = "shell"
    description = (
        "Execute shell commands. Supports running commands, capturing output, "
        "and piping. Has safety checks to prevent destructive operations."
    )
    parameters = {
        "command": {
            "type": "string",
            "description": "The shell command to execute",
        },
        "cwd": {
            "type": "string",
            "description": "Working directory for the command",
        },
        "timeout": {
            "type": "number",
            "description": "Timeout in seconds (default: 30)",
        },
        "env": {
            "type": "object",
            "description": "Additional environment variables",
        },
    }
    required_params = ["command"]
    timeout = 60.0

    def __init__(self, safe_mode: bool = True):
        self.safe_mode = safe_mode

    async def execute(
        self,
        command: str,
        cwd: str | None = None,
        timeout: float = 30.0,
        env: dict[str, str] | None = None,
        **kwargs,
    ) -> ToolResult:
        """Execute a shell command."""
        # Safety checks
        if self.safe_mode:
            safety_check = self._check_safety(command)
            if safety_check:
                return ToolResult(
                    success=False,
                    output="",
                    error=f"Command blocked by safety check: {safety_check}",
                )

        # Prepare environment
        cmd_env = os.environ.copy()
        if env:
            cmd_env.update(env)

        try:
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=cwd,
                env=cmd_env,
            )

            stdout, stderr = await asyncio.wait_for(
                process.communicate(), timeout=timeout
            )

            stdout_str = stdout.decode("utf-8", errors="replace")
            stderr_str = stderr.decode("utf-8", errors="replace")

            output = stdout_str
            if stderr_str:
                output += f"\n[stderr]\n{stderr_str}"

            return ToolResult(
                success=process.returncode == 0,
                output=output.strip(),
                error=stderr_str if process.returncode != 0 else "",
                metadata={
                    "exit_code": process.returncode,
                    "command": command,
                },
            )

        except asyncio.TimeoutError:
            return ToolResult(
                success=False,
                output="",
                error=f"Command timed out after {timeout}s: {command}",
            )
        except Exception as e:
            return ToolResult(
                success=False,
                output="",
                error=f"Command failed: {str(e)}",
            )

    def _check_safety(self, command: str) -> str | None:
        """Check if a command is safe to execute. Returns error message or None."""
        cmd_lower = command.lower().strip()

        # Check blocked commands
        for blocked in BLOCKED_COMMANDS:
            if blocked in cmd_lower:
                return f"Blocked dangerous command: {blocked}"

        # Check dangerous patterns
        for pattern in DANGEROUS_PATTERNS:
            if pattern.lower() in cmd_lower:
                return f"Potentially dangerous pattern detected: {pattern}"

        return None
