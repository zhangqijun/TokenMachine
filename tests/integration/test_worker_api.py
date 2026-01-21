"""
Integration tests for Worker API endpoints.

Tests the complete HTTP request/response cycle for Worker management.
"""
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.models.database import (
    Cluster, Worker, WorkerStatus, ClusterType, ClusterStatus
)
from backend.api.v1.workers import router


@pytest.fixture
def client(integration_db_session: Session):
    """Create test client with worker router only."""
    # Create minimal FastAPI app with just the worker router
    app = FastAPI()
    app.include_router(router)

    # Override get_db dependency
    from backend.api.v1 import workers
    original_get_db = workers.get_db

    def override_get_db():
        try:
            yield integration_db_session
        finally:
            pass

    workers.get_db = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    # Restore
    workers.get_db = original_get_db


@pytest.fixture
def test_cluster(integration_db_session: Session):
    """Create a test cluster."""
    cluster = Cluster(
        name="test-cluster",
        type=ClusterType.STANDALONE,
        is_default=True,
        status=ClusterStatus.RUNNING
    )
    integration_db_session.add(cluster)
    integration_db_session.commit()
    integration_db_session.refresh(cluster)
    return cluster


@pytest.mark.integration
class TestWorkerCreateAPI:
    """Tests for POST /api/v1/workers endpoint."""

    def test_create_worker_success(self, client: TestClient, test_cluster):
        """Test successfully creating a worker."""
        response = client.post(
            "/workers",
            json={
                "name": "test-worker",
                "cluster_id": test_cluster.id,
                "expected_gpu_count": 4
            }
        )

        # Verify HTTP response
        assert response.status_code == 201

        # Verify response structure
        data = response.json()
        assert "id" in data
        assert "name" in data
        assert "status" in data
        assert "register_token" in data
        assert "install_command" in data
        assert "expected_gpu_count" in data
        assert "current_gpu_count" in data
        assert "created_at" in data

        # Verify values
        assert data["name"] == "test-worker"
        assert data["status"] == "registering"
        assert data["expected_gpu_count"] == 4
        assert data["current_gpu_count"] == 0
        assert "TM_TOKEN=" in data["install_command"]
        assert len(data["register_token"]) > 0

    def test_create_worker_with_default_cluster(self, client: TestClient, integration_db_session):
        """Test creating worker without specifying cluster (uses default)."""
        # Create default cluster
        default_cluster = Cluster(
            name="default",
            type=ClusterType.STANDALONE,
            is_default=True,
            status=ClusterStatus.RUNNING
        )
        integration_db_session.add(default_cluster)
        integration_db_session.commit()

        response = client.post(
            "/workers",
            json={
                "name": "default-worker",
                "expected_gpu_count": 2
            }
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "default-worker"

    def test_create_worker_with_labels(self, client: TestClient, test_cluster):
        """Test creating worker with custom labels."""
        response = client.post(
            "/workers",
            json={
                "name": "labeled-worker",
                "cluster_id": test_cluster.id,
                "labels": {
                    "gpu-type": "A100",
                    "zone": "us-west-1",
                    "rack": "rack-01"
                }
            }
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "labeled-worker"

    def test_create_worker_duplicate_name(self, client: TestClient, test_cluster):
        """Test creating worker with duplicate name returns 409."""
        # Create first worker
        client.post(
            "/workers",
            json={
                "name": "duplicate-worker",
                "cluster_id": test_cluster.id
            }
        )

        # Try to create duplicate
        response = client.post(
            "/workers",
            json={
                "name": "duplicate-worker",
                "cluster_id": test_cluster.id
            }
        )

        assert response.status_code == 409
        data = response.json()
        assert "already exists" in data["detail"].lower()

    def test_create_worker_invalid_cluster(self, client: TestClient):
        """Test creating worker with non-existent cluster."""
        response = client.post(
            "/workers",
            json={
                "name": "orphan-worker",
                "cluster_id": 99999
            }
        )

        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"].lower()


@pytest.mark.integration
class TestWorkerListAPI:
    """Tests for GET /api/v1/workers endpoint."""

    def test_list_workers_empty(self, client: TestClient):
        """Test listing workers when none exist."""
        response = client.get("/workers")

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert "page" in data
        assert "page_size" in data
        assert data["total"] == 0
        assert len(data["items"]) == 0

    def test_list_workers_with_data(self, client: TestClient, test_cluster):
        """Test listing workers with multiple workers."""
        # Create multiple workers
        for i in range(3):
            client.post(
                "/workers",
                json={
                    "name": f"worker-{i}",
                    "cluster_id": test_cluster.id
                }
            )

        response = client.get("/workers")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 3
        assert len(data["items"]) >= 3


@pytest.mark.integration
class TestWorkerGetAPI:
    """Tests for GET /api/v1/workers/{worker_id} endpoint."""

    def test_get_worker_success(self, client: TestClient, test_cluster):
        """Test getting a worker by ID."""
        # Create worker
        create_response = client.post(
            "/workers",
            json={
                "name": "get-test-worker",
                "cluster_id": test_cluster.id
            }
        )
        worker_id = create_response.json()["id"]

        # Get worker
        response = client.get(f"/workers/{worker_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == worker_id
        assert data["name"] == "get-test-worker"

    def test_get_worker_not_found(self, client: TestClient):
        """Test getting non-existent worker."""
        response = client.get("/workers/99999")

        assert response.status_code == 404


@pytest.mark.integration
class TestWorkerSetStatusAPI:
    """Tests for POST /api/v1/workers/{worker_id}/set-status endpoint."""

    def test_set_worker_status(self, client: TestClient, test_cluster):
        """Test setting worker status."""
        # Create worker
        create_response = client.post(
            "/workers",
            json={
                "name": "status-worker",
                "cluster_id": test_cluster.id
            }
        )
        worker_id = create_response.json()["id"]

        # Set status to ready
        response = client.post(
            f"/workers/{worker_id}/set-status?new_status=ready"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "ready" in data["message"].lower()

    def test_set_worker_status_not_found(self, client: TestClient):
        """Test setting status for non-existent worker."""
        response = client.post(
            "/workers/99999/set-status?new_status=ready"
        )

        assert response.status_code == 404


@pytest.mark.integration
class TestWorkerStatsAPI:
    """Tests for GET /api/v1/workers/{worker_id}/stats endpoint."""

    def test_get_worker_stats(self, client: TestClient, test_cluster):
        """Test getting worker statistics."""
        # Create worker
        create_response = client.post(
            "/workers",
            json={
                "name": "stats-worker",
                "cluster_id": test_cluster.id,
                "expected_gpu_count": 4
            }
        )
        worker_id = create_response.json()["id"]

        # Get stats
        response = client.get(f"/workers/{worker_id}/stats")

        assert response.status_code == 200
        data = response.json()
        assert "worker_id" in data
        assert "worker_name" in data
        assert "status" in data
        assert "total_gpus" in data
        assert "in_use_gpus" in data
        assert "error_gpus" in data

    def test_get_worker_stats_not_found(self, client: TestClient):
        """Test getting stats for non-existent worker."""
        response = client.get("/workers/99999/stats")

        assert response.status_code == 404


@pytest.mark.integration
class TestWorkerAddGPUAPI:
    """Tests for POST /api/v1/workers/{worker_id}/add-gpu endpoint."""

    def test_add_gpu_token(self, client: TestClient, test_cluster):
        """Test getting token for adding GPUs to worker."""
        # Create worker
        create_response = client.post(
            "/workers",
            json={
                "name": "add-gpu-worker",
                "cluster_id": test_cluster.id
            }
        )
        worker_id = create_response.json()["id"]

        # Get add GPU token
        response = client.post(f"/workers/{worker_id}/add-gpu")

        assert response.status_code == 200
        data = response.json()
        assert "register_token" in data
        assert "install_command" in data
        assert "message" in data

    def test_add_gpu_not_found(self, client: TestClient):
        """Test adding GPU to non-existent worker."""
        response = client.post("/workers/99999/add-gpu")

        assert response.status_code == 404


@pytest.mark.integration
class TestWorkerDeleteAPI:
    """Tests for DELETE /api/v1/workers/{worker_id} endpoint."""

    def test_delete_worker_success(self, client: TestClient, test_cluster):
        """Test deleting a worker."""
        # Create worker
        create_response = client.post(
            "/workers",
            json={
                "name": "delete-worker",
                "cluster_id": test_cluster.id
            }
        )
        worker_id = create_response.json()["id"]

        # Delete worker
        response = client.delete(f"/workers/{worker_id}")

        assert response.status_code == 204

        # Verify deleted
        get_response = client.get(f"/workers/{worker_id}")
        assert get_response.status_code == 404

    def test_delete_worker_not_found(self, client: TestClient):
        """Test deleting non-existent worker."""
        response = client.delete("/workers/99999")

        assert response.status_code == 404


@pytest.mark.integration
class TestWorkerLifecycle:
    """Tests for complete worker lifecycle."""

    def test_worker_full_lifecycle(self, client: TestClient, test_cluster):
        """Test worker from creation to deletion."""
        # 1. Create worker
        create_response = client.post(
            "/workers",
            json={
                "name": "lifecycle-worker",
                "cluster_id": test_cluster.id,
                "expected_gpu_count": 2
            }
        )
        assert create_response.status_code == 201
        worker_id = create_response.json()["id"]
        initial_token = create_response.json()["register_token"]

        # 2. Get worker details
        get_response = client.get(f"/workers/{worker_id}")
        assert get_response.status_code == 200
        assert get_response.json()["name"] == "lifecycle-worker"

        # 3. Update status to ready
        status_response = client.post(
            f"/workers/{worker_id}/set-status?new_status=ready"
        )
        assert status_response.status_code == 200

        # 4. Get stats
        stats_response = client.get(f"/workers/{worker_id}/stats")
        assert stats_response.status_code == 200

        # 5. Add GPU token
        add_gpu_response = client.post(f"/workers/{worker_id}/add-gpu")
        assert add_gpu_response.status_code == 200
        new_token = add_gpu_response.json()["register_token"]
        assert new_token != initial_token  # Should be different token

        # 6. Delete worker
        delete_response = client.delete(f"/workers/{worker_id}")
        assert delete_response.status_code == 204

        # 7. Verify deletion
        final_get = client.get(f"/workers/{worker_id}")
        assert final_get.status_code == 404
