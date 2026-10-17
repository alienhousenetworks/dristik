"""Compatibility re-export from app.workers."""
from app.workers.queue import TaskQueue, task_queue
from app.workers.audit_tasks import *  # noqa: F401, F403
from app.workers.crawl_tasks import *  # noqa: F401, F403
from app.workers.report_tasks import *  # noqa: F401, F403

__all__ = ["TaskQueue", "task_queue"]
