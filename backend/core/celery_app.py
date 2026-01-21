"""
Celery application configuration for async benchmark tasks.
"""
from celery import Celery
from backend.core.config import settings

celery_app = Celery(
    "tokenmachine",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["backend.workers.benchmark_tasks"]
)

celery_app.conf.update(
    # Serialization
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Shanghai",
    enable_utc=True,

    # Task tracking
    task_track_started=True,
    task_time_limit=3600,  # 1 hour hard limit
    task_soft_time_limit=3300,  # 55 minutes soft limit

    # Worker configuration
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=50,

    # Result backend
    result_expires=86400,  # 24 hours
    result_extended=True,
)
