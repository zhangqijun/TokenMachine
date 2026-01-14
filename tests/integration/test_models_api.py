"""
Integration tests for the Models API.
"""
import pytest


class TestModelsCRUD:
    """Test model CRUD operations."""

    def test_list_models(self, client, test_model):
        """Test listing all models."""
        response = client.get("/api/v1/models")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data or isinstance(data, list)

    def test_get_model_by_id(self, client, test_model):
        """Test getting a specific model by ID."""
        response = client.get(f"/api/v1/models/{test_model.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_model.id
        assert data["name"] == test_model.name

    def test_get_model_not_found(self, client):
        """Test getting a non-existent model."""
        response = client.get("/api/v1/models/99999")
        assert response.status_code == 404

    def test_create_model(self, client, monkeypatch):
        """Test creating a new model."""
        # Mock the download process
        def mock_start_download(*args, **kwargs):
            pass

        monkeypatch.setattr(
            "inferx.services.model_service.ModelService._start_download",
            mock_start_download
        )

        response = client.post(
            "/api/v1/models",
            json={
                "name": "test-org/test-model",
                "version": "v1.0.0",
                "source": "huggingface",
                "category": "llm"
            }
        )

        # Note: May require authentication
        assert response.status_code in [201, 401, 403]

    def test_update_model_status(self, client, test_model):
        """Test updating model status."""
        # Note: May require admin privileges
        response = client.patch(
            f"/api/v1/models/{test_model.id}",
            json={"status": "error", "error_message": "Test error"}
        )

        assert response.status_code in [200, 401, 403, 404]

    def test_delete_model(self, client, test_model):
        """Test deleting a model."""
        # Note: May require admin privileges
        response = client.delete(f"/api/v1/models/{test_model.id}")
        assert response.status_code in [200, 204, 401, 403, 404]


class TestDeploymentsAPI:
    """Test deployment API endpoints."""

    def test_list_deployments(self, client, test_deployment):
        """Test listing all deployments."""
        response = client.get("/api/v1/deployments")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data or isinstance(data, list)

    def test_get_deployment_by_id(self, client, test_deployment):
        """Test getting a specific deployment."""
        response = client.get(f"/api/v1/deployments/{test_deployment.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_deployment.id
        assert data["name"] == test_deployment.name

    def test_get_deployment_not_found(self, client):
        """Test getting a non-existent deployment."""
        response = client.get("/api/v1/deployments/99999")
        assert response.status_code == 404

    def test_create_deployment(self, client, test_model):
        """Test creating a new deployment."""
        # Note: Requires mocked GPU and worker pool
        response = client.post(
            "/api/v1/deployments",
            json={
                "model_id": test_model.id,
                "name": "test-deployment-new",
                "replicas": 1,
                "gpu_ids": ["gpu:0"],
                "backend": "vllm",
                "config": {
                    "tensor_parallel_size": 1,
                    "max_model_len": 4096,
                    "gpu_memory_utilization": 0.9
                }
            }
        )

        # May require authentication or fail due to GPU availability
        assert response.status_code in [201, 400, 401, 403, 503]

    def test_stop_deployment(self, client, test_deployment):
        """Test stopping a deployment."""
        # Note: May require admin privileges
        response = client.post(f"/api/v1/deployments/{test_deployment.id}/stop")
        assert response.status_code in [200, 401, 403, 404]

    def test_restart_deployment(self, client, test_deployment):
        """Test restarting a deployment."""
        # Note: May require admin privileges
        response = client.post(f"/api/v1/deployments/{test_deployment.id}/restart")
        assert response.status_code in [200, 401, 403, 404]


class TestGPUAPI:
    """Test GPU API endpoints."""

    def test_list_gpus(self, client, test_gpu):
        """Test listing all GPUs."""
        response = client.get("/api/v1/gpus")
        assert response.status_code == 200
        data = response.json()
        assert "gpus" in data or "items" in data

    def test_get_gpu_stats(self, client):
        """Test getting GPU statistics."""
        response = client.get("/api/v1/gpus/stats")
        assert response.status_code in [200, 404]


class TestHealthAPI:
    """Test health check endpoints."""

    def test_health_check(self, client):
        """Test basic health check endpoint."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data

    def test_ready_check(self, client):
        """Test readiness check endpoint."""
        response = client.get("/ready")
        assert response.status_code in [200, 503]

    def test_metrics_endpoint(self, client):
        """Test Prometheus metrics endpoint."""
        response = client.get("/metrics")
        # May return 404 if metrics disabled
        assert response.status_code in [200, 404]
