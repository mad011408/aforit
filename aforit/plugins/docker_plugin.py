"""Docker plugin - manage Docker containers and images."""

from __future__ import annotations

import asyncio
import json
from typing import Any

from aforit.core.registry import ToolRegistry
from aforit.plugins.loader import PluginBase
from aforit.tools.base import BaseTool, ToolResult


class DockerTool(BaseTool):
    """Docker management tool."""

    name = "docker"
    description = (
        "Manage Docker containers and images. List, start, stop, remove "
        "containers; build, pull, push images; view logs and inspect."
    )
    parameters = {
        "action": {
            "type": "string",
            "enum": [
                "ps", "images", "run", "stop", "start", "rm", "rmi",
                "logs", "inspect", "build", "pull", "exec", "stats",
                "compose_up", "compose_down", "compose_ps",
            ],
            "description": "Docker operation to perform",
        },
        "target": {
            "type": "string",
            "description": "Container ID, image name, or service name",
        },
        "args": {
            "type": "string",
            "description": "Additional arguments",
        },
    }
    required_params = ["action"]
    timeout = 60.0

    async def execute(
        self,
        action: str,
        target: str = "",
        args: str = "",
        **kwargs,
    ) -> ToolResult:
        """Execute a Docker operation."""
        command_map = {
            "ps": f"docker ps --format 'table {{{{.ID}}}}\\t{{{{.Names}}}}\\t{{{{.Status}}}}\\t{{{{.Ports}}}}' {args}",
            "images": f"docker images --format 'table {{{{.Repository}}}}\\t{{{{.Tag}}}}\\t{{{{.Size}}}}' {args}",
            "run": f"docker run -d {args} {target}",
            "stop": f"docker stop {target} {args}",
            "start": f"docker start {target} {args}",
            "rm": f"docker rm {target} {args}",
            "rmi": f"docker rmi {target} {args}",
            "logs": f"docker logs --tail 50 {target} {args}",
            "inspect": f"docker inspect {target}",
            "build": f"docker build {args} {target}",
            "pull": f"docker pull {target}",
            "exec": f"docker exec {target} {args}",
            "stats": f"docker stats --no-stream --format 'table {{{{.Name}}}}\\t{{{{.CPUPerc}}}}\\t{{{{.MemUsage}}}}' {args}",
            "compose_up": f"docker compose up -d {args}",
            "compose_down": f"docker compose down {args}",
            "compose_ps": f"docker compose ps {args}",
        }

        cmd = command_map.get(action)
        if not cmd:
            return ToolResult(success=False, output="", error=f"Unknown docker action: {action}")

        try:
            process = await asyncio.create_subprocess_shell(
                cmd.strip(),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=55.0)

            output = stdout.decode("utf-8", errors="replace")
            err = stderr.decode("utf-8", errors="replace")

            if process.returncode == 0:
                return ToolResult(success=True, output=output.strip())
            else:
                return ToolResult(success=False, output=output.strip(), error=err.strip())

        except asyncio.TimeoutError:
            return ToolResult(success=False, output="", error="Docker command timed out")
        except Exception as e:
            return ToolResult(success=False, output="", error=str(e))


class DockerPlugin(PluginBase):
    """Plugin that adds Docker management tools."""

    name = "docker"
    version = "1.0.0"
    description = "Docker container and image management"

    def on_load(self, registry: ToolRegistry):
        registry.register(DockerTool())
