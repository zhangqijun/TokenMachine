"""
Worker Controller - manages worker nodes.
"""
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import logging

from sqlalchemy.orm import Session
from backend.models.database import Worker, WorkerStatus, Cluster

logger = logging.getLogger(__name__)


class WorkerController:
    """Controller for managing Worker entities."""

    def __init__(self, db_session: Session):
        """Initialize WorkerController.

        Args:
            db_session: SQLAlchemy database session
        """
        self.db = db_session

    def create_worker(
        self,
        name: str,
        ip: str,
        ifname: Optional[str] = None,
        hostname: Optional[str] = None,
        cluster_id: Optional[int] = None,
        token_hash: Optional[str] = None,
    ) -> Worker:
        """Create a new worker.

        Args:
            name: Worker name
            ip: Worker IP address
            ifname: Network interface name
            hostname: Worker hostname
            cluster_id: Optional cluster ID
            token_hash: Optional hashed token for authentication

        Returns:
            Created Worker instance
        """
        worker = Worker(
            name=name,
            ip=ip,
            ifname=ifname,
            hostname=hostname,
            cluster_id=cluster_id,
            token_hash=token_hash,
            status=WorkerStatus.REGISTERING,
        )

        self.db.add(worker)
        self.db.commit()
        self.db.refresh(worker)

        logger.info(f"Created worker: {worker.id} - {name}")
        return worker

    def get_worker(self, worker_id: int) -> Optional[Worker]:
        """Get a worker by ID.

        Args:
            worker_id: Worker ID

        Returns:
            Worker instance or None if not found
        """
        return self.db.query(Worker).filter(Worker.id == worker_id).first()

    def get_worker_by_name(self, name: str, cluster_id: Optional[int] = None) -> Optional[Worker]:
        """Get a worker by name.

        Args:
            name: Worker name
            cluster_id: Optional cluster ID for scoping

        Returns:
            Worker instance or None if not found
        """
        query = self.db.query(Worker).filter(Worker.name == name)

        if cluster_id is not None:
            query = query.filter(Worker.cluster_id == cluster_id)

        return query.first()

    def list_workers(
        self,
        cluster_id: Optional[int] = None,
        status: Optional[WorkerStatus] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Worker]:
        """List workers with optional filters.

        Args:
            cluster_id: Optional cluster ID filter
            status: Optional status filter
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            List of Worker instances
        """
        query = self.db.query(Worker)

        if cluster_id is not None:
            query = query.filter(Worker.cluster_id == cluster_id)

        if status is not None:
            query = query.filter(Worker.status == status)

        return query.order_by(Worker.created_at.desc()).limit(limit).offset(offset).all()

    def update_worker_status(self, worker_id: int, status: WorkerStatus) -> Optional[Worker]:
        """Update worker status.

        Args:
            worker_id: Worker ID
            status: New status

        Returns:
            Updated Worker instance or None if not found
        """
        worker = self.get_worker(worker_id)
        if not worker:
            return None

        worker.status = status
        self.db.commit()
        self.db.refresh(worker)

        logger.info(f"Updated worker {worker_id} status to {status}")
        return worker

    def update_worker_heartbeat(self, worker_id: int) -> Optional[Worker]:
        """Update worker heartbeat timestamp.

        Args:
            worker_id: Worker ID

        Returns:
            Updated Worker instance or None if not found
        """
        worker = self.get_worker(worker_id)
        if not worker:
            return None

        worker.last_heartbeat_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(worker)

        return worker

    def update_worker_gpu_count(self, worker_id: int, gpu_count: int) -> Optional[Worker]:
        """Update worker GPU count.

        Args:
            worker_id: Worker ID
            gpu_count: Number of GPUs

        Returns:
            Updated Worker instance or None if not found
        """
        worker = self.get_worker(worker_id)
        if not worker:
            return None

        worker.gpu_count = gpu_count
        self.db.commit()
        self.db.refresh(worker)

        return worker

    def delete_worker(self, worker_id: int) -> bool:
        """Delete a worker.

        Args:
            worker_id: Worker ID

        Returns:
            True if deleted, False if not found
        """
        worker = self.get_worker(worker_id)
        if not worker:
            return False

        self.db.delete(worker)
        self.db.commit()

        logger.info(f"Deleted worker: {worker_id}")
        return True

    def mark_unhealthy_workers(self, timeout_seconds: int = 90) -> List[Worker]:
        """Mark workers as unhealthy if they haven't sent heartbeat.

        Args:
            timeout_seconds: Heartbeat timeout in seconds

        Returns:
            List of workers marked as unhealthy
        """
        threshold = datetime.utcnow() - timedelta(seconds=timeout_seconds)

        workers = self.db.query(Worker).filter(
            Worker.status == WorkerStatus.READY,
            Worker.last_heartbeat_at < threshold,
        ).all()

        unhealthy_workers = []
        for worker in workers:
            worker.status = WorkerStatus.UNHEALTHY
            unhealthy_workers.append(worker)
            logger.warning(f"Worker {worker.id} marked as unhealthy (last heartbeat: {worker.last_heartbeat_at})")

        if unhealthy_workers:
            self.db.commit()

        return unhealthy_workers

    def get_workers_by_status(self, status: WorkerStatus) -> List[Worker]:
        """Get all workers with a specific status.

        Args:
            status: Worker status

        Returns:
            List of Worker instances
        """
        return self.db.query(Worker).filter(Worker.status == status).all()

    def get_available_workers(self) -> List[Worker]:
        """Get workers that are ready to accept tasks.

        Returns:
            List of available Worker instances
        """
        return self.get_workers_by_status(WorkerStatus.READY)

    def drain_worker(self, worker_id: int) -> Optional[Worker]:
        """Mark a worker as draining (stops accepting new tasks).

        Args:
            worker_id: Worker ID

        Returns:
            Updated Worker instance or None if not found
        """
        return self.update_worker_status(worker_id, WorkerStatus.DRAINING)
