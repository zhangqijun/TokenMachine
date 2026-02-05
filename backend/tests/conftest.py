"""
Pytest configuration for backend tests.

This module provides fixtures and configuration for testing the TokenMachine backend.
"""
import os
import sys
import pytest
import asyncio
from typing import AsyncGenerator, Generator
from datetime import datetime
from unittest.mock import Mock, AsyncMock, patch
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from backend.core.database import get_db
from backend.models.database import Base
from backend.main import app
from backend.core.config import get_settings
from backend.core.security import hash_worker_token, generate_worker_token


# ============================================================================
# Test Configuration
# ============================================================================

# Use in-memory SQLite for fast tests
TEST_DATABASE_URL = "sqlite:///:memory:"

# Override settings for testing
class TestSettings:
    """Test-specific settings."""
    app_name = "TokenMachine Test"
    environment = "test"
    debug = True
    api_host = "127.0.0.1"
    api_port = 8001
    database_url = TEST_DATABASE_URL
    redis_url = "redis://localhost:6379/15"  # Use different DB for tests
    secret_key = "test-secret-key-for-testing-only"
    api_key_prefix = "tm_test_"
    model_storage_path = "/tmp/test_tokenmachine/models"
    log_path = "/tmp/test_tokenmachine/logs"
    worker_base_port = 8500
    worker_start_timeout = 60
    gpu_memory_utilization = 0.8
    max_model_len = 2048
    use_mock_data = True


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create an instance of the event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# ============================================================================
# Database Fixtures
# ============================================================================

@pytest.fixture(scope="function")
def db_engine():
    """Create a test database engine."""
    engine = create_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture(scope="function")
def db_session(db_engine) -> Generator[Session, None, None]:
    """Create a test database session."""
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)
    session = TestingSessionLocal()

    try:
        yield session
    finally:
        session.close()


# ============================================================================
# FastAPI Test Client
# ============================================================================

@pytest.fixture(scope="function")
def client(db_session: Session):
    """Create a test client for the FastAPI app."""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


# ============================================================================
# Model Fixtures - Organizations, Users, Clusters
# ============================================================================

@pytest.fixture
def test_organization(db_session: Session):
    """Create a test organization."""
    from backend.models.database import Organization, OrganizationPlan

    org = Organization(
        name="test-org",
        plan=OrganizationPlan.PROFESSIONAL,
        quota_tokens=1000000,
        quota_models=10,
        quota_gpus=5,
        max_workers=10
    )
    db_session.add(org)
    db_session.commit()
    db_session.refresh(org)
    return org


