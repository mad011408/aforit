"""Task scheduler for background and deferred operations."""

from __future__ import annotations

import asyncio
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Coroutine


class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class ScheduledTask:
    """A task that can be scheduled for execution."""

    task_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""
    coro_factory: Callable[..., Coroutine] | None = None
    args: tuple = ()
    kwargs: dict[str, Any] = field(default_factory=dict)
    status: TaskStatus = TaskStatus.PENDING
    result: Any = None
    error: str | None = None
    created_at: float = field(default_factory=time.time)
    started_at: float | None = None
    completed_at: float | None = None
    retry_count: int = 0
    max_retries: int = 3
    priority: int = 0  # Higher = more important

    @property
    def duration(self) -> float | None:
        if self.started_at and self.completed_at:
            return self.completed_at - self.started_at
        return None


class TaskScheduler:
    """Async task scheduler with priority queue and retry logic."""

    def __init__(self, max_concurrent: int = 5):
        self.max_concurrent = max_concurrent
        self._tasks: dict[str, ScheduledTask] = {}
        self._queue: asyncio.PriorityQueue = asyncio.PriorityQueue()
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._running = False

    async def submit(
        self,
        name: str,
        coro_factory: Callable[..., Coroutine],
        *args,
        priority: int = 0,
        max_retries: int = 3,
        **kwargs,
    ) -> str:
        """Submit a task for execution. Returns the task ID."""
        task = ScheduledTask(
            name=name,
            coro_factory=coro_factory,
            args=args,
            kwargs=kwargs,
            priority=priority,
            max_retries=max_retries,
        )
        self._tasks[task.task_id] = task
        await self._queue.put((-priority, task.task_id))
        return task.task_id

    async def run(self):
        """Start processing the task queue."""
        self._running = True
        workers = [asyncio.create_task(self._worker(i)) for i in range(self.max_concurrent)]
        await asyncio.gather(*workers, return_exceptions=True)

    async def _worker(self, worker_id: int):
        """Worker coroutine that processes tasks from the queue."""
        while self._running:
            try:
                _, task_id = await asyncio.wait_for(self._queue.get(), timeout=1.0)
            except asyncio.TimeoutError:
                continue

            task = self._tasks.get(task_id)
            if not task or task.status == TaskStatus.CANCELLED:
                continue

            async with self._semaphore:
                await self._execute_task(task)

    async def _execute_task(self, task: ScheduledTask):
        """Execute a single task with retry logic."""
        task.status = TaskStatus.RUNNING
        task.started_at = time.time()

        try:
            if task.coro_factory:
                task.result = await task.coro_factory(*task.args, **task.kwargs)
            task.status = TaskStatus.COMPLETED
        except Exception as e:
            task.error = f"{type(e).__name__}: {str(e)}"
            task.retry_count += 1

            if task.retry_count < task.max_retries:
                task.status = TaskStatus.PENDING
                await self._queue.put((-task.priority, task.task_id))
            else:
                task.status = TaskStatus.FAILED
        finally:
            task.completed_at = time.time()

    def cancel(self, task_id: str) -> bool:
        """Cancel a pending task."""
        task = self._tasks.get(task_id)
        if task and task.status == TaskStatus.PENDING:
            task.status = TaskStatus.CANCELLED
            return True
        return False

    def get_status(self, task_id: str) -> dict[str, Any] | None:
        """Get the current status of a task."""
        task = self._tasks.get(task_id)
        if not task:
            return None
        return {
            "task_id": task.task_id,
            "name": task.name,
            "status": task.status.value,
            "result": task.result,
            "error": task.error,
            "duration": task.duration,
            "retry_count": task.retry_count,
        }

    def get_all_statuses(self) -> list[dict[str, Any]]:
        """Get status of all tasks."""
        return [self.get_status(tid) for tid in self._tasks]

    def stop(self):
        """Stop the scheduler."""
        self._running = False
