"""
Worker Service tests.

This module tests the WorkerService business logic layer.
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

from backend.services.worker_service import WorkerService
from backend.models.database import Worker, WorkerStatus, Cluster, GPUDevice, GPUDeviceState, ModelInstance
from backend.core.security import hash_worker_token


# ============================================================================
# Worker Registration Tests
# ============================================================================

class TestWorkerServiceRegistration:
    """Test worker registration in service layer."""

    @pytest.mark.unit
    def test_register_worker_success(self, db_session, test_cluster):
        """Test successful worker registration."""
        service = WorkerService(db_session)
        token_hash = hash_worker_token("test-token")

        worker = service.register_worker(
            name="test-worker-new",
            cluster_id=test_cluster.id,
            ip="192.168.1.100",
            port=8080,
            hostname="worker-host",
            labels={"gpu_type": "nvidia"},
            token_hash=token_hash
        )

        assert worker.id is not None
        assert worker.name == "test-worker-new"
        assert worker.cluster_id == test_cluster.id
        assert worker.ip == "192.168.1.100"
        assert worker.status == WorkerStatus.REGISTERING
        assert worker.token_hash == token_hash

    @pytest.mark.unit
    def test_register_worker_update_existing(self, db_session, test_cluster, test_worker):
        """Test updating existing worker on re-registration."""
        service = WorkerService(db_session)
        new_token_hash = hash_worker_token("new-token")

        worker = service.register_worker(
            name=test_worker.name,
            cluster_id=test_cluster.id,
            ip="192.168.1.200",
            port=9000,
            hostname="updated-host",
            labels={"updated": True},
            token_hash=new_token_hash
        )

        assert worker.id == test_worker.id
        assert worker.ip == "192.168.1.200"
        assert worker.port == 9000
        assert worker.hostname == "updated-host"
        assert worker.labels == {"updated": True}
        assert worker.token_hash == new_token_hash
        assert worker.status == WorkerStatus.REGISTERING

    @pytest.mark.unit
    def test_register_worker_nonexistent_cluster(self, db_session):
        """Test registration with non-existent cluster."""
        service = WorkerService(db_session)

        with pytest.raises(ValueError, match="Cluster with ID .* not found"):
            service.register_worker(
                name="test-worker",
                cluster_id=99999
            )

    @pytest.mark.unit
    def test_register_worker_with_pool(self, db_session, test_cluster, test_worker_pool):
        """Test worker registration with pool."""
        service = WorkerService(db_session)

        worker = service.register_worker(
            name="pooled-worker",
            cluster_id=test_cluster.id,
            pool_id=test_worker_pool.id,
            ip="192.168.1.100"
        )

        assert worker.pool_id == test_worker_pool.id

    @pytest.mark.unit
    def test_register_worker_invalid_pool(self, db_session, test_cluster):
        """Test worker registration with invalid pool."""
        service = WorkerService(db_session)

        with pytest.raises(ValueError, match="Worker pool with ID .* not found"):
            service.register_worker(
                name="test-worker",
                cluster_id=test_cluster.id,
                pool_id=99999
            )


# ============================================================================
# Worker Heartbeat Tests
# ============================================================================

class TestWorkerServiceHeartbeat:
    """Test worker heartbeat functionality."""

    @pytest.mark.unit
    def test_heartbeat_success(self, db_session, test_worker):
        """Test successful heartbeat update."""
        service = WorkerService(db_session)

        old_heartbeat = test_worker.last_heartbeat_at
        result = service.heartbeat(test_worker.id)

        assert result is True
        test_worker = db_session.query(Worker).filter(Worker.id == test_worker.id).first()
        assert test_worker.last_heartbeat_at > old_heartbeat

    @pytest.mark.unit
    def test_heartbeat_worker_not_found(self, db_session):
        """Test heartbeat for non-existent worker."""
        service = WorkerService(db_session)

        result = service.heartbeat(99999)
        assert result is False

    @pytest.mark.unit
    def test_heartbeat_recovers_offline_worker(self, db_session):
        """Test heartbeat recovers offline worker."""
        from backend.models.database import Worker

        service = WorkerService(db_session)

        # Create an offline worker
        worker = Worker(
            cluster_id=1,
            name="offline-worker",
            status=WorkerStatus.OFFLINE,
            last_heartbeat_at=datetime.utcnow() - timedelta(seconds=120)
        )
        db_session.add(worker)
        db_session.commit()
        db_session.refresh(worker)

        service.heartbeat(worker.id)

        worker = db_session.query(Worker).filter(Worker.id == worker.id).first()
        assert worker.status == WorkerStatus.READY

    @pytest.mark.unit
    def test_heartbeat_recovers_unhealthy_worker(self, db_session):
        """Test heartbeat recovers unhealthy worker."""
        from backend.models.database import Worker

        service = WorkerService(db_session)

        # Create an unhealthy worker
        worker = Worker(
            cluster_id=1,
            name="unhealthy-worker",
            status=WorkerStatus.UNHEALTHY,
            last_heartbeat_at=datetime.utcnow() - timedelta(seconds=120)
        )
        db_session.add(worker)
        db_session.commit()
        db_session.refresh(worker)

        service.heartbeat(worker.id)

        worker = db_session.query(Worker).filter(Worker.id == worker.id).first()
        assert worker.status == WorkerStatus.READY


# ============================================================================
# Worker Status Update Tests
# ============================================================================

class TestWorkerServiceStatusUpdate:
    """Test worker status updates."""

    @pytest.mark.unit
    def test_update_status_success(self, db_session, test_worker):
        """Test successful status update."""
        service = WorkerService(db_session)

        status_data = {
            "cpu": {"usage": 45.2, "cores": 16},
            "memory": {"total": 64 * 1024, "used": 32 * 1024},
            "gpu_devices": [
                {
                    "uuid": "gpu-0",
                    "name": "NVIDIA A100",
                    "index": 0,
                    "memory_total": 40 * 1024 * 1024 * 1024,
                    "memory_used": 20 * 1024 * 1024 * 1024,
                    "memory_utilization_rate": 50.0,
                    "core_utilization_rate": 30.0,
                    "temperature": 45.0,
                    "state": "available"
                }
            ],
            "filesystem": {
                "/": {"total": 500 * 1024, "used": 200 * 1024}
            }
        }

        result = service.update_status(test_worker.id, status_data)

        assert result is True
        worker = db_session.query(Worker).filter(Worker.id == test_worker.id).first()
        assert worker.status_json == status_data
        assert worker.gpu_count == 1

    @pytest.mark.unit
    def test_update_status_creates_gpu_devices(self, db_session, test_worker):
        """Test status update creates GPU device records."""
        service = WorkerService(db_session)

        status_data = {
            "gpu_devices": [
                {
                    "uuid": "gpu-test-1",
                    "name": "NVIDIA A100",
                    "index": 0,
                    "memory_total": 40 * 1024 * 1024 * 1024,
                    "memory_used": 10 * 1024 * 1024 * 1024,
                    "memory_utilization_rate": 25.0,
                    "temperature": 35.0,
                    "state": "available"
                },
                {
                    "uuid": "gpu-test-2",
                    "name": "NVIDIA A100",
                    "index": 1,
                    "memory_total": 40 * 1024 * 1024 * 1024,
                    "memory_used": 15 * 1024 * 1024 * 1024,
                    "memory_utilization_rate": 37.5,
                    "temperature": 40.0,
                    "state": "in_use"
                }
            ]
        }

        service.update_status(test_worker.id, status_data)

        gpus = db_session.query(GPUDevice).filter(
            GPUDevice.worker_id == test_worker.id
        ).all()

        assert len(gpus) == 2

    @pytest.mark.unit
    def test_update_status_worker_not_found(self, db_session):
        """Test status update for non-existent worker."""
        service = WorkerService(db_session)

        result = service.update_status(99999, {})
        assert result is False


# ============================================================================
# Worker Query Tests
# ============================================================================

class TestWorkerServiceQueries:
    """Test worker query methods."""

    @pytest.mark.unit
    def test_get_worker_success(self, db_session, test_worker):
        """Test getting worker by ID."""
        service = WorkerService(db_session)

        worker = service.get_worker(test_worker.id)

        assert worker is not None
        assert worker.id == test_worker.id
        assert worker.name == test_worker.name

    @pytest.mark.unit
    def test_get_worker_not_found(self, db_session):
        """Test getting non-existent worker."""
        service = WorkerService(db_session)

        worker = service.get_worker(99999)
        assert worker is None

    @pytest.mark.unit
    def test_list_workers_all(self, db_session, test_workers_batch):
        """Test listing all workers."""
        service = WorkerService(db_session)

        workers = service.list_workers()

        assert len(workers) >= len(test_workers_batch)

    @pytest.mark.unit
    def test_list_workers_by_cluster(self, db_session, test_workers_batch, test_cluster):
        """Test listing workers by cluster."""
        service = WorkerService(db_session)

        workers = service.list_workers(cluster_id=test_cluster.id)

        for worker in workers:
            assert worker.cluster_id == test_cluster.id

    @pytest.mark.unit
    def test_list_workers_by_status(self, db_session, test_worker):
        """Test listing workers by status."""
        service = WorkerService(db_session)

        workers = service.list_workers(status=WorkerStatus.READY)

        for worker in workers:
            assert worker.status == WorkerStatus.READY

    @pytest.mark.unit
    def test_list_workers_by_labels(self, db_session, test_worker):
        """Test listing workers by labels filter."""
        service = WorkerService(db_session)

        workers = service.list_workers(
            labels_filter={"gpu_type": "nvidia"}
        )

        for worker in workers:
            assert worker.labels.get("gpu_type") == "nvidia"

    @pytest.mark.unit
    def test_list_workers_by_pool(self, db_session, test_cluster, test_worker_pool):
        """Test listing workers by pool."""
        # Create a worker in the pool
        service = WorkerService(db_session)
        worker = service.register_worker(
            name="pooled-worker",
            cluster_id=test_cluster.id,
            pool_id=test_worker_pool.id,
            ip="192.168.1.100"
        )

        workers = service.list_workers(pool_id=test_worker_pool.id)

        assert len(workers) >= 1
        assert all(w.pool_id == test_worker_pool.id for w in workers)


# ============================================================================
# Worker Update Tests
# ============================================================================

class TestWorkerServiceUpdates:
    """Test worker update methods."""

    @pytest.mark.unit
    def test_update_worker_success(self, db_session, test_worker):
        """Test successful worker update."""
        service = WorkerService(db_session)

        worker = service.update_worker(
            test_worker.id,
            ip="192.168.1.200",
            port=9000,
            labels={"updated": True}
        )

        assert worker is not None
        assert worker.ip == "192.168.1.200"
        assert worker.port == 9000
        assert worker.labels == {"updated": True}

    @pytest.mark.unit
    def test_update_worker_not_found(self, db_session):
        """Test updating non-existent worker."""
        service = WorkerService(db_session)

        worker = service.update_worker(99999, ip="192.168.1.200")
        assert worker is None

    @pytest.mark.unit
    def test_set_worker_status(self, db_session, test_worker):
        """Test setting worker status."""
        service = WorkerService(db_session)

        worker = service.set_worker_status(test_worker.id, WorkerStatus.MAINTENANCE)

        assert worker.status == WorkerStatus.MAINTENANCE

    @pytest.mark.unit
    def test_drain_worker(self, db_session, test_worker):
        """Test draining worker."""
        service = WorkerService(db_session)

        worker = service.drain_worker(test_worker.id)

        assert worker.status == WorkerStatus.DRAINING

    @pytest.mark.unit
    def test_set_worker_maintenance(self, db_session, test_worker):
        """Test setting worker to maintenance mode."""
        service = WorkerService(db_session)

        worker = service.set_worker_maintenance(test_worker.id)

        assert worker.status == WorkerStatus.MAINTENANCE


# ============================================================================
# Worker Deletion Tests
# ============================================================================

class TestWorkerServiceDeletion:
    """Test worker deletion methods."""

    @pytest.mark.unit
    def test_delete_worker_success(self, db_session, test_cluster):
        """Test successful worker deletion."""
        from backend.models.database import Worker

        service = WorkerService(db_session)

        # Create a worker with no running instances
        worker = Worker(
            cluster_id=test_cluster.id,
            name="worker-to-delete",
            status=WorkerStatus.OFFLINE
        )
        db_session.add(worker)
        db_session.commit()
        db_session.refresh(worker)

        result = service.delete_worker(worker.id)

        assert result is True

        deleted_worker = db_session.query(Worker).filter(
            Worker.id == worker.id
        ).first()
        assert deleted_worker is None

    @pytest.mark.unit
    def test_delete_worker_not_found(self, db_session):
        """Test deleting non-existent worker."""
        service = WorkerService(db_session)

        result = service.delete_worker(99999)
        assert result is False

    @pytest.mark.unit
    def test_delete_worker_with_instances_fails(self, db_session, test_model_instance):
        """Test deleting worker with running instances fails."""
        service = WorkerService(db_session)

        with pytest.raises(ValueError, match="Cannot delete worker with .* running instances"):
            service.delete_worker(test_model_instance.worker_id)


# ============================================================================
# Worker Health Monitoring Tests
# ============================================================================

class TestWorkerServiceHealthMonitoring:
    """Test worker health monitoring."""

    @pytest.mark.unit
    def test_check_offline_workers(self, db_session, test_cluster):
        """Test checking for offline workers."""
        from backend.models.database import Worker

        service = WorkerService(db_session)

        # Create a worker with old heartbeat
        worker = Worker(
            cluster_id=test_cluster.id,
            name="stale-worker",
            status=WorkerStatus.READY,
            last_heartbeat_at=datetime.utcnow() - timedelta(seconds=120)
        )
        db_session.add(worker)
        db_session.commit()

        offline_workers = service.check_offline_workers(timeout_seconds=60)

        assert len(offline_workers) >= 1
        assert any(w.name == "stale-worker" for w in offline_workers)

        worker = db_session.query(Worker).filter(Worker.name == "stale-worker").first()
        assert worker.status == WorkerStatus.OFFLINE

    @pytest.mark.unit
    def test_get_unhealthy_workers(self, db_session, test_cluster):
        """Test getting unhealthy workers."""
        from backend.models.database import Worker

        service = WorkerService(db_session)

        # Create unhealthy workers
        for i in range(2):
            worker = Worker(
                cluster_id=test_cluster.id,
                name=f"unhealthy-worker-{i}",
                status=WorkerStatus.OFFLINE,
                last_heartbeat_at=datetime.utcnow() - timedelta(seconds=300)
            )
            db_session.add(worker)
        db_session.commit()

        unhealthy = service.get_unhealthy_workers()

        assert len(unhealthy) >= 2
        assert all("id" in w and "name" in w and "status" in w for w in unhealthy)


# ============================================================================
# Worker Statistics Tests
# ============================================================================

class TestWorkerServiceStatistics:
    """Test worker statistics methods."""

    @pytest.mark.unit
    def test_get_worker_stats(self, db_session, test_worker, test_gpu_devices_batch):
        """Test getting worker statistics."""
        service = WorkerService(db_session)

        stats = service.get_worker_stats(test_worker.id)

        assert stats["id"] == test_worker.id
        assert stats["name"] == test_worker.name
        assert stats["gpu_count"] == test_worker.gpu_count
        assert "gpu_devices" in stats
        assert "model_instances" in stats
        assert "last_heartbeat" in stats

    @pytest.mark.unit
    def test_get_worker_stats_with_instances(self, db_session, test_model_instance):
        """Test worker stats includes model instances."""
        service = WorkerService(db_session)

        stats = service.get_worker_stats(test_model_instance.worker_id)

        assert stats["model_instances"]["total"] >= 1

    @pytest.mark.unit
    def test_get_worker_stats_not_found(self, db_session):
        """Test getting stats for non-existent worker."""
        service = WorkerService(db_session)

        stats = service.get_worker_stats(99999)
        assert stats == {}


# ============================================================================
# Worker Scheduling Tests
# ============================================================================

class TestWorkerServiceScheduling:
    """Test worker scheduling methods."""

    @pytest.mark.unit
    def test_get_workers_for_scheduling(self, db_session, test_worker):
        """Test getting workers available for scheduling."""
        service = WorkerService(db_session)

        workers = service.get_workers_for_scheduling()

        assert len(workers) >= 1
        assert all(w.status in [WorkerStatus.READY, WorkerStatus.BUSY] for w in workers)

    @pytest.mark.unit
    def test_get_workers_for_scheduling_with_gpu_count(self, db_session, test_worker):
        """Test filtering workers by GPU count."""
        service = WorkerService(db_session)

        workers = service.get_workers_for_scheduling(gpu_count=2)

        assert all(w.gpu_count >= 2 for w in workers)

    @pytest.mark.unit
    def test_get_workers_for_scheduling_with_labels(self, db_session, test_worker):
        """Test filtering workers by labels."""
        service = WorkerService(db_session)

        workers = service.get_workers_for_scheduling(
            labels_filter={"gpu_type": "nvidia"}
        )

        assert all(w.labels.get("gpu_type") == "nvidia" for w in workers)

    @pytest.mark.unit
    def test_cleanup_offline_workers(self, db_session, test_cluster):
        """Test cleaning up old offline workers."""
        from backend.models.database import Worker

        service = WorkerService(db_session)

        # Create old offline worker without instances
        worker = Worker(
            cluster_id=test_cluster.id,
            name="old-offline-worker",
            status=WorkerStatus.OFFLINE,
            last_heartbeat_at=datetime.utcnow() - timedelta(seconds=300)
        )
        db_session.add(worker)
        db_session.commit()

        count = service.cleanup_offline_workers(timeout_seconds=120)

        assert count >= 1

        deleted = db_session.query(Worker).filter(
            Worker.name == "old-offline-worker"
        ).first()
        assert deleted is None
