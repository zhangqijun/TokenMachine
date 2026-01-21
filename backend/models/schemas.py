"""
Pydantic schemas for request/response validation.
"""
from datetime import datetime
from typing import Optional, List, Dict, Any, Literal
from enum import Enum
from pydantic import BaseModel, Field, field_validator, ConfigDict

# Import TaskType from database models for reuse
from backend.models.database import TaskType


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


class AddLocalModelRequest(BaseModel):
    """Request schema for adding a local model."""
    name: str = Field(..., min_length=1, max_length=255, description="Model name (e.g., Qwen3-Coder-30B)")
    version: str = Field(..., min_length=1, max_length=50, description="Model version (e.g., v1.0.0)")
    local_path: str = Field(..., min_length=1, description="Local model path (e.g., /home/ht706/Qwen3-Coder-30B-A3B-Instruct-Int4-W4A16)")
    category: ModelCategory = Field(default=ModelCategory.LLM, description="Model category")
    quantization: Optional[str] = Field(default="int8", description="Model quantization (fp16, int8, int4, etc.)")


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
    owned_by: str = "tokenmachine"


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


# ============================================================================
# Worker Schemas (GPU Worker Management)
# ============================================================================

class WorkerStatus(str, Enum):
    """Worker status enumeration."""
    CREATING = "creating"
    REGISTERING = "registering"
    READY = "ready"
    DEGRADED = "degraded"
    OFFLINE = "offline"
    MAINTENANCE = "maintenance"


class WorkerCreate(BaseModel):
    """Worker creation schema."""
    name: str = Field(..., min_length=1, max_length=255, description="Worker name")
    cluster_id: Optional[int] = Field(None, description="Cluster ID (default to default cluster)")
    labels: Optional[Dict[str, str]] = Field(None, description="Worker labels (e.g., gpu-type, zone)")
    expected_gpu_count: Optional[int] = Field(0, ge=0, description="Expected GPU count")


class WorkerUpdate(BaseModel):
    """Worker update schema."""
    labels: Optional[Dict[str, str]] = None
    status: Optional[WorkerStatus] = None
    expected_gpu_count: Optional[int] = Field(None, ge=0)


class GPUDeviceResponse(BaseModel):
    """GPU device response schema."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    uuid: str
    name: str
    vendor: Optional[str]
    index: int
    ip: str
    port: int
    hostname: Optional[str]
    pci_bus: Optional[str]
    core_total: Optional[int]
    core_utilization_rate: Optional[float]
    memory_total: int
    memory_used: int
    memory_allocated: int
    memory_utilization_rate: Optional[float]
    temperature: Optional[float]
    state: str
    status_json: Optional[Dict[str, Any]]
    created_at: datetime
    updated_at: datetime


class WorkerResponse(BaseModel):
    """Worker response schema."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    cluster_id: int
    status: WorkerStatus
    labels: Optional[Dict[str, str]]
    expected_gpu_count: int
    gpu_count: int
    last_heartbeat_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    gpus: Optional[List[GPUDeviceResponse]] = None


class WorkerCreateResponse(BaseModel):
    """Worker creation response schema."""
    id: int
    name: str
    status: WorkerStatus
    register_token: str  # Only returned once
    install_command: str
    expected_gpu_count: int
    current_gpu_count: int
    created_at: datetime


class WorkerListResponse(BaseModel):
    """Worker list response schema."""
    items: List[WorkerResponse]
    total: int
    page: int
    page_size: int


# ============================================================================
# GPU Registration Schemas
# ============================================================================

class GPUDeviceInfo(BaseModel):
    """GPU device info from agent."""
    gpu_uuid: str = Field(..., description="GPU UUID")
    gpu_index: int = Field(..., ge=0, description="GPU index on the machine")
    ip: str = Field(..., description="Physical machine IP")
    port: int = Field(..., ge=1024, le=65535, description="Agent port")
    memory_total: int = Field(..., gt=0, description="Total memory in bytes")
    memory_allocated: int = Field(..., ge=0, description="Allocated memory in bytes")
    memory_utilization_rate: float = Field(0.0, ge=0.0, le=1.0, description="Memory utilization rate")
    temperature: float = Field(..., ge=0.0, le=150.0, description="GPU temperature in Celsius")
    agent_pid: int = Field(..., gt=0, description="Agent process ID")
    vllm_pid: Optional[int] = Field(None, description="vLLM process ID (if running)")
    timestamp: str = Field(..., description="ISO format timestamp")
    state: str = Field("in_use", description="GPU state")
    extra: Optional[Dict[str, Any]] = Field(None, description="Additional GPU info (name, hostname, pci_bus)")


