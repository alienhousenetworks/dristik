import asyncio
from typing import Callable, Any

class TaskQueue:
    """In-memory asynchronous task runner."""
    def __init__(self):
        self._tasks = []

    def enqueue(self, coro_func: Callable, *args, **kwargs):
        task = asyncio.create_task(coro_func(*args, **kwargs))
        self._tasks.append(task)
        return task

task_queue = TaskQueue()
