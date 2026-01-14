"""
Cluster Controller - manages clusters.
"""
from typing import List, Optional, Dict, Any
import logging

from sqlalchemy.orm import Session
from backend.models.database import Cluster, ClusterType

logger = logging.getLogger(__name__)


class ClusterController:
    """Controller for managing Cluster entities."""

    def __init__(self, db_session: Session):
        """Initialize ClusterController.

        Args:
            db_session: SQLAlchemy database session
        """
        self.db = db_session

    def create_cluster(
        self,
        name: str,
        cluster_type: ClusterType = ClusterType.STANDALONE,
        description: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None,
    ) -> Cluster:
        """Create a new cluster.

        Args:
            name: Cluster name (must be unique)
            cluster_type: Type of cluster (docker, kubernetes, standalone)
            description: Optional description
            config: Optional cluster-specific configuration

        Returns:
            Created Cluster instance
        """
        cluster = Cluster(
            name=name,
            type=cluster_type,
            description=description,
            config=config or {},
        )

        self.db.add(cluster)
        self.db.commit()
        self.db.refresh(cluster)

        logger.info(f"Created cluster: {cluster.id} - {name}")
        return cluster

    def get_cluster(self, cluster_id: int) -> Optional[Cluster]:
        """Get a cluster by ID.

        Args:
            cluster_id: Cluster ID

        Returns:
            Cluster instance or None if not found
        """
        return self.db.query(Cluster).filter(Cluster.id == cluster_id).first()

    def get_cluster_by_name(self, name: str) -> Optional[Cluster]:
        """Get a cluster by name.

        Args:
            name: Cluster name

        Returns:
            Cluster instance or None if not found
        """
        return self.db.query(Cluster).filter(Cluster.name == name).first()

    def list_clusters(
        self,
        cluster_type: Optional[ClusterType] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Cluster]:
        """List clusters with optional filters.

        Args:
            cluster_type: Optional cluster type filter
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            List of Cluster instances
        """
        query = self.db.query(Cluster)

        if cluster_type is not None:
            query = query.filter(Cluster.type == cluster_type)

        return query.order_by(Cluster.created_at.desc()).limit(limit).offset(offset).all()

    def update_cluster(
        self,
        cluster_id: int,
        name: Optional[str] = None,
        description: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None,
    ) -> Optional[Cluster]:
        """Update a cluster.

        Args:
            cluster_id: Cluster ID
            name: Optional new name
            description: Optional new description
            config: Optional new configuration

        Returns:
            Updated Cluster instance or None if not found
        """
        cluster = self.get_cluster(cluster_id)
        if not cluster:
            return None

        if name is not None:
            cluster.name = name
        if description is not None:
            cluster.description = description
        if config is not None:
            cluster.config = config

        self.db.commit()
        self.db.refresh(cluster)

        logger.info(f"Updated cluster: {cluster_id}")
        return cluster

    def delete_cluster(self, cluster_id: int) -> bool:
        """Delete a cluster.

        Args:
            cluster_id: Cluster ID

        Returns:
            True if deleted, False if not found
        """
        cluster = self.get_cluster(cluster_id)
        if not cluster:
            return False

        self.db.delete(cluster)
        self.db.commit()

        logger.info(f"Deleted cluster: {cluster_id}")
        return True

    def get_cluster_workers(self, cluster_id: int) -> List[Any]:
        """Get all workers in a cluster.

        Args:
            cluster_id: Cluster ID

        Returns:
            List of Worker instances
        """
        from backend.models.database import Worker

        return self.db.query(Worker).filter(Worker.cluster_id == cluster_id).all()

    def get_cluster_stats(self, cluster_id: int) -> Dict[str, Any]:
        """Get statistics for a cluster.

        Args:
            cluster_id: Cluster ID

        Returns:
            Dictionary with cluster statistics
        """
        from backend.models.database import Worker, ModelInstance
        from sqlalchemy import func

        cluster = self.get_cluster(cluster_id)
        if not cluster:
            return {}

        # Count workers
        worker_count = self.db.query(func.count(Worker.id)).filter(
            Worker.cluster_id == cluster_id
        ).scalar()

        # Count model instances
        instance_count = self.db.query(func.count(ModelInstance.id)).join(
            Worker, ModelInstance.worker_id == Worker.id
        ).filter(Worker.cluster_id == cluster_id).scalar()

        return {
            "id": cluster.id,
            "name": cluster.name,
            "type": cluster.type.value,
            "worker_count": worker_count or 0,
            "instance_count": instance_count or 0,
        }
