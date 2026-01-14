"""
Deployment service for managing model deployments.
"""
import asyncio
from typing import List, Optional, Dict, Any
from loguru import logger
from sqlalchemy.orm import Session

from backend.models.database import (
    Deployment, DeploymentStatus, Model, ModelStatus, GPU, GPUStatus
)
from backend.models.schemas import DeploymentCreate, DeploymentConfig
from backend.workers.worker_pool import VLLMWorkerPool
from backend.services.model_service import ModelService
from backend.core.config import get_settings
from backend.core.gpu import get_gpu_manager

settings = get_settings()


class DeploymentService:
    """Service for deployment management operations."""

    def __init__(self, db: Session):
        """Initialize deployment service."""
        self.db = db
        self.gpu_manager = get_gpu_manager()
        self.model_service = ModelService(db)
        self.worker_pool = VLLMWorkerPool()

    async def create_deployment(self, data: DeploymentCreate) -> Deployment:
        """
        Create a new deployment.

        Args:
            data: Deployment creation data

        Returns:
            Created Deployment instance
        """
        # Verify model exists and is ready
        model = self.model_service.get_model(data.model_id)
        if not model:
            raise ValueError(f"Model {data.model_id} not found")

        if model.status != ModelStatus.READY:
            raise ValueError(f"Model {model.name} is not ready (status: {model.status})")

        # Check if deployment name already exists
        existing = self.db.query(Deployment).filter(
            Deployment.name == data.name
        ).first()
        if existing:
            raise ValueError(f"Deployment with name '{data.name}' already exists")

        # Verify GPU availability
        required_memory = self.model_service.estimate_gpu_memory(model)
        available_gpus = self.gpu_manager.find_available_gpus(
            required_memory_mb=required_memory,
            count=len(data.gpu_ids),
            exclude_gpus=[]  # Don't exclude any GPUs
        )

        # Check if requested GPUs are available
        for gpu_id in data.gpu_ids:
            if gpu_id not in available_gpus:
                # Check GPU status in database
                gpu = self.db.query(GPU).filter(GPU.gpu_id == gpu_id).first()
                if gpu and gpu.status == GPUStatus.IN_USE:
                    raise ValueError(f"GPU {gpu_id} is already in use")

        # Create deployment record
        deployment = Deployment(
            model_id=data.model_id,
            name=data.name,
            status=DeploymentStatus.STARTING,
            replicas=data.replicas,
            gpu_ids=data.gpu_ids,
            backend=data.backend,
            config=data.config.model_dump()
        )
        self.db.add(deployment)
        self.db.commit()
        self.db.refresh(deployment)

        # Start workers
        try:
            await self._start_workers(deployment, model)
        except Exception as e:
            deployment.status = DeploymentStatus.ERROR
            deployment.config = {**deployment.config, "error": str(e)}
            self.db.commit()
            raise

        logger.info(f"Created deployment {data.name} with ID {deployment.id}")
        return deployment

    async def _start_workers(self, deployment: Deployment, model: Model):
        """Start worker processes for a deployment."""
        logger.info(f"Starting {deployment.replicas} workers for deployment {deployment.name}")

        config = DeploymentConfig(**deployment.config) if deployment.config else DeploymentConfig()
        workers = []

        for i in range(deployment.replicas):
            gpu_id = deployment.gpu_ids[i % len(deployment.gpu_ids)]
            port = settings.get_worker_port(deployment.id * 10 + i)

            worker_config = {
                "model_path": model.path,
                "model_name": deployment.name,
                "gpu_id": gpu_id,
                "port": port,
                "config": {
                    "tensor_parallel_size": config.tensor_parallel_size,
                    "max_model_len": config.max_model_len,
                    "gpu_memory_utilization": config.gpu_memory_utilization,
                    "dtype": config.dtype,
                    "trust_remote_code": config.trust_remote_code,
                }
            }

            worker = await self.worker_pool.create_worker(
                deployment_id=deployment.id,
                worker_index=i,
                **worker_config
            )
            workers.append(worker)

        # Update GPU status
        for gpu_id in deployment.gpu_ids:
            gpu = self.db.query(GPU).filter(GPU.gpu_id == gpu_id).first()
            if gpu:
                gpu.status = GPUStatus.IN_USE
                gpu.deployment_id = deployment.id

        # Update deployment status
        all_healthy = all(w.is_healthy() for w in workers)
        deployment.status = DeploymentStatus.RUNNING if all_healthy else DeploymentStatus.ERROR
        deployment.health_status = {
            str(i): {"healthy": w.is_healthy(), "endpoint": w.get_endpoint()}
            for i, w in enumerate(workers)
        }
        self.db.commit()

        logger.info(f"Workers started for deployment {deployment.name}: {len(workers)} healthy")

    async def stop_deployment(self, deployment_id: int) -> Deployment:
        """
        Stop a deployment.

        Args:
            deployment_id: Deployment ID

        Returns:
            Updated Deployment instance
        """
        deployment = self.get_deployment(deployment_id)
        if not deployment:
            raise ValueError(f"Deployment {deployment_id} not found")

        if deployment.status == DeploymentStatus.STOPPED:
            return deployment

        # Stop all workers
        await self.worker_pool.stop_deployment_workers(deployment_id)

        # Free up GPUs
        for gpu_id in deployment.gpu_ids or []:
            gpu = self.db.query(GPU).filter(GPU.gpu_id == gpu_id).first()
            if gpu:
                gpu.status = GPUStatus.AVAILABLE
                gpu.deployment_id = None

        # Update deployment status
        deployment.status = DeploymentStatus.STOPPED
        deployment.health_status = None
        self.db.commit()

        logger.info(f"Stopped deployment {deployment.name}")
        return deployment

    async def restart_deployment(self, deployment_id: int) -> Deployment:
        """Restart a deployment."""
        await self.stop_deployment(deployment_id)

        deployment = self.get_deployment(deployment_id)
        model = self.model_service.get_model(deployment.model_id)

        deployment.status = DeploymentStatus.STARTING
        self.db.commit()

        await self._start_workers(deployment, model)
        return deployment

    def get_deployment(self, deployment_id: int) -> Optional[Deployment]:
        """Get a deployment by ID."""
        return self.db.query(Deployment).filter(Deployment.id == deployment_id).first()

    def get_deployment_by_name(self, name: str) -> Optional[Deployment]:
        """Get a deployment by name."""
        return self.db.query(Deployment).filter(Deployment.name == name).first()

    def list_deployments(
        self,
        status: Optional[DeploymentStatus] = None,
        model_id: Optional[int] = None
    ) -> List[Deployment]:
        """List deployments with optional filters."""
        query = self.db.query(Deployment)
        if status:
            query = query.filter(Deployment.status == status)
        if model_id:
            query = query.filter(Deployment.model_id == model_id)
        return query.order_by(Deployment.created_at.desc()).all()

    def update_deployment(
        self,
        deployment_id: int,
        replicas: Optional[int] = None
    ) -> Optional[Deployment]:
        """Update deployment configuration."""
        deployment = self.get_deployment(deployment_id)
        if not deployment:
            return None

        if replicas is not None and replicas != deployment.replicas:
            # For now, require restart to change replica count
            deployment.replicas = replicas
            self.db.commit()
            # In production, you'd want to scale up/down gracefully

        self.db.refresh(deployment)
        return deployment

    def get_worker_endpoints(self, deployment_id: int) -> List[str]:
        """Get list of worker endpoints for a deployment."""
        workers = self.worker_pool.get_deployment_workers(deployment_id)
        return [w.get_endpoint() for w in workers if w.is_healthy()]

    def get_deployment_stats(self, deployment_id: int) -> Dict[str, Any]:
        """Get deployment statistics."""
        deployment = self.get_deployment(deployment_id)
        if not deployment:
            return {}

        workers = self.worker_pool.get_deployment_workers(deployment_id)
        healthy_workers = [w for w in workers if w.is_healthy()]

        return {
            "deployment_id": deployment.id,
            "name": deployment.name,
            "status": deployment.status,
            "replicas": deployment.replicas,
            "healthy_replicas": len(healthy_workers),
            "endpoints": [w.get_endpoint() for w in healthy_workers],
            "gpus": deployment.gpu_ids,
        }
