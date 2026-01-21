"""
Model Download Service - Handles ModelScope model downloads.

This service manages downloading models from ModelScope, tracking progress,
and notifying workers when models are ready.
"""
import asyncio
import json
import os
import re
import subprocess
from datetime import datetime
from typing import Optional

from loguru import logger
from sqlalchemy.orm import Session

from backend.models.database import (
    Model,
    ModelDownloadTask,
    ModelDownloadTaskStatus,
    ModelStatus,
)
from backend.core.config import get_settings


class ModelDownloadService:
    """Model download service - based on ModelScope SDK."""

    def __init__(self, db: Session):
        """
        Initialize the model download service.

        Args:
            db: Database session
        """
        self.db = db
        settings = get_settings()
        self.storage_base = settings.model_storage_path
        self.modelscope_cache = settings.modelscope_cache_dir
        self.log_path = settings.log_path

        # Ensure directories exist
        os.makedirs(self.storage_base, exist_ok=True)
        os.makedirs(self.modelscope_cache, exist_ok=True)
        os.makedirs(f"{self.log_path}/downloads", exist_ok=True)

    async def create_download_task(
        self,
        model_id: int,
        modelscope_repo_id: str,
        revision: str = "master"
    ) -> ModelDownloadTask:
        """
        Create a ModelScope model download task.

        Args:
            model_id: Database model ID
            modelscope_repo_id: ModelScope repo ID (e.g., "Qwen/qwen-72b-chat")
            revision: Branch/tag/commit (default: master)

        Returns:
            ModelDownloadTask: Download task object

        Raises:
            ValueError: If model not found or already downloaded
        """
        # 1. Validate model
        model = self.db.query(Model).filter(Model.id == model_id).first()
        if not model:
            raise ValueError(f"Model {model_id} not found")

        if model.status == ModelStatus.READY:
            raise ValueError("Model already downloaded")

        # 2. Check for existing active task
        existing_task = self.db.query(ModelDownloadTask).filter(
            ModelDownloadTask.model_id == model_id,
            ModelDownloadTask.status.in_([
                ModelDownloadTaskStatus.PENDING,
                ModelDownloadTaskStatus.DOWNLOADING
            ])
        ).first()

        if existing_task:
            logger.info(f"Active download task already exists: {existing_task.id}")
            return existing_task

        # 3. Get model info from ModelScope API
        repo_info = await self._get_modelscope_repo_info(modelscope_repo_id, revision)

        # 4. Calculate storage path (convert org/name to org--name)
        safe_name = modelscope_repo_id.replace("/", "--")
        storage_path = f"{self.storage_base}/{safe_name}"

        # 5. Create download task
        task = ModelDownloadTask(
            model_id=model_id,
            modelscope_repo_id=modelscope_repo_id,
            modelscope_revision=revision,
            status=ModelDownloadTaskStatus.PENDING,
            total_files=repo_info.get("file_count", 0),
            total_bytes=repo_info.get("total_size", 0)
        )

        self.db.add(task)
        self.db.commit()
        self.db.refresh(task)

        # 6. Update model record
        model.modelscope_repo_id = modelscope_repo_id
        model.modelscope_revision = revision
        model.storage_path = storage_path
        model.download_task_id = task.id
        model.status = ModelStatus.DOWNLOADING
        self.db.commit()

        logger.info(f"Created download task {task.id} for model {model_id}: {modelscope_repo_id}")

        # 7. Execute download asynchronously
        asyncio.create_task(self._execute_download(task.id))

        return task

    async def _get_modelscope_repo_info(
        self,
        repo_id: str,
        revision: str
    ) -> dict:
        """
        Get ModelScope repository information.

        Args:
            repo_id: ModelScope repository ID
            revision: Git revision

        Returns:
            dict with 'file_count' and 'total_size'
        """
        try:
            from modelscope.hub.api import HubApi

            api = HubApi()
            model_info = api.get_model(repo_id)

            # 计算总大小
            siblings = model_info.get('siblings', [])
            total_size = sum(
                f.get('size', 0)
                for f in siblings
                if f.get('type') == 'file'  # 只计算文件，不包括目录
            )

            file_count = len([
                f for f in siblings
                if f.get('type') == 'file'
            ])

            logger.info(f"ModelScope repo info: {repo_id} - {file_count} files, {total_size} bytes")

            return {
                "file_count": file_count,
                "total_size": total_size
            }
        except Exception as e:
            logger.warning(f"Failed to get ModelScope repo info for {repo_id}: {e}")
            # Return default values if API call fails
            return {"file_count": 0, "total_size": 0}

    async def _execute_download(self, task_id: int):
        """
        Execute download task (runs in background).

        Args:
            task_id: Download task ID
        """
        task = self.db.query(ModelDownloadTask).filter(
            ModelDownloadTask.id == task_id
        ).first()

        if not task:
            logger.error(f"Task {task_id} not found")
            return

        log_file = None

        try:
            # Update status
            task.status = ModelDownloadTaskStatus.DOWNLOADING
            task.started_at = datetime.now()
            self.db.commit()

            # Create log file
            log_dir = f"{self.log_path}/downloads"
            os.makedirs(log_dir, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            log_file = f"{log_dir}/{task.modelscope_repo_id.replace('/', '_')}_{timestamp}.log"

            # Get storage path
            storage_path = task.model.storage_path

            # Log start
            with open(log_file, "w") as log:
                log.write(f"[{datetime.now()}] Starting download: {task.modelscope_repo_id}\n")
                log.write(f"[{datetime.now()}] Storage path: {storage_path}\n")
                log.write(f"[{datetime.now()}] Revision: {task.modelscope_revision}\n")
                log.flush()

                # Import ModelScope download function
                from modelscope.hub.snapshot_download import snapshot_download

                # Custom progress callback
                class ProgressCallback:
                    def __init__(self, task_obj, log_file_obj):
                        self.task = task_obj
                        self.log = log_file_obj

                    def __call__(self, progress_info):
                        # Update progress in database
                        if 'downloaded_bytes' in progress_info:
                            self.task.downloaded_bytes = progress_info['downloaded_bytes']
                        if 'total_bytes' in progress_info:
                            self.task.total_bytes = progress_info['total_bytes']
                        if progress_info.get('total_bytes', 0) > 0:
                            progress = int(progress_info.get('downloaded_bytes', 0) / progress_info['total_bytes'] * 100)
                            self.task.progress = progress

                        self.db.commit()

                        # Log progress
                        self.log.write(f"[{datetime.now()}] Progress: {self.task.progress}%\n")
                        self.log.flush()

                # Execute download in thread pool to avoid blocking
                loop = asyncio.get_event_loop()

                try:
                    downloaded_path = await loop.run_in_executor(
                        None,
                        lambda: snapshot_download(
                            task.modelscope_repo_id,
                            revision=task.modelscope_revision,
                            cache_dir=self.modelscope_cache,
                            local_dir=storage_path
                        )
                    )

                    log.write(f"[{datetime.now()}] Download completed successfully\n")
                    log.write(f"[{datetime.now()}] Downloaded to: {downloaded_path}\n")
                    logger.info(f"Download task {task_id} completed successfully")

                    # Update task and model
                    task.status = ModelDownloadTaskStatus.COMPLETED
                    task.completed_at = datetime.now()
                    task.progress = 100

                    # Calculate actual size
                    actual_size = self._calculate_model_size(storage_path)
                    task.total_bytes = actual_size

                    # Update model status
                    model = task.model
                    model.status = ModelStatus.READY
                    model.size_gb = actual_size / (1024 ** 3)
                    model.path = storage_path
                    self.db.commit()

                    # Save download metadata
                    self._save_download_metadata(storage_path, task)

                    # Notify all workers
                    await self._notify_workers_model_ready(model.id)

                    logger.info(f"Model {model.id} is ready, workers notified")

                except Exception as download_error:
                    error_msg = str(download_error)
                    log.write(f"[{datetime.now()}] Download failed: {error_msg}\n")
                    logger.error(f"Download task {task_id} failed: {error_msg}")

                    task.status = ModelDownloadTaskStatus.FAILED
                    task.error_message = error_msg

                    # Update model status
                    model = task.model
                    model.status = ModelStatus.ERROR
                    model.error_message = f"Download failed: {error_msg[:500]}"
                    self.db.commit()

        except Exception as e:
            error_msg = str(e)
            if log_file:
                with open(log_file, "a") as log:
                    log.write(f"[{datetime.now()}] Exception: {error_msg}\n")

            logger.exception(f"Download task {task_id} raised exception")

            task.status = ModelDownloadTaskStatus.FAILED
            task.error_message = error_msg

            # Update model status
            model = task.model
            model.status = ModelStatus.ERROR
            model.error_message = error_msg
            self.db.commit()

    async def _monitor_download_progress(
        self,
        task: ModelDownloadTask,
        process: asyncio.subprocess.Process,
        log_file
    ):
        """
        Monitor download progress by parsing ModelScope output.

        Args:
            task: Download task
            process: Subprocess
            log_file: Log file object
        """
        # ModelScope output patterns
        progress_pattern = re.compile(r'Downloading:\s+(\d+)%')
        file_pattern = re.compile(r'Downloading\s+(.+)')

        while True:
            line = await process.stdout.readline()
            if not line:
                break

            line_str = line.decode().strip()

            # Write to log
            if log_file:
                log_file.write(f"{line_str}\n")
                log_file.flush()

            # Parse progress
            progress_match = progress_pattern.search(line_str)
            if progress_match:
                task.progress = int(progress_match.group(1))
                self.db.commit()

            # Parse current file
            file_match = file_pattern.search(line_str)
            if file_match:
                task.current_file = file_match.group(1)
                self.db.commit()

            # TODO: WebSocket push to frontend
            # await websocket_manager.broadcast(...)

    def _calculate_model_size(self, path: str) -> int:
        """
        Calculate model size in bytes (excluding cache files).

        Args:
            path: Model directory path

        Returns:
            int: Total size in bytes
        """
        total_size = 0
        for dirpath, dirnames, filenames in os.walk(path):
            # Exclude hidden files and cache
            dirnames[:] = [d for d in dirnames if not d.startswith(".")]

            for filename in filenames:
                if not filename.startswith("."):
                    filepath = os.path.join(dirpath, filename)
                    if os.path.exists(filepath) and os.path.isfile(filepath):
                        total_size += os.path.getsize(filepath)

        return total_size

    def _save_download_metadata(self, storage_path: str, task: ModelDownloadTask):
        """
        Save download metadata to model directory.

        Args:
            storage_path: Model storage path
            task: Download task
        """
        metadata = {
            "modelscope_repo_id": task.modelscope_repo_id,
            "revision": task.modelscope_revision,
            "downloaded_at": datetime.now().isoformat(),
            "task_id": task.id,
            "total_bytes": task.total_bytes,
            "total_files": task.total_files
        }

        metadata_file = f"{storage_path}/.download_metadata.json"
        with open(metadata_file, "w") as f:
            json.dump(metadata, f, indent=2)

        logger.info(f"Saved download metadata to {metadata_file}")

    async def _notify_workers_model_ready(self, model_id: int):
        """
        Notify all workers that a model is ready.

        Args:
            model_id: Model ID
        """
        try:
            from api.deps import redis_client

            message = json.dumps({
                "type": "model_ready",
                "model_id": model_id,
                "timestamp": datetime.now().isoformat()
            })

            await redis_client.publish("model:events", message)
            logger.info(f"Published model_ready event for model {model_id}")

        except Exception as e:
            logger.warning(f"Failed to publish model_ready event: {e}")

    async def get_download_status(self, model_id: int) -> dict:
        """
        Get download status for a model.

        Args:
            model_id: Model ID

        Returns:
            dict: Download status

        Raises:
            ValueError: If download task not found
        """
        model = self.db.query(Model).filter(Model.id == model_id).first()

        if not model or not model.download_task_id:
            raise ValueError("Download task not found")

        task = self.db.query(ModelDownloadTask).filter(
            ModelDownloadTask.id == model.download_task_id
        ).first()

        if not task:
            raise ValueError("Task not found")

        return {
            "task_id": task.id,
            "model_id": model_id,
            "status": task.status.value,
            "progress": task.progress,
            "current_file": task.current_file,
            "downloaded_files": task.downloaded_files,
            "total_files": task.total_files,
            "downloaded_bytes": task.downloaded_bytes,
            "total_bytes": task.total_bytes,
            "download_speed_mbps": float(task.download_speed_mbps) if task.download_speed_mbps else None,
            "error_message": task.error_message,
            "created_at": task.created_at.isoformat() if task.created_at else None,
            "started_at": task.started_at.isoformat() if task.started_at else None,
            "completed_at": task.completed_at.isoformat() if task.completed_at else None
        }

    def list_download_tasks(self, status: Optional[str] = None, limit: int = 100) -> list[dict]:
        """
        List download tasks.

        Args:
            status: Filter by status (optional)
            limit: Maximum number of tasks to return

        Returns:
            list of dict: Download tasks
        """
        query = self.db.query(ModelDownloadTask)

        if status:
            query = query.filter(ModelDownloadTask.status == status)

        tasks = query.order_by(ModelDownloadTask.created_at.desc()).limit(limit).all()

        return [
            {
                "task_id": task.id,
                "model_id": task.model_id,
                "model_name": task.model.name,
                "modelscope_repo_id": task.modelscope_repo_id,
                "status": task.status.value,
                "progress": task.progress,
                "created_at": task.created_at.isoformat() if task.created_at else None,
                "started_at": task.started_at.isoformat() if task.started_at else None,
                "completed_at": task.completed_at.isoformat() if task.completed_at else None
            }
            for task in tasks
        ]
