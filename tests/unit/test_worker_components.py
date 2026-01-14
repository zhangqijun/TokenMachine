"""
Unit tests for Worker components.
"""
import pytest
from unittest.mock import Mock, MagicMock, AsyncMock, patch

from backend.worker.collector import WorkerStatusCollector
from backend.worker.exporter import MetricExporter
from backend.worker.serve_manager import ServeManager


# ============================================================================
# WorkerStatusCollector Tests
# ============================================================================

class TestWorkerStatusCollector:
    """Tests for WorkerStatusCollector."""

    def test_collect_basic(self):
        """Test basic status collection."""
        collector = WorkerStatusCollector(
            worker_ip="192.168.1.100",
            worker_name="test-worker",
        )

        status = collector.collect()

        assert status["worker_ip"] == "192.168.1.100"
        assert status["worker_name"] == "test-worker"
        assert "gpus" in status
        assert "system" in status

    @patch("backend.worker.collector.GPUManager")
    def test_collect_gpu_info(self, mock_gpu_manager_class):
        """Test GPU information collection."""
        # Setup mock
        mock_gpu_manager = MagicMock()
        mock_gpu_manager.get_all_gpus.return_value = [
            {
                "id": "gpu:0",
                "name": "NVIDIA RTX 4090",
                "memory_total_mb": 24576,
                "memory_free_mb": 20000,
                "utilization_percent": 50.0,
                "temperature_celsius": 65.0,
            }
        ]
        mock_gpu_manager_class.return_value = mock_gpu_manager

        collector = WorkerStatusCollector(
            worker_ip="192.168.1.100",
            worker_name="test-worker",
        )

        status = collector.collect()

        assert len(status["gpus"]) == 1
        assert status["gpus"][0]["id"] == "gpu:0"
        assert status["gpus"][0]["utilization_percent"] == 50.0

    @patch("backend.worker.collector.psutil")
    def test_collect_system_info(self, mock_psutil):
        """Test system information collection."""
        # Setup mock
        mock_psutil.cpu_percent.return_value = 45.0
        mock_psutil.virtual_memory.return_value = MagicMock(
            used=8 * 1024 * 1024 * 1024,  # 8 GB
            total=16 * 1024 * 1024 * 1024,  # 16 GB
        )
        mock_psutil.disk_usage.return_value = MagicMock(percent=60.0)

        collector = WorkerStatusCollector(
            worker_ip="192.168.1.100",
            worker_name="test-worker",
        )

        status = collector.collect()

        assert status["system"]["cpu_percent"] == 45.0
        assert status["system"]["memory_used_mb"] == 8192  # 8 GB
        assert status["system"]["disk_usage_percent"] == 60.0


# ============================================================================
# MetricExporter Tests
# ============================================================================

class TestMetricExporter:
    """Tests for MetricExporter."""

    def test_initialization(self):
        """Test MetricExporter initialization."""
        collector = Mock()
        exporter = MetricExporter(
            collector=collector,
            server_url="http://server:8000",
            token="test-token",
        )

        assert exporter.collector == collector
        assert exporter.server_url == "http://server:8000"
        assert exporter.token == "test-token"
        assert exporter._is_running is False

    @pytest.mark.asyncio
    async def test_export_metrics(self):
        """Test exporting metrics to server."""
        collector = Mock()
        collector.collect.return_value = {
            "worker_ip": "192.168.1.100",
            "gpus": [],
            "system": {},
        }

        exporter = MetricExporter(
            collector=collector,
            server_url="http://server:8000",
            token="test-token",
        )

        # Mock worker_id_getter to return a worker ID
        exporter._get_worker_id = Mock(return_value=1)

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client

            await exporter._export_metrics()

            # Verify POST was called
            mock_client.post.assert_called_once()

    def test_stop(self):
        """Test stopping the metric exporter."""
        collector = Mock()
        exporter = MetricExporter(
            collector=collector,
            server_url="http://server:8000",
            token="test-token",
        )

        exporter._is_running = True
        exporter.stop()

        assert exporter._is_running is False


# ============================================================================
# ServeManager Tests
# ============================================================================