class GPURegisterRequest(BaseModel):
    """GPU registration request schema (from agent)."""
    gpu: GPUDeviceInfo


class GPURegisterResponse(BaseModel):
    """GPU registration response schema."""
    success: bool
    gpu_device_id: int
    worker_id: int
    worker_name: str
    current_gpu_count: int
    expected_gpu_count: int
    worker_status: WorkerStatus


class WorkerAddGPUResponse(BaseModel):
    """Response for getting token to add GPU to existing worker."""
    register_token: str
    install_command: str
    message: str


# ============================================================================
# GPU Heartbeat Schemas
# ============================================================================

class GPUHeartbeatRequest(BaseModel):
    """GPU heartbeat request schema (from agent)."""
    gpu_uuid: str
    gpu_index: int
    ip: str
    port: int
    memory_total: int
    memory_used: int
    memory_allocated: int
    memory_utilization_rate: float
    core_utilization_rate: float
    temperature: float
    agent_pid: int
    vllm_pid: Optional[int] = None
    timestamp: str
    state: str
    extra: Optional[Dict[str, Any]] = None


class GPUHeartbeatResponse(BaseModel):
    """GPU heartbeat response schema."""
    success: bool
    message: str


class BatchHeartbeatRequest(BaseModel):
    """Batch GPU heartbeat request schema (from agent)."""
    heartbeats: List[GPUHeartbeatRequest] = Field(..., min_length=1, max_length=100)


class BatchHeartbeatResponse(BaseModel):
    """Batch GPU heartbeat response schema."""
    success: bool
    updated_count: int


# ============================================================================
# Playground (Dialogue Testing) Schemas
# ============================================================================

class PlaygroundSessionCreate(BaseModel):
    """Create playground session request."""
    deployment_id: Optional[int] = None
    session_name: Optional[str] = "Untitled Session"
    model_parameters: Dict[str, Any] = Field(
        ...,
        alias="model_config",
        json_schema_extra={
            "example": {
                "model": "llama-3-8b-instruct",
                "temperature": 0.7,
                "topP": 0.9,
                "maxTokens": 2048,
                "frequencyPenalty": 0.0,
                "presencePenalty": 0.0,
                "systemPrompt": "You are a helpful assistant"
            }
        }
    )

    class Config:
        populate_by_name = True


class PlaygroundMessageCreate(BaseModel):
    """Send message request."""
    content: str = Field(..., min_length=1, max_length=10000)


class PlaygroundMessageResponse(BaseModel):
    """Message response."""
    id: int
    role: str
    content: str
    input_tokens: int
    output_tokens: int
    timestamp: datetime

    model_config = ConfigDict(from_attributes=True)


class PlaygroundSessionResponse(BaseModel):
    """Session response."""
    id: int
    user_id: int
    deployment_id: Optional[int]
    session_name: str
    model_parameters: Dict[str, Any] = Field(alias="model_config")
    input_tokens: int
    output_tokens: int
    total_cost: float
    created_at: datetime
    updated_at: datetime
    messages: List[PlaygroundMessageResponse] = []

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


# ============================================================================
# Benchmark (Batch Testing) Schemas
# ============================================================================

class BenchmarkTaskCreate(BaseModel):
    """Create benchmark task request."""
    deployment_id: Optional[int] = None
    task_name: str = Field(..., min_length=1, max_length=255)
    task_type: TaskType
    config: Dict[str, Any] = Field(
        ...,
        example={
            "model": "llama-3-8b-instruct",
            "dataset": "mmlu",
            "data_type": "all",
            "limit": 100,
            "generation_config": {
                "max_tokens": 2048,
                "temperature": 0.7
            }
        }
    )


class BenchmarkTaskResponse(BaseModel):
    """Benchmark task response."""
    id: int
    user_id: int
    deployment_id: Optional[int]
    task_name: str
    task_type: str
    status: str
    config: Dict[str, Any]
    result: Optional[Dict[str, Any]] = None
    output_dir: Optional[str] = None
    error_message: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    celery_task_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class BenchmarkDatasetResponse(BaseModel):
    """Benchmark dataset response."""
    id: int
    name: str
    category: Optional[str]
    description: Optional[str]
    dataset_size: Optional[int]
    meta_data: Optional[Dict[str, Any]] = None
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# Backend Engine Schemas
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


