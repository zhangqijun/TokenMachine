"""
Model Instance Management API endpoints.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import logging

from backend.api.deps import get_db, get_current_admin_user
from backend.models.database import ModelInstanceStatus
from backend.server.controllers.instance_controller import ModelInstanceController

router = APIRouter()
logger = logging.getLogger(__name__)


# ============================================================================
# Request/Response Schemas
# ============================================================================

class CreateInstanceRequest(BaseModel):
    """Create instance request."""

    model_id: int = Field(..., description="Model ID")
    worker_id: int = Field(..., description="Worker ID")
    name: str = Field(..., description="Instance name")
    backend: str = Field(default="vllm", description="Backend type")
    gpu_ids: List[int] = Field(default_factory=list, description="GPU IDs")
    config: Dict[str, Any] = Field(default_factory=dict, description="Backend configuration")


class InstanceInfo(BaseModel):
    """Instance information."""

    id: int
    model_id: int
    worker_id: int
    name: str
    status: str
    backend: str
    gpu_ids: List[int]
    port: Optional[int]
    health_status: Optional[Dict[str, Any]]
    created_at: str


class InstanceListResponse(BaseModel):
    """Instance list response."""

    items: List[InstanceInfo]
    total: int


class UpdateInstanceStatusRequest(BaseModel):
    """Update instance status request."""

    status: str
    health_status: Optional[Dict[str, Any]] = None


# ============================================================================
# API Endpoints
# ============================================================================

@router.post("", response_model=InstanceInfo, status_code=status.HTTP_201_CREATED)
async def create_instance(
    request: CreateInstanceRequest,
    db=Depends(get_db),
    current_user=Depends(get_current_admin_user),
):
    """Create a new model instance."""
    instance_controller = ModelInstanceController(db)

    # Verify model exists
    from backend.server.controllers.model_controller import ModelController
    model_controller = ModelController(db)
    model = model_controller.get_model(request.model_id)
    if not model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Model {request.model_id} not found",
        )

    # Verify worker exists
    from backend.server.controllers.worker_controller import WorkerController
    worker_controller = WorkerController(db)
    worker = worker_controller.get_worker(request.worker_id)
    if not worker:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Worker {request.worker_id} not found",
        )

    # Create instance
    instance = instance_controller.create_instance(
        model_id=request.model_id,
        worker_id=request.worker_id,
        name=request.name,
        backend=request.backend,
        config=request.config,
        gpu_ids=request.gpu_ids,
    )

    return InstanceInfo(
        id=instance.id,
        model_id=instance.model_id,
        worker_id=instance.worker_id,
        name=instance.name,
        status=instance.status.value,
        backend=instance.backend,
        gpu_ids=instance.gpu_ids or [],
        port=instance.port,
        health_status=instance.health_status,
        created_at=instance.created_at.isoformat(),
    )


@router.get("", response_model=InstanceListResponse)
async def list_instances(
    model_id: Optional[int] = None,
    worker_id: Optional[int] = None,
    status_filter: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    db=Depends(get_db),
    current_user=Depends(get_current_admin_user),
):
    """List model instances."""
    instance_controller = ModelInstanceController(db)

    status = None
    if status_filter:
        try:
            status = ModelInstanceStatus(status_filter)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status: {status_filter}",
            )

    instances = instance_controller.list_instances(
        model_id=model_id,
        worker_id=worker_id,
        status=status,
        limit=limit,
        offset=offset,
    )

    total = len(instances)  # Simplified

    return InstanceListResponse(
        items=[
            InstanceInfo(
                id=inst.id,
                model_id=inst.model_id,
                worker_id=inst.worker_id,
                name=inst.name,
                status=inst.status.value,
                backend=inst.backend,
                gpu_ids=inst.gpu_ids or [],
                port=inst.port,
                health_status=inst.health_status,
                created_at=inst.created_at.isoformat(),
            )
            for inst in instances
        ],
        total=total,
    )


@router.get("/{instance_id}")
async def get_instance(
    instance_id: int,
    db=Depends(get_db),
    current_user=Depends(get_current_admin_user),
):
    """Get instance details."""
    instance_controller = ModelInstanceController(db)

    instance = instance_controller.get_instance(instance_id)
    if not instance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Instance {instance_id} not found",
        )

    return InstanceInfo(
        id=instance.id,
        model_id=instance.model_id,
        worker_id=instance.worker_id,
        name=instance.name,
        status=instance.status.value,
        backend=instance.backend,
        gpu_ids=instance.gpu_ids or [],
        port=instance.port,
        health_status=instance.health_status,
        created_at=instance.created_at.isoformat(),
    )


@router.patch("/{instance_id}/status")
async def update_instance_status(
    instance_id: int,
    request: UpdateInstanceStatusRequest,
    db=Depends(get_db),
):
    """Update instance status (internal API called by workers)."""
    instance_controller = ModelInstanceController(db)

    try:
        status = ModelInstanceStatus(request.status)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid status: {request.status}",
        )

    instance = instance_controller.update_instance_status(
        instance_id,
        status,
        health_status=request.health_status,
    )

    if not instance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Instance {instance_id} not found",
        )

    return InstanceInfo(
        id=instance.id,
        model_id=instance.model_id,
        worker_id=instance.worker_id,
        name=instance.name,
        status=instance.status.value,
        backend=instance.backend,
        gpu_ids=instance.gpu_ids or [],
        port=instance.port,
        health_status=instance.health_status,
        created_at=instance.created_at.isoformat(),
    )


@router.delete("/{instance_id}")
async def delete_instance(
    instance_id: int,
    db=Depends(get_db),
    current_user=Depends(get_current_admin_user),
):
    """Delete an instance."""
    instance_controller = ModelInstanceController(db)

    success = instance_controller.delete_instance(instance_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Instance {instance_id} not found",
        )

    return None
