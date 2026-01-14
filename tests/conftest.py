"""
Pytest configuration and shared fixtures for InferX tests.
"""
import os
import sys
import asyncio
import pytest
import pytest_asyncio
from typing import AsyncGenerator, Generator
from pathlib import Path
from unittest.mock import Mock, AsyncMock, MagicMock, patch
from datetime import datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from inferx.core.config import Settings, get_settings
from inferx.models.database import Base, User, Model, Deployment, GPU, ApiKey, UsageLog
from inferx.models.database import (
    ModelCategory, ModelSource, ModelStatus,
    DeploymentStatus, GPUStatus, UsageLogStatus
)


# ============================================================================
# Test Settings Override
# ============================================================================

@pytest.fixture
def test_settings() -> Settings:
    """Get test settings with safe defaults."""
    return Settings(
        app_name="InferX-Test",
        environment="testing",
        debug=True,
        database_url="sqlite:///:memory:",
        redis_url="redis://localhost:6379/1",  # Use different DB for testing
        secret_key="test-secret-key-for-testing-only",
        api_key_prefix="test_sk_",
        api_key_length=16,
        access_token_expire_minutes=60,
        model_storage_path="/tmp/test_inferx/models",
        log_path="/tmp/test_inferx/logs",
        gpu_memory_utilization=0.9,
        max_model_len=4096,
        worker_base_port=9000,
        worker_start_timeout=10,
        prometheus_port=9091,
        metrics_enabled=False,  # Disable metrics during tests
        rate_limit_enabled=False,  # Disable rate limiting during tests
        log_level="DEBUG",
    )


@pytest.fixture(autouse=True)
def override_settings(test_settings: Settings, monkeypatch):
    """Automatically override settings for all tests."""
    def mock_get_settings():
        return test_settings

    monkeypatch.setattr("inferx.core.config.get_settings", mock_get_settings)
    monkeypatch.setattr("inferx.core.security.settings", test_settings)

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
def db_engine(test_settings: Settings):
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
def db_session(db_session_factory) -> Generator[Session, None, None]:
    """Create a test database session."""
    session = db_session_factory()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


# ============================================================================
# Model Fixtures
# ============================================================================

@pytest.fixture
def test_user(db_session: Session) -> User:
    """Create a test user."""
    from inferx.core.security import hash_password
    user = User(
        username="testuser",
        email="test@example.com",
        password_hash=hash_password("testpassword123"),
        is_admin=False
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def test_admin_user(db_session: Session) -> User:
    """Create a test admin user."""
    from inferx.core.security import hash_password
    user = User(
        username="admin",
        email="admin@example.com",
        password_hash=hash_password("adminpassword123"),
        is_admin=True
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def test_api_key(db_session: Session, test_user: User) -> ApiKey:
    """Create a test API key."""
    from inferx.core.security import generate_api_key, hash_api_key
    api_key = generate_api_key(test_user.id)
    key = ApiKey(
        key_hash=hash_api_key(api_key),
        key_prefix=api_key[:10],
        user_id=test_user.id,
        name="Test API Key",
        quota_tokens=1000000,
        tokens_used=0,
        is_active=True
    )
    db_session.add(key)
    db_session.commit()
    db_session.refresh(key)
    return key, api_key  # Return both record and raw key


@pytest.fixture
def test_model(db_session: Session) -> Model:
    """Create a test model."""
    model = Model(
        name="meta-llama/Llama-3-8B-Instruct",
        version="v1.0.0",
        source=ModelSource.HUGGINGFACE,
        category=ModelCategory.LLM,
        path="/tmp/test_models/llama-3-8b",
        size_gb=16.0,
        status=ModelStatus.READY,
        download_progress=100
    )
    db_session.add(model)
    db_session.commit()
    db_session.refresh(model)
    return model


@pytest.fixture
def test_gpu(db_session: Session) -> GPU:
    """Create a test GPU."""
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


@pytest.fixture
def test_deployment(
    db_session: Session,
    test_model: Model,
    test_gpu: GPU
) -> Deployment:
    """Create a test deployment."""
    deployment = Deployment(
        model_id=test_model.id,
        name="llama-3-8b-deployment",
        status=DeploymentStatus.RUNNING,
        replicas=1,
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

    # Update GPU status
    test_gpu.status = GPUStatus.IN_USE
    test_gpu.deployment_id = deployment.id

    db_session.commit()
    db_session.refresh(deployment)
    return deployment


@pytest.fixture
def test_usage_log(
    db_session: Session,
    test_api_key,
    test_deployment: Deployment,
    test_model: Model
) -> UsageLog:
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
            "power_draw_watts": 50,
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
            "power_draw_watts": 45,
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
    with patch("inferx.core.gpu.get_gpu_manager", return_value=mock_gpu_manager):
        with patch("inferx.services.gpu_service.get_gpu_manager", return_value=mock_gpu_manager):
            with patch("inferx.services.deployment_service.get_gpu_manager", return_value=mock_gpu_manager):
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
    with patch("inferx.workers.worker_pool.get_worker_pool", return_value=mock_worker_pool):
        with patch("inferx.services.deployment_service.VLLMWorkerPool", return_value=mock_worker_pool):
            with patch("inferx.api.v1.chat.get_worker_pool", return_value=mock_worker_pool):
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
def client(test_settings: Settings, db_session: Session):
    """Create a test client for the FastAPI app."""
    from fastapi.testclient import TestClient
    from inferx.main import app

    # Override database dependency
    def get_test_db():
        try:
            yield db_session
        finally:
            pass

    from inferx.api.deps import get_current_db
    app.dependency_overrides[get_current_db] = get_test_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


# ============================================================================
# HTTP Client Mock
# ============================================================================

@pytest.fixture
def mock_httpx_client():
    """Create a mock HTTP client for testing external requests."""
    # Create a mock response
    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.json = MagicMock(return_value={
        "id": "chatcmpl-test123",
        "object": "chat.completion",
        "created": 1234567890,
        "model": "llama-3-8b-deployment",
        "choices": [{
            "index": 0,
            "message": {
                "role": "assistant",
                "content": "This is a test response."
            },
            "finish_reason": "stop"
        }],
        "usage": {
            "prompt_tokens": 10,
            "completion_tokens": 5,
            "total_tokens": 15
        }
    })

    # Create async client with mocked post method
    async_client = AsyncMock()
    async_client.post = AsyncMock(return_value=mock_response)
    async_client.stream = MagicMock()

    return async_client