class TestServeManager:
    """Tests for ServeManager."""

    def test_initialization(self):
        """Test ServeManager initialization."""
        worker_id_getter = Mock(return_value=1)
        manager = ServeManager(
            worker_id_getter=worker_id_getter,
            server_url="http://server:8000",
            token="test-token",
        )

        assert manager.worker_id_getter == worker_id_getter
        assert manager.server_url == "http://server:8000"
        assert manager.token == "test-token"
        assert manager._model_cache_by_instance == {}
        assert manager._backend_by_instance == {}

    @pytest.mark.asyncio
    async def test_watch_model_instances(self):
        """Test watching model instance changes."""
        worker_id_getter = Mock(return_value=1)
        manager = ServeManager(
            worker_id_getter=worker_id_getter,
            server_url="http://server:8000",
            token="test-token",
        )

        # Mock HTTP response
        with patch("httpx.AsyncClient") as mock_client_class:
            # First call returns instances, second call returns empty
            mock_response1 = MagicMock()
            mock_response1.json.return_value = {
                "items": [
                    {
                        "id": 1,
                        "model": {"name": "test-model", "path": "/tmp/model"},
                        "backend": "vllm",
                        "config": {},
                    }
                ]
            }
            mock_response1.raise_for_status = MagicMock()

            mock_response2 = MagicMock()
            mock_response2.json.return_value = {"items": []}
            mock_response2.raise_for_status = MagicMock()

            mock_client = AsyncMock()
            mock_client.get = AsyncMock(side_effect=[mock_response1, mock_response2])
            mock_client_class.return_value.__aenter__.return_value = mock_client

            # Mock _start_instance to prevent actual backend creation
            manager._start_instance = AsyncMock()

            # Run one iteration
            task = asyncio.create_task(manager.watch_model_instances(interval_seconds=0.1))
            await asyncio.sleep(0.2)
            manager.stop()  # This won't actually stop the loop

            # Verify instances were checked
            assert mock_client.get.called

    @pytest.mark.asyncio
    async def test_update_instance_status(self):
        """Test updating instance status."""
        worker_id_getter = Mock(return_value=1)
        manager = ServeManager(
            worker_id_getter=worker_id_getter,
            server_url="http://server:8000",
            token="test-token",
        )

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.patch = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client

            await manager._update_instance_status(1, "running")

            # Verify PATCH was called
            mock_client.patch.assert_called_once()
            call_args = mock_client.patch.call_args
            assert "running" in call_args[1]["json"]["status"]

    @pytest.mark.asyncio
    async def test_stop_all_instances(self):
        """Test stopping all instances."""
        worker_id_getter = Mock(return_value=1)
        manager = ServeManager(
            worker_id_getter=worker_id_getter,
            server_url="http://server:8000",
            token="test-token",
        )

        # Add mock backends
        backend1 = AsyncMock()
        backend2 = AsyncMock()
        manager._backend_by_instance = {1: backend1, 2: backend2}
        manager._model_cache_by_instance = {1: {}, 2: {}}

        await manager.stop_all_instances()

        # Verify all backends were stopped
        backend1.stop.assert_called_once()
        backend2.stop.assert_called_once()
        assert len(manager._backend_by_instance) == 0
        assert len(manager._model_cache_by_instance) == 0


# ============================================================================
# InferenceBackend Tests
# ============================================================================

class TestInferenceBackend:
    """Tests for InferenceBackend base class."""

    def test_base_backend_cannot_be_instantiated(self):
        """Test that InferenceBackend cannot be instantiated directly."""
        from backend.worker.backends.base import InferenceBackend

        # Should raise TypeError when trying to instantiate abstract class
        with pytest.raises(TypeError):
            InferenceBackend(
                model_path="/tmp/model",
                model_name="test",
                config={},
            )

    def test_concrete_backend_implementation(self):
        """Test creating a concrete backend implementation."""
        from backend.worker.backends.base import InferenceBackend

        class ConcreteBackend(InferenceBackend):
            async def start(self):
                self._is_running = True

            async def stop(self):
                self._is_running = False

            async def health_check(self):
                return self._is_running

        backend = ConcreteBackend(
            model_path="/tmp/model",
            model_name="test",
            config={},
        )

        assert backend.model_path == "/tmp/model"
        assert backend.model_name == "test"
        assert backend.config == {}
        assert backend.is_running() is False


# ============================================================================
# VLLMBackend Tests
# ============================================================================

class TestVLLMBackend:
    """Tests for VLLMBackend."""

    def test_initialization(self):
        """Test VLLMBackend initialization."""
        from backend.worker.backends.vllm_backend import VLLMBackend

        backend = VLLMBackend(
            model_path="/tmp/model",
            model_name="test-model",
            config={"port": 8001, "gpu_memory_utilization": 0.9},
        )

        assert backend.model_path == "/tmp/model"
        assert backend.model_name == "test-model"
        assert backend.port == 8001
        assert backend.config["gpu_memory_utilization"] == 0.9
        assert backend.is_running() is False

    @pytest.mark.asyncio
    async def test_start_fails_without_vllm(self):
        """Test that start fails when vLLM is not available."""
        from backend.worker.backends.vllm_backend import VLLMBackend

        backend = VLLMBackend(
            model_path="/tmp/model",
            model_name="test-model",
            config={},
        )

        # Should fail because vLLM is not installed
        with pytest.raises(Exception):
            await backend.start()

        assert backend.is_running() is False


# ============================================================================
# Integration Tests
# ============================================================================

class TestWorkerIntegration:
    """Integration tests for Worker components."""

    @pytest.mark.asyncio
    async def test_collector_to_exporter_flow(self):
        """Test data flow from collector to exporter."""
        # Create collector
        collector = WorkerStatusCollector(
            worker_ip="192.168.1.100",
            worker_name="test-worker",
        )

        # Create exporter with collector
        exporter = MetricExporter(
            collector=collector,
            server_url="http://server:8000",
            token="test-token",
        )

        # Get status from collector
        status = collector.collect()
        assert status is not None

        # Verify exporter can access collector
        assert exporter.collector == collector

    def test_serve_manager_backend_management(self):
        """Test backend management in ServeManager."""
        worker_id_getter = Mock(return_value=1)
        manager = ServeManager(
            worker_id_getter=worker_id_getter,
            server_url="http://server:8000",
            token="test-token",
        )

        # Create mock backend
        backend = AsyncMock()
        manager._backend_by_instance[1] = backend
        manager._model_cache_by_instance[1] = {"model": "test"}

        # Get running backends
        running = manager.get_running_backends()

        assert len(running) == 1
        assert running[1] == backend
