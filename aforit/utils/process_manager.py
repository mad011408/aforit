"""Process manager - manage background processes and daemons."""

from __future__ import annotations

import asyncio
import os
import signal
import time
from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass
class ProcessInfo:
    """Information about a managed process."""

    pid: int
    name: str
    command: str
    started_at: float = field(default_factory=time.time)
    process: asyncio.subprocess.Process | None = None
    status: str = "running"  # running, stopped, failed
    exit_code: int | None = None
    stdout_lines: list[str] = field(default_factory=list)
    stderr_lines: list[str] = field(default_factory=list)

    @property
    def uptime(self) -> float:
        return time.time() - self.started_at

    @property
    def is_running(self) -> bool:
        return self.status == "running" and self.process is not None and self.process.returncode is None


class ProcessManager:
    """Manage background processes spawned by the agent."""

    def __init__(self, max_processes: int = 10):
        self.max_processes = max_processes
        self._processes: dict[str, ProcessInfo] = {}
        self._counter = 0

    async def spawn(
        self,
        name: str,
        command: str,
        cwd: str | None = None,
        env: dict[str, str] | None = None,
        capture_output: bool = True,
    ) -> ProcessInfo:
        """Spawn a new background process."""
        if len(self._active_processes) >= self.max_processes:
            raise RuntimeError(f"Max processes ({self.max_processes}) reached")

        cmd_env = os.environ.copy()
        if env:
            cmd_env.update(env)

        process = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE if capture_output else None,
            stderr=asyncio.subprocess.PIPE if capture_output else None,
            cwd=cwd,
            env=cmd_env,
        )

        self._counter += 1
        proc_id = f"proc_{self._counter}"

        info = ProcessInfo(
            pid=process.pid,
            name=name,
            command=command,
            process=process,
        )
        self._processes[proc_id] = info

        # Start output capture in background
        if capture_output:
            asyncio.create_task(self._capture_output(proc_id, info))

        return info

    async def _capture_output(self, proc_id: str, info: ProcessInfo):
        """Capture stdout/stderr in the background."""
        if not info.process:
            return

        async def read_stream(stream, lines: list[str]):
            if stream:
                while True:
                    line = await stream.readline()
                    if not line:
                        break
                    lines.append(line.decode("utf-8", errors="replace").rstrip())
                    # Keep buffer bounded
                    if len(lines) > 1000:
                        lines[:] = lines[-500:]

        await asyncio.gather(
            read_stream(info.process.stdout, info.stdout_lines),
            read_stream(info.process.stderr, info.stderr_lines),
        )

        info.exit_code = info.process.returncode
        info.status = "stopped" if info.exit_code == 0 else "failed"

    async def stop(self, proc_id: str, force: bool = False) -> bool:
        """Stop a running process."""
        info = self._processes.get(proc_id)
        if not info or not info.process:
            return False

        if info.is_running:
            if force:
                info.process.kill()
            else:
                info.process.terminate()

            try:
                await asyncio.wait_for(info.process.wait(), timeout=5.0)
            except asyncio.TimeoutError:
                info.process.kill()
                await info.process.wait()

            info.exit_code = info.process.returncode
            info.status = "stopped"
            return True
        return False

    async def stop_all(self):
        """Stop all running processes."""
        for proc_id in list(self._processes.keys()):
            await self.stop(proc_id)

    def get_info(self, proc_id: str) -> ProcessInfo | None:
        return self._processes.get(proc_id)

    def list_processes(self) -> list[dict[str, Any]]:
        """List all processes with their status."""
        result = []
        for proc_id, info in self._processes.items():
            result.append({
                "id": proc_id,
                "name": info.name,
                "pid": info.pid,
                "command": info.command,
                "status": info.status,
                "uptime": f"{info.uptime:.1f}s",
                "exit_code": info.exit_code,
            })
        return result

    def get_output(self, proc_id: str, tail: int = 50) -> dict[str, list[str]]:
        """Get recent output from a process."""
        info = self._processes.get(proc_id)
        if not info:
            return {"stdout": [], "stderr": []}
        return {
            "stdout": info.stdout_lines[-tail:],
            "stderr": info.stderr_lines[-tail:],
        }

    @property
    def _active_processes(self) -> list[ProcessInfo]:
        return [p for p in self._processes.values() if p.is_running]
