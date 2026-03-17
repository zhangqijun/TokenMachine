"""
Backend Engine Service - handles inference engine management business logic.

This service manages the lifecycle of backend inference engines (vLLM, MindIE, llama.cpp),
including installation, version management, and status tracking.
"""
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session

from backend.models.database import (
    BackendEngine,
    BackendEngineType,
    BackendEngineStatus,
)
from backend.models.schemas import BackendEngineInstallRequest

logger = logging.getLogger(__name__)


# Engine metadata
ENGINE_METADATA = {
    "vllm": {
        "display_name": "vLLM",
        "icon": "🚀",
        "description": "高性能推理引擎，支持 PagedAttention 和连续批处理",
        "homepage": "https://github.com/vllm-project/vllm",
        "features": {
            "tensor_parallel": True,
            "prefix_caching": True,
            "multi_lora": True,
            "speculative_decoding": True,
            "quantization": ["fp16", "int8", "fp4", "fp8"],
            "model_formats": ["hf", "safetensors"]
        },
        "compatibility": {
            "gpu_vendors": ["nvidia"],
            "min_gpu_memory_mb": 16384,
            "supported_models": ["llama", "mistral", "qwen", "baichuan"]
        }
    },
    "mindie": {
        "display_name": "MindIE",
        "icon": "🧠",
        "description": "华为昇腾推理引擎，适配华为昇腾系列芯片",
        "homepage": "https://www.huawei.com/",
        "features": {
            "tensor_parallel": True,
            "ascend_npu": True,
            "quantization": ["fp16", "int8"]
        },
        "compatibility": {
            "gpu_vendors": ["ascend"],
            "min_gpu_memory_mb": 16384,
            "supported_models": ["llama", "qwen", "baichuan"]
        }
    },
    "llama_cpp": {
        "display_name": "llama.cpp",
        "icon": "🗄️",
        "description": "轻量级推理引擎，支持 CPU 和 Apple Silicon",
        "homepage": "https://github.com/ggerganov/llama.cpp",
        "features": {
            "tensor_parallel": False,
            "prefix_caching": False,
            "multi_lora": False,
            "speculative_decoding": True,
            "quantization": ["q4_0", "q4_k", "q5_0", "q6_k", "q8_0", "gguf"],
            "model_formats": ["gguf"]
        },
        "compatibility": {
            "gpu_vendors": ["nvidia", "amd", "apple"],
            "min_gpu_memory_mb": 4096,
            "supported_models": ["llama", "mistral", "qwen", "baichuan"]
        }
    }
}

# Default registry URL
DEFAULT_REGISTRY = "registry.tokenmachine.ai"


