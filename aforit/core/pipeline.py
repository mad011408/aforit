"""Processing pipeline - chain multiple operations together."""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Coroutine

import yaml

from aforit.core.config import Config


@dataclass
class PipelineStep:
    """A single step in a processing pipeline."""

    name: str
    action: str
    params: dict[str, Any] = field(default_factory=dict)
    on_error: str = "stop"  # stop, skip, retry
    max_retries: int = 2
    timeout: float = 60.0
    depends_on: list[str] = field(default_factory=list)


@dataclass
class PipelineResult:
    """Result of a pipeline execution."""

    step_name: str
    success: bool
    output: Any = None
    error: str | None = None
    duration: float = 0.0


class PipelineExecutor:
    """Execute multi-step processing pipelines."""

    def __init__(self, config: Config):
        self.config = config
        self._action_handlers: dict[str, Callable] = {}
        self._register_builtin_actions()

    def _register_builtin_actions(self):
        """Register built-in pipeline actions."""
        self._action_handlers.update({
            "llm_query": self._action_llm_query,
            "file_read": self._action_file_read,
            "file_write": self._action_file_write,
            "shell": self._action_shell,
            "transform": self._action_transform,
            "filter": self._action_filter,
            "aggregate": self._action_aggregate,
            "parallel": self._action_parallel,
        })

    def register_action(self, name: str, handler: Callable):
        """Register a custom pipeline action."""
        self._action_handlers[name] = handler

    async def run_from_file(self, path: str | Path) -> list[PipelineResult]:
        """Load and execute a pipeline from a YAML file."""
        path = Path(path)
        with open(path) as f:
            pipeline_def = yaml.safe_load(f)

        steps = [
            PipelineStep(
                name=step["name"],
                action=step["action"],
                params=step.get("params", {}),
                on_error=step.get("on_error", "stop"),
                max_retries=step.get("max_retries", 2),
                timeout=step.get("timeout", 60.0),
                depends_on=step.get("depends_on", []),
            )
            for step in pipeline_def.get("steps", [])
        ]

        return await self.execute(steps, pipeline_def.get("context", {}))

    async def execute(
        self, steps: list[PipelineStep], context: dict[str, Any] | None = None
    ) -> list[PipelineResult]:
        """Execute a list of pipeline steps."""
        results: list[PipelineResult] = []
        step_outputs: dict[str, Any] = context or {}

        for step in steps:
            # Check dependencies
            if step.depends_on:
                dep_results = {r.step_name: r for r in results}
                if any(
                    dep not in dep_results or not dep_results[dep].success
                    for dep in step.depends_on
                ):
                    results.append(PipelineResult(
                        step_name=step.name,
                        success=False,
                        error="Dependency not met",
                    ))
                    if step.on_error == "stop":
                        break
                    continue

            result = await self._execute_step(step, step_outputs)
            results.append(result)

            if result.success:
                step_outputs[step.name] = result.output
            elif step.on_error == "stop":
                break

        return results

    async def _execute_step(
        self, step: PipelineStep, context: dict[str, Any]
    ) -> PipelineResult:
        """Execute a single pipeline step with retry logic."""
        handler = self._action_handlers.get(step.action)
        if not handler:
            return PipelineResult(
                step_name=step.name,
                success=False,
                error=f"Unknown action: {step.action}",
            )

        params = {**step.params, "_context": context}
        last_error = None

        for attempt in range(step.max_retries + 1):
            start = time.time()
            try:
                output = await asyncio.wait_for(
                    handler(**params), timeout=step.timeout
                )
                return PipelineResult(
                    step_name=step.name,
                    success=True,
                    output=output,
                    duration=time.time() - start,
                )
            except Exception as e:
                last_error = f"{type(e).__name__}: {str(e)}"
                if attempt < step.max_retries:
                    await asyncio.sleep(1.0 * (attempt + 1))

        return PipelineResult(
            step_name=step.name,
            success=False,
            error=last_error,
            duration=time.time() - start,
        )

    # Built-in action handlers

    async def _action_llm_query(self, prompt: str = "", _context: dict = None, **kw) -> str:
        from aforit.llm.router import ModelRouter
        router = ModelRouter(self.config)
        messages = [{"role": "user", "content": prompt}]
        chunks = []
        async for chunk in router.stream(messages):
            if chunk.get("type") == "text":
                chunks.append(chunk["content"])
        return "".join(chunks)

    async def _action_file_read(self, path: str = "", _context: dict = None, **kw) -> str:
        return Path(path).read_text()

    async def _action_file_write(
        self, path: str = "", content: str = "", _context: dict = None, **kw
    ) -> str:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        Path(path).write_text(content)
        return f"Written to {path}"

    async def _action_shell(self, command: str = "", _context: dict = None, **kw) -> str:
        proc = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        return stdout.decode() + stderr.decode()

    async def _action_transform(
        self, input_key: str = "", template: str = "", _context: dict = None, **kw
    ) -> str:
        data = (_context or {}).get(input_key, "")
        return template.format(data=data, **(_context or {}))

    async def _action_filter(
        self, input_key: str = "", contains: str = "", _context: dict = None, **kw
    ) -> str:
        data = str((_context or {}).get(input_key, ""))
        lines = data.split("\n")
        return "\n".join(line for line in lines if contains in line)

    async def _action_aggregate(
        self, keys: list[str] = None, separator: str = "\n", _context: dict = None, **kw
    ) -> str:
        keys = keys or []
        parts = [str((_context or {}).get(k, "")) for k in keys]
        return separator.join(parts)

    async def _action_parallel(
        self, steps: list[dict] = None, _context: dict = None, **kw
    ) -> dict[str, Any]:
        steps = steps or []
        tasks = {}
        for step_def in steps:
            step = PipelineStep(**step_def)
            tasks[step.name] = self._execute_step(step, _context or {})
        results = await asyncio.gather(*tasks.values())
        return {name: r.output for name, r in zip(tasks.keys(), results)}
