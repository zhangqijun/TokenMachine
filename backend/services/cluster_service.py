"""
Cluster service for managing clusters and worker pools.
"""
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_
from datetime import datetime

from models.database import (
    Cluster, WorkerPool, Worker, ModelInstance,
    ClusterType, ClusterStatus, WorkerPoolStatus
)


class ClusterService:
    """Service for managing clusters and worker pools."""

    def __init__(self, db: Session):
        self.db = db

    # ========================================================================
    # Cluster Management
    # ========================================================================

    def create_cluster(
        self,
        name: str,
        cluster_type: ClusterType,
        config: Optional[Dict[str, Any]] = None,
        description: Optional[str] = None,
        is_default: bool = False
    ) -> Cluster:
        """
        Create a new cluster.

        Args:
            name: Cluster name
            cluster_type: Type of cluster (docker, kubernetes, standalone, etc.)
            config: Cluster-specific configuration
            description: Optional description
            is_default: Whether this is the default cluster

        Returns:
            Created Cluster object

        Raises:
            ValueError: If a cluster with the same name exists
        """
        # Check if cluster name already exists
        existing = self.db.query(Cluster).filter(Cluster.name == name).first()
        if existing:
            raise ValueError(f"Cluster with name '{name}' already exists")

        # If setting as default, unset other default clusters
        if is_default:
            self.db.query(Cluster).filter(
                Cluster.is_default == True
            ).update({"is_default": False}, synchronize_session=False)

        cluster = Cluster(
            name=name,
            type=cluster_type,
            description=description,
            config=config or {},
            is_default=is_default,
            status=ClusterStatus.RUNNING
        )
        self.db.add(cluster)
        self.db.commit()
        self.db.refresh(cluster)

        return cluster

    def get_cluster(self, cluster_id: int) -> Optional[Cluster]:
        """Get a cluster by ID."""
        return self.db.query(Cluster).filter(Cluster.id == cluster_id).first()

    def get_cluster_by_name(self, name: str) -> Optional[Cluster]:
        """Get a cluster by name."""
        return self.db.query(Cluster).filter(Cluster.name == name).first()

    def get_default_cluster(self) -> Optional[Cluster]:
        """Get the default cluster."""
        return self.db.query(Cluster).filter(Cluster.is_default == True).first()

    def list_clusters(
        self,
        cluster_type: Optional[ClusterType] = None,
        status: Optional[ClusterStatus] = None
    ) -> List[Cluster]:
        """
        List all clusters with optional filtering.

        Args:
            cluster_type: Filter by cluster type
            status: Filter by status

        Returns:
            List of Cluster objects
        """
        query = self.db.query(Cluster)

        if cluster_type:
            query = query.filter(Cluster.type == cluster_type)
        if status:
            query = query.filter(Cluster.status == status)

        return query.order_by(Cluster.created_at.desc()).all()

    def update_cluster(
        self,
        cluster_id: int,
        **kwargs
    ) -> Optional[Cluster]:
        """
        Update a cluster.

        Args:
            cluster_id: Cluster ID
            **kwargs: Fields to update (name, description, config, status, is_default)

        Returns:
            Updated Cluster object or None if not found
        """
        cluster = self.get_cluster(cluster_id)
        if not cluster:
            return None

        # Handle is_default specially
        if "is_default" in kwargs and kwargs["is_default"]:
            self.db.query(Cluster).filter(
                and_(Cluster.is_default == True, Cluster.id != cluster_id)
            ).update({"is_default": False}, synchronize_session=False)

        # Update allowed fields
        allowed_fields = {"name", "description", "config", "status", "is_default"}
        for key, value in kwargs.items():
            if key in allowed_fields and hasattr(cluster, key):
                setattr(cluster, key, value)

        self.db.commit()
        self.db.refresh(cluster)

        return cluster

    def set_default_cluster(self, cluster_id: int) -> Optional[Cluster]:
        """
        Set a cluster as the default.

        Args:
            cluster_id: Cluster ID

        Returns:
            Updated Cluster object or None if not found
        """
        return self.update_cluster(cluster_id, is_default=True)

    def delete_cluster(self, cluster_id: int) -> bool:
        """
        Delete a cluster.

        Args:
            cluster_id: Cluster ID

        Returns:
            True if deleted, False if not found

        Raises:
            ValueError: If cluster has running workers or worker pools
        """
        cluster = self.get_cluster(cluster_id)
        if not cluster:
            return False

        # Check for running workers
        running_workers = self.db.query(Worker).filter(
            and_(
                Worker.cluster_id == cluster_id,
                Worker.status.in_(["ready", "allocating", "busy"])
            )
        ).count()

        if running_workers > 0:
            raise ValueError(
                f"Cannot delete cluster with {running_workers} running workers. "
                "Stop or drain the workers first."
            )

        # Check for active worker pools
        active_pools = self.db.query(WorkerPool).filter(
            and_(
                WorkerPool.cluster_id == cluster_id,
                WorkerPool.status == WorkerPoolStatus.RUNNING
            )
        ).count()

        if active_pools > 0:
            raise ValueError(
                f"Cannot delete cluster with {active_pools} active worker pools. "
                "Stop the pools first."
            )

        self.db.delete(cluster)
        self.db.commit()

        return True

    def get_cluster_stats(self, cluster_id: int) -> Dict[str, Any]:
        """
        Get statistics for a cluster.

        Args:
            cluster_id: Cluster ID

        Returns:
            Dictionary with cluster statistics
        """
        cluster = self.get_cluster(cluster_id)
        if not cluster:
            return {}

        # Count workers by status
        workers = self.db.query(Worker).filter(Worker.cluster_id == cluster_id).all()
        worker_stats = {"total": len(workers), "by_status": {}}
        for worker in workers:
            status = worker.status.value if hasattr(worker.status, 'value') else str(worker.status)
            worker_stats["by_status"][status] = worker_stats["by_status"].get(status, 0) + 1

        # Count worker pools
        pools = self.db.query(WorkerPool).filter(WorkerPool.cluster_id == cluster_id).all()

        # Count model instances
        instances = self.db.query(ModelInstance).join(Worker).filter(
            Worker.cluster_id == cluster_id
        ).all()

        return {
            "id": cluster.id,
            "name": cluster.name,
            "type": cluster.type.value if hasattr(cluster.type, 'value') else str(cluster.type),
            "status": cluster.status.value if hasattr(cluster.status, 'value') else str(cluster.status),
            "worker_pools": len(pools),
            "workers": worker_stats,
            "model_instances": len(instances),
            "created_at": cluster.created_at.isoformat() if cluster.created_at else None
        }

    # ========================================================================
    # Worker Pool Management
    # ========================================================================

    def create_worker_pool(
        self,
        cluster_id: int,
        name: str,
        min_workers: int = 1,
        max_workers: int = 10,
        config: Optional[Dict[str, Any]] = None
    ) -> WorkerPool:
        """
        Create a new worker pool in a cluster.

        Args:
            cluster_id: Cluster ID
            name: Pool name
            min_workers: Minimum number of workers
            max_workers: Maximum number of workers
            config: Pool-specific configuration

        Returns:
            Created WorkerPool object

        Raises:
            ValueError: If cluster doesn't exist or pool name exists in cluster
        """
        # Verify cluster exists
        cluster = self.get_cluster(cluster_id)
        if not cluster:
            raise ValueError(f"Cluster with ID {cluster_id} not found")

        # Check if pool name already exists in cluster
        existing = self.db.query(WorkerPool).filter(
            and_(WorkerPool.cluster_id == cluster_id, WorkerPool.name == name)
        ).first()

        if existing:
            raise ValueError(f"Worker pool with name '{name}' already exists in cluster")

        pool = WorkerPool(
            cluster_id=cluster_id,
            name=name,
            min_workers=min_workers,
            max_workers=max_workers,
            config=config or {},
            status=WorkerPoolStatus.RUNNING
        )
        self.db.add(pool)
        self.db.commit()
        self.db.refresh(pool)

        return pool

    def get_worker_pool(self, pool_id: int) -> Optional[WorkerPool]:
        """Get a worker pool by ID."""
        return self.db.query(WorkerPool).filter(WorkerPool.id == pool_id).first()

    def list_worker_pools(
        self,
        cluster_id: Optional[int] = None,
        status: Optional[WorkerPoolStatus] = None
    ) -> List[WorkerPool]:
        """
        List worker pools with optional filtering.

        Args:
            cluster_id: Filter by cluster ID
            status: Filter by status

        Returns:
            List of WorkerPool objects
        """
        query = self.db.query(WorkerPool)

        if cluster_id:
            query = query.filter(WorkerPool.cluster_id == cluster_id)
        if status:
            query = query.filter(WorkerPool.status == status)

        return query.order_by(WorkerPool.created_at.desc()).all()

    def update_worker_pool(
        self,
        pool_id: int,
        **kwargs
    ) -> Optional[WorkerPool]:
        """
        Update a worker pool.

        Args:
            pool_id: Pool ID
            **kwargs: Fields to update (name, min_workers, max_workers, config, status)

        Returns:
            Updated WorkerPool object or None if not found
        """
        pool = self.get_worker_pool(pool_id)
        if not pool:
            return None

        # Update allowed fields
        allowed_fields = {"name", "min_workers", "max_workers", "config", "status"}
        for key, value in kwargs.items():
            if key in allowed_fields and hasattr(pool, key):
                setattr(pool, key, value)

        self.db.commit()
        self.db.refresh(pool)

        return pool

    def delete_worker_pool(self, pool_id: int) -> bool:
        """
        Delete a worker pool.

        Args:
            pool_id: Pool ID

        Returns:
            True if deleted, False if not found

        Raises:
            ValueError: If pool has workers assigned
        """
        pool = self.get_worker_pool(pool_id)
        if not pool:
            return False

        # Check for workers in pool
        worker_count = self.db.query(Worker).filter(
            Worker.pool_id == pool_id
        ).count()

        if worker_count > 0:
            raise ValueError(
                f"Cannot delete worker pool with {worker_count} workers. "
                "Reassign or remove the workers first."
            )

        self.db.delete(pool)
        self.db.commit()

        return True

    def get_worker_pool_stats(self, pool_id: int) -> Dict[str, Any]:
        """
        Get statistics for a worker pool.

        Args:
            pool_id: Pool ID

        Returns:
            Dictionary with pool statistics
        """
        pool = self.get_worker_pool(pool_id)
        if not pool:
            return {}

        # Count workers in pool
        workers = self.db.query(Worker).filter(Worker.pool_id == pool_id).all()

        worker_stats = {"total": len(workers), "by_status": {}}
        for worker in workers:
            status = worker.status.value if hasattr(worker.status, 'value') else str(worker.status)
            worker_stats["by_status"][status] = worker_stats["by_status"].get(status, 0) + 1

        return {
            "id": pool.id,
            "name": pool.name,
            "cluster_id": pool.cluster_id,
            "min_workers": pool.min_workers,
            "max_workers": pool.max_workers,
            "status": pool.status.value if hasattr(pool.status, 'value') else str(pool.status),
            "workers": worker_stats,
            "created_at": pool.created_at.isoformat() if pool.created_at else None
        }

    def scale_worker_pool(
        self,
        pool_id: int,
        min_workers: Optional[int] = None,
        max_workers: Optional[int] = None
    ) -> Optional[WorkerPool]:
        """
        Scale a worker pool by adjusting min/max workers.

        Args:
            pool_id: Pool ID
            min_workers: New minimum workers
            max_workers: New maximum workers

        Returns:
            Updated WorkerPool object or None if not found

        Raises:
            ValueError: If min_workers > max_workers
        """
        pool = self.get_worker_pool(pool_id)
        if not pool:
            return None

        # Apply constraints
        if min_workers is not None and max_workers is not None:
            if min_workers > max_workers:
                raise ValueError("min_workers cannot be greater than max_workers")

        updates = {}
        if min_workers is not None:
            updates["min_workers"] = min_workers
        if max_workers is not None:
            updates["max_workers"] = max_workers

        return self.update_worker_pool(pool_id, **updates)

    # ========================================================================
    # Health and Status
    # ========================================================================

    def check_cluster_health(self, cluster_id: int) -> Dict[str, Any]:
        """
        Check the health status of a cluster.

        Args:
            cluster_id: Cluster ID

        Returns:
            Dictionary with health status
        """
        cluster = self.get_cluster(cluster_id)
        if not cluster:
            return {"status": "unknown", "message": "Cluster not found"}

        from datetime import timedelta

        # Get workers
        workers = self.db.query(Worker).filter(Worker.cluster_id == cluster_id).all()
        total_workers = len(workers)

        # Check for recent heartbeats (within 60 seconds)
        timeout = datetime.utcnow() - timedelta(seconds=60)
        healthy_workers = sum(1 for w in workers if w.last_heartbeat_at and w.last_heartbeat_at >= timeout)

        # Determine overall health
        if total_workers == 0:
            health_status = "warning"
            message = "No workers in cluster"
        elif healthy_workers == total_workers:
            health_status = "healthy"
            message = f"All {total_workers} workers healthy"
        else:
            health_status = "degraded"
            message = f"{healthy_workers}/{total_workers} workers healthy"

        return {
            "status": health_status,
            "message": message,
            "cluster_id": cluster_id,
            "cluster_name": cluster.name,
            "total_workers": total_workers,
            "healthy_workers": healthy_workers,
            "unhealthy_workers": total_workers - healthy_workers
        }