class BackendEngineService:
    """Backend engine service."""

    @staticmethod
    def list_engines(
        db: Session,
        engine_type: Optional[BackendEngineType] = None
    ) -> List[Dict[str, Any]]:
        """
        List all engines with their versions.

        Args:
            db: Database session
            engine_type: Optional filter by engine type

        Returns:
            List of engine information dictionaries
        """
        query = db.query(BackendEngine)
        if engine_type:
            query = query.filter(BackendEngine.engine_type == engine_type)

        engines = query.all()

        # Convert to frontend-expected format
        result = []
        for engine in engines:
            metadata = ENGINE_METADATA.get(engine.engine_type.value, {})
            result.append({
                "id": engine.id,
                "name": engine.engine_type.value,
                "display_name": metadata.get("display_name", ""),
                "version": engine.version,
                "status": engine.status.value,
                "icon": metadata.get("icon", ""),
                "description": metadata.get("description", ""),
                "homepage": metadata.get("homepage", ""),
                "features": metadata.get("features", {}),
                "compatibility": metadata.get("compatibility", {}),
                "registry_url": engine.registry_url,
                "image_name": engine.image_name,
                "config": engine.config,
                "env_vars": engine.env_vars,
                "stats": {
                    "active_deployments": engine.active_deployments,
                    "size_mb": engine.size_mb,
                }
            })

        return result

    @staticmethod
    def install_engine(
        db: Session,
        engine_type: BackendEngineType,
        request: BackendEngineInstallRequest
    ) -> BackendEngine:
        """
        Install an engine version from private registry.

        Args:
            db: Database session
            engine_type: Type of engine to install
            request: Installation request parameters

        Returns:
            Created or updated BackendEngine instance

        Raises:
            ValueError: If engine is already installed
        """
        # Check if already installed
        existing = db.query(BackendEngine).filter(
            BackendEngine.engine_type == engine_type,
            BackendEngine.version == request.version
        ).first()

        if existing and existing.status == BackendEngineStatus.INSTALLED:
            raise ValueError(
                f"{engine_type.value} {request.version} is already installed"
            )

        # Set default image name if not provided
        image_name = request.image_name
        registry_url = request.registry_url or DEFAULT_REGISTRY

        if not image_name:
            if engine_type == BackendEngineType.VLLM:
                image_name = f"{registry_url}/vllm/vllm-openai:{request.version}"
            elif engine_type == BackendEngineType.MINDIE:
                image_name = f"{registry_url}/mindie/mindie-serving:{request.version}"
            elif engine_type == BackendEngineType.LLAMA_CPP:
                image_name = f"{registry_url}/llamacpp/llama-cpp-python:{request.version}"

        # Create or update engine record
        if existing:
            engine = existing
        else:
            engine = BackendEngine(
                engine_type=engine_type,
                version=request.version,
                status=BackendEngineStatus.NOT_INSTALLED,
            )

        engine.registry_url = registry_url
        engine.image_name = image_name
        engine.config = request.config or {}
        engine.env_vars = request.env_vars or {}

        db.add(engine)
        db.commit()
        db.refresh(engine)

        # TODO: Implement actual Docker pull from private registry
        # For now, mark as installed directly
        engine.status = BackendEngineStatus.INSTALLED
        engine.size_mb = 2048  # Placeholder size
        engine.installed_at = datetime.utcnow()
        logger.info(f"Successfully installed {engine_type.value} {request.version}")

        db.commit()
        db.refresh(engine)

        return engine

    @staticmethod
    def delete_engine(
        db: Session,
        engine_type: BackendEngineType,
        version: str
    ) -> bool:
        """
        Delete an engine version.

        Args:
            db: Database session
            engine_type: Type of engine to delete
            version: Version string

        Returns:
            True if deleted successfully

        Raises:
            ValueError: If engine not found or has active deployments
        """
        engine = db.query(BackendEngine).filter(
            BackendEngine.engine_type == engine_type,
            BackendEngine.version == version
        ).first()

        if not engine:
            raise ValueError(f"{engine_type.value} {version} not found")

        if engine.active_deployments > 0:
            raise ValueError(
                f"Cannot delete engine with {engine.active_deployments} active deployments"
            )

        # TODO: Implement actual Docker image removal
        db.delete(engine)
        db.commit()
        logger.info(f"Deleted {engine_type.value} {version}")

        return True

    @staticmethod
    def get_engine_stats(
        db: Session,
        engine_type: BackendEngineType,
        version: str
    ) -> Dict[str, Any]:
        """
        Get engine statistics.

        Args:
            db: Database session
            engine_type: Type of engine
            version: Version string

        Returns:
            Dictionary containing engine statistics

        Raises:
            ValueError: If engine not found
        """
        engine = db.query(BackendEngine).filter(
            BackendEngine.engine_type == engine_type,
            BackendEngine.version == version
        ).first()

        if not engine:
            raise ValueError(f"{engine_type.value} {version} not found")

        return {
            "engine_type": engine.engine_type.value,
            "version": engine.version,
            "status": engine.status.value,
            "active_deployments": engine.active_deployments,
            "size_mb": engine.size_mb,
            "installed_at": engine.installed_at.isoformat() if engine.installed_at else None,
            "registry_url": engine.registry_url,
            "image_name": engine.image_name,
        }
