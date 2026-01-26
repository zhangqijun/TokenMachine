"""
Worker service for managing worker lifecycle.
"""
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func
from datetime import datetime, timedelta

from backend.models.database import (
    Worker, Cluster, WorkerPool, GPUDevice, ModelInstance,
    WorkerStatus
)


class WorkerService:
    """Service for managing worker lifecycle."""

    def __init__(self, db: Session):
        self.db = db
        self._heartbeat_timeout_seconds = 60
        self._offline_timeout_seconds = 120

    # ========================================================================
    # Worker Registration
    # ========================================================================

    def register_worker(
        self,
        name: str,
        cluster_id: int,
        pool_id: Optional[int] = None,
        ip: Optional[str] = None,
        port: int = 8080,
        hostname: Optional[str] = None,
        ifname: Optional[str] = None,
        labels: Optional[Dict[str, Any]] = None,
        token_hash: Optional[str] = None
    ) -> Worker:
        """
        Register or update a worker.

        Args:
            name: Worker name
            cluster_id: Cluster ID
            pool_id: Optional Worker Pool ID
            ip: Worker IP address
            port: Worker port
            hostname: Worker hostname
            ifname: Network interface name
            labels: Worker labels (GPU type, zone, etc.)
            token_hash: Authentication token hash

        Returns:
            Registered Worker object

        Raises:
            ValueError: If cluster doesn't exist
        """
        # Verify cluster exists
        cluster = self.db.query(Cluster).filter(Cluster.id == cluster_id).first()
        if not cluster:
            raise ValueError(f"Cluster with ID {cluster_id} not found")

        # Verify pool exists if provided
        if pool_id:
            pool = self.db.query(WorkerPool).filter(WorkerPool.id == pool_id).first()
            if not pool or pool.cluster_id != cluster_id:
                raise ValueError(f"Worker pool with ID {pool_id} not found in cluster")

        # Check if worker already exists
        existing = self.db.query(Worker).filter(
            and_(Worker.cluster_id == cluster_id, Worker.name == name)
        ).first()

        if existing:
            # Update existing worker (re-registering)
            existing.pool_id = pool_id
            existing.ip = ip
            existing.port = port
            existing.hostname = hostname
            existing.ifname = ifname
            existing.labels = labels or {}
            existing.token_hash = token_hash
            existing.status = WorkerStatus.REGISTERING
            existing.last_heartbeat_at = datetime.utcnow()
            self.db.commit()
            self.db.refresh(existing)
            return existing

        # Create new worker
        worker = Worker(
            cluster_id=cluster_id,
            pool_id=pool_id,
            name=name,
            ip=ip,
            port=port,
            hostname=hostname,
            ifname=ifname,
            labels=labels or {},
            token_hash=token_hash,
            status=WorkerStatus.REGISTERING,
            gpu_count=0,
            last_heartbeat_at=datetime.utcnow()
        )
        self.db.add(worker)
        self.db.commit()
        self.db.refresh(worker)

        return worker

    def heartbeat(self, worker_id: int) -> bool:
        """
        Update worker heartbeat timestamp.

        Args:
            worker_id: Worker ID

        Returns:
            True if worker found and updated, False otherwise
        """
        worker = self.db.query(Worker).filter(Worker.id == worker_id).first()
        if not worker:
            return False

        worker.last_heartbeat_at = datetime.utcnow()

        # If worker was offline or unhealthy, mark it as ready
        if worker.status in [WorkerStatus.OFFLINE, WorkerStatus.UNHEALTHY]:
            worker.status = WorkerStatus.READY

        self.db.commit()
        return True

    def update_status(
        self,
        worker_id: int,
        status: Dict[str, Any]
    ) -> bool:
        """
        Update worker status from worker report.

        Args:
            worker_id: Worker ID
            status: Status dictionary containing:
                - cpu: CPU info
                - memory: Memory info
                - gpu_devices: List of GPU devices
                - filesystem: Filesystem info

        Returns:
            True if worker found and updated, False otherwise
        """
        worker = self.db.query(Worker).filter(Worker.id == worker_id).first()
        if not worker:
            return False

        worker.status_json = status
        worker.last_status_update_at = datetime.utcnow()
        worker.gpu_count = len(status.get("gpu_devices", []))

        # Update GPU devices
        if "gpu_devices" in status:
            self._update_gpu_devices(worker_id, status["gpu_devices"])

        self.db.commit()
        return True

    def _update_gpu_devices(
        self,
        worker_id: int,
        gpu_devices: List[Dict[str, Any]]
    ) -> None:
        """
        Update GPU device information for a worker.

        Args:
            worker_id: Worker ID
            gpu_devices: List of GPU device dictionaries
        """
        for gpu_data in gpu_devices:
            uuid = gpu_data.get("uuid")
            if not uuid:
                continue

            # Find or create GPU device record
            gpu = self.db.query(GPUDevice).filter(
                and_(GPUDevice.worker_id == worker_id, GPUDevice.uuid == uuid)
            ).first()

            if not gpu:
                gpu = GPUDevice(
                    worker_id=worker_id,
                    uuid=uuid
                )
                self.db.add(gpu)

            # Update GPU information
            gpu.name = gpu_data.get("name", "")
            gpu.vendor = gpu_data.get("vendor")
            gpu.index = gpu_data.get("index", 0)
            gpu.core_total = gpu_data.get("core_total")
            gpu.core_utilization_rate = gpu_data.get("core_utilization_rate")
            gpu.memory_total = gpu_data.get("memory_total")
            gpu.memory_used = gpu_data.get("memory_used")
            gpu.memory_allocated = gpu_data.get("memory_allocated")
            gpu.memory_utilization_rate = gpu_data.get("memory_utilization_rate")
            gpu.temperature = gpu_data.get("temperature")
            gpu.state = gpu_data.get("state", "available")
            gpu.updated_at = datetime.utcnow()

        self.db.flush()

    # ========================================================================
    # Worker Queries
    # ========================================================================

    def get_worker(self, worker_id: int) -> Optional[Worker]:
        """Get a worker by ID."""
        return self.db.query(Worker).filter(Worker.id == worker_id).first()

    def list_workers(
        self,
        cluster_id: Optional[int] = None,
        pool_id: Optional[int] = None,
        status: Optional[WorkerStatus] = None,
        labels_filter: Optional[Dict[str, str]] = None
    ) -> List[Worker]:
        """
        List workers with optional filtering.

        Args:
            cluster_id: Filter by cluster ID
            pool_id: Filter by pool ID
            status: Filter by status
            labels_filter: Filter by labels (key-value pairs)

        Returns:
            List of Worker objects
        """
        query = self.db.query(Worker)

        if cluster_id:
            query = query.filter(Worker.cluster_id == cluster_id)
        if pool_id:
            query = query.filter(Worker.pool_id == pool_id)
        if status:
            query = query.filter(Worker.status == status)

        workers = query.order_by(Worker.created_at.desc()).all()

        # Filter by labels if provided
        if labels_filter:
            filtered = []
            for worker in workers:
                worker_labels = worker.labels or {}
                match = True
                for key, value in labels_filter.items():
                    if worker_labels.get(key) != value:
                        match = False
                        break
                if match:
                    filtered.append(worker)
            return filtered

        return workers

    # ========================================================================
    # Worker Updates
    # ========================================================================

    def update_worker(
        self,
        worker_id: int,
        **kwargs
    ) -> Optional[Worker]:
        """
        Update a worker.

        Args:
            worker_id: Worker ID
            **kwargs: Fields to update (pool_id, status, labels, etc.)

        Returns:
            Updated Worker object or None if not found
        """
        worker = self.get_worker(worker_id)
        if not worker:
            return None

        # Update allowed fields
        allowed_fields = {
            "pool_id", "status", "labels", "ip", "port", "hostname", "ifname"
        }
        for key, value in kwargs.items():
            if key in allowed_fields and hasattr(worker, key):
                setattr(worker, key, value)

        self.db.commit()
        self.db.refresh(worker)

        return worker

    def set_worker_status(
        self,
        worker_id: int,
        status: WorkerStatus
    ) -> Optional[Worker]:
        """
        Set worker status.

        Args:
            worker_id: Worker ID
            status: New status

        Returns:
            Updated Worker object or None if not found
        """
        return self.update_worker(worker_id, status=status)

    def drain_worker(self, worker_id: int) -> Optional[Worker]:
        """
        Drain a worker (stop scheduling new instances).

        Args:
            worker_id: Worker ID

        Returns:
            Updated Worker object or None if not found
        """
        return self.set_worker_status(worker_id, WorkerStatus.DRAINING)

    def set_worker_maintenance(self, worker_id: int) -> Optional[Worker]:
        """
        Set worker to maintenance mode.

        Args:
            worker_id: Worker ID

        Returns:
            Updated Worker object or None if not found
        """
        return self.set_worker_status(worker_id, WorkerStatus.MAINTENANCE)

    # ========================================================================
    # Worker Deletion
    # ========================================================================

    def delete_worker(self, worker_id: int) -> bool:
        """
        Delete a worker.

        Args:
            worker_id: Worker ID

        Returns:
            True if deleted, False if not found

        Raises:
            ValueError: If worker has running instances
        """
        worker = self.get_worker(worker_id)
        if not worker:
            return False

        # Check for running model instances
        running_instances = self.db.query(ModelInstance).filter(
            and_(
                ModelInstance.worker_id == worker_id,
                ModelInstance.status.in_(["starting", "running"])
            )
        ).count()

        if running_instances > 0:
            raise ValueError(
                f"Cannot delete worker with {running_instances} running instances. "
                "Stop the instances first."
            )

        self.db.delete(worker)
        self.db.commit()

        return True

    # ========================================================================
    # Worker Health Monitoring
    # ========================================================================

    def check_offline_workers(self, timeout_seconds: Optional[int] = None) -> List[Worker]:
        """
        Check for workers that have gone offline.

        Args:
            timeout_seconds: Timeout in seconds (defaults to _heartbeat_timeout_seconds)

        Returns:
            List of workers marked as offline
        """
        timeout = timeout_seconds or self._heartbeat_timeout_seconds
        timeout_threshold = datetime.utcnow() - timedelta(seconds=timeout)

        offline_workers = self.db.query(Worker).filter(
            and_(
                Worker.status.in_([WorkerStatus.READY, WorkerStatus.BUSY, WorkerStatus.ALLOCATING]),
                Worker.last_heartbeat_at < timeout_threshold
            )
        ).all()

        # Mark as offline
        for worker in offline_workers:
            worker.status = WorkerStatus.OFFLINE

        self.db.commit()
        return offline_workers

    def get_unhealthy_workers(self) -> List[Dict[str, Any]]:
        """
        Get list of unhealthy workers.

        Returns:
            List of dictionaries with unhealthy worker info
        """
        offline = self.db.query(Worker).filter(
            Worker.status == WorkerStatus.OFFLINE
        ).all()

        unhealthy = self.db.query(Worker).filter(
            Worker.status == WorkerStatus.UNHEALTHY
        ).all()

        result = []
        for worker in offline + unhealthy:
            result.append({
                "id": worker.id,
                "name": worker.name,
                "cluster_id": worker.cluster_id,
                "status": worker.status.value if hasattr(worker.status, 'value') else str(worker.status),
                "last_heartbeat": worker.last_heartbeat_at.isoformat() if worker.last_heartbeat_at else None
            })

        return result

    # ========================================================================
    # Worker Statistics
    # ========================================================================

    def get_worker_stats(self, worker_id: int) -> Dict[str, Any]:
        """
        Get detailed statistics for a worker.

        Args:
            worker_id: Worker ID

        Returns:
            Dictionary with worker statistics
        """
        worker = self.get_worker(worker_id)
        if not worker:
            return {}

        # Count model instances by status
        instances = self.db.query(ModelInstance).filter(
            ModelInstance.worker_id == worker_id
        ).all()

        instance_stats = {"total": len(instances), "by_status": {}}
        for instance in instances:
            status = instance.status.value if hasattr(instance.status, 'value') else str(instance.status)
            instance_stats["by_status"][status] = instance_stats["by_status"].get(status, 0) + 1

        # Count GPU devices
        gpu_count = self.db.query(GPUDevice).filter(
            GPUDevice.worker_id == worker_id
        ).count()

        return {
            "id": worker.id,
            "name": worker.name,
            "cluster_id": worker.cluster_id,
            "pool_id": worker.pool_id,
            "status": worker.status.value if hasattr(worker.status, 'value') else str(worker.status),
            "ip": worker.ip,
            "port": worker.port,
            "hostname": worker.hostname,
            "gpu_count": worker.gpu_count,
            "gpu_devices": gpu_count,
            "model_instances": instance_stats,
            "labels": worker.labels or {},
            "last_heartbeat": worker.last_heartbeat_at.isoformat() if worker.last_heartbeat_at else None,
            "last_status_update": worker.last_status_update_at.isoformat() if worker.last_status_update_at else None,
            "created_at": worker.created_at.isoformat() if worker.created_at else None
        }

    def get_workers_for_scheduling(
        self,
        cluster_id: Optional[int] = None,
        gpu_count: Optional[int] = None,
        labels_filter: Optional[Dict[str, str]] = None
    ) -> List[Worker]:
        """
        Get workers available for scheduling new instances.

        Args:
            cluster_id: Filter by cluster
            gpu_count: Required GPU count
            labels_filter: Required labels

        Returns:
            List of available workers
        """
        query = self.db.query(Worker).filter(
            Worker.status.in_([WorkerStatus.READY, WorkerStatus.BUSY])
        )

        if cluster_id:
            query = query.filter(Worker.cluster_id == cluster_id)

        workers = query.all()

        # Filter by GPU count if specified
        if gpu_count:
            workers = [w for w in workers if w.gpu_count >= gpu_count]

        # Filter by labels if specified
        if labels_filter:
            filtered = []
            for worker in workers:
                worker_labels = worker.labels or {}
                match = True
                for key, value in labels_filter.items():
                    if worker_labels.get(key) != value:
                        match = False
                        break
                if match:
                    filtered.append(worker)
            workers = filtered

        return workers

    def cleanup_offline_workers(self, timeout_seconds: Optional[int] = None) -> int:
        """
        Cleanup workers that have been offline for too long.

        Args:
            timeout_seconds: Timeout in seconds (defaults to _offline_timeout_seconds)

        Returns:
            Number of workers cleaned up
        """
        timeout = timeout_seconds or self._offline_timeout_seconds
        timeout_threshold = datetime.utcnow() - timedelta(seconds=timeout)

        # Find workers offline for too long with no running instances
        workers_to_cleanup = self.db.query(Worker).join(ModelInstance, isouter=True).filter(
            and_(
                Worker.status == WorkerStatus.OFFLINE,
                Worker.last_heartbeat_at < timeout_threshold,
                ModelInstance.id.is_(None)
            )
        ).all()

        count = len(workers_to_cleanup)
        for worker in workers_to_cleanup:
            self.db.delete(worker)

        self.db.commit()
        return count
