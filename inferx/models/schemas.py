"""
Pydantic schemas for request/response validation.
"""
from datetime import datetime
from typing import Optional, List, Dict, Any, Literal
from enum import Enum
from pydantic import BaseModel, Field, field_validator, ConfigDict


# ============================================================================
# User Schemas
# ============================================================================

class UserBase(BaseModel):
    """Base user schema."""
    username: str = Field(..., min_length=3, max_length=255)
    email: str = Field(..., pattern=r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")


class UserCreate(UserBase):
    """User creation schema."""
    password: str = Field(..., min_length=8, max_length=255)
    is_admin: bool = False


class UserUpdate(BaseModel):
    """User update schema."""
    email: Optional[str] = None
    password: Optional[str] = Field(None, min_length=8, max_length=255)


class UserResponse(UserBase):
    """User response schema."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    is_admin: bool
    created_at: datetime
    updated_at: datetime


# ============================================================================
# API Key Schemas
# ============================================================================

class ApiKeyBase(BaseModel):
    """Base API key schema."""
    name: str = Field(..., min_length=1, max_length=255)
    quota_tokens: int = Field(default=10000000, ge=0)


class ApiKeyCreate(ApiKeyBase):
    """API key creation schema."""
    user_id: int


class ApiKeyResponse(ApiKeyBase):
    """API key response schema."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    key_prefix: str
    tokens_used: int
    is_active: bool
    expires_at: Optional[datetime]
    last_used_at: Optional[datetime]
    created_at: datetime


class ApiKeyCreateResponse(BaseModel):
    """API key creation response with the actual key."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    key: str  # Only shown once
    key_prefix: str
    name: str
    quota_tokens: int
    tokens_used: int


# ============================================================================
# Model Schemas
# ============================================================================

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


class ModelCreate(BaseModel):
    """Model creation schema."""
    name: str = Field(..., min_length=1, max_length=255)
    version: str = Field(..., min_length=1, max_length=50)
    source: ModelSource
    category: ModelCategory = ModelCategory.LLM
    huggingface_token: Optional[str] = None


class ModelUpdate(BaseModel):
    """Model update schema."""
    status: Optional[ModelStatus] = None
    error_message: Optional[str] = None


class ModelResponse(BaseModel):
    """Model response schema."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    version: str
    source: str
    category: str
    path: Optional[str]
    size_gb: Optional[float]
    status: str
    download_progress: int
    error_message: Optional[str]
    created_at: datetime
    updated_at: datetime


# ============================================================================
# Deployment Schemas
# ============================================================================

class DeploymentStatus(str, Enum):
    """Deployment status enumeration."""
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"


class DeploymentConfig(BaseModel):
    """Deployment configuration schema."""
    tensor_parallel_size: int = Field(default=1, ge=1)
    max_model_len: int = Field(default=4096, ge=1)
    gpu_memory_utilization: float = Field(default=0.9, ge=0.1, le=1.0)
    dtype: str = "auto"
    trust_remote_code: bool = True


class DeploymentCreate(BaseModel):
    """Deployment creation schema."""
    model_id: int = Field(..., ge=1)
    name: str = Field(..., min_length=1, max_length=255, pattern=r"^[a-zA-Z0-9-_]+$")
    replicas: int = Field(default=1, ge=1)
    gpu_ids: List[str] = Field(..., min_length=1)
    backend: str = Field(default="vllm", pattern=r"^(vllm|sglang)$")
    config: DeploymentConfig = Field(default_factory=DeploymentConfig)

    @field_validator("gpu_ids")
    @classmethod
    def validate_gpu_ids(cls, v: List[str]) -> List[str]:
        """Validate GPU ID format."""
        for gpu_id in v:
            if not gpu_id.startswith("gpu:"):
                raise ValueError(f"Invalid GPU ID format: {gpu_id}. Expected format: gpu:0, gpu:1, etc.")
        return v


class DeploymentUpdate(BaseModel):
    """Deployment update schema."""
    replicas: Optional[int] = Field(None, ge=1)
    status: Optional[DeploymentStatus] = None
    config: Optional[DeploymentConfig] = None


class DeploymentResponse(BaseModel):
    """Deployment response schema."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    model_id: int
    name: str
    status: str
    replicas: int
    gpu_ids: Optional[List[str]]
    backend: str
    config: Optional[Dict[str, Any]]
    health_status: Optional[Dict[str, Any]]
    created_at: datetime
    updated_at: datetime
    model: Optional[ModelResponse] = None


# ============================================================================
# GPU Schemas
# ============================================================================

class GPUStatus(str, Enum):
    """GPU status enumeration."""
    AVAILABLE = "available"
    IN_USE = "in_use"
    ERROR = "error"


class GPUInfo(BaseModel):
    """GPU information schema."""
    id: str
    name: str
    memory_total_mb: int
    memory_free_mb: int
    memory_used_mb: int
    utilization_percent: float
    temperature_celsius: float
    status: str
    deployment_id: Optional[int] = None
    updated_at: datetime


class GPUsResponse(BaseModel):
    """GPUs list response schema."""
    gpus: List[GPUInfo]
    total: int
    available: int
    in_use: int


# ============================================================================
# OpenAI Compatible API Schemas
# ============================================================================

class ChatMessage(BaseModel):
    """Chat message schema."""
    role: Literal["system", "user", "assistant"]
    content: str


class ChatCompletionRequest(BaseModel):
    """Chat completion request schema (OpenAI compatible)."""
    model: str
    messages: List[ChatMessage]
    temperature: Optional[float] = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: Optional[int] = Field(default=2048, ge=1)
    top_p: Optional[float] = Field(default=1.0, ge=0.0, le=1.0)
    frequency_penalty: Optional[float] = Field(default=0.0, ge=-2.0, le=2.0)
    presence_penalty: Optional[float] = Field(default=0.0, ge=-2.0, le=2.0)
    stop: Optional[List[str]] = None
    stream: Optional[bool] = False


class ChatCompletionChoice(BaseModel):
    """Chat completion choice schema."""
    index: int
    message: ChatMessage
    finish_reason: Optional[str] = None


class UsageInfo(BaseModel):
    """Token usage information schema."""
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


class ChatCompletionResponse(BaseModel):
    """Chat completion response schema (OpenAI compatible)."""
    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: List[ChatCompletionChoice]
    usage: UsageInfo


class ChatCompletionStreamChoice(BaseModel):
    """Chat completion stream choice schema."""
    index: int
    delta: Dict[str, Any]
    finish_reason: Optional[str] = None


class ChatCompletionStreamResponse(BaseModel):
    """Chat completion stream response schema (OpenAI compatible)."""
    id: str
    object: str = "chat.completion.chunk"
    created: int
    model: str
    choices: List[ChatCompletionStreamChoice]


# ============================================================================
# Models List API (OpenAI Compatible)
# ============================================================================

class ModelInfo(BaseModel):
    """Model information schema (OpenAI compatible)."""
    id: str
    object: str = "model"
    created: int
    owned_by: str = "inferx"


class ModelsListResponse(BaseModel):
    """Models list response schema (OpenAI compatible)."""
    object: str = "list"
    data: List[ModelInfo]


# ============================================================================
# Health Check Schemas
# ============================================================================

class HealthResponse(BaseModel):
    """Health check response schema."""
    status: str
    version: str
    database: str
    redis: str
    gpu_detected: bool
    gpu_count: int


# ============================================================================
# Error Schemas
# ============================================================================

class ErrorResponse(BaseModel):
    """Error response schema."""
    error: str
    message: str
    detail: Optional[str] = None
    request_id: Optional[str] = None


# ============================================================================
# Statistics Schemas
# ============================================================================

class SystemStats(BaseModel):
    """System statistics schema."""
    gpu_total: int
    gpu_used: int
    gpu_available: int
    models_total: int
    models_ready: int
    deployments_total: int
    deployments_running: int
    api_keys_total: int
    api_keys_active: int


class MonitoringStats(BaseModel):
    """Monitoring statistics schema."""
    api_requests_total: int
    api_requests_success: int
    api_requests_error: int
    tokens_generated_total: int
    avg_latency_ms: float
