"""
Unit tests for WorkerController.
"""
import pytest
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from backend.models.database import (
    Cluster, Worker, WorkerStatus, ClusterType
)
from backend.server.controllers.worker_controller import WorkerController


@pytest.fixture
def test_cluster(db_session: Session):
    """Create a test cluster."""
    cluster = Cluster(
        name="test-cluster",
        type=ClusterType.STANDALONE,
        is_default=True
    )
    db_session.add(cluster)
    db_session.commit()
    db_session.refresh(cluster)
    return cluster


@pytest.mark.unit
class TestWorkerController:
    """Tests for WorkerController."""

    # ========================================================================
    # Create Worker Tests
    # ========================================================================

    def test_create_worker(self, db_session: Session, test_cluster):
        """Test creating a new worker."""
        controller = WorkerController(db_session)

        worker = controller.create_worker(
            name="test-worker",
            ip="192.168.1.100",
            ifname="eth0",
            hostname="worker-01",
            cluster_id=test_cluster.id
        )

        # Verify
        assert worker.id is not None
        assert worker.name == "test-worker"
        assert worker.ip == "192.168.1.100"
        assert worker.ifname == "eth0"
        assert worker.hostname == "worker-01"
        assert worker.status == WorkerStatus.REGISTERING
        assert worker.cluster_id == test_cluster.id

    def test_create_worker_with_cluster(self, db_session: Session):
        """Test creating a worker in a cluster."""
        # Create cluster
        cluster = Cluster(
            name="test-cluster",
            type=ClusterType.STANDALONE,
            is_default=True
        )
        db_session.add(cluster)
        db_session.commit()
        db_session.refresh(cluster)

        # Create worker
        controller = WorkerController(db_session)
        worker = controller.create_worker(
            name="test-worker",
            ip="192.168.1.100",
            cluster_id=cluster.id
        )

        # Verify
        assert worker.cluster_id == cluster.id
        assert worker.status == WorkerStatus.REGISTERING

    def test_create_worker_with_token(self, db_session: Session, test_cluster):
        """Test creating a worker with token hash."""
        controller = WorkerController(db_session)

        worker = controller.create_worker(
            name="test-worker",
            ip="192.168.1.100",
            cluster_id=test_cluster.id,
            token_hash="hashed_token_abc123"
        )

        # Verify
        assert worker.token_hash == "hashed_token_abc123"

    # ========================================================================
    # Get Worker Tests
    # ========================================================================

    def test_get_worker_by_id(self, db_session: Session, test_cluster):
        """Test getting a worker by ID."""
        controller = WorkerController(db_session)

        # Create worker
        created = controller.create_worker(
            name="test-worker",
            ip="192.168.1.100",
            cluster_id=test_cluster.id
        )

        # Get worker
        retrieved = controller.get_worker(created.id)

        # Verify
        assert retrieved is not None
        assert retrieved.id == created.id
        assert retrieved.name == "test-worker"
        assert retrieved.ip == "192.168.1.100"

    def test_get_worker_not_found(self, db_session: Session):
        """Test getting a non-existent worker."""
        controller = WorkerController(db_session)
        worker = controller.get_worker(999)
        assert worker is None

    def test_get_worker_by_name(self, db_session: Session, test_cluster):
        """Test getting a worker by name."""
        controller = WorkerController(db_session)

        # Create worker
        created = controller.create_worker(
            name="test-worker",
            ip="192.168.1.100",
            cluster_id=test_cluster.id
        )

        # Get by name
        retrieved = controller.get_worker_by_name("test-worker")

        # Verify
        assert retrieved is not None
        assert retrieved.id == created.id
        assert retrieved.name == "test-worker"

    def test_get_worker_by_name_with_cluster(self, db_session: Session):
        """Test getting a worker by name within a cluster."""
        # Create cluster
        cluster = Cluster(
            name="test-cluster",
            type=ClusterType.STANDALONE,
            is_default=True
        )
        db_session.add(cluster)
        db_session.commit()
        db_session.refresh(cluster)

        controller = WorkerController(db_session)

        # Create worker
        created = controller.create_worker(
            name="test-worker",
            ip="192.168.1.100",
            cluster_id=cluster.id
        )

        # Get by name with cluster
        retrieved = controller.get_worker_by_name("test-worker", cluster_id=cluster.id)

        # Verify
        assert retrieved is not None
        assert retrieved.id == created.id

    def test_get_worker_by_name_not_found(self, db_session: Session):
        """Test getting a non-existent worker by name."""
        controller = WorkerController(db_session)
        worker = controller.get_worker_by_name("non-existent")
        assert worker is None

    # ========================================================================
    # List Workers Tests
    # ========================================================================

    def test_list_workers_all(self, db_session: Session, test_cluster):
        """Test listing all workers."""
        controller = WorkerController(db_session)

        # Create multiple workers
        controller.create_worker(name="worker-1", ip="192.168.1.101", cluster_id=test_cluster.id)
        controller.create_worker(name="worker-2", ip="192.168.1.102", cluster_id=test_cluster.id)
        controller.create_worker(name="worker-3", ip="192.168.1.103", cluster_id=test_cluster.id)

        # List all
        workers = controller.list_workers()

        # Verify
        assert len(workers) >= 3

    def test_list_workers_by_cluster(self, db_session: Session):
        """Test listing workers filtered by cluster."""
        # Create two clusters
        cluster1 = Cluster(name="cluster-1", type=ClusterType.STANDALONE)
        cluster2 = Cluster(name="cluster-2", type=ClusterType.STANDALONE)
        db_session.add(cluster1)
        db_session.add(cluster2)
        db_session.commit()

        controller = WorkerController(db_session)

        # Create workers in different clusters
        controller.create_worker(name="worker-1", ip="192.168.1.101", cluster_id=cluster1.id)
        controller.create_worker(name="worker-2", ip="192.168.1.102", cluster_id=cluster1.id)
        controller.create_worker(name="worker-3", ip="192.168.1.103", cluster_id=cluster2.id)

        # List workers for cluster1
        cluster1_workers = controller.list_workers(cluster_id=cluster1.id)

        # Verify
        assert len(cluster1_workers) == 2
        assert all(w.cluster_id == cluster1.id for w in cluster1_workers)

    def test_list_workers_by_status(self, db_session: Session, test_cluster):
        """Test listing workers filtered by status."""
        controller = WorkerController(db_session)

        # Create workers with different statuses
        worker1 = controller.create_worker(name="worker-1", ip="192.168.1.101", cluster_id=test_cluster.id)
        worker2 = controller.create_worker(name="worker-2", ip="192.168.1.102", cluster_id=test_cluster.id)

        # Update status
        worker1.status = WorkerStatus.READY
        worker2.status = WorkerStatus.BUSY
        db_session.commit()

        # List READY workers
        ready_workers = controller.list_workers(status=WorkerStatus.READY)

        # Verify
        assert len(ready_workers) >= 1
        assert all(w.status == WorkerStatus.READY for w in ready_workers)

    def test_list_workers_with_pagination(self, db_session: Session, test_cluster):
        """Test listing workers with pagination."""
        controller = WorkerController(db_session)

        # Create multiple workers
        for i in range(10):
            controller.create_worker(name=f"worker-{i}", ip=f"192.168.1.{100+i}", cluster_id=test_cluster.id)

        # Get first page
        page1 = controller.list_workers(limit=5, offset=0)

        # Get second page
        page2 = controller.list_workers(limit=5, offset=5)

        # Verify
        assert len(page1) == 5
        assert len(page2) == 5
        assert page1[0].id != page2[0].id  # Different workers

    # ========================================================================
    # Update Worker Tests
    # ========================================================================

    def test_update_worker_status(self, db_session: Session, test_cluster):
        """Test updating worker status."""
        controller = WorkerController(db_session)

        # Create worker
        worker = controller.create_worker(name="test-worker", ip="192.168.1.100", cluster_id=test_cluster.id)

        # Update status
        updated = controller.update_worker_status(worker.id, WorkerStatus.READY)

        # Verify
        assert updated is not None
        assert updated.status == WorkerStatus.READY
        assert updated.id == worker.id

    def test_update_worker_status_not_found(self, db_session: Session):
        """Test updating status for non-existent worker."""
        controller = WorkerController(db_session)
        updated = controller.update_worker_status(999, WorkerStatus.READY)
        assert updated is None

    def test_update_worker_heartbeat(self, db_session: Session, test_cluster):
        """Test updating worker heartbeat."""
        controller = WorkerController(db_session)

        # Create worker
        worker = controller.create_worker(name="test-worker", ip="192.168.1.100", cluster_id=test_cluster.id)

        # Clear initial heartbeat
        worker.last_heartbeat_at = None
        db_session.commit()

        # Update heartbeat
        updated = controller.update_worker_heartbeat(worker.id)

        # Verify
        assert updated is not None
        assert updated.last_heartbeat_at is not None

    def test_update_worker_heartbeat_not_found(self, db_session: Session):
        """Test updating heartbeat for non-existent worker."""
        controller = WorkerController(db_session)
        updated = controller.update_worker_heartbeat(999)
        assert updated is None

    def test_update_worker_gpu_count(self, db_session: Session, test_cluster):
        """Test updating worker GPU count."""
        controller = WorkerController(db_session)

        # Create worker
        worker = controller.create_worker(name="test-worker", ip="192.168.1.100", cluster_id=test_cluster.id)

        # Update GPU count
        updated = controller.update_worker_gpu_count(worker.id, 4)

        # Verify
        assert updated is not None
        assert updated.gpu_count == 4

    def test_update_worker_gpu_count_not_found(self, db_session: Session):
        """Test updating GPU count for non-existent worker."""
        controller = WorkerController(db_session)
        updated = controller.update_worker_gpu_count(999, 4)
        assert updated is None

    # ========================================================================
    # Delete Worker Tests
    # ========================================================================

    def test_delete_worker(self, db_session: Session, test_cluster):
        """Test deleting a worker."""
        controller = WorkerController(db_session)

        # Create worker
        worker = controller.create_worker(name="test-worker", ip="192.168.1.100", cluster_id=test_cluster.id)
        worker_id = worker.id

        # Delete
        result = controller.delete_worker(worker_id)

        # Verify
        assert result is True

        # Worker should no longer exist
        deleted_worker = controller.get_worker(worker_id)
        assert deleted_worker is None

    def test_delete_worker_not_found(self, db_session: Session):
        """Test deleting a non-existent worker."""
        controller = WorkerController(db_session)
        result = controller.delete_worker(999)
        assert result is False

    # ========================================================================
    # Health Check Tests
    # ========================================================================

    def test_mark_unhealthy_workers(self, db_session: Session, test_cluster):
        """Test marking workers as unhealthy."""
        controller = WorkerController(db_session)

        # Create a worker with old heartbeat
        worker = controller.create_worker(name="test-worker", ip="192.168.1.100", cluster_id=test_cluster.id)
        worker.status = WorkerStatus.READY
        worker.last_heartbeat_at = datetime.utcnow() - timedelta(seconds=120)
        db_session.commit()

        # Mark unhealthy (timeout=90s)
        unhealthy = controller.mark_unhealthy_workers(timeout_seconds=90)

        # Verify
        assert len(unhealthy) > 0
        assert worker.id in [w.id for w in unhealthy]
        db_session.refresh(worker)
        assert worker.status == WorkerStatus.UNHEALTHY

    def test_mark_unhealthy_workers_no_timeout(self, db_session: Session, test_cluster):
        """Test that recent workers are not marked unhealthy."""
        controller = WorkerController(db_session)

        # Create a worker with recent heartbeat
        worker = controller.create_worker(name="test-worker", ip="192.168.1.100", cluster_id=test_cluster.id)
        worker.status = WorkerStatus.READY
        worker.last_heartbeat_at = datetime.utcnow() - timedelta(seconds=30)
        db_session.commit()

        # Mark unhealthy (timeout=90s)
        unhealthy = controller.mark_unhealthy_workers(timeout_seconds=90)

        # Verify
        assert len(unhealthy) == 0
        db_session.refresh(worker)
        assert worker.status == WorkerStatus.READY

    def test_get_workers_by_status(self, db_session: Session, test_cluster):
        """Test getting workers by status."""
        controller = WorkerController(db_session)

        # Create workers with different statuses
        worker1 = controller.create_worker(name="worker-1", ip="192.168.1.101", cluster_id=test_cluster.id)
        worker2 = controller.create_worker(name="worker-2", ip="192.168.1.102", cluster_id=test_cluster.id)

        worker1.status = WorkerStatus.READY
        worker2.status = WorkerStatus.BUSY
        db_session.commit()

        # Get READY workers
        ready_workers = controller.get_workers_by_status(WorkerStatus.READY)

        # Verify
        assert len(ready_workers) >= 1
        assert all(w.status == WorkerStatus.READY for w in ready_workers)

    def test_get_available_workers(self, db_session: Session, test_cluster):
        """Test getting available workers."""
        controller = WorkerController(db_session)

        # Create workers
        worker1 = controller.create_worker(name="worker-1", ip="192.168.1.101", cluster_id=test_cluster.id)
        worker2 = controller.create_worker(name="worker-2", ip="192.168.1.102", cluster_id=test_cluster.id)

        worker1.status = WorkerStatus.READY
        worker2.status = WorkerStatus.BUSY
        db_session.commit()

        # Get available workers
        available = controller.get_available_workers()

        # Verify
        assert len(available) >= 1
        assert all(w.status == WorkerStatus.READY for w in available)

    def test_drain_worker(self, db_session: Session, test_cluster):
        """Test draining a worker."""
        controller = WorkerController(db_session)

        # Create worker
        worker = controller.create_worker(name="test-worker", ip="192.168.1.100", cluster_id=test_cluster.id)

        # Drain worker
        drained = controller.drain_worker(worker.id)

        # Verify
        assert drained is not None
        assert drained.status == WorkerStatus.DRAINING

    def test_drain_worker_not_found(self, db_session: Session):
        """Test draining a non-existent worker."""
        controller = WorkerController(db_session)
        drained = controller.drain_worker(999)
        assert drained is None
