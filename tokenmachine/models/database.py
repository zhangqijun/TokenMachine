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


class User(Base):
    """User model."""
    __tablename__ = "users"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    username = Column(String(255), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    is_admin = Column(Boolean, default=False, nullable=False)
    created_at = Column(TIMESTAMP, default=func.now(), nullable=False)
    updated_at = Column(TIMESTAMP, default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    api_keys = relationship("ApiKey", back_populates="user", cascade="all, delete-orphan")


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


class Model(Base):
    """Model model."""
    __tablename__ = "models"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False, index=True)
    version = Column(String(50), nullable=False)
    source = Column(SQLEnum(ModelSource), nullable=False)
    category = Column(SQLEnum(ModelCategory), nullable=False, index=True)
    path = Column(String(1024))
    size_gb = Column(DECIMAL(10, 2))
    status = Column(SQLEnum(ModelStatus), default=ModelStatus.DOWNLOADING, nullable=False, index=True)
    download_progress = Column(Integer, default=0)
    error_message = Column(Text)
    created_at = Column(TIMESTAMP, default=func.now(), nullable=False)
    updated_at = Column(TIMESTAMP, default=func.now(), onupdate=func.now(), nullable=False)

    # Unique constraint on name + version
    __table_args__ = (
        Index('ix_model_name_version', 'name', 'version', unique=True),
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


class Deployment(Base):
    """Deployment model."""
    __tablename__ = "deployments"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    model_id = Column(BigInteger, ForeignKey("models.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(255), nullable=False, unique=True, index=True)
    status = Column(SQLEnum(DeploymentStatus), default=DeploymentStatus.STARTING, nullable=False, index=True)
    replicas = Column(Integer, default=1, nullable=False)
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
    name = Column(String(255), nullable=False)
    quota_tokens = Column(BigInteger, default=10000000, nullable=False)  # 10M tokens
    tokens_used = Column(BigInteger, default=0, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    expires_at = Column(TIMESTAMP, nullable=True)
    last_used_at = Column(TIMESTAMP, nullable=True)
    created_at = Column(TIMESTAMP, default=func.now(), nullable=False)

    # Relationships
    user = relationship("User", back_populates="api_keys")
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
