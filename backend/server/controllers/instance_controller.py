"""
Model Instance Controller - manages model instances on workers.
"""
from typing import List, Optional, Dict, Any
import asyncio
import logging
from datetime import datetime

from sqlalchemy.orm import Session
from backend.models.database import ModelInstance, ModelInstanceStatus, Model, Worker

logger = logging.getLogger(__name__)


class ModelInstanceController:
    """Controller for managing ModelInstance entities."""

    def __init__(self, db_session: Session):
        """Initialize ModelInstanceController.

        Args:
            db_session: SQLAlchemy database session
        """
        self.db = db_session
        self._health_check_running = False

    def create_instance(
        self,
        model_id: int,
        worker_id: int,
        name: str,
        backend: str = "vllm",
        config: Optional[Dict[str, Any]] = None,
        gpu_ids: Optional[List[int]] = None,
        port: Optional[int] = None,
    ) -> ModelInstance:
        """Create a new model instance.

        Args:
            model_id: Model ID
            worker_id: Worker ID
            name: Instance name
            backend: Backend type (vllm, sglang, etc.)
            config: Backend-specific configuration
            gpu_ids: List of GPU IDs assigned to this instance
            port: Port number for the instance

        Returns:
            Created ModelInstance instance
        """
        instance = ModelInstance(
            model_id=model_id,
            worker_id=worker_id,
            name=name,
            backend=backend,
            config=config or {},
            gpu_ids=gpu_ids or [],
            port=port,
            status=ModelInstanceStatus.STARTING,
        )

        self.db.add(instance)
        self.db.commit()
        self.db.refresh(instance)

        logger.info(f"Created model instance: {instance.id} - {name} on worker {worker_id}")
        return instance

    def get_instance(self, instance_id: int) -> Optional[ModelInstance]:
        """Get a model instance by ID.

        Args:
            instance_id: Instance ID

        Returns:
            ModelInstance instance or None if not found
        """
        return self.db.query(ModelInstance).filter(ModelInstance.id == instance_id).first()

    def list_instances(
        self,
        model_id: Optional[int] = None,
        worker_id: Optional[int] = None,
        status: Optional[ModelInstanceStatus] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[ModelInstance]:
        """List model instances with optional filters.

        Args:
            model_id: Optional model ID filter
            worker_id: Optional worker ID filter
            status: Optional status filter
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            List of ModelInstance instances
        """
        query = self.db.query(ModelInstance)

        if model_id is not None:
            query = query.filter(ModelInstance.model_id == model_id)

        if worker_id is not None:
            query = query.filter(ModelInstance.worker_id == worker_id)

        if status is not None:
            query = query.filter(ModelInstance.status == status)

        return query.order_by(ModelInstance.created_at.desc()).limit(limit).offset(offset).all()

    def update_instance_status(
        self,
        instance_id: int,
        status: ModelInstanceStatus,
        health_status: Optional[Dict[str, Any]] = None,
    ) -> Optional[ModelInstance]:
        """Update model instance status.

        Args:
            instance_id: Instance ID
            status: New status
            health_status: Optional health status data

        Returns:
            Updated ModelInstance instance or None if not found
        """
        instance = self.get_instance(instance_id)
        if not instance:
            return None

        instance.status = status
        if health_status is not None:
            instance.health_status = health_status

        self.db.commit()
        self.db.refresh(instance)

        logger.info(f"Updated instance {instance_id} status to {status}")
        return instance

    def delete_instance(self, instance_id: int) -> bool:
        """Delete a model instance.

        Args:
            instance_id: Instance ID

        Returns:
            True if deleted, False if not found
        """
        instance = self.get_instance(instance_id)
        if not instance:
            return False

        self.db.delete(instance)
        self.db.commit()

        logger.info(f"Deleted model instance: {instance_id}")
        return True

    def get_instances_by_model(self, model_id: int) -> List[ModelInstance]:
        """Get all instances for a specific model.

        Args:
            model_id: Model ID

        Returns:
            List of ModelInstance instances
        """
        return self.db.query(ModelInstance).filter(ModelInstance.model_id == model_id).all()

    def get_instances_by_worker(self, worker_id: int) -> List[ModelInstance]:
        """Get all instances on a specific worker.

        Args:
            worker_id: Worker ID

        Returns:
            List of ModelInstance instances
        """
        return self.db.query(ModelInstance).filter(ModelInstance.worker_id == worker_id).all()

    def get_running_instances(self) -> List[ModelInstance]:
        """Get all running instances.

        Returns:
            List of running ModelInstance instances
        """
        return self.db.query(ModelInstance).filter(ModelInstance.status == ModelInstanceStatus.RUNNING).all()

    async def health_check_loop(self, interval_seconds: int = 30):
        """Background task to check health of running instances.

        Args:
            interval_seconds: Interval between health checks
        """
        if self._health_check_running:
            logger.warning("Health check loop is already running")
            return

        self._health_check_running = True
        logger.info("Starting model instance health check loop")

        try:
            while self._health_check_running:
                try:
                    await self._check_all_instances()
                except Exception as e:
                    logger.error(f"Error in health check loop: {e}")

                await asyncio.sleep(interval_seconds)
        finally:
            self._health_check_running = False
            logger.info("Model instance health check loop stopped")

    async def _check_all_instances(self):
        """Check health of all running instances."""
        running_instances = self.get_running_instances()

        for instance in running_instances:
            try:
                # TODO: Implement actual health check by calling worker API
                # For now, just log
                logger.debug(f"Health check for instance {instance.id}")
            except Exception as e:
                logger.error(f"Health check failed for instance {instance.id}: {e}")
                # Mark as error if health check fails
                self.update_instance_status(instance.id, ModelInstanceStatus.ERROR)

    def stop_health_check_loop(self):
        """Stop the health check loop."""
        self._health_check_running = False

    def get_instance_health_summary(self) -> Dict[str, int]:
        """Get summary of instance health.

        Returns:
            Dictionary with counts by status
        """
        from sqlalchemy import func

        result = self.db.query(
            ModelInstance.status,
            func.count(ModelInstance.id)
        ).group_by(ModelInstance.status).all()

        return {status.value: count for status, count in result}
