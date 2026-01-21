"""
Backend Engine Service - handles inference engine management business logic.

This service manages the lifecycle of backend inference engines (vLLM, SGLang, llama.cpp),
including installation, version management, and status tracking.
"""
import os
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


# Engine metadata (hardcoded for now, can be moved to config file later)
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
    "sglang": {
        "display_name": "SGLang",
        "icon": "⚡",
        "description": "高吞吐量推理引擎，优化结构化生成",
        "homepage": "https://github.com/sgl-project/sglang",
        "features": {
            "tensor_parallel": True,
            "prefix_caching": True,
            "multi_lora": False,
            "speculative_decoding": True,
            "quantization": ["fp16", "int8"],
            "model_formats": ["hf", "safetensors"]
        },
        "compatibility": {
            "gpu_vendors": ["nvidia"],
            "min_gpu_memory_mb": 16384,
            "supported_models": ["llama", "mistral", "qwen"]
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
                "config": engine.config,
                "env_vars": engine.env_vars,
                "stats": {
                    "active_deployments": engine.active_deployments,
                    "total_requests": 0,  # Can be fetched from deployment stats later
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
        Install an engine version.

        This creates a fake tarball file and marks the engine as installed.
        In production, this would trigger actual Docker image download/save.

        Args:
            db: Database session
            engine_type: Type of engine to install
            request: Installation request parameters

        Returns:
            Created or updated BackendEngine instance

        Raises:
            ValueError: If engine is already installed or currently being installed
        """
        # Check if already installed
        existing = db.query(BackendEngine).filter(
            BackendEngine.engine_type == engine_type,
            BackendEngine.version == request.version
        ).first()

        if existing:
            if existing.status == BackendEngineStatus.INSTALLED:
                raise ValueError(
                    f"{engine_type.value} {request.version} is already installed"
                )
            elif existing.status == BackendEngineStatus.INSTALLING:
                raise ValueError(
                    f"{engine_type.value} {request.version} is currently being installed"
                )

        # Set default image name if not provided
        image_name = request.image_name
        if not image_name:
            if engine_type == BackendEngineType.VLLM:
                image_name = f"vllm/vllm-openai:{request.version}"
            elif engine_type == BackendEngineType.SGLANG:
                image_name = f"lmsysorg/sglang:{request.version}"
            elif engine_type == BackendEngineType.LLAMA_CPP:
                image_name = f"llama-cpp-python:{request.version}"

        # Create or update engine record
        if existing:
            engine = existing
        else:
            engine = BackendEngine(
                engine_type=engine_type,
                version=request.version,
                status=BackendEngineStatus.INSTALLING,
            )

        engine.install_path = request.install_path
        engine.image_name = image_name
        engine.config = request.config or {}
        engine.env_vars = request.env_vars or {}

        db.add(engine)
        db.commit()
        db.refresh(engine)

        # Execute fake installation (create fake tarball)
        try:
            tarball_path = BackendEngineService._create_fake_tarball(engine)
            engine.tarball_path = tarball_path
            engine.size_mb = 1024  # Fake size: 1GB
            engine.status = BackendEngineStatus.INSTALLED
            engine.installed_at = datetime.utcnow()
            logger.info(f"Successfully installed {engine_type.value} {request.version}")
        except Exception as e:
            engine.status = BackendEngineStatus.ERROR
            logger.error(f"Failed to install {engine_type.value} {request.version}: {e}")
            db.commit()
            raise

        db.commit()
        db.refresh(engine)

        return engine

    @staticmethod
    def _create_fake_tarball(engine: BackendEngine) -> str:
        """
        Create a fake tarball file for the engine.

        In production, this would:
        1. Pull Docker image
        2. Save image to tarball using `docker save`
        3. Store in configured path

        For now, we create a small fake file.

        Args:
            engine: BackendEngine instance

        Returns:
            Path to the tarball file
        """
        # Create storage directory if it doesn't exist
        storage_dir = "/tmp/tokenmachine/engines"
        os.makedirs(storage_dir, exist_ok=True)

        # Create fake tarball path
        tarball_filename = f"{engine.engine_type.value}-{engine.version}.tar"
        tarball_path = os.path.join(storage_dir, tarball_filename)

        # Write fake data to file
        with open(tarball_path, 'w') as f:
            f.write(f"Fake tarball for {engine.engine_type.value} {engine.version}\n")
            f.write(f"This is a placeholder for the actual Docker image tarball.\n")
            f.write(f"Image: {engine.image_name}\n")

        logger.info(f"Created fake tarball at {tarball_path}")
        return tarball_path

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

        # Delete tarball file if it exists
        if engine.tarball_path and os.path.exists(engine.tarball_path):
            try:
                os.remove(engine.tarball_path)
                logger.info(f"Deleted tarball at {engine.tarball_path}")
            except Exception as e:
                logger.warning(f"Failed to delete tarball file: {e}")

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
            "install_path": engine.install_path,
            "image_name": engine.image_name,
            "tarball_path": engine.tarball_path,
        }
