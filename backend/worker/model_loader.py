"""
Worker Model Loader - Handles model loading on worker nodes.

This service manages model path resolution, cache tracking, and validation
for worker nodes loading models from NFS shared storage.
"""
import os
from datetime import datetime
from typing import Optional, List

from loguru import logger
from sqlalchemy.orm import Session

from backend.models.database import (
    Model,
    ModelStatus,
    Worker,
    WorkerModelCache,
    WorkerCacheSyncStatus,
)
from backend.core.config import settings


class WorkerModelLoader:
    """Worker model loader - handles model loading from NFS storage."""

    def __init__(self, worker_id: int, db: Session):
        """
        Initialize the worker model loader.

        Args:
            worker_id: Worker ID
            db: Database session
        """
        self.worker_id = worker_id
        self.db = db
        self.nfs_mount_point = settings.NFS_MOUNT_POINT

    def get_model_path(self, model_id: int) -> Optional[str]:
        """
        Get model loading path for this worker.

        Process:
        1. Query database for model storage_path
        2. Map to NFS mount point
        3. Verify file exists
        4. Update cache record

        Args:
            model_id: Model ID

        Returns:
            str: NFS path to model, or None if unavailable
        """
        # 1. Query model
        model = self.db.query(Model).filter(Model.id == model_id).first()
        if not model:
            logger.warning(f"Model {model_id} not found")
            return None

        # 2. Check model status
        if model.status != ModelStatus.READY:
            logger.warning(f"Model {model_id} is not ready (status: {model.status})")
            return None

        # 3. Get storage path
        storage_path = model.storage_path
        if not storage_path:
            logger.warning(f"Model {model_id} has no storage_path")
            return None

        # 4. Map to NFS mount point
        # Server: /var/lib/tokenmachine/models/Qwen--qwen-72b-chat
        # Worker: /mnt/models/Qwen--qwen-72b-chat
        nfs_path = storage_path.replace(
            "/var/lib/tokenmachine/models",
            self.nfs_mount_point
        )

        # 5. Verify path exists
        if not os.path.exists(nfs_path):
            logger.warning(f"Model path does not exist: {nfs_path}")
            return None

        # 6. Verify required files exist
        required_files = ["config.json"]
        for filename in required_files:
            filepath = os.path.join(nfs_path, filename)
            if not os.path.exists(filepath):
                logger.warning(f"Required file missing: {filepath}")
                return None

        logger.info(f"Model {model_id} available at {nfs_path}")

        # 7. Update cache record
        self._update_cache(model_id, nfs_path)

        return nfs_path

    def _update_cache(self, model_id: int, cache_path: str):
        """
        Update worker cache record for a model.

        Args:
            model_id: Model ID
            cache_path: Cache path (NFS path)
        """
        cache = self.db.query(WorkerModelCache).filter(
            WorkerModelCache.worker_id == self.worker_id,
            WorkerModelCache.model_id == model_id
        ).first()

        if not cache:
            # Create new cache record
            cache = WorkerModelCache(
                worker_id=self.worker_id,
                model_id=model_id,
                is_cached=True,
                cache_path=cache_path,
                sync_status=WorkerCacheSyncStatus.SYNCED
            )
            self.db.add(cache)
            logger.info(f"Created cache record for worker {self.worker_id}, model {model_id}")
        else:
            # Update existing record
            cache.is_cached = True
            cache.cache_path = cache_path
            cache.sync_status = WorkerCacheSyncStatus.SYNCED

        cache.last_loaded_at = datetime.now()
        cache.load_count += 1
        cache.last_synced_at = datetime.now()
        self.db.commit()

    def sync_model_cache(self) -> int:
        """
        Sync model cache (check which models are available).

        Updates cache records for all ready models based on NFS availability.

        Returns:
            int: Number of cached models
        """
        # Get all ready models
        ready_models = self.db.query(Model).filter(
            Model.status == ModelStatus.READY
        ).all()

        cached_count = 0

        for model in ready_models:
            # Map to NFS path
            if not model.storage_path:
                continue

            nfs_path = model.storage_path.replace(
                "/var/lib/tokenmachine/models",
                self.nfs_mount_point
            )

            is_available = os.path.exists(nfs_path)

            # Update or create cache record
            cache = self.db.query(WorkerModelCache).filter(
                WorkerModelCache.worker_id == self.worker_id,
                WorkerModelCache.model_id == model.id
            ).first()

            if not cache:
                cache = WorkerModelCache(
                    worker_id=self.worker_id,
                    model_id=model.id,
                    is_cached=is_available,
                    cache_path=nfs_path if is_available else None,
                    sync_status=WorkerCacheSyncStatus.SYNCED if is_available else WorkerCacheSyncStatus.OUTDATED
                )
                self.db.add(cache)
            else:
                cache.is_cached = is_available
                cache.cache_path = nfs_path if is_available else None
                cache.sync_status = WorkerCacheSyncStatus.SYNCED if is_available else WorkerCacheSyncStatus.OUTDATED

            if is_available:
                cached_count += 1

        self.db.commit()
        logger.info(f"Worker {self.worker_id} cache sync complete: {cached_count} models cached")

        return cached_count

    def list_cached_models(self) -> List[dict]:
        """
        List all cached models for this worker.

        Returns:
            list of dict: Cached models
        """
        caches = self.db.query(WorkerModelCache).filter(
            WorkerModelCache.worker_id == self.worker_id,
            WorkerModelCache.is_cached == True
        ).all()

        return [
            {
                "model_id": c.model_id,
                "model_name": c.model.name,
                "cache_path": c.cache_path,
                "last_loaded_at": c.last_loaded_at.isoformat() if c.last_loaded_at else None,
                "load_count": c.load_count,
                "sync_status": c.sync_status.value
            }
            for c in caches
        ]

    def invalidate_cache(self, model_id: int):
        """
        Invalidate cache for a specific model.

        Args:
            model_id: Model ID
        """
        cache = self.db.query(WorkerModelCache).filter(
            WorkerModelCache.worker_id == self.worker_id,
            WorkerModelCache.model_id == model_id
        ).first()

        if cache:
            cache.is_cached = False
            cache.sync_status = WorkerCacheSyncStatus.OUTDATED
            self.db.commit()
            logger.info(f"Invalidated cache for worker {self.worker_id}, model {model_id}")

    def validate_model(self, model_id: int) -> bool:
        """
        Validate that a model is properly cached and accessible.

        Args:
            model_id: Model ID

        Returns:
            bool: True if model is valid
        """
        cache = self.db.query(WorkerModelCache).filter(
            WorkerModelCache.worker_id == self.worker_id,
            WorkerModelCache.model_id == model_id,
            WorkerModelCache.is_cached == True
        ).first()

        if not cache:
            return False

        # Verify file still exists
        if cache.cache_path and os.path.exists(cache.cache_path):
            return True

        # File no longer exists, invalidate cache
        self.invalidate_cache(model_id)
        return False

    def get_cache_stats(self) -> dict:
        """
        Get cache statistics for this worker.

        Returns:
            dict: Cache statistics
        """
        all_caches = self.db.query(WorkerModelCache).filter(
            WorkerModelCache.worker_id == self.worker_id
        ).all()

        cached = self.db.query(WorkerModelCache).filter(
            WorkerModelCache.worker_id == self.worker_id,
            WorkerModelCache.is_cached == True
        ).all()

        total_size_gb = sum(
            float(c.cache_size_gb) for c in cached if c.cache_size_gb
        )

        return {
            "worker_id": self.worker_id,
            "total_models": len(all_caches),
            "cached_models": len(cached),
            "total_size_gb": round(total_size_gb, 2),
            "most_loaded_model_id": max(cached, key=lambda c: c.load_count).model_id if cached else None
        }
