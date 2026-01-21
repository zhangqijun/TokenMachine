"""
Database models for TokenMachine.
"""
from datetime import datetime
from typing import Optional, List
from enum import Enum

from sqlalchemy import (
    Column, BigInteger, String, Boolean, Integer, DECIMAL, Text, JSON,
    ForeignKey, TIMESTAMP, Index, Enum as SQLEnum, CheckConstraint
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, Mapped
from sqlalchemy.sql import func

Base = declarative_base()


class OrganizationPlan(str, Enum):
    """Organization plan enumeration."""
    FREE = "free"
    PROFESSIONAL = "professional"
    ENTERPRISE = "enterprise"


class Organization(Base):
    """Organization model for multi-tenancy support."""
    __tablename__ = "organizations"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    name = Column(String(255), unique=True, nullable=False, index=True)
    plan = Column(SQLEnum(OrganizationPlan), default=OrganizationPlan.FREE, nullable=False)
    quota_tokens = Column(BigInteger, default=10000, nullable=False)  # Monthly token quota
    quota_models = Column(Integer, default=1, nullable=False)  # Max deployable models
    quota_gpus = Column(Integer, default=1, nullable=False)  # Max usable GPUs
    max_workers = Column(Integer, default=2, nullable=False)  # Max workers
    created_at = Column(TIMESTAMP, default=func.now(), nullable=False)
    updated_at = Column(TIMESTAMP, default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    users = relationship("User", back_populates="organization", cascade="all, delete-orphan")
    api_keys = relationship("ApiKey", back_populates="organization")
    invoices = relationship("Invoice", back_populates="organization", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="organization")


class UserRole(str, Enum):
    """User role enumeration."""
    ADMIN = "admin"
    USER = "user"
    READONLY = "readonly"


class User(Base):
    """User model."""
    __tablename__ = "users"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    username = Column(String(255), nullable=False, index=True)
    email = Column(String(255), nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    organization_id = Column(BigInteger, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=True, index=True)
    role = Column(SQLEnum(UserRole), default=UserRole.USER, nullable=False, index=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(TIMESTAMP, default=func.now(), nullable=False)
    updated_at = Column(TIMESTAMP, default=func.now(), onupdate=func.now(), nullable=False)

    # Unique constraint on organization_id + username
    __table_args__ = (
        Index('ix_user_org_username', 'organization_id', 'username', unique=True),
        Index('ix_user_org_email', 'organization_id', 'email', unique=True),
    )

    # Relationships
    organization = relationship("Organization", back_populates="users")
    api_keys = relationship("ApiKey", back_populates="user", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="user")

    @property
    def is_admin(self) -> bool:
        """Check if user has admin role."""
        return self.role == UserRole.ADMIN


class ModelCategory(str, Enum):
    """Model category enumeration."""
    LLM = "llm"
    EMBEDDING = "embedding"
    RERANKER = "reranker"
    IMAGE = "image"
    TTS = "tts"
    STT = "stt"


class ModelSource(str, Enum):
    """Model source enumeration."""
    HUGGINGFACE = "huggingface"
    MODELSCOPE = "modelscope"
    LOCAL = "local"


class ModelStatus(str, Enum):
    """Model status enumeration."""
    DOWNLOADING = "downloading"
    READY = "ready"
    ERROR = "error"


class ModelQuantization(str, Enum):
    """Model quantization enumeration."""
    FP16 = "fp16"
    INT8 = "int8"
    FP4 = "fp4"
    FP8 = "fp8"


class Model(Base):
    """Model model."""
    __tablename__ = "models"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False, index=True)
    version = Column(String(50), nullable=False)
    source = Column(SQLEnum(ModelSource), nullable=False)
    category = Column(SQLEnum(ModelCategory), nullable=False, index=True)
    quantization = Column(SQLEnum(ModelQuantization), default=ModelQuantization.FP16, nullable=False)
    path = Column(String(1024))
    size_gb = Column(DECIMAL(10, 2))
    status = Column(SQLEnum(ModelStatus), default=ModelStatus.DOWNLOADING, nullable=False, index=True)
    download_progress = Column(Integer, default=0)
    error_message = Column(Text)
    created_at = Column(TIMESTAMP, default=func.now(), nullable=False)
    updated_at = Column(TIMESTAMP, default=func.now(), onupdate=func.now(), nullable=False)

    # Unique constraint on name + version + quantization
    __table_args__ = (
        Index('ix_model_name_version_quant', 'name', 'version', 'quantization', unique=True),
    )

    # Relationships
    deployments = relationship("Deployment", back_populates="model", cascade="all, delete-orphan")


class DeploymentStatus(str, Enum):
    """Deployment status enumeration."""
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"


class DeploymentEnvironment(str, Enum):
    """Deployment environment enumeration."""
    DEV = "dev"
    TEST = "test"
    STAGING = "staging"
    PRODUCTION = "production"


class Deployment(Base):
    """Deployment model."""
    __tablename__ = "deployments"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    model_id = Column(BigInteger, ForeignKey("models.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(255), nullable=False, unique=True, index=True)
    environment = Column(SQLEnum(DeploymentEnvironment), default=DeploymentEnvironment.PRODUCTION, nullable=False, index=True)
    status = Column(SQLEnum(DeploymentStatus), default=DeploymentStatus.STARTING, nullable=False, index=True)
    replicas = Column(Integer, default=1, nullable=False)
    traffic_weight = Column(Integer, default=100, nullable=False)  # For canary deployments
    gpu_ids = Column(JSON)  # List of GPU IDs like ["gpu:0", "gpu:1"]
    backend = Column(String(50), default="vllm", nullable=False)
    config = Column(JSON)  # Backend configuration parameters
    health_status = Column(JSON)  # Health status for each replica
    created_at = Column(TIMESTAMP, default=func.now(), nullable=False)
    updated_at = Column(TIMESTAMP, default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    model = relationship("Model", back_populates="deployments")
    gpus = relationship("GPU", back_populates="deployment", cascade="all, delete-orphan")
    usage_logs = relationship("UsageLog", back_populates="deployment")
    model_instances = relationship("ModelInstance", back_populates="deployment", cascade="all, delete-orphan")


class GPUStatus(str, Enum):
    """GPU status enumeration."""
    AVAILABLE = "available"
    IN_USE = "in_use"
    ERROR = "error"


class GPU(Base):
    """GPU model."""
    __tablename__ = "gpus"

    id = Column(Integer, primary_key=True, autoincrement=True)
    gpu_id = Column(String(50), unique=True, nullable=False, index=True)  # gpu:0, gpu:1
    name = Column(String(255), nullable=False)
    memory_total_mb = Column(BigInteger)
    memory_free_mb = Column(BigInteger)
    utilization_percent = Column(DECIMAL(5, 2))
    temperature_celsius = Column(DECIMAL(5, 2))
    status = Column(SQLEnum(GPUStatus), default=GPUStatus.AVAILABLE, nullable=False, index=True)
    deployment_id = Column(BigInteger, ForeignKey("deployments.id", ondelete="SET NULL"), nullable=True, index=True)
    updated_at = Column(TIMESTAMP, default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    deployment = relationship("Deployment", back_populates="gpus")


class ApiKey(Base):
    """API Key model."""
    __tablename__ = "api_keys"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    key_hash = Column(String(255), unique=True, nullable=False, index=True)
    key_prefix = Column(String(10), nullable=False)  # For display purposes
    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    organization_id = Column(BigInteger, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    quota_tokens = Column(BigInteger, default=10000000, nullable=False)  # 10M tokens
    tokens_used = Column(BigInteger, default=0, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    expires_at = Column(TIMESTAMP, nullable=True)
    last_used_at = Column(TIMESTAMP, nullable=True)
    created_at = Column(TIMESTAMP, default=func.now(), nullable=False)

    # Relationships
    user = relationship("User", back_populates="api_keys")
    organization = relationship("Organization", back_populates="api_keys")
    usage_logs = relationship("UsageLog", back_populates="api_key", cascade="all, delete-orphan")


class UsageLogStatus(str, Enum):
    """Usage log status enumeration."""
    SUCCESS = "success"
    ERROR = "error"


class UsageLog(Base):
    """Usage log model."""
    __tablename__ = "usage_logs"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    api_key_id = Column(BigInteger, ForeignKey("api_keys.id", ondelete="CASCADE"), nullable=False, index=True)
    deployment_id = Column(BigInteger, ForeignKey("deployments.id", ondelete="CASCADE"), nullable=False, index=True)
    model_id = Column(BigInteger, ForeignKey("models.id", ondelete="CASCADE"), nullable=False)
    input_tokens = Column(Integer, default=0, nullable=False)
    output_tokens = Column(Integer, default=0, nullable=False)
    latency_ms = Column(Integer)
    status = Column(SQLEnum(UsageLogStatus), default=UsageLogStatus.SUCCESS, nullable=False, index=True)
    error_message = Column(Text)
    created_at = Column(TIMESTAMP, default=func.now(), nullable=False, index=True)

    # Relationships
    api_key = relationship("ApiKey", back_populates="usage_logs")
    deployment = relationship("Deployment", back_populates="usage_logs")


# ============================================================================
# Server-Worker Architecture Models
# ============================================================================

class ClusterType(str, Enum):
    """Cluster type enumeration."""
    DOCKER = "docker"
    KUBERNETES = "kubernetes"
    STANDALONE = "standalone"
    DIGITALOCEAN = "digitalocean"
    AWS = "aws"


class ClusterStatus(str, Enum):
    """Cluster status enumeration."""
    RUNNING = "running"
    STOPPED = "stopped"
    ERROR = "error"


class Cluster(Base):
    """Cluster model - represents a logical cluster of workers."""
    __tablename__ = "clusters"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), unique=True, nullable=False, index=True)
    description = Column(Text)
    type = Column(SQLEnum(ClusterType), nullable=False, default=ClusterType.STANDALONE, index=True)
    is_default = Column(Boolean, default=False, nullable=False)
    status = Column(SQLEnum(ClusterStatus), default=ClusterStatus.RUNNING, nullable=False, index=True)
    config = Column(JSON)  # Cluster-specific configuration
    created_at = Column(TIMESTAMP, default=func.now(), nullable=False)
    updated_at = Column(TIMESTAMP, default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    workers = relationship("Worker", back_populates="cluster", cascade="all, delete-orphan")
    worker_pools = relationship("WorkerPool", back_populates="cluster", cascade="all, delete-orphan")


class WorkerPoolStatus(str, Enum):
    """Worker pool status enumeration."""
    RUNNING = "running"
    SCALING = "scaling"
    STOPPED = "stopped"


class WorkerPool(Base):
    """Worker pool model - for elastic worker scaling."""
    __tablename__ = "worker_pools"

    id = Column(Integer, primary_key=True, autoincrement=True)
    cluster_id = Column(Integer, ForeignKey("clusters.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    min_workers = Column(Integer, default=1, nullable=False)
    max_workers = Column(Integer, default=10, nullable=False)
    status = Column(SQLEnum(WorkerPoolStatus), default=WorkerPoolStatus.RUNNING, nullable=False)
    config = Column(JSON)  # Pool-specific configuration (docker, k8s, cloud)
    created_at = Column(TIMESTAMP, default=func.now(), nullable=False)
    updated_at = Column(TIMESTAMP, default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    cluster = relationship("Cluster", back_populates="worker_pools")
    workers = relationship("Worker", back_populates="pool")


class WorkerStatus(str, Enum):
    """Worker status enumeration."""
    NEW = "new"
    REGISTERING = "registering"
    READY = "ready"
    ALLOCATING = "allocating"
    BUSY = "busy"
    RELEASING = "releasing"
    UNHEALTHY = "unhealthy"
    DRAINING = "draining"
    TERMINATED = "terminated"
    OFFLINE = "offline"
    MAINTENANCE = "maintenance"


class Worker(Base):
    """Worker model - represents a worker node in the cluster."""
    __tablename__ = "workers"

    id = Column(Integer, primary_key=True, autoincrement=True)
    cluster_id = Column(Integer, ForeignKey("clusters.id", ondelete="CASCADE"), nullable=False, index=True)
    pool_id = Column(Integer, ForeignKey("worker_pools.id", ondelete="SET NULL"), nullable=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    ip = Column(String(45), nullable=True)  # IPv4 or IPv6 (deprecated: kept for compatibility)
    port = Column(Integer, default=8080, nullable=False)  # (deprecated: kept for compatibility)
    ifname = Column(String(50))  # Network interface name (deprecated: kept for compatibility)
    hostname = Column(String(255))  # (deprecated: kept for compatibility)
    status = Column(SQLEnum(WorkerStatus), default=WorkerStatus.REGISTERING, nullable=False, index=True)
    labels = Column(JSON)  # {"gpu": "nvidia", "zone": "us-west-1"}
    status_json = Column(JSON)  # {cpu: {...}, memory: {...}, gpu_devices: [...], filesystem: [...]}
    token_hash = Column(String(255), unique=True, nullable=True, index=True)
    gpu_count = Column(Integer, default=0, nullable=False)
    expected_gpu_count = Column(Integer, default=0, nullable=False)  # Expected GPU count for the worker
    last_heartbeat_at = Column(TIMESTAMP, nullable=True)
    last_status_update_at = Column(TIMESTAMP, nullable=True)
    created_at = Column(TIMESTAMP, default=func.now(), nullable=False)
    updated_at = Column(TIMESTAMP, default=func.now(), onupdate=func.now(), nullable=False)

    # Unique constraint on cluster_id + name
    __table_args__ = (
        Index('ix_worker_cluster_name', 'cluster_id', 'name', unique=True),
    )

    # Relationships
    cluster = relationship("Cluster", back_populates="workers")
    pool = relationship("WorkerPool", back_populates="workers")
    model_instances = relationship("ModelInstance", back_populates="worker", cascade="all, delete-orphan")
    gpu_devices = relationship("GPUDevice", back_populates="worker", cascade="all, delete-orphan")


class ModelInstanceStatus(str, Enum):
    """Model instance status enumeration."""
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"


class ModelInstance(Base):
    """Model instance model - represents a running instance of a model on a worker."""
    __tablename__ = "model_instances"

    id = Column(Integer, primary_key=True, autoincrement=True)
    deployment_id = Column(BigInteger, ForeignKey("deployments.id", ondelete="CASCADE"), nullable=False, index=True)
    model_id = Column(BigInteger, ForeignKey("models.id", ondelete="CASCADE"), nullable=False, index=True)
    worker_id = Column(Integer, ForeignKey("workers.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(255), nullable=False, unique=True, index=True)
    status = Column(SQLEnum(ModelInstanceStatus), default=ModelInstanceStatus.STARTING, nullable=False, index=True)
    endpoint = Column(String(255))  # http://worker-1:8001
    backend = Column(String(50), nullable=False, default="vllm")  # vllm, sglang, tensorrt, etc.
    config = Column(JSON)  # Backend-specific configuration
    gpu_ids = Column(JSON)  # List of GPU IDs assigned to this instance
    port = Column(Integer)  # Port number for the instance
    health_status = Column(JSON)  # Health check result
    created_at = Column(TIMESTAMP, default=func.now(), nullable=False)
    updated_at = Column(TIMESTAMP, default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    deployment = relationship("Deployment", back_populates="model_instances")
    model = relationship("Model")
    worker = relationship("Worker", back_populates="model_instances")


# ============================================================================
# GPU Device Tracking
# ============================================================================

class GPUVendor(str, Enum):
    """GPU vendor enumeration."""
    NVIDIA = "nvidia"
    AMD = "amd"
    APPLE = "apple"
    ASCEND = "ascend"
    MUXI = "muxi"


class GPUDeviceState(str, Enum):
    """GPU device state enumeration."""
    AVAILABLE = "available"
    IN_USE = "in_use"
    ERROR = "error"


class GPUDevice(Base):
    """GPU device model - detailed GPU tracking from worker status reports."""
    __tablename__ = "gpu_devices"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    worker_id = Column(Integer, ForeignKey("workers.id", ondelete="CASCADE"), nullable=False, index=True)
    uuid = Column(String(255), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    vendor = Column(SQLEnum(GPUVendor), nullable=True)
    index = Column(Integer, nullable=False)
    ip = Column(String(45), nullable=False)  # Physical machine IP where this GPU is located
    port = Column(Integer, nullable=False)  # Agent port for this GPU
    hostname = Column(String(255))  # Hostname of the physical machine
    pci_bus = Column(String(100))  # PCI bus ID (e.g., "0000:07:00.0")
    core_total = Column(Integer)
    core_utilization_rate = Column(DECIMAL(5, 2))
    memory_total = Column(BigInteger)
    memory_used = Column(BigInteger)
    memory_allocated = Column(BigInteger)
    memory_utilization_rate = Column(DECIMAL(5, 2))
    temperature = Column(DECIMAL(5, 2))
    state = Column(SQLEnum(GPUDeviceState), default=GPUDeviceState.AVAILABLE, nullable=False, index=True)
    status_json = Column(JSON)  # Additional status info (agent_pid, vllm_pid, etc.)
    created_at = Column(TIMESTAMP, default=func.now(), nullable=False)
    updated_at = Column(TIMESTAMP, default=func.now(), onupdate=func.now(), nullable=False)

    # Unique constraint on worker_id + uuid
    __table_args__ = (
        Index('ix_gpu_device_worker_uuid', 'worker_id', 'uuid', unique=True),
    )

    # Relationships
    worker = relationship("Worker", back_populates="gpu_devices")


# ============================================================================
# Billing Models
# ============================================================================

class InvoiceStatus(str, Enum):
    """Invoice status enumeration."""
    PENDING = "pending"
    PAID = "paid"
    CANCELLED = "cancelled"


class Invoice(Base):
    """Invoice model for billing."""
    __tablename__ = "invoices"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    organization_id = Column(BigInteger, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    amount = Column(DECIMAL(10, 2), nullable=False)
    currency = Column(String(3), default="USD", nullable=False)
    status = Column(SQLEnum(InvoiceStatus), default=InvoiceStatus.PENDING, nullable=False, index=True)
    period_start = Column(TIMESTAMP, nullable=False)
    period_end = Column(TIMESTAMP, nullable=False)
    tokens_used = Column(BigInteger, default=0, nullable=False)
    created_at = Column(TIMESTAMP, default=func.now(), nullable=False)
    updated_at = Column(TIMESTAMP, default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    organization = relationship("Organization", back_populates="invoices")


# ============================================================================
# Audit Log Models
# ============================================================================

class AuditAction(str, Enum):
    """Audit action enumeration."""
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    DEPLOY = "deploy"
    STOP = "stop"
    START = "start"


class AuditStatus(str, Enum):
    """Audit status enumeration."""
    SUCCESS = "success"
    FAILURE = "failure"


class ResourceType(str, Enum):
    """Resource type enumeration."""
    MODEL = "model"
    DEPLOYMENT = "deployment"
    CLUSTER = "cluster"
    WORKER = "worker"
    API_KEY = "api_key"
    USER = "user"
    ORGANIZATION = "organization"


class AuditLog(Base):
    """Audit log model for compliance and debugging."""
    __tablename__ = "audit_logs"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    organization_id = Column(BigInteger, ForeignKey("organizations.id", ondelete="SET NULL"), nullable=True, index=True)
    action = Column(SQLEnum(AuditAction), nullable=False, index=True)
    resource_type = Column(SQLEnum(ResourceType), nullable=True, index=True)
    resource_id = Column(BigInteger, nullable=True)
    resource_name = Column(String(255))
    ip_address = Column(String(45))
    user_agent = Column(Text)
    status = Column(SQLEnum(AuditStatus), default=AuditStatus.SUCCESS, nullable=False)
    error_message = Column(Text)
    created_at = Column(TIMESTAMP, default=func.now(), nullable=False, index=True)

    # Relationships
    user = relationship("User", back_populates="audit_logs")
    organization = relationship("Organization", back_populates="audit_logs")


# ============================================================================
# Playground Models
# ============================================================================

class PlaygroundSession(Base):
    """Dialogue testing session model."""
    __tablename__ = "playground_sessions"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    deployment_id = Column(BigInteger, ForeignKey("deployments.id", ondelete="SET NULL"), nullable=True)
    session_name = Column(String(255), default="Untitled Session")
    model_parameters = Column(JSON, nullable=False)  # Renamed from model_config to avoid SQLAlchemy conflict
    input_tokens = Column(BigInteger, default=0)
    output_tokens = Column(BigInteger, default=0)
    total_cost = Column(DECIMAL(10, 6), default=0.0000)
    created_at = Column(TIMESTAMP, default=func.now(), nullable=False)
    updated_at = Column(TIMESTAMP, default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    messages = relationship("PlaygroundMessage", back_populates="session", cascade="all, delete-orphan")

    __table_args__ = (
        Index('ix_playground_session_user_id', 'user_id'),
        Index('ix_playground_session_created_at', 'created_at'),
    )


class PlaygroundMessage(Base):
    """Dialogue message model."""
    __tablename__ = "playground_messages"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    session_id = Column(BigInteger, ForeignKey("playground_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    role = Column(String(20), nullable=False)  # user, assistant, system
    content = Column(Text, nullable=False)
    input_tokens = Column(Integer, default=0)
    output_tokens = Column(Integer, default=0)
    timestamp = Column(TIMESTAMP, default=func.now(), nullable=False)

    # Relationships
    session = relationship("PlaygroundSession", back_populates="messages")

    __table_args__ = (
        Index('ix_playground_message_session_id', 'session_id'),
        Index('ix_playground_message_timestamp', 'timestamp'),
    )


class TaskType(str, Enum):
    """Benchmark task type enumeration."""
    EVAL = "eval"
    PERF = "perf"


class TaskStatus(str, Enum):
    """Benchmark task status enumeration."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class BenchmarkTask(Base):
    """Benchmark task model."""
    __tablename__ = "benchmark_tasks"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    deployment_id = Column(BigInteger, ForeignKey("deployments.id", ondelete="SET NULL"), nullable=True)
    task_name = Column(String(255), nullable=False)
    task_type = Column(SQLEnum(TaskType), nullable=False)
    status = Column(SQLEnum(TaskStatus), default=TaskStatus.PENDING, nullable=False, index=True)
    config = Column(JSON, nullable=False)  # EvalScope configuration
    result = Column(JSON)  # Benchmark results
    output_dir = Column(String(1024))  # EvalScope output directory
    error_message = Column(Text)
    started_at = Column(TIMESTAMP)
    completed_at = Column(TIMESTAMP)
    celery_task_id = Column(String(255), index=True)  # Celery task ID
    created_at = Column(TIMESTAMP, default=func.now(), nullable=False)
    updated_at = Column(TIMESTAMP, default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        Index('ix_benchmark_task_user_id', 'user_id'),
        Index('ix_benchmark_task_status', 'status'),
        Index('ix_benchmark_task_created_at', 'created_at'),
        Index('ix_benchmark_task_celery_task_id', 'celery_task_id'),
    )


class BenchmarkDataset(Base):
    """Benchmark dataset model."""
    __tablename__ = "benchmark_datasets"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), unique=True, nullable=False, index=True)
    category = Column(String(100), index=True)  # mmlu, gsm8k, ceval, custom
    description = Column(Text)
    dataset_size = Column(Integer)
    meta_data = Column(JSON)  # Dataset metadata (renamed to avoid SQLAlchemy conflict)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(TIMESTAMP, default=func.now(), nullable=False)

    __table_args__ = (
        Index('ix_benchmark_dataset_category', 'category'),
        Index('ix_benchmark_dataset_name', 'name'),
    )


# ============================================================================
# Backend Engine Models
# ============================================================================

class BackendEngineType(str, Enum):
    """Backend engine type enumeration."""
    VLLM = "vllm"
    SGLANG = "sglang"
    LLAMA_CPP = "llama_cpp"


class BackendEngineStatus(str, Enum):
    """Backend engine status enumeration."""
    NOT_INSTALLED = "not_installed"
    INSTALLING = "installing"
    INSTALLED = "installed"
    ERROR = "error"
    OUTDATED = "outdated"


class BackendEngine(Base):
    """Backend engine model - manages inference engine installations and versions."""
    __tablename__ = "backend_engines"

    id = Column(Integer, primary_key=True)
    engine_type = Column(SQLEnum(BackendEngineType), nullable=False, index=True)
    version = Column(String(50), nullable=False)
    status = Column(SQLEnum(BackendEngineStatus), default=BackendEngineStatus.NOT_INSTALLED, nullable=False, index=True)

    # Installation information
    install_path = Column(String(1024))  # Installation path
    image_name = Column(String(255))  # Docker image name
    tarball_path = Column(String(1024))  # Path to tarball file
    installed_at = Column(TIMESTAMP)  # Installation time

    # Configuration
    config = Column(JSON)  # Engine-specific configuration
    env_vars = Column(JSON)  # Environment variables

    # Statistics
    size_mb = Column(Integer)  # Disk space usage in MB
    active_deployments = Column(Integer, default=0, nullable=False)  # Number of active deployments

    created_at = Column(TIMESTAMP, default=func.now(), nullable=False)
    updated_at = Column(TIMESTAMP, default=func.now(), onupdate=func.now(), nullable=False)

    # Unique constraint on engine_type + version
    __table_args__ = (
        Index('ix_backend_engine_type_version', 'engine_type', 'version', unique=True),
    )


# ============================================================================
# Gateway Management Models
# ============================================================================

class RoutingMode(str, Enum):
    """路由模式枚举"""
    SEMANTIC = "semantic"
    WEIGHT = "weight"
    ROUND_ROBIN = "round_robin"
    LEAST_CONN = "least_conn"


class InstanceHealthStatus(str, Enum):
    """实例健康状态枚举"""
    HEALTHY = "healthy"
    WARNING = "warning"
    FAILED = "failed"


class RoutingStrategy(Base):
    """路由策略表"""
    __tablename__ = "routing_strategies"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False, unique=True, index=True)
    description = Column(Text)
    mode = Column(SQLEnum(RoutingMode), nullable=False, default=RoutingMode.SEMANTIC, index=True)
    rules = Column(JSON, nullable=False, default=list)  # 路由规则列表
    is_enabled = Column(Boolean, default=True, nullable=False, index=True)

    # API 聚合配置
    enable_aggregation = Column(Boolean, default=False)
    unified_endpoint = Column(String(255))  # /v1/models/unified
    response_mode = Column(String(50))  # best/all/custom

    # 统计信息
    bound_keys_count = Column(Integer, default=0, nullable=False)
    today_requests = Column(BigInteger, default=0, nullable=False)
    p95_latency_ms = Column(Integer, default=0, nullable=False)

    created_at = Column(TIMESTAMP, default=func.now(), nullable=False)
    updated_at = Column(TIMESTAMP, default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    api_key_bindings = relationship("ApiKeyRouteBinding", back_populates="routing_strategy", cascade="all, delete-orphan")


class ApiKeyRouteBinding(Base):
    """API密钥与路由策略绑定表"""
    __tablename__ = "api_key_route_bindings"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    api_key_id = Column(BigInteger, ForeignKey("api_keys.id", ondelete="CASCADE"), nullable=False, index=True)
    routing_strategy_id = Column(BigInteger, ForeignKey("routing_strategies.id", ondelete="CASCADE"), nullable=False, index=True)
    traffic_weight = Column(Integer, default=100, nullable=False)  # 流量权重 0-100
    created_at = Column(TIMESTAMP, default=func.now(), nullable=False)

    # Relationships
    api_key = relationship("ApiKey")
    routing_strategy = relationship("RoutingStrategy", back_populates="api_key_bindings")

    __table_args__ = (
        Index('ix_apikey_routing_binding', 'api_key_id', 'routing_strategy_id', unique=True),
    )


class GatewayConfig(Base):
    """网关全局配置表"""
    __tablename__ = "gateway_configs"

    id = Column(BigInteger, primary_key=True, autoincrement=True)

    # 负载均衡配置
    enable_dynamic_lb = Column(Boolean, default=True, nullable=False)
    schedule_strategy = Column(String(50), default="queue", nullable=False)  # queue/response/resource/combined
    queue_threshold = Column(Integer, default=50, nullable=False)
    response_threshold = Column(Integer, default=5000, nullable=False)
    gpu_threshold = Column(Integer, default=95, nullable=False)

    # 健康检查配置
    enable_failover = Column(Boolean, default=True, nullable=False)
    check_method = Column(String(50), default="active", nullable=False)  # active/passive
    check_interval = Column(Integer, default=10, nullable=False)  # 秒
    timeout = Column(Integer, default=5, nullable=False)  # 秒
    fail_threshold = Column(Integer, default=3, nullable=False)
    response_time_threshold = Column(Integer, default=5000, nullable=False)
    error_rate_threshold = Column(Integer, default=10, nullable=False)
    queue_depth_threshold = Column(Integer, default=100, nullable=False)
    auto_recover = Column(Boolean, default=True, nullable=False)
    recover_threshold = Column(Integer, default=3, nullable=False)

    updated_at = Column(TIMESTAMP, default=func.now(), onupdate=func.now(), nullable=False)


class InstanceHealth(Base):
    """实例健康状态表"""
    __tablename__ = "instance_health"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    model_instance_id = Column(BigInteger, ForeignKey("model_instances.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    status = Column(SQLEnum(InstanceHealthStatus), default=InstanceHealthStatus.HEALTHY, nullable=False, index=True)
    last_check_at = Column(TIMESTAMP, default=func.now(), nullable=False)
    fail_count = Column(Integer, default=0, nullable=False)
    consecutive_success_count = Column(Integer, default=0, nullable=False)

    # 实时指标
    queue_depth = Column(Integer, default=0, nullable=False)
    response_time_ms = Column(Integer, default=0, nullable=False)
    gpu_utilization = Column(DECIMAL(5, 2), default=0, nullable=False)
    error_rate = Column(DECIMAL(5, 2), default=0, nullable=False)

    created_at = Column(TIMESTAMP, default=func.now(), nullable=False)
    updated_at = Column(TIMESTAMP, default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    model_instance = relationship("ModelInstance")


class FailoverEventType(str, Enum):
    """故障转移事件类型"""
    TIMEOUT = "timeout"
    ERROR = "error"
    OVERLOAD = "overload"
    MANUAL = "manual"
    HEALTH_CHECK_FAILED = "health_check_failed"


class FailoverEvent(Base):
    """故障转移事件记录表"""
    __tablename__ = "failover_events"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    source_instance_id = Column(BigInteger, ForeignKey("model_instances.id", ondelete="SET NULL"), nullable=True)
    target_instance_id = Column(BigInteger, ForeignKey("model_instances.id", ondelete="SET NULL"), nullable=True)
    event_type = Column(SQLEnum(FailoverEventType), nullable=False, index=True)
    reason = Column(Text)
    triggered_by = Column(String(50))  # auto/manual
    created_at = Column(TIMESTAMP, default=func.now(), nullable=False, index=True)

    # Relationships
    source_instance = relationship("ModelInstance", foreign_keys=[source_instance_id])
    target_instance = relationship("ModelInstance", foreign_keys=[target_instance_id])