class BackendEngineFeatures(BaseModel):
    """Backend engine features."""
    tensor_parallel: bool = False
    prefix_caching: bool = False
    multi_lora: bool = False
    speculative_decoding: bool = False
    quantization: List[str] = []
    model_formats: List[str] = []


class BackendEngineCompatibility(BaseModel):
    """Backend engine compatibility information."""
    gpu_vendors: List[str] = []
    min_gpu_memory_mb: int = 0
    supported_models: List[str] = []


class BackendEngineResponse(BaseModel):
    """Backend engine response."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    engine_type: str
    version: str
    status: str
    install_path: Optional[str] = None
    image_name: Optional[str] = None
    tarball_path: Optional[str] = None
    installed_at: Optional[datetime] = None
    size_mb: Optional[int] = None
    active_deployments: int
    config: Optional[Dict[str, Any]] = None
    env_vars: Optional[Dict[str, Any]] = None

    created_at: datetime
    updated_at: datetime


class BackendEngineInfo(BaseModel):
    """Backend engine detailed information."""
    id: int
    name: str  # vllm, sglang, llama_cpp
    display_name: str
    version: str
    status: str
    icon: str
    description: str
    homepage: str
    features: BackendEngineFeatures
    compatibility: BackendEngineCompatibility
    config: Optional[Dict[str, Any]] = None
    env_vars: Optional[Dict[str, Any]] = None
    stats: Dict[str, Any]


class BackendEngineInstallRequest(BaseModel):
    """Backend engine installation request."""
    version: str = Field(..., min_length=1, max_length=50, description="Engine version")
    image_name: Optional[str] = Field(None, max_length=255, description="Custom image name")
    install_path: Optional[str] = Field(None, max_length=1024, description="Installation path")
    config: Optional[Dict[str, Any]] = Field(None, description="Engine configuration")
    env_vars: Optional[Dict[str, str]] = Field(None, description="Environment variables")


class BackendEngineInstallResponse(BaseModel):
    """Backend engine installation response."""
    id: int
    engine_type: str
    version: str
    status: str
    install_command: Optional[str] = None
    message: str


class BackendEngineListResponse(BaseModel):
    """Backend engine list response."""
    items: List[BackendEngineInfo]
    total: int


class BackendEngineStatsResponse(BaseModel):
    """Backend engine statistics response."""
    engine_type: str
    version: str
    status: str
    active_deployments: int
    size_mb: Optional[int] = None
    installed_at: Optional[str] = None


# ============================================================================
# Gateway Management Schemas
# ============================================================================

class RoutingMode(str, Enum):
    """路由模式枚举"""
    SEMANTIC = "semantic"
    WEIGHT = "weight"
    ROUND_ROBIN = "round_robin"
    LEAST_CONN = "least_conn"


class RoutingRule(BaseModel):
    """路由规则"""
    pattern: str = Field(..., description="匹配模式（支持正则表达式）")
    target: str = Field(..., description="目标实例名称")
    weight: int = Field(default=100, ge=0, le=100, description="权重百分比")
    priority: int = Field(default=1, ge=1, le=10, description="优先级（数字越小优先级越高）")


class RoutingStrategyBase(BaseModel):
    """路由策略基础 schema"""
    name: str = Field(..., min_length=1, max_length=255, description="策略名称")
    description: Optional[str] = Field(None, description="策略描述")
    mode: RoutingMode = Field(default=RoutingMode.SEMANTIC, description="路由模式")
    rules: List[RoutingRule] = Field(default_factory=list, description="路由规则列表")
    is_enabled: bool = Field(default=True, description="是否启用")
    enable_aggregation: bool = Field(default=False, description="启用 API 聚合")
    unified_endpoint: Optional[str] = Field(None, description="统一端点路径")
    response_mode: Optional[str] = Field("best", description="响应模式: best/all/custom")


class RoutingStrategyCreate(RoutingStrategyBase):
    """创建路由策略请求"""
    pass


class RoutingStrategyUpdate(BaseModel):
    """更新路由策略请求"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    mode: Optional[RoutingMode] = None
    rules: Optional[List[RoutingRule]] = None
    is_enabled: Optional[bool] = None
    enable_aggregation: Optional[bool] = None
    unified_endpoint: Optional[str] = None
    response_mode: Optional[str] = None


