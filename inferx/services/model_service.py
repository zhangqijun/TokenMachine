"""
Model service for managing AI models.
"""
import os
import subprocess
import asyncio
import threading
from typing import Optional, List
from pathlib import Path
from loguru import logger
from sqlalchemy.orm import Session

from inferx.models.database import Model, ModelStatus, ModelSource, ModelCategory
from inferx.core.config import get_settings
from inferx.core.gpu import get_gpu_manager

settings = get_settings()


class ModelService:
    """Service for model management operations."""

    def __init__(self, db: Session):
        """Initialize model service."""
        self.db = db
        self.gpu_manager = get_gpu_manager()
        self._active_downloads: dict = {}

    def create_model(
        self,
        name: str,
        version: str,
        source: ModelSource,
        category: ModelCategory = ModelCategory.LLM,
        huggingface_token: Optional[str] = None
    ) -> Model:
        """
        Create a new model record and start downloading.

        Args:
            name: Model name (e.g., "meta-llama/Llama-3-8B-Instruct")
            version: Model version
            source: Model source (huggingface, modelscope, local)
            category: Model category
            huggingface_token: Optional HuggingFace token for gated models

        Returns:
            Created Model instance
        """
        # Check if model already exists
        existing = self.db.query(Model).filter(
            Model.name == name,
            Model.version == version
        ).first()
        if existing:
            raise ValueError(f"Model {name}:{version} already exists")

        # Create model record
        model = Model(
            name=name,
            version=version,
            source=source,
            category=category,
            status=ModelStatus.DOWNLOADING,
            download_progress=0
        )
        self.db.add(model)
        self.db.commit()
        self.db.refresh(model)

        # Start async download
        self._start_download(model.id, name, source, huggingface_token)

        logger.info(f"Created model {name}:{version} with ID {model.id}")
        return model

    def _start_download(
        self,
        model_id: int,
        name: str,
        source: ModelSource,
        token: Optional[str] = None
    ):
        """Start model download in background thread."""
        if model_id in self._active_downloads:
            logger.warning(f"Download already active for model {model_id}")
            return

        def download_worker():
            try:
                self._download_model(model_id, name, source, token)
            except Exception as e:
                logger.error(f"Download worker error for model {model_id}: {e}")
            finally:
                self._active_downloads.pop(model_id, None)

        self._active_downloads[model_id] = True
        thread = threading.Thread(target=download_worker, daemon=True)
        thread.start()

    def _download_model(
        self,
        model_id: int,
        name: str,
        source: ModelSource,
        token: Optional[str] = None
    ):
        """Download model from source."""
        logger.info(f"Starting download for model {name} from {source}")

        # Generate storage path
        safe_name = name.replace("/", "--")
        storage_path = os.path.join(settings.model_storage_path, safe_name)

        try:
            if source == ModelSource.HUGGINGFACE:
                self._download_from_huggingface(name, storage_path, token)
            elif source == ModelSource.MODELSCOPE:
                self._download_from_modelscope(name, storage_path)
            elif source == ModelSource.LOCAL:
                # For local models, just verify the path exists
                if not os.path.exists(name):
                    raise ValueError(f"Local model path does not exist: {name}")
                storage_path = name
            else:
                raise ValueError(f"Unsupported source: {source}")

            # Calculate model size
            size_gb = self._calculate_model_size(storage_path)

            # Update model status
            model = self.db.query(Model).filter(Model.id == model_id).first()
            if model:
                model.status = ModelStatus.READY
                model.path = storage_path
                model.size_gb = size_gb
                model.download_progress = 100
                self.db.commit()

            logger.info(f"Successfully downloaded model {name} to {storage_path}")

        except Exception as e:
            logger.error(f"Failed to download model {name}: {e}")
            model = self.db.query(Model).filter(Model.id == model_id).first()
            if model:
                model.status = ModelStatus.ERROR
                model.error_message = str(e)
                self.db.commit()

    def _download_from_huggingface(
        self,
        model_name: str,
        storage_path: str,
        token: Optional[str] = None
    ):
        """Download model from HuggingFace."""
        cmd = [
            "huggingface-cli", "download",
            model_name,
            "--local-dir", storage_path,
            "--local-dir-use-symlinks", "False"
        ]
        if token:
            cmd.extend(["--token", token])

        logger.info(f"Running HuggingFace download: {' '.join(cmd)}")

        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        # Wait for completion
        stdout, stderr = process.communicate()

        if process.returncode != 0:
            raise Exception(f"HuggingFace download failed: {stderr}")

        logger.debug(f"HuggingFace download output: {stdout}")

    def _download_from_modelscope(self, model_name: str, storage_path: str):
        """Download model from ModelScope."""
        cmd = [
            "modelscope", "download",
            "--model", model_name,
            "--local_dir", storage_path
        ]

        logger.info(f"Running ModelScope download: {' '.join(cmd)}")

        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        stdout, stderr = process.communicate()

        if process.returncode != 0:
            raise Exception(f"ModelScope download failed: {stderr}")

    def _calculate_model_size(self, path: str) -> float:
        """Calculate model size in GB."""
        total_size = 0
        for dirpath, dirnames, filenames in os.walk(path):
            for filename in filenames:
                filepath = os.path.join(dirpath, filename)
                if os.path.exists(filepath) and not os.path.islink(filepath):
                    total_size += os.path.getsize(filepath)
        return round(total_size / (1024**3), 2)

    def get_model(self, model_id: int) -> Optional[Model]:
        """Get a model by ID."""
        return self.db.query(Model).filter(Model.id == model_id).first()

    def get_model_by_name_version(self, name: str, version: str) -> Optional[Model]:
        """Get a model by name and version."""
        return self.db.query(Model).filter(
            Model.name == name,
            Model.version == version
        ).first()

    def list_models(
        self,
        category: Optional[ModelCategory] = None,
        status: Optional[ModelStatus] = None
    ) -> List[Model]:
        """List all models with optional filters."""
        query = self.db.query(Model)
        if category:
            query = query.filter(Model.category == category)
        if status:
            query = query.filter(Model.status == status)
        return query.order_by(Model.created_at.desc()).all()

    def update_model_status(
        self,
        model_id: int,
        status: ModelStatus,
        error_message: Optional[str] = None
    ) -> Optional[Model]:
        """Update model status."""
        model = self.get_model(model_id)
        if model:
            model.status = status
            if error_message:
                model.error_message = error_message
            self.db.commit()
            self.db.refresh(model)
        return model

    def delete_model(self, model_id: int) -> bool:
        """Delete a model."""
        model = self.get_model(model_id)
        if not model:
            return False

        # Check if model is in use
        from inferx.models.database import Deployment, DeploymentStatus
        active_deployments = self.db.query(Deployment).filter(
            Deployment.model_id == model_id,
            Deployment.status.in_([DeploymentStatus.RUNNING, DeploymentStatus.STARTING])
        ).count()
        if active_deployments > 0:
            raise ValueError(f"Cannot delete model with {active_deployments} active deployments")

        # Delete model files
        if model.path and os.path.exists(model.path):
            import shutil
            shutil.rmtree(model.path)
            logger.info(f"Deleted model files at {model.path}")

        # Delete database record
        self.db.delete(model)
        self.db.commit()
        return True

    def estimate_gpu_memory(self, model: Model) -> int:
        """
        Estimate GPU memory requirement for a model.

        Args:
            model: Model instance

        Returns:
            Estimated memory in MB
        """
        # Rough estimation based on parameter count
        # This is a simplified calculation - actual usage varies
        name_lower = model.name.lower()

        # Common model sizes (in GB)
        if any(x in name_lower for x in ["7b", "8b"]):
            return 16 * 1024  # 16 GB
        elif any(x in name_lower for x in ["13b", "14b"]):
            return 24 * 1024  # 24 GB
        elif any(x in name_lower for x in ["32b", "34b"]):
            return 48 * 1024  # 48 GB
        elif any(x in name_lower for x in ["70b", "72b"]):
            return 140 * 1024  # 140 GB
        else:
            # Default to 16 GB
            return 16 * 1024
