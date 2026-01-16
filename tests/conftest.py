"""
Pytest configuration and shared fixtures for TokenMachine tests.
"""
import os
import sys
import asyncio
import pytest
import pytest_asyncio
from typing import AsyncGenerator, Generator
from pathlib import Path
from unittest.mock import Mock, AsyncMock, MagicMock, patch
from datetime import datetime, timedelta
from decimal import Decimal

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import backend models
from backend.models.database import (
    Base, User, Model, Deployment, GPU, ApiKey, UsageLog,
    Organization, Cluster, WorkerPool, Worker, GPUDevice,
    Invoice, ModelInstance,
    OrganizationPlan, UserRole, ModelCategory, ModelSource,
    ModelStatus, ModelQuantization, DeploymentStatus, DeploymentEnvironment,
    GPUStatus, WorkerStatus, WorkerPoolStatus, ClusterType, ClusterStatus,
    InvoiceStatus, UsageLogStatus, ModelInstanceStatus
)
from backend.core.config import get_settings


# ============================================================================
# Test Settings Override
# ============================================================================

@pytest.fixture
def test_settings():
    """Get test settings with safe defaults."""
    from backend.core.config import Settings
    return Settings(
        app_name="TokenMachine-Test",
        environment="testing",
        debug=True,
        database_url="sqlite:///:memory:",
        redis_url="redis://localhost:6379/1",
        secret_key="test-secret-key-for-testing-only",
        api_key_prefix="tm_test_",
        api_key_length=16,
        access_token_expire_minutes=60,
        model_storage_path="/tmp/test_tokenmachine/models",
        log_path="/tmp/test_tokenmachine/logs",
        gpu_memory_utilization=0.9,
        max_model_len=4096,
        worker_base_port=9000,
        worker_start_timeout=10,
        prometheus_port=9091,
        metrics_enabled=False,
        rate_limit_enabled=False,
        log_level="DEBUG",
    )


@pytest.fixture(autouse=True)
def override_settings(test_settings, monkeypatch):
    """Automatically override settings for all tests."""
    def mock_get_settings():
        return test_settings

    monkeypatch.setattr("backend.core.config.get_settings", mock_get_settings)
    monkeypatch.setattr("backend.core.security.settings", test_settings)

    # Ensure test directories exist
    os.makedirs(test_settings.model_storage_path, exist_ok=True)
    os.makedirs(test_settings.log_path, exist_ok=True)

    yield

    # Cleanup test directories
    import shutil
    if os.path.exists(test_settings.model_storage_path):
        shutil.rmtree(test_settings.model_storage_path)
    if os.path.exists(test_settings.log_path):
        shutil.rmtree(test_settings.log_path)


# ============================================================================
# Database Fixtures
# ============================================================================

@pytest.fixture
def db_engine(test_settings):
    """Create a test database engine."""
    engine = create_engine(
        test_settings.database_url,
        connect_args={"check_same_thread": False} if "sqlite" in test_settings.database_url else {}
    )
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture
def db_session_factory(db_engine):
    """Create a test database session factory."""
    return sessionmaker(autocommit=False, autoflush=False, bind=db_engine)


@pytest.fixture
def db_session(db_session_factory):
    """Create a test database session."""
    session = db_session_factory()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


# ============================================================================
# Organization Fixtures
# ============================================================================

@pytest.fixture
def test_organization(db_session):
    """Create a test organization."""
    org = Organization(
        name="test-org",
        plan=OrganizationPlan.FREE,
        quota_tokens=10000,
        quota_models=1,
        quota_gpus=1,
        max_workers=2
    )
    db_session.add(org)
    db_session.commit()
    db_session.refresh(org)
    return org


# ============================================================================
# User Fixtures
# ============================================================================