class RoutingStrategyResponse(RoutingStrategyBase):
    """路由策略响应"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    bound_keys_count: int
    today_requests: int
    p95_latency_ms: int
    created_at: datetime
    updated_at: datetime


class ApiKeyRouteBindingCreate(BaseModel):
    """创建 API 密钥路由绑定"""
    api_key_id: int = Field(..., ge=1)
    routing_strategy_id: int = Field(..., ge=1)
    traffic_weight: int = Field(default=100, ge=0, le=100, description="流量权重")


class ApiKeyRouteBindingResponse(BaseModel):
    """API 密钥路由绑定响应"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    api_key_id: int
    routing_strategy_id: int
    traffic_weight: int
    created_at: datetime


class GatewayConfigUpdate(BaseModel):
    """更新网关配置"""
    # 负载均衡配置
    enable_dynamic_lb: Optional[bool] = None
    schedule_strategy: Optional[str] = Field(None, pattern="^(queue|response|resource|combined)$")
    queue_threshold: Optional[int] = Field(None, ge=1, le=200)
    response_threshold: Optional[int] = Field(None, ge=100, le=30000)
    gpu_threshold: Optional[int] = Field(None, ge=50, le=100)

    # 健康检查配置
    enable_failover: Optional[bool] = None
    check_method: Optional[str] = Field(None, pattern="^(active|passive)$")
    check_interval: Optional[int] = Field(None, ge=1, le=300)
    timeout: Optional[int] = Field(None, ge=1, le=60)
    fail_threshold: Optional[int] = Field(None, ge=1, le=10)
    response_time_threshold: Optional[int] = Field(None, ge=100, le=30000)
    error_rate_threshold: Optional[int] = Field(None, ge=1, le=100)
    queue_depth_threshold: Optional[int] = Field(None, ge=10, le=500)
    auto_recover: Optional[bool] = None
    recover_threshold: Optional[int] = Field(None, ge=1, le=10)


class GatewayConfigResponse(BaseModel):
    """网关配置响应"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    # 负载均衡配置
    enable_dynamic_lb: bool
    schedule_strategy: str
    queue_threshold: int
    response_threshold: int
    gpu_threshold: int

    # 健康检查配置
    enable_failover: bool
    check_method: str
    check_interval: int
    timeout: int
    fail_threshold: int
    response_time_threshold: int
    error_rate_threshold: int
    queue_depth_threshold: int
    auto_recover: bool
    recover_threshold: int

    updated_at: datetime


class InstanceHealthStatus(str, Enum):
    """实例健康状态枚举"""
    HEALTHY = "healthy"
    WARNING = "warning"
    FAILED = "failed"


class InstanceHealthResponse(BaseModel):
    """实例健康状态响应"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    model_instance_id: int
    status: InstanceHealthStatus
    last_check_at: datetime
    fail_count: int
    consecutive_success_count: int
    queue_depth: int
    response_time_ms: int
    gpu_utilization: float
    error_rate: float
    created_at: datetime
    updated_at: datetime


class FailoverEventType(str, Enum):
    """故障转移事件类型枚举"""
    TIMEOUT = "timeout"
    ERROR = "error"
    OVERLOAD = "overload"
    MANUAL = "manual"
    HEALTH_CHECK_FAILED = "health_check_failed"


class FailoverEventResponse(BaseModel):
    """故障转移事件响应"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    source_instance_id: Optional[int]
    target_instance_id: Optional[int]
    event_type: FailoverEventType
    reason: Optional[str]
    triggered_by: Optional[str]
    created_at: datetime


class ManualFailoverRequest(BaseModel):
    """手动故障转移请求"""
    source_instance_id: int = Field(..., ge=1, description="源实例 ID")
    target_instance_id: Optional[int] = Field(None, ge=1, description="目标实例 ID（可选，自动选择）")
    reason: Optional[str] = Field(None, description="转移原因")


class InstanceLoadResponse(BaseModel):
    """实例负载响应"""
    model_instance_id: int
    instance_name: str
    queue_depth: int
    response_time_ms: int
    gpu_utilization: float
    status: InstanceHealthStatus
