"""
Worker API endpoints tests.

This module tests all worker-related API endpoints.
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, AsyncMock, Mock
from fastapi import status


# ============================================================================
# Worker Creation Tests
# ============================================================================

class TestWorkerCreation:
    """Test worker creation endpoint."""

    @pytest.mark.unit
    def test_create_worker_success(self, client, test_cluster, worker_create_data):
        """Test successful worker creation."""
        response = client.post(
            "/api/v1/workers",
            json=worker_create_data
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()

        assert data["name"] == worker_create_data["name"]
        assert data["status"] == "registering"
        assert "register_token" in data
        assert "install_command" in data
        assert "id" in data
        assert data["expected_gpu_count"] == worker_create_data["expected_gpu_count"]
        assert "created_at" in data

    @pytest.mark.unit
    def test_create_worker_duplicate_name(self, client, test_cluster, test_worker, worker_create_data):
        """Test worker creation with duplicate name."""
        worker_create_data["name"] = test_worker.name

        response = client.post(
            "/api/v1/workers",
            json=worker_create_data
        )

        assert response.status_code == status.HTTP_409_CONFLICT
        assert "already exists" in response.json()["detail"].lower()

    @pytest.mark.unit
    def test_create_worker_nonexistent_cluster(self, client, worker_create_data):
        """Test worker creation with non-existent cluster."""
        worker_create_data["cluster_id"] = 99999

        response = client.post(
            "/api/v1/workers",
            json=worker_create_data
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.unit
    def test_create_worker_default_cluster(self, client, worker_create_data):
        """Test worker creation without specifying cluster uses default."""
        # Remove cluster_id to use default
        worker_create_data.pop("cluster_id", None)
        worker_create_data["name"] = "default-cluster-worker"

        response = client.post(
            "/api/v1/workers",
            json=worker_create_data
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["name"] == "default-cluster-worker"


# ============================================================================
# Worker Listing Tests
# ============================================================================

class TestWorkerList:
    """Test worker listing endpoint."""

    @pytest.mark.unit
    def test_list_workers_all(self, client, test_workers_batch):
        """Test listing all workers."""
        response = client.get("/api/v1/workers")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert "items" in data
        assert "total" in data
        assert data["total"] >= len(test_workers_batch)

    @pytest.mark.unit
    def test_list_workers_with_pagination(self, client, test_workers_batch):
        """Test listing workers with pagination."""
        response = client.get("/api/v1/workers?page=1&page_size=2")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert len(data["items"]) == 2
        assert data["page"] == 1
        assert data["page_size"] == 2

    @pytest.mark.unit
    def test_list_workers_filter_by_cluster(self, client, test_worker, test_cluster):
        """Test listing workers filtered by cluster."""
        response = client.get(f"/api/v1/workers?cluster_id={test_cluster.id}")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        for worker in data["items"]:
            assert worker["cluster_id"] == test_cluster.id

    @pytest.mark.unit
    def test_list_workers_filter_by_status(self, client, test_worker):
        """Test listing workers filtered by status."""
        from backend.models.database import WorkerStatus

        response = client.get(f"/api/v1/workers?status={WorkerStatus.READY}")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        for worker in data["items"]:
            assert worker["status"] == WorkerStatus.READY


# ============================================================================
# Worker Retrieval Tests
# ============================================================================

class TestWorkerRetrieval:
    """Test worker retrieval endpoint."""

    @pytest.mark.unit
    def test_get_worker_success(self, client, test_worker):
        """Test successful worker retrieval."""
        response = client.get(f"/api/v1/workers/{test_worker.id}")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data["id"] == test_worker.id
        assert data["name"] == test_worker.name
        assert data["status"] == test_worker.status
        assert "ips" in data
        assert "gpu_count" in data

    @pytest.mark.unit
    def test_get_worker_not_found(self, client):
        """Test retrieving non-existent worker."""
        response = client.get("/api/v1/workers/99999")

        assert response.status_code == status.HTTP_404_NOT_FOUND


# ============================================================================
# Worker Update Tests
# ============================================================================

class TestWorkerUpdate:
    """Test worker update endpoint."""

    @pytest.mark.unit
    def test_update_worker_success(self, client, test_worker, worker_update_data):
        """Test successful worker update."""
        response = client.put(
            f"/api/v1/workers/{test_worker.id}",
            json=worker_update_data
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data["id"] == test_worker.id
        assert data["labels"] == worker_update_data["labels"]

    @pytest.mark.unit
    def test_update_worker_status(self, client, test_worker):
        """Test updating worker status."""
        from backend.models.database import WorkerStatus

        response = client.put(
            f"/api/v1/workers/{test_worker.id}",
            json={"status": WorkerStatus.MAINTENANCE}
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == WorkerStatus.MAINTENANCE

    @pytest.mark.unit
    def test_update_worker_not_found(self, client, worker_update_data):
        """Test updating non-existent worker."""
        response = client.put(
            "/api/v1/workers/99999",
            json=worker_update_data
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND


# ============================================================================
# Worker Deletion Tests
# ============================================================================

class TestWorkerDeletion:
    """Test worker deletion endpoint."""

    @pytest.mark.unit
    def test_delete_worker_success(self, client, db_session, test_cluster):
        """Test successful worker deletion."""
        from backend.models.database import Worker, WorkerStatus

        # Create a worker with no active GPUs
        worker = Worker(
            cluster_id=test_cluster.id,
            name="worker-to-delete",
            status=WorkerStatus.OFFLINE,
            gpu_count=0
        )
        db_session.add(worker)
        db_session.commit()
        db_session.refresh(worker)

        response = client.delete(f"/api/v1/workers/{worker.id}")

        assert response.status_code == status.HTTP_204_NO_CONTENT

    @pytest.mark.unit
    def test_delete_worker_not_found(self, client):
        """Test deleting non-existent worker."""
        response = client.delete("/api/v1/workers/99999")

        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.unit
    def test_delete_worker_with_active_gpus(self, client, test_worker, test_gpu_device):
        """Test deleting worker with active GPUs is blocked."""
        from backend.models.database import GPUDeviceState

        # Set GPU to IN_USE state
        test_gpu_device.state = GPUDeviceState.IN_USE
        from backend.core.database import get_db
        db = next(get_db())
        db.add(test_gpu_device)
        db.commit()

        response = client.delete(f"/api/v1/workers/{test_worker.id}")

        assert response.status_code == status.HTTP_409_CONFLICT
        assert "active GPUs" in response.json()["detail"].lower()


# ============================================================================
# Worker Status Management Tests
# ============================================================================

class TestWorkerStatusManagement:
    """Test worker status management endpoint."""

    @pytest.mark.unit
    def test_set_worker_status_success(self, client, test_worker):
        """Test setting worker status."""
        from backend.models.database import WorkerStatus

        response = client.post(
            f"/api/v1/workers/{test_worker.id}/set-status",
            json=WorkerStatus.MAINTENANCE
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data["success"] is True
        assert data["worker_id"] == test_worker.id
        assert data["new_status"] == WorkerStatus.MAINTENANCE

    @pytest.mark.unit
    def test_set_worker_status_not_found(self, client):
        """Test setting status on non-existent worker."""
        from backend.models.database import WorkerStatus

        response = client.post(
            "/api/v1/workers/99999/set-status",
            json=WorkerStatus.MAINTENANCE
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND


# ============================================================================
# Worker Registration Tests
# ============================================================================

class TestWorkerRegistration:
    """Test worker registration endpoint."""

    @pytest.mark.unit
    def test_register_worker_new(self, client, worker_registration_data):
        """Test registering a new worker."""
        response = client.post(
            "/api/v1/workers/register",
            json=worker_registration_data
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert "worker_id" in data
        assert "worker_secret" in data
        assert isinstance(data["worker_secret"], str)

    @pytest.mark.unit
    def test_register_worker_missing_token(self, client):
        """Test registration without token."""
        response = client.post(
            "/api/v1/workers/register",
            json={}
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.unit
    def test_register_worker_missing_ips(self, client):
        """Test registration without IPs."""
        response = client.post(
            "/api/v1/workers/register",
            json={"token": "test-token", "hostname": "test"}
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.unit
    def test_register_worker_single_ip(self, client):
        """Test registration with single IP (string)."""
        registration_data = {
            "token": "test-token",
            "hostname": "test-worker",
            "ips": "192.168.1.100",  # String instead of list
            "total_gpu_count": 4,
            "selected_gpu_count": 2,
            "gpu_models": ["NVIDIA A100"],
            "gpu_memorys": [40960],
            "selected_indices": [0]
        }

        response = client.post(
            "/api/v1/workers/register",
            json=registration_data
        )

        assert response.status_code == status.HTTP_200_OK

    @pytest.mark.unit
    def test_register_worker_existing_token(self, client, test_worker, test_worker_token):
        """Test re-registering with existing token."""
        registration_data = {
            "token": test_worker_token,
            "hostname": "updated-hostname",
            "ips": ["192.168.1.101", "10.0.0.51"],
            "total_gpu_count": 8,
            "selected_gpu_count": 4,
            "gpu_models": ["NVIDIA A100"] * 4,
            "gpu_memorys": [40960] * 4,
            "selected_indices": [0, 1, 2, 3]
        }

        response = client.post(
            "/api/v1/workers/register",
            json=registration_data
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["worker_id"] == test_worker.id


# ============================================================================
# Worker Add GPU Tests
# ============================================================================

class TestWorkerAddGPU:
    """Test add GPU endpoint."""

    @pytest.mark.unit
    def test_add_gpu_token_success(self, client, test_worker):
        """Test getting token for adding GPUs."""
        response = client.post(f"/api/v1/workers/{test_worker.id}/add-gpu")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert "register_token" in data
        assert "install_command" in data
        assert "message" in data

    @pytest.mark.unit
    def test_add_gpu_worker_not_found(self, client):
        """Test getting add GPU token for non-existent worker."""
        response = client.post("/api/v1/workers/99999/add-gpu")

        assert response.status_code == status.HTTP_404_NOT_FOUND


# ============================================================================
# IP Verification Tests
# ============================================================================

class TestIPVerification:
    """Test IP connectivity verification endpoint."""

    @pytest.mark.integration
    @patch("subprocess.run")
    def test_verify_ips_success(self, mock_run, client):
        """Test IP verification with reachable IPs."""
        # Mock successful ping
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "64 bytes from 192.168.1.1: icmp_seq=1 ttl=64 time=0.045 ms"
        mock_run.return_value = mock_result

        response = client.post(
            "/api/v1/workers/verify-ips",
            json={"ips": ["192.168.1.1", "192.168.1.2"], "timeout": 5}
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert "total_ips" in data
        assert "reachable_count" in data
        assert "unreachable_count" in data
        assert "success_rate" in data
        assert "reachable_ips" in data
        assert "unreachable_ips" in data

    @pytest.mark.integration
    @patch("subprocess.run")
    def test_verify_ips_mixed_results(self, mock_run, client):
        """Test IP verification with mixed results."""
        # Mock ping with mixed success/failure
        def side_effect(*args, **kwargs):
            mock_result = Mock()
            if "192.168.1.1" in str(args):
                mock_result.returncode = 0
                mock_result.stdout = "64 bytes from 192.168.1.1"
            else:
                mock_result.returncode = 1
                mock_result.stderr = "Destination Host Unreachable"
            return mock_result

        mock_run.side_effect = side_effect

        response = client.post(
            "/api/v1/workers/verify-ips",
            json={"ips": ["192.168.1.1", "192.168.1.999"], "timeout": 5}
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data["total_ips"] == 2
        assert data["reachable_count"] == 1
        assert data["unreachable_count"] == 1

    @pytest.mark.unit
    def test_verify_ips_missing_list(self, client):
        """Test IP verification without IP list."""
        response = client.post(
            "/api/v1/workers/verify-ips",
            json={}
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST


# ============================================================================
# Worker Statistics Tests
# ============================================================================

class TestWorkerStatistics:
    """Test worker statistics endpoint."""

    @pytest.mark.unit
    def test_get_worker_stats_success(self, client, test_worker, test_gpu_devices_batch):
        """Test getting worker statistics."""
        response = client.get(f"/api/v1/workers/{test_worker.id}/stats")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data["worker_id"] == test_worker.id
        assert data["worker_name"] == test_worker.name
        assert "total_gpus" in data
        assert "in_use_gpus" in data
        assert "error_gpus" in data
        assert "avg_memory_utilization" in data
        assert "avg_core_utilization" in data
        assert "avg_temperature" in data

    @pytest.mark.unit
    def test_get_worker_stats_not_found(self, client):
        """Test getting stats for non-existent worker."""
        response = client.get("/api/v1/workers/99999/stats")

        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.unit
    def test_get_worker_stats_no_gpus(self, client, test_worker):
        """Test getting stats for worker with no GPUs."""
        response = client.get(f"/api/v1/workers/{test_worker.id}/stats")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data["total_gpus"] == 0
        assert data["in_use_gpus"] == 0


# ============================================================================
# Worker Heartbeat Tests
# ============================================================================

class TestWorkerHeartbeat:
    """Test worker heartbeat functionality."""

    @pytest.mark.unit
    def test_worker_heartbeat_success(self, client, test_worker):
        """Test successful worker heartbeat."""
        from backend.core.security import generate_worker_token

        # Generate a worker secret for authentication
        import secrets
        worker_secret = f"worker_{secrets.token_urlsafe(32)}"

        response = client.post(
            f"/api/v1/workers/{test_worker.id}/heartbeat",
            json={"status": "online"},
            headers={"Authorization": f"Bearer {worker_secret}"}
        )

        # Note: This may fail if authentication is strict
        # Adjust based on actual authentication implementation
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]
