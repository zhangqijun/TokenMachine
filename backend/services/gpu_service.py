"""
GPU service for GPU resource management.
"""
from typing import List, Optional, Dict, Any
from datetime import datetime
from loguru import logger
from sqlalchemy.orm import Session

from backend.models.database import GPU, GPUStatus, Deployment
from backend.core.gpu import get_gpu_manager
from backend.models.schemas import GPUInfo, GPUsResponse


class GPUService:
    """Service for GPU management operations."""

    def __init__(self, db: Session):
        """Initialize GPU service."""
        self.db = db
        self.gpu_manager = get_gpu_manager()

    def refresh_gpu_status(self) -> List[GPU]:
        """
        Refresh GPU status from hardware and update database.

        Returns:
            List of updated GPU records
        """
        if not self.gpu_manager.is_available():
            logger.warning("GPU manager not available, skipping refresh")
            return []

        gpu_infos = self.gpu_manager.get_all_gpus()
        updated_gpus = []

        for gpu_info in gpu_infos:
            gpu = self.db.query(GPU).filter(GPU.gpu_id == gpu_info["id"]).first()

            if gpu:
                # Update existing GPU record
                gpu.name = gpu_info["name"]
                gpu.memory_total_mb = gpu_info["memory_total_mb"]
                gpu.memory_free_mb = gpu_info["memory_free_mb"]
                gpu.utilization_percent = gpu_info["utilization_percent"]
                gpu.temperature_celsius = gpu_info["temperature_celsius"]
                gpu.updated_at = datetime.now()
            else:
                # Create new GPU record
                gpu = GPU(
                    gpu_id=gpu_info["id"],
                    name=gpu_info["name"],
                    memory_total_mb=gpu_info["memory_total_mb"],
                    memory_free_mb=gpu_info["memory_free_mb"],
                    utilization_percent=gpu_info["utilization_percent"],
                    temperature_celsius=gpu_info["temperature_celsius"],
                    status=GPUStatus.AVAILABLE
                )
                self.db.add(gpu)

            updated_gpus.append(gpu)

        self.db.commit()
        logger.info(f"Refreshed {len(updated_gpus)} GPUs")
        return updated_gpus

    def get_all_gpus(self) -> List[GPU]:
        """Get all GPU records from database."""
        return self.db.query(GPU).order_by(GPU.id).all()

    def get_gpu(self, gpu_id: str) -> Optional[GPU]:
        """Get a GPU by its GPU ID (e.g., 'gpu:0')."""
        return self.db.query(GPU).filter(GPU.gpu_id == gpu_id).first()

    def get_available_gpus(self) -> List[GPU]:
        """Get all available GPUs."""
        return self.db.query(GPU).filter(GPU.status == GPUStatus.AVAILABLE).all()

    def allocate_gpus(
        self,
        gpu_ids: List[str],
        deployment_id: int
    ) -> bool:
        """
        Allocate GPUs to a deployment.

        Args:
            gpu_ids: List of GPU IDs to allocate
            deployment_id: Deployment ID to allocate GPUs to

        Returns:
            True if successful, False otherwise
        """
        # Check if all GPUs are available
        for gpu_id in gpu_ids:
            gpu = self.get_gpu(gpu_id)
            if not gpu:
                logger.error(f"GPU {gpu_id} not found in database")
                return False
            if gpu.status != GPUStatus.AVAILABLE:
                logger.error(f"GPU {gpu_id} is not available (status: {gpu.status})")
                return False

        # Allocate GPUs
        for gpu_id in gpu_ids:
            gpu = self.get_gpu(gpu_id)
            gpu.status = GPUStatus.IN_USE
            gpu.deployment_id = deployment_id

        self.db.commit()
        logger.info(f"Allocated GPUs {gpu_ids} to deployment {deployment_id}")
        return True

    def release_gpus(self, deployment_id: int) -> int:
        """
        Release all GPUs allocated to a deployment.

        Args:
            deployment_id: Deployment ID

        Returns:
            Number of GPUs released
        """
        gpus = self.db.query(GPU).filter(
            GPU.deployment_id == deployment_id
        ).all()

        count = 0
        for gpu in gpus:
            gpu.status = GPUStatus.AVAILABLE
            gpu.deployment_id = None
            count += 1

        self.db.commit()
        logger.info(f"Released {count} GPUs from deployment {deployment_id}")
        return count

    def get_gpu_stats(self) -> GPUsResponse:
        """
        Get GPU statistics.

        Returns:
            GPUsResponse containing GPU information
        """
        # First refresh from hardware
        self.refresh_gpu_status()

        gpus = self.get_all_gpus()
        gpu_infos = []

        for gpu in gpus:
            gpu_infos.append(GPUInfo(
                id=gpu.gpu_id,
                name=gpu.name,
                memory_total_mb=gpu.memory_total_mb or 0,
                memory_free_mb=gpu.memory_free_mb or 0,
                memory_used_mb=(gpu.memory_total_mb or 0) - (gpu.memory_free_mb or 0),
                utilization_percent=float(gpu.utilization_percent or 0),
                temperature_celsius=float(gpu.temperature_celsius or 0),
                status=gpu.status.value,
                deployment_id=gpu.deployment_id,
                updated_at=gpu.updated_at
            ))

        total = len(gpu_infos)
        available = sum(1 for g in gpu_infos if g.status == GPUStatus.AVAILABLE.value)
        in_use = sum(1 for g in gpu_infos if g.status == GPUStatus.IN_USE.value)

        return GPUsResponse(
            gpus=gpu_infos,
            total=total,
            available=available,
            in_use=in_use
        )

    def get_cluster_stats(self) -> Dict[str, Any]:
        """Get overall cluster statistics."""
        if not self.gpu_manager.is_available():
            return {
                "total_gpus": 0,
                "total_memory_mb": 0,
                "free_memory_mb": 0,
                "average_utilization": 0.0,
                "average_temperature": 0.0,
            }

        return {
            "total_gpus": self.gpu_manager.num_gpus,
            "total_memory_mb": self.gpu_manager.get_total_memory(),
            "free_memory_mb": self.gpu_manager.get_free_memory(),
            "average_utilization": self.gpu_manager.get_average_utilization(),
            "average_temperature": self.gpu_manager.get_average_temperature(),
        }

    def check_gpu_health(self) -> Dict[str, bool]:
        """
        Check health of all GPUs.

        Returns:
            Dictionary mapping GPU IDs to health status
        """
        health = {}
        gpu_infos = self.gpu_manager.get_all_gpus()

        for gpu_info in gpu_infos:
            gpu_id = gpu_info["id"]
            # Check if GPU is responding and has reasonable metrics
            is_healthy = (
                gpu_info["temperature_celsius"] < 95 and
                gpu_info["utilization_percent"] <= 100
            )
            health[gpu_id] = is_healthy

        return health

    def find_suitable_gpus(
        self,
        required_memory_mb: int,
        count: int = 1
    ) -> List[str]:
        """
        Find suitable GPUs for deployment.

        Args:
            required_memory_mb: Required memory per GPU
            count: Number of GPUs needed

        Returns:
            List of available GPU IDs
        """
        return self.gpu_manager.find_available_gpus(
            required_memory_mb=required_memory_mb,
            count=count
        )
