"""
Configuration management for InferX.
"""
import os
from typing import Optional
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    # Application
    app_name: str = "InferX"
    app_version: str = "0.1.0"
    environment: str = "development"
    debug: bool = True

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_reload: bool = False

    # Database
    database_url: str = "postgresql://inferx:inferx_password@localhost:5432/inferx"
    database_pool_size: int = 10
    database_max_overflow: int = 20

    # Redis
    redis_url: str = "redis://localhost:6379/0"
    redis_pool_size: int = 10

    # Security
    secret_key: str = "your-secret-key-change-this-in-production"
    api_key_prefix: str = "inferx_sk_"
    api_key_length: int = 32
    access_token_expire_minutes: int = 60 * 24 * 7  # 7 days

    # Storage
    model_storage_path: str = "/var/lib/inferx/models"
    log_path: str = "/var/log/inferx"

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

    @property
    def is_development(self) -> bool:
        """Check if running in development mode."""
        return self.environment == "development"

    @property
    def is_production(self) -> bool:
        """Check if running in production mode."""
        return self.environment == "production"

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
