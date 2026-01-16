"""
Unit tests for the GPUService.
"""
import pytest
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock

from backend.services.gpu_service import GPUService
from backend.models.database import GPUStatus, DeploymentStatus


class TestGPUService:
    """Test GPUService class."""

    def test_refresh_gpu_status_success(self, db_session, mock_gpu_manager):
        """Test successfully refreshing GPU status."""
        service = GPUService(db_session)
        gpus = service.refresh_gpu_status()

        assert len(gpus) == 2
        assert gpus[0].gpu_id == "gpu:0"
        assert gpus[1].gpu_id == "gpu:1"
        mock_gpu_manager.get_all_gpus.assert_called_once()

    def test_refresh_gpu_status_unavailable(self, db_session):
        """Test refreshing GPU status when manager is unavailable."""
        mock_manager = MagicMock()
        mock_manager.is_available.return_value = False

        service = GPUService(db_session)
        service.gpu_manager = mock_manager

        gpus = service.refresh_gpu_status()
        assert gpus == []

    def test_get_all_gpus(self, db_session, test_gpu, mock_gpu_manager):
        """Test getting all GPUs."""
        service = GPUService(db_session)
        gpus = service.get_all_gpus()
        assert len(gpus) >= 1
        assert test_gpu in gpus

    def test_get_gpu_by_id(self, db_session, test_gpu, mock_gpu_manager):
        """Test getting a GPU by ID."""
        service = GPUService(db_session)
        gpu = service.get_gpu("gpu:0")
        assert gpu is not None
        assert gpu.gpu_id == "gpu:0"

    def test_get_gpu_not_found(self, db_session, mock_gpu_manager):
        """Test getting a non-existent GPU."""
        service = GPUService(db_session)
        gpu = service.get_gpu("gpu:999")
        assert gpu is None

    def test_get_available_gpus(self, db_session, test_gpu, mock_gpu_manager):
        """Test getting available GPUs."""
        service = GPUService(db_session)
        available = service.get_available_gpus()
        assert test_gpu in available

    def test_allocate_gpus_success(self, db_session, test_gpu, mock_gpu_manager):
        """Test successfully allocating GPUs."""
        service = GPUService(db_session)

        result = service.allocate_gpus(["gpu:0"], deployment_id=1)
        assert result is True

        # Verify GPU status is updated
        db_session.refresh(test_gpu)
        assert test_gpu.status == GPUStatus.IN_USE
        assert test_gpu.deployment_id == 1

    def test_allocate_gpus_not_found(self, db_session, mock_gpu_manager):
        """Test allocating non-existent GPU."""
        service = GPUService(db_session)

        result = service.allocate_gpus(["gpu:999"], deployment_id=1)
        assert result is False

    def test_allocate_gpus_already_in_use(self, db_session, test_gpu, mock_gpu_manager):
        """Test allocating an already in-use GPU."""
        service = GPUService(db_session)
        test_gpu.status = GPUStatus.IN_USE
        db_session.commit()

        result = service.allocate_gpus(["gpu:0"], deployment_id=2)
        assert result is False

    def test_release_gpus(self, db_session, test_gpu, mock_gpu_manager):
        """Test releasing GPUs."""
        service = GPUService(db_session)

        # First allocate
        test_gpu.status = GPUStatus.IN_USE
        test_gpu.deployment_id = 1
        db_session.commit()

        # Then release
        count = service.release_gpus(deployment_id=1)
        assert count == 1

        # Verify GPU status is updated
        db_session.refresh(test_gpu)
        assert test_gpu.status == GPUStatus.AVAILABLE
        assert test_gpu.deployment_id is None

    def test_release_gpus_empty_deployment(self, db_session, mock_gpu_manager):
        """Test releasing GPUs from deployment with no GPUs."""
        service = GPUService(db_session)
        count = service.release_gpus(deployment_id=999)
        assert count == 0

    def test_get_gpu_stats(self, db_session, test_gpu, mock_gpu_manager):
        """Test getting GPU statistics."""
        service = GPUService(db_session)
        stats = service.get_gpu_stats()

        assert stats.total >= 1
        assert stats.available >= 0
        assert stats.in_use >= 0
        assert stats.total == stats.available + stats.in_use
        assert len(stats.gpus) >= 1

    def test_get_cluster_stats(self, db_session, mock_gpu_manager):
        """Test getting cluster statistics."""
        service = GPUService(db_session)
        stats = service.get_cluster_stats()

        assert "total_gpus" in stats
        assert "total_memory_mb" in stats
        assert "free_memory_mb" in stats
        assert "average_utilization" in stats
        assert "average_temperature" in stats
        assert stats["total_gpus"] == 2
        assert stats["total_memory_mb"] == 49152

    def test_get_cluster_stats_unavailable(self, db_session):
        """Test cluster stats when GPU manager is unavailable."""
        mock_manager = MagicMock()
        mock_manager.is_available.return_value = False
        service = GPUService(db_session)
        service.gpu_manager = mock_manager

        stats = service.get_cluster_stats()
        assert stats["total_gpus"] == 0

    def test_check_gpu_health(self, db_session, mock_gpu_manager):
        """Test checking GPU health."""
        service = GPUService(db_session)
        health = service.check_gpu_health()

        assert "gpu:0" in health
        assert "gpu:1" in health
        assert health["gpu:0"] is True  # Mock returns healthy
        assert health["gpu:1"] is True

    def test_find_suitable_gpus(self, db_session, mock_gpu_manager):
        """Test finding suitable GPUs."""
        service = GPUService(db_session)
        gpu_ids = service.find_suitable_gpus(required_memory_mb=16000, count=1)

        assert len(gpu_ids) >= 0
        mock_gpu_manager.find_available_gpus.assert_called_once()


class TestGPUServiceIntegration:
    """Integration tests for GPU service."""

    def test_full_allocation_cycle(self, db_session, mock_gpu_manager):
        """Test full GPU allocation and release cycle."""
        service = GPUService(db_session)

        # Refresh GPU status
        service.refresh_gpu_status()

        # Allocate GPU
        success = service.allocate_gpus(["gpu:0"], deployment_id=1)
        assert success is True

        # Check stats
        stats = service.get_gpu_stats()
        assert stats.in_use >= 1

        # Release GPU
        count = service.release_gpus(deployment_id=1)
        assert count == 1

        # Check stats again
        stats = service.get_gpu_stats()
        assert stats.available >= 1

    def test_multiple_gpu_allocation(self, db_session, mock_gpu_manager):
        """Test allocating multiple GPUs."""
        service = GPUService(db_session)
        service.refresh_gpu_status()

        success = service.allocate_gpus(["gpu:0", "gpu:1"], deployment_id=1)
        assert success is True

        stats = service.get_gpu_stats()
        assert stats.in_use == 2

        # Release all
        count = service.release_gpus(deployment_id=1)
        assert count == 2