@pytest.fixture
def test_user(db_session, test_organization):
    """Create a test user."""
    from backend.core.security import hash_password
    user = User(
        username="testuser",
        email="test@example.com",
        password_hash=hash_password("testpassword123"),
        organization_id=test_organization.id,
        role=UserRole.USER,
        is_active=True
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def test_admin_user(db_session, test_organization):
    """Create a test admin user."""
    from backend.core.security import hash_password
    user = User(
        username="admin",
        email="admin@example.com",
        password_hash=hash_password("adminpassword123"),
        organization_id=test_organization.id,
        role=UserRole.ADMIN,
        is_active=True
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def test_readonly_user(db_session, test_organization):
    """Create a test readonly user."""
    from backend.core.security import hash_password
    user = User(
        username="readonly",
        email="readonly@example.com",
        password_hash=hash_password("readonly123"),
        organization_id=test_organization.id,
        role=UserRole.READONLY,
        is_active=True
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


# ============================================================================
# API Key Fixtures
# ============================================================================

@pytest.fixture
def test_api_key(db_session, test_user, test_organization):
    """Create a test API key."""
    from backend.core.security import generate_api_key, hash_api_key
    api_key = generate_api_key()
    key_hash, key_prefix = hash_api_key(api_key)

    key = ApiKey(
        key_hash=key_hash,
        key_prefix=key_prefix,
        user_id=test_user.id,
        organization_id=test_organization.id,
        name="Test API Key",
        quota_tokens=1000000,
        tokens_used=0,
        is_active=True
    )
    db_session.add(key)
    db_session.commit()
    db_session.refresh(key)
    return key, api_key


# ============================================================================
# Model Fixtures
# ============================================================================

@pytest.fixture
def test_model(db_session):
    """Create a test model."""
    model = Model(
        name="meta-llama/Llama-3-8B-Instruct",
        version="v1.0.0",
        source=ModelSource.HUGGINGFACE,
        category=ModelCategory.LLM,
        quantization=ModelQuantization.FP16,
        path="/tmp/test_models/llama-3-8b",
        size_gb=16.0,
        status=ModelStatus.READY,
        download_progress=100
    )
    db_session.add(model)
    db_session.commit()
    db_session.refresh(model)
    return model


# ============================================================================
# Cluster Fixtures
# ============================================================================

@pytest.fixture
def test_cluster(db_session):
    """Create a test cluster."""
    cluster = Cluster(
        name="test-cluster",
        type=ClusterType.STANDALONE,
        is_default=True,
        status=ClusterStatus.RUNNING
    )
    db_session.add(cluster)
    db_session.commit()
    db_session.refresh(cluster)
    return cluster


@pytest.fixture
def test_worker_pool(db_session, test_cluster):
    """Create a test worker pool."""
    pool = WorkerPool(
        cluster_id=test_cluster.id,
        name="test-pool",
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
def test_worker(db_session, test_cluster):
    """Create a test worker."""
    worker = Worker(
        cluster_id=test_cluster.id,
        name="test-worker",
        ip="192.168.1.100",
        port=8080,
        status=WorkerStatus.READY,
        gpu_count=2,
        last_heartbeat_at=datetime.utcnow()
    )
    db_session.add(worker)
    db_session.commit()
    db_session.refresh(worker)
    return worker


# ============================================================================
# GPU Device Fixtures
# ============================================================================

@pytest.fixture
def test_gpu_device(db_session, test_worker):
    """Create a test GPU device."""
    from backend.models.database import GPUVendor, GPUDeviceState
    gpu = GPUDevice(
        worker_id=test_worker.id,
        uuid="GPU-12345",
        name="NVIDIA RTX 3090",
        vendor=GPUVendor.NVIDIA,
        index=0,
        core_total=10496,
        memory_total=24000000000,
        state=GPUDeviceState.AVAILABLE
    )
    db_session.add(gpu)
    db_session.commit()
    db_session.refresh(gpu)
    return gpu


@pytest.fixture
def test_gpu(db_session):
    """Create a test GPU (legacy model)."""
    gpu = GPU(
        gpu_id="gpu:0",
        name="NVIDIA GeForce RTX 4090",
        memory_total_mb=24576,
        memory_free_mb=24576,
        utilization_percent=0.0,
        temperature_celsius=30.0,
        status=GPUStatus.AVAILABLE
    )
    db_session.add(gpu)
    db_session.commit()
    db_session.refresh(gpu)
    return gpu


# ============================================================================
# Deployment Fixtures
# ============================================================================

@pytest.fixture
def test_deployment(db_session, test_model, test_gpu):
    """Create a test deployment."""
    deployment = Deployment(
        model_id=test_model.id,
        name="llama-3-8b-deployment",
        environment=DeploymentEnvironment.PRODUCTION,
        status=DeploymentStatus.RUNNING,
        replicas=1,
        traffic_weight=100,
        gpu_ids=["gpu:0"],
        backend="vllm",
        config={
            "tensor_parallel_size": 1,
            "max_model_len": 4096,
            "gpu_memory_utilization": 0.9,
            "dtype": "auto",
            "trust_remote_code": True
        },
        health_status={
            "0": {"healthy": True, "endpoint": "http://localhost:8001"}
        }
    )
    db_session.add(deployment)
    db_session.commit()
    db_session.refresh(deployment)
    return deployment


# ============================================================================
# Invoice Fixtures
# ============================================================================

@pytest.fixture
def test_invoice(db_session, test_organization):
    """Create a test invoice."""
    end_date = date.today()
    start_date = end_date - timedelta(days=30)

    invoice = Invoice(
        organization_id=test_organization.id,
        amount=Decimal("100.00"),
        currency="USD",
        status=InvoiceStatus.PENDING,
        period_start=datetime.combine(start_date, datetime.min.time()),
        period_end=datetime.combine(end_date, datetime.max.time()),
        tokens_used=50000
    )
    db_session.add(invoice)
    db_session.commit()
    db_session.refresh(invoice)
    return invoice


# ============================================================================
# Usage Log Fixtures
# ============================================================================

@pytest.fixture
def test_usage_log(db_session, test_api_key, test_deployment, test_model):
    """Create a test usage log."""
    api_key, _ = test_api_key
    usage_log = UsageLog(
        api_key_id=api_key.id,
        deployment_id=test_deployment.id,
        model_id=test_model.id,
        input_tokens=100,
        output_tokens=200,
        latency_ms=1500,
        status=UsageLogStatus.SUCCESS
    )
    db_session.add(usage_log)
    db_session.commit()
    db_session.refresh(usage_log)
    return usage_log


# ============================================================================
# Mock GPU Manager
# ============================================================================

@pytest.fixture
def mock_gpu_manager():
    """Create a mock GPU manager."""
    manager = MagicMock()
    manager.is_available.return_value = True
    manager.num_gpus = 2

    manager.get_gpu_info = MagicMock(side_effect=[
        {
            "id": "gpu:0",
            "index": 0,
            "name": "NVIDIA GeForce RTX 4090",
            "memory_total_mb": 24576,
            "memory_free_mb": 24576,
            "memory_used_mb": 0,
            "utilization_percent": 0,
            "temperature_celsius": 30,
        },
        {
            "id": "gpu:1",
            "index": 1,
            "name": "NVIDIA GeForce RTX 4090",
            "memory_total_mb": 24576,
            "memory_free_mb": 24576,
            "memory_used_mb": 0,
            "utilization_percent": 0,
            "temperature_celsius": 28,
        }
    ])

    manager.get_all_gpus = MagicMock(return_value=[
        {
            "id": "gpu:0",
            "index": 0,
            "name": "NVIDIA GeForce RTX 4090",
            "memory_total_mb": 24576,
            "memory_free_mb": 24576,
            "memory_used_mb": 0,
            "utilization_percent": 0,
            "temperature_celsius": 30,
        },
        {
            "id": "gpu:1",
            "index": 1,
            "name": "NVIDIA GeForce RTX 4090",
            "memory_total_mb": 24576,
            "memory_free_mb": 24576,
            "memory_used_mb": 0,
            "utilization_percent": 0,
            "temperature_celsius": 28,
        }
    ])

    manager.find_available_gpus = MagicMock(return_value=["gpu:0"])
    manager.get_total_memory = MagicMock(return_value=49152)
    manager.get_free_memory = MagicMock(return_value=49152)
    manager.get_average_utilization = MagicMock(return_value=0.0)
    manager.get_average_temperature = MagicMock(return_value=29.0)

    return manager


@pytest.fixture
def patch_gpu_manager(mock_gpu_manager):
    """Patch the GPU manager with mock."""
    with patch("backend.core.gpu.get_gpu_manager", return_value=mock_gpu_manager):
        with patch("backend.services.gpu_service.get_gpu_manager", return_value=mock_gpu_manager):
            with patch("backend.services.deployment_service.get_gpu_manager", return_value=mock_gpu_manager):
                yield mock_gpu_manager


# ============================================================================
# Mock Worker Pool
# ============================================================================

@pytest.fixture
def mock_worker():
    """Create a mock worker."""
    worker = MagicMock()
    worker.is_healthy.return_value = True
    worker.get_endpoint.return_value = "http://localhost:8001"
    worker.start = AsyncMock()
    worker.stop = AsyncMock()
    return worker


@pytest.fixture
def mock_worker_pool(mock_worker):
    """Create a mock worker pool."""
    pool = MagicMock()
    pool.create_worker = AsyncMock(return_value=mock_worker)
    pool.stop_deployment_workers = AsyncMock()
    pool.get_deployment_workers = MagicMock(return_value=[mock_worker])
    pool.get_healthy_worker_endpoint = MagicMock(return_value="http://localhost:8001")

    return pool


@pytest.fixture
def patch_worker_pool(mock_worker_pool):
    """Patch the worker pool with mock."""
    with patch("backend.workers.worker_pool.get_worker_pool", return_value=mock_worker_pool):
        with patch("backend.services.deployment_service.VLLMWorkerPool", return_value=mock_worker_pool):
            with patch("backend.api.v1.chat.get_worker_pool", return_value=mock_worker_pool):
                yield mock_worker_pool


# ============================================================================
# Async Event Loop
# ============================================================================

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# ============================================================================
# FastAPI Test Client
# ============================================================================

@pytest.fixture
def client(test_settings, db_session):
    """Create a test client for the FastAPI app."""
    from fastapi.testclient import TestClient
    from backend.main import app

    # Override database dependency
    def get_test_db():
        try:
            yield db_session
        finally:
            pass

    from backend.api.deps import get_db
    app.dependency_overrides[get_db] = get_test_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()
