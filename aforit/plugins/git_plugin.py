"""Git plugin - provides Git repository operations as tools."""

from __future__ import annotations

import asyncio
from typing import Any

from aforit.core.registry import ToolRegistry
from aforit.plugins.loader import PluginBase
from aforit.tools.base import BaseTool, ToolResult


class GitTool(BaseTool):
    """Git operations tool."""

    name = "git"
    description = (
        "Perform Git operations: status, log, diff, commit, branch, "
        "checkout, stash, blame, and more."
    )
    parameters = {
        "action": {
            "type": "string",
            "enum": [
                "status", "log", "diff", "commit", "add", "branch",
                "checkout", "stash", "blame", "show", "remote", "pull",
                "push", "merge", "rebase", "tag", "cherry_pick",
            ],
            "description": "Git operation to perform",
        },
        "args": {
            "type": "string",
            "description": "Additional arguments for the git command",
        },
        "cwd": {
            "type": "string",
            "description": "Repository path (defaults to current directory)",
        },
        "message": {
            "type": "string",
            "description": "Commit message (for commit action)",
        },
    }
    required_params = ["action"]
    timeout = 30.0

    async def execute(
        self,
        action: str,
        args: str = "",
        cwd: str = ".",
        message: str = "",
        **kwargs,
    ) -> ToolResult:
        """Execute a git operation."""
        command_map = {
            "status": f"git status {args}".strip(),
            "log": f"git log --oneline -20 {args}".strip(),
            "diff": f"git diff {args}".strip(),
            "commit": f"git commit -m '{message}' {args}".strip() if message else "git commit",
            "add": f"git add {args or '.'}".strip(),
            "branch": f"git branch {args}".strip(),
            "checkout": f"git checkout {args}".strip(),
            "stash": f"git stash {args}".strip(),
            "blame": f"git blame {args}".strip(),
            "show": f"git show {args}".strip(),
            "remote": f"git remote -v {args}".strip(),
            "pull": f"git pull {args}".strip(),
            "push": f"git push {args}".strip(),
            "merge": f"git merge {args}".strip(),
            "rebase": f"git rebase {args}".strip(),
            "tag": f"git tag {args}".strip(),
            "cherry_pick": f"git cherry-pick {args}".strip(),
        }

        cmd = command_map.get(action)
        if not cmd:
            return ToolResult(success=False, output="", error=f"Unknown git action: {action}")

        try:
            process = await asyncio.create_subprocess_shell(
                cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=cwd,
            )
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=25.0)

            output = stdout.decode("utf-8", errors="replace")
            err = stderr.decode("utf-8", errors="replace")

            # Git sometimes writes to stderr for non-error info
            if process.returncode == 0:
                full_output = output
                if err and "warning" not in err.lower():
                    full_output += f"\n{err}"
                return ToolResult(success=True, output=full_output.strip())
            else:
                return ToolResult(
                    success=False,
                    output=output.strip(),
                    error=err.strip(),
                )
        except asyncio.TimeoutError:
            return ToolResult(success=False, output="", error=f"Git command timed out: {cmd}")
        except Exception as e:
            return ToolResult(success=False, output="", error=str(e))


class GitPlugin(PluginBase):
    """Plugin that adds Git tools to the agent."""

    name = "git"
    version = "1.0.0"
    description = "Git repository operations"

    def on_load(self, registry: ToolRegistry):
        registry.register(GitTool())