@pytest.fixture
def test_user(db_session: Session, test_organization):
    """Create a test user."""
    from backend.models.database import User, UserRole
    import hashlib

    password_hash = hashlib.sha256("test_password".encode()).hexdigest()

    user = User(
        username="testuser",
        email="test@example.com",
        password_hash=password_hash,
        organization_id=test_organization.id,
        role=UserRole.ADMIN,
        is_active=True
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def test_api_key(db_session: Session, test_user, test_organization):
    """Create a test API key."""
    from backend.models.database import ApiKey
    import hashlib

    key_secret = "tm_test_test_api_key_12345"
    key_hash = hashlib.sha256(key_secret.encode()).hexdigest()

    api_key = ApiKey(
        key_hash=key_hash,
        key_prefix="tm_test_",
        user_id=test_user.id,
        organization_id=test_organization.id,
        name="Test API Key",
        quota_tokens=10000000,
        tokens_used=0,
        is_active=True
    )
    db_session.add(api_key)
    db_session.commit()
    db_session.refresh(api_key)
    return api_key


@pytest.fixture
def test_cluster(db_session: Session):
    """Create a test cluster."""
    from backend.models.database import Cluster, ClusterType, ClusterStatus

    cluster = Cluster(
        name="test-cluster",
        description="Test cluster for testing",
        type=ClusterType.STANDALONE,
        is_default=True,
        status=ClusterStatus.RUNNING
    )
    db_session.add(cluster)
    db_session.commit()
    db_session.refresh(cluster)
    return cluster


@pytest.fixture
def test_worker_pool(db_session: Session, test_cluster):
    """Create a test worker pool."""
    from backend.models.database import WorkerPool, WorkerPoolStatus

    pool = WorkerPool(
        cluster_id=test_cluster.id,
        name="test-worker-pool",
        min_workers=1,
        max_workers=5,
        status=WorkerPoolStatus.RUNNING
    )
    db_session.add(pool)
    db_session.commit()
    db_session.refresh(pool)
    return pool


# ============================================================================
# Worker Fixtures
# ============================================================================

@pytest.fixture
def test_worker_token():
    """Create a test worker token."""
    return generate_worker_token()


@pytest.fixture
def test_worker(db_session: Session, test_cluster, test_worker_token):
    """Create a test worker."""
    from backend.models.database import Worker, WorkerStatus

    token_hash = hash_worker_token(test_worker_token)

    worker = Worker(
        cluster_id=test_cluster.id,
        name="test-worker-1",
        ips=["192.168.1.100", "10.0.0.50"],
        port=8080,
        hostname="worker-host-1",
        status=WorkerStatus.READY,
        labels={"gpu_type": "nvidia", "zone": "us-west-1"},
        token_hash=token_hash,
        gpu_count=4,
        expected_gpu_count=4,
        last_heartbeat_at=datetime.utcnow()
    )
    db_session.add(worker)
    db_session.commit()
    db_session.refresh(worker)
    return worker


@pytest.fixture
def test_workers_batch(db_session: Session, test_cluster):
    """Create multiple test workers for batch testing."""
    from backend.models.database import Worker, WorkerStatus

    workers = []
    for i in range(3):
        token = generate_worker_token()
        token_hash = hash_worker_token(token)

        worker = Worker(
            cluster_id=test_cluster.id,
            name=f"test-worker-{i+1}",
            ips=[f"192.168.1.{100+i}"],
            port=8080 + i,
            hostname=f"worker-host-{i+1}",
            status=WorkerStatus.READY,
            labels={"gpu_type": "nvidia", "zone": f"us-west-{i+1}"},
            token_hash=token_hash,
            gpu_count=4,
            expected_gpu_count=4,
            last_heartbeat_at=datetime.utcnow()
        )
        db_session.add(worker)
        db_session.commit()
        db_session.refresh(worker)
        workers.append(worker)

    return workers


@pytest.fixture
def test_gpu_device(db_session: Session, test_worker):
    """Create a test GPU device."""
    from backend.models.database import GPUDevice, GPUDeviceState, GPUVendor

    gpu = GPUDevice(
        worker_id=test_worker.id,
        uuid=f"gpu-{test_worker.id}-0",
        name="NVIDIA A100-SXM4-40GB",
        vendor=GPUVendor.NVIDIA,
        index=0,
        ip="192.168.1.100",
        port=9001,
        hostname="worker-host-1",
        pci_bus="0000:07:00.0",
        core_total=10752,
        core_utilization_rate=0.0,
        memory_total=40 * 1024 * 1024 * 1024,  # 40GB in bytes
        memory_used=0,
        memory_allocated=0,
        memory_utilization_rate=0.0,
        temperature=35.0,
        state=GPUDeviceState.AVAILABLE
    )
    db_session.add(gpu)
    db_session.commit()
    db_session.refresh(gpu)
    return gpu


@pytest.fixture
def test_gpu_devices_batch(db_session: Session, test_worker):
    """Create multiple test GPU devices."""
    from backend.models.database import GPUDevice, GPUDeviceState, GPUVendor

    gpus = []
    for i in range(4):
        gpu = GPUDevice(
            worker_id=test_worker.id,
            uuid=f"gpu-{test_worker.id}-{i}",
            name="NVIDIA A100-SXM4-40GB",
            vendor=GPUVendor.NVIDIA,
            index=i,
            ip="192.168.1.100",
            port=9001,
            hostname="worker-host-1",
            pci_bus=f"0000:07:{i:02d}.0",
            core_total=10752,
            core_utilization_rate=0.0,
            memory_total=40 * 1024 * 1024 * 1024,
            memory_used=0,
            memory_allocated=0,
            memory_utilization_rate=0.0,
            temperature=30.0 + i,
            state=GPUDeviceState.AVAILABLE
        )
        db_session.add(gpu)
        db_session.commit()
        db_session.refresh(gpu)
        gpus.append(gpu)

    return gpus


# ============================================================================
# Model & Deployment Fixtures
# ============================================================================

@pytest.fixture
def test_model(db_session: Session):
    """Create a test model."""
    from backend.models.database import Model, ModelSource, ModelCategory, ModelStatus, ModelQuantization

    model = Model(
        name="qwen-7b-chat",
        version="v1.0.0",
        source=ModelSource.MODELSCOPE,
        category=ModelCategory.LLM,
        quantization=ModelQuantization.FP16,
        path="/mnt/models/qwen--7b-chat",
        size_gb=14.5,
        status=ModelStatus.READY,
        download_progress=100,
        modelscope_repo_id="Qwen/qwen-7b-chat",
        modelscope_revision="v1.0.0",
        storage_path="/mnt/models/Qwen--qwen-7b-chat",
        storage_type="nfs"
    )
    db_session.add(model)
    db_session.commit()
    db_session.refresh(model)
    return model


@pytest.fixture
def test_deployment(db_session: Session, test_model):
    """Create a test deployment."""
    from backend.models.database import Deployment, DeploymentStatus, DeploymentEnvironment

    deployment = Deployment(
        model_id=test_model.id,
        name="test-deployment",
        environment=DeploymentEnvironment.DEV,
        status=DeploymentStatus.RUNNING,
        replicas=2,
        traffic_weight=100,
        gpu_ids=["gpu:0", "gpu:1"],
        backend="vllm",
        config={
            "gpu_memory_utilization": 0.9,
            "max_model_len": 4096,
            "tensor_parallel_size": 1,
            "trust_remote_code": True
        }
    )
    db_session.add(deployment)
    db_session.commit()
    db_session.refresh(deployment)
    return deployment


@pytest.fixture
def test_model_instance(db_session: Session, test_deployment, test_model, test_worker):
    """Create a test model instance."""
    from backend.models.database import ModelInstance, ModelInstanceStatus

    instance = ModelInstance(
        deployment_id=test_deployment.id,
        model_id=test_model.id,
        worker_id=test_worker.id,
        name=f"{test_deployment.name}-instance-1",
        status=ModelInstanceStatus.RUNNING,
        endpoint=f"http://{test_worker.ips[0]}:8501",
        backend="vllm",
        config={
            "gpu_memory_utilization": 0.9,
            "max_model_len": 4096
        },
        gpu_ids=["gpu:0"],
        port=8501,
        health_status={"healthy": True, "last_check": datetime.utcnow().isoformat()}
    )
    db_session.add(instance)
    db_session.commit()
    db_session.refresh(instance)
    return instance


# ============================================================================
# Mock Fixtures
# ============================================================================

@pytest.fixture
def mock_gpu_manager():
    """Create a mock GPU manager."""
    manager = AsyncMock()

    manager.get_available_gpus.return_value = [
        {
            "id": "gpu:0",
            "name": "NVIDIA A100-SXM4-40GB",
            "memory_total_mb": 40960,
            "memory_free_mb": 40960,
            "utilization_percent": 0.0
        },
        {
            "id": "gpu:1",
            "name": "NVIDIA A100-SXM4-40GB",
            "memory_total_mb": 40960,
            "memory_free_mb": 40960,
            "utilization_percent": 0.0
        }
    ]

    manager.allocate_gpu.return_value = "gpu:0"
    manager.release_gpu.return_value = True
    manager.get_gpu_status.return_value = {
        "id": "gpu:0",
        "name": "NVIDIA A100-SXM4-40GB",
        "memory_total_mb": 40960,
        "memory_free_mb": 40960,
        "utilization_percent": 0.0,
        "temperature_celsius": 35.0
    }

    return manager

@pytest.fixture
def mock_httpx_client():
    """Create a mock httpx client."""
    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()

        # Mock successful response
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "chatcmpl-123",
            "object": "chat.completion",
            "created": 1677652288,
            "model": "qwen-7b-chat",
            "choices": [{
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": "Hello! How can I help you today?"
                },
                "finish_reason": "stop"
            }],
            "usage": {
                "prompt_tokens": 10,
                "completion_tokens": 9,
                "total_tokens": 19
            }
        }

        mock_client.post.return_value = mock_response
        mock_client.get.return_value = mock_response

        mock_client_class.return_value = mock_client

        yield mock_client


