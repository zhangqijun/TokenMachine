"""
Celery tasks for benchmark testing.
"""
import os
from datetime import datetime
from typing import Dict, Any

try:
    from celery import Task
    from backend.core.celery_app import celery_app
    HAS_CELERY = True
except ImportError:
    HAS_CELERY = False
    Task = object

from backend.core.database import SessionLocal
from backend.models.database import BenchmarkTask, TaskStatus, TaskType
from backend.core.config import get_settings


class DatabaseTask(Task):
    """Base task with database session management."""
    _db = None

    @property
    def db(self):
        """Get or create database session."""
        if self._db is None:
            self._db = SessionLocal()
        return self._db

    def after_return(self, *args, **kwargs):
        """Clean up database session after task completion."""
        if self._db is not None:
            self._db.close()
            self._db = None


# Define task decorators based on Celery availability
if HAS_CELERY:
    _eval_task_decorator = celery_app.task(bind=True, base=DatabaseTask, max_retries=3)
    _perf_task_decorator = celery_app.task(bind=True, base=DatabaseTask, max_retries=3)
else:
    # Fallback: create dummy decorators for development
    def _dummy_decorator(func):
        return func
    _eval_task_decorator = _dummy_decorator
    _perf_task_decorator = _dummy_decorator


@_eval_task_decorator
def run_eval_task(self, task_id: int) -> Dict[str, Any]:
    """
    Execute evaluation benchmark task (calls EvalScope API).

    Process:
    1. Update task status to running
    2. Call EvalScope /api/v1/eval (synchronous blocking call)
    3. Parse results and update database
    4. Change status to completed/failed

    Note:
    - EvalScope API is synchronous and blocking
    - Task execution may take tens of minutes
    - Database is updated upon completion (frontend polls for results)
    """
    task = self.db.query(BenchmarkTask).filter(BenchmarkTask.id == task_id).first()
    if not task:
        return {"task_id": task_id, "status": "error", "error": "Task not found"}

    try:
        # Update status: running
        task.status = TaskStatus.RUNNING
        task.started_at = datetime.now()
        self.db.commit()

        # Call EvalScope API
        settings = get_settings()
        evalscope_url = settings.evalscope_service_url

        import httpx
        with httpx.Client(timeout=settings.evalscope_timeout) as client:
            response = client.post(
                f"{evalscope_url}/api/v1/eval",
                json=task.config,
                headers={"Content-Type": "application/json"}
            )
            response.raise_for_status()
            result = response.json()

        # Save results
        task.status = TaskStatus.COMPLETED
        task.result = result
        task.output_dir = result.get("output_dir")
        task.completed_at = datetime.now()
        self.db.commit()

        return {"task_id": task_id, "status": "completed"}

    except Exception as e:
        # Task failed
        task.status = TaskStatus.FAILED
        task.error_message = str(e)
        task.completed_at = datetime.now()
        self.db.commit()

        # Retry logic
        if self.request.retries < self.max_retries:
            raise self.retry(exc=e, countdown=60)

        return {"task_id": task_id, "status": "failed", "error": str(e)}


@_perf_task_decorator
def run_perf_task(self, task_id: int) -> Dict[str, Any]:
    """
    Execute performance benchmark task (calls EvalScope API).

    Process:
    1. Update task status to running
    2. Call EvalScope /api/v1/perf
    3. Parse results (QPS, latency, throughput, etc.)
    4. Change status to completed/failed

    Performance Metrics:
    - QPS (Queries Per Second)
    - Token throughput (tokens/second)
    - P50/P95/P99 latency
    - GPU utilization
    """
    task = self.db.query(BenchmarkTask).filter(BenchmarkTask.id == task_id).first()
    if not task:
        return {"task_id": task_id, "status": "error", "error": "Task not found"}

    try:
        # Update status: running
        task.status = TaskStatus.RUNNING
        task.started_at = datetime.now()
        self.db.commit()

        # Call EvalScope API
        settings = get_settings()
        evalscope_url = settings.evalscope_service_url

        import httpx
        with httpx.Client(timeout=settings.evalscope_timeout) as client:
            response = client.post(
                f"{evalscope_url}/api/v1/perf",
                json=task.config,
                headers={"Content-Type": "application/json"}
            )
            response.raise_for_status()
            result = response.json()

        # Save results
        task.status = TaskStatus.COMPLETED
        task.result = result
        task.output_dir = result.get("output_dir")
        task.completed_at = datetime.now()
        self.db.commit()

        return {"task_id": task_id, "status": "completed"}

    except Exception as e:
        # Task failed
        task.status = TaskStatus.FAILED
        task.error_message = str(e)
        task.completed_at = datetime.now()
        self.db.commit()

        # Retry logic
        if self.request.retries < self.max_retries:
            raise self.retry(exc=e, countdown=60)

        return {"task_id": task_id, "status": "failed", "error": str(e)}
