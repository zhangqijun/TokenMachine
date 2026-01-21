"""
Benchmark service for batch testing.
"""
from typing import List, Optional
from sqlalchemy.orm import Session
from backend.models.database import BenchmarkTask, BenchmarkDataset, TaskStatus, TaskType
from backend.models.schemas import BenchmarkTaskCreate


class BenchmarkService:
    """Batch testing service."""

    def __init__(self, db: Session):
        self.db = db

    def create_task(
        self,
        user_id: int,
        data: BenchmarkTaskCreate,
        celery_task_id: str
    ) -> BenchmarkTask:
        """
        Create benchmark task and submit to Celery.

        Process:
        1. Create task record (status: pending)
        2. Submit to Celery for async execution
        3. Update celery_task_id
        """
        task = BenchmarkTask(
            user_id=user_id,
            deployment_id=data.deployment_id,
            task_name=data.task_name,
            task_type=data.task_type,
            status=TaskStatus.PENDING,
            config=data.config,
            celery_task_id=celery_task_id
        )
        self.db.add(task)
        self.db.commit()
        self.db.refresh(task)
        return task

    def list_tasks(
        self,
        user_id: int,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 50
    ) -> List[BenchmarkTask]:
        """Get user's benchmark tasks."""
        query = self.db.query(BenchmarkTask)\
            .filter(BenchmarkTask.user_id == user_id)

        if status:
            query = query.filter(BenchmarkTask.status == status)

        return query.order_by(BenchmarkTask.created_at.desc())\
            .offset(skip)\
            .limit(min(limit, 100))\
            .all()

    def get_task(
        self,
        task_id: int,
        user_id: int
    ) -> Optional[BenchmarkTask]:
        """Get task details."""
        return self.db.query(BenchmarkTask)\
            .filter(
                BenchmarkTask.id == task_id,
                BenchmarkTask.user_id == user_id
            )\
            .first()

    def cancel_task(self, task_id: int, user_id: int):
        """
        Cancel benchmark task.

        1. If task is running, revoke Celery task
        2. Update status to cancelled
        """
        task = self.get_task(task_id, user_id)
        if not task:
            raise ValueError("Task not found")

        if task.status == TaskStatus.RUNNING and task.celery_task_id:
            # Revoke Celery task (will be handled by API layer)
            pass

        task.status = TaskStatus.CANCELLED
        self.db.commit()

    def list_datasets(
        self,
        category: Optional[str] = None
    ) -> List[BenchmarkDataset]:
        """Get available benchmark datasets."""
        query = self.db.query(BenchmarkDataset)\
            .filter(BenchmarkDataset.is_active == True)

        if category:
            query = query.filter(BenchmarkDataset.category == category)

        return query.order_by(BenchmarkDataset.name).all()

    def get_dataset(self, dataset_id: int) -> Optional[BenchmarkDataset]:
        """Get dataset details."""
        return self.db.query(BenchmarkDataset)\
            .filter(BenchmarkDataset.id == dataset_id)\
            .first()
