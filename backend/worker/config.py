"""
Worker configuration management.
"""
from typing import Optional, Dict, Any
from pydantic_settings import BaseSettings


class WorkerSettings(BaseSettings):
    """Worker settings."""

    # Worker identification
    worker_name: Optional[str] = None

    # API server
    api_port: int = 8001

    # Server connection
    server_url: str = "http://localhost:8000"
    heartbeat_interval: int = 30

    # Model serving
    model_storage_path: str = "/var/lib/tokenmachine/models"

    # Monitoring
    metric_export_interval: int = 15

    class Config:
        env_prefix = "WORKER_"
        env_file = ".env"


def get_worker_config() -> Dict[str, Any]:
    """Get worker configuration as a dictionary.

    Returns:
        Dictionary containing worker configuration
    """
    settings = WorkerSettings()
    return settings.model_dump()
