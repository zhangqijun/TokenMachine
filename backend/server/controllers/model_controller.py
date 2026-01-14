"""
Model Controller - manages model definitions.
"""
from typing import List, Optional, Dict, Any
import logging

from sqlalchemy.orm import Session
from backend.models.database import Model, ModelStatus, ModelSource, ModelCategory

logger = logging.getLogger(__name__)


class ModelController:
    """Controller for managing Model entities."""

    def __init__(self, db_session: Session):
        """Initialize ModelController.

        Args:
            db_session: SQLAlchemy database session
        """
        self.db = db_session

    def create_model(
        self,
        name: str,
        version: str,
        source: ModelSource,
        category: ModelCategory = ModelCategory.LLM,
        path: Optional[str] = None,
    ) -> Model:
        """Create a new model.

        Args:
            name: Model name (e.g., "meta-llama/Llama-3-8B-Instruct")
            version: Model version
            source: Model source (huggingface, modelscope, local)
            category: Model category (llm, embedding, etc.)
            path: Optional model path

        Returns:
            Created Model instance
        """
        model = Model(
            name=name,
            version=version,
            source=source,
            category=category,
            path=path,
            status=ModelStatus.DOWNLOADING,
        )

        self.db.add(model)
        self.db.commit()
        self.db.refresh(model)

        logger.info(f"Created model: {model.id} - {name} v{version}")
        return model

    def get_model(self, model_id: int) -> Optional[Model]:
        """Get a model by ID.

        Args:
            model_id: Model ID

        Returns:
            Model instance or None if not found
        """
        return self.db.query(Model).filter(Model.id == model_id).first()

    def get_model_by_name_version(self, name: str, version: str) -> Optional[Model]:
        """Get a model by name and version.

        Args:
            name: Model name
            version: Model version

        Returns:
            Model instance or None if not found
        """
        return self.db.query(Model).filter(
            Model.name == name,
            Model.version == version
        ).first()

    def list_models(
        self,
        source: Optional[ModelSource] = None,
        category: Optional[ModelCategory] = None,
        status: Optional[ModelStatus] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Model]:
        """List models with optional filters.

        Args:
            source: Optional model source filter
            category: Optional category filter
            status: Optional status filter
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            List of Model instances
        """
        query = self.db.query(Model)

        if source is not None:
            query = query.filter(Model.source == source)

        if category is not None:
            query = query.filter(Model.category == category)

        if status is not None:
            query = query.filter(Model.status == status)

        return query.order_by(Model.created_at.desc()).limit(limit).offset(offset).all()

    def update_model_status(
        self,
        model_id: int,
        status: ModelStatus,
        path: Optional[str] = None,
        size_gb: Optional[float] = None,
        error_message: Optional[str] = None,
    ) -> Optional[Model]:
        """Update model status.

        Args:
            model_id: Model ID
            status: New status
            path: Optional model path
            size_gb: Optional model size in GB
            error_message: Optional error message if status is ERROR

        Returns:
            Updated Model instance or None if not found
        """
        model = self.get_model(model_id)
        if not model:
            return None

        model.status = status
        if path is not None:
            model.path = path
        if size_gb is not None:
            model.size_gb = size_gb
        if error_message is not None:
            model.error_message = error_message

        self.db.commit()
        self.db.refresh(model)

        logger.info(f"Updated model {model_id} status to {status}")
        return model

    def update_download_progress(self, model_id: int, progress: int) -> Optional[Model]:
        """Update model download progress.

        Args:
            model_id: Model ID
            progress: Download progress (0-100)

        Returns:
            Updated Model instance or None if not found
        """
        model = self.get_model(model_id)
        if not model:
            return None

        model.download_progress = max(0, min(100, progress))
        self.db.commit()
        self.db.refresh(model)

        return model

    def delete_model(self, model_id: int) -> bool:
        """Delete a model.

        Args:
            model_id: Model ID

        Returns:
            True if deleted, False if not found
        """
        model = self.get_model(model_id)
        if not model:
            return False

        self.db.delete(model)
        self.db.commit()

        logger.info(f"Deleted model: {model_id}")
        return True

    def get_ready_models(self) -> List[Model]:
        """Get all models that are ready for deployment.

        Returns:
            List of ready Model instances
        """
        return self.db.query(Model).filter(Model.status == ModelStatus.READY).all()
