"""
Configuration management for TokenMachine.
"""
import os
from typing import Optional
from functools import lru_cache
from enum import Enum
from pydantic_settings import BaseSettings, SettingsConfigDict


class Environment(str, Enum):
    """Application environment types."""
    DEVELOPMENT = "development"
    TEST = "test"
    PRODUCTION = "production"


class Settings(BaseSettings):
    """Application settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    # Application
    app_name: str = "TokenMachine"
    app_version: str = "0.1.0"
    environment: Environment = Environment.DEVELOPMENT
    debug: bool = True

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8001
    api_reload: bool = False

    # Database
    database_url: str = "postgresql://tokenmachine:tokenmachine_password@localhost:5432/tokenmachine"
    database_pool_size: int = 10
    database_max_overflow: int = 20

    # Redis
    redis_url: str = "redis://localhost:6379/0"
    redis_pool_size: int = 10

    # Security
    secret_key: str = "your-secret-key-change-this-in-production"
    api_key_prefix: str = "tmachine_sk_"
    api_key_length: int = 32
    access_token_expire_minutes: int = 60 * 24 * 7  # 7 days

    # Storage
    model_storage_path: str = "/var/lib/tokenmachine/models"
    log_path: str = "/var/log/tokenmachine"

    # ModelScope Configuration
    modelscope_cache_dir: str = "/var/lib/tokenmachine/cache/modelscope"
    modelscope_sdk_debug: bool = False

    # Model Download Configuration
    download_max_concurrent: int = 3
    download_timeout_seconds: int = 7200  # 2 hours

    # NFS Configuration
    nfs_mount_point: str = "/mnt/models"  # Worker mount point

    # GPU
    gpu_memory_utilization: float = 0.9
    max_model_len: int = 4096
    gpu_check_interval_seconds: int = 30

    # Workers
    worker_base_port: int = 8001
    worker_start_timeout: int = 300  # 5 minutes
    worker_health_check_interval: int = 10

    # Monitoring
    prometheus_port: int = 9090
    metrics_enabled: bool = True

    # vLLM
    vllm_tensor_parallel_size: int = 1
    vllm_max_model_len: int = 4096
    vllm_gpu_memory_utilization: float = 0.9
    vllm_dtype: str = "auto"
    vllm_trust_remote_code: bool = True

    # Rate Limiting
    rate_limit_enabled: bool = True
    rate_limit_per_minute: int = 60

    # Logging
    log_level: str = "INFO"
    log_rotation: str = "500 MB"
    log_retention: str = "30 days"

    # Feature flags
    use_mock_data: bool = False  # Use mock data instead of real data

    # Playground
    inference_service_url: str = "http://localhost:8000"
    token_cost_rate: float = 0.0001  # Cost per token in CNY

    # Celery (for async benchmark tasks)
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/1"

    # EvalScope (for benchmark testing)
    evalscope_service_url: str = "http://localhost:9000"
    evalscope_timeout: int = 3600  # 1 hour timeout for benchmark tasks
    benchmark_output_dir: str = "/var/lib/tokenmachine/benchmark_outputs"

    @property
    def is_development(self) -> bool:
        """Check if running in development mode."""
        return self.environment == Environment.DEVELOPMENT

    @property
    def is_test(self) -> bool:
        """Check if running in test mode."""
        return self.environment == Environment.TEST

    @property
    def is_production(self) -> bool:
        """Check if running in production mode."""
        return self.environment == Environment.PRODUCTION

    @property
    def is_deployment(self) -> bool:
        """Check if running in deployment environment (test or production)."""
        return self.environment in (Environment.TEST, Environment.PRODUCTION)

    def get_worker_port(self, worker_index: int) -> int:
        """Get port for a specific worker."""
        return self.worker_base_port + worker_index


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


# Create directories on import
def ensure_directories(settings: Settings) -> None:
    """Ensure required directories exist."""
    import os
    os.makedirs(settings.model_storage_path, exist_ok=True)
    os.makedirs(settings.log_path, exist_ok=True)
    os.makedirs(os.path.join(settings.log_path, "workers"), exist_ok=True)
    os.makedirs(os.path.join(settings.log_path, "downloads"), exist_ok=True)
    os.makedirs(settings.modelscope_cache_dir, exist_ok=True)