@pytest.fixture
def mock_vllm_subprocess():
    """Create a mock vLLM subprocess."""
    with patch("subprocess.Popen") as mock_popen:
        mock_process = Mock()
        mock_process.pid = 12345
        mock_process.poll.return_value = None  # Process is running
        mock_process.wait.return_value = 0
        mock_process.terminate.return_value = None
        mock_process.kill.return_value = None

        mock_popen.return_value = mock_process

        yield mock_popen


# ============================================================================
# Test Data Helpers
# ============================================================================

@pytest.fixture
def worker_registration_data():
    """Sample worker registration data."""
    return {
        "token": "test-worker-token-12345",
        "hostname": "test-worker-host",
        "ips": ["192.168.1.100", "10.0.0.50"],
        "total_gpu_count": 4,
        "selected_gpu_count": 2,
        "gpu_models": ["NVIDIA A100-SXM4-40GB", "NVIDIA A100-SXM4-40GB"],
        "gpu_memorys": [40960, 40960],
        "selected_indices": [0, 1],
        "capabilities": ["vLLM", "SGLang"],
        "agent_type": "gpu",
        "agent_version": "1.0.0"
    }


@pytest.fixture
def worker_create_data():
    """Sample worker creation data."""
    return {
        "name": "new-test-worker",
        "cluster_id": 1,
        "pool_id": None,
        "expected_gpu_count": 4,
        "labels": {"gpu_type": "nvidia", "zone": "us-west-1"}
    }


@pytest.fixture
def worker_update_data():
    """Sample worker update data."""
    return {
        "labels": {"gpu_type": "nvidia", "zone": "us-east-1", "updated": True},
        "expected_gpu_count": 8
    }


# ============================================================================
# Markers
# ============================================================================

def pytest_configure(config):
    """Configure pytest markers."""
    config.addinivalue_line("markers", "unit: Unit tests (fast, isolated)")
    config.addinivalue_line("markers", "integration: Integration tests (slower, may use external resources)")
    config.addinivalue_line("markers", "slow: Slow running tests")
    config.addinivalue_line("markers", "gpu: Tests that require GPU access")
    config.addinivalue_line("markers", "worker: Tests related to worker functionality")
    config.addinivalue_line("markers", "auth: Tests related to authentication")
