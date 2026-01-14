"""
Worker Management API endpoints.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import logging

from backend.api.deps import get_db, get_current_admin_user
from backend.models.database import Worker, WorkerStatus, ModelInstance
from backend.server.controllers.worker_controller import WorkerController
from backend.server.controllers.instance_controller import ModelInstanceController

router = APIRouter()
logger = logging.getLogger(__name__)


# ============================================================================
# Request/Response Schemas
# ============================================================================

class WorkerRegisterRequest(BaseModel):
    """Worker registration request."""

    name: str = Field(..., description="Worker name")
    ip: str = Field(..., description="Worker IP address")
    ifname: Optional[str] = Field(None, description="Network interface name")
    hostname: Optional[str] = Field(None, description="Worker hostname")
    cluster_id: Optional[int] = Field(None, description="Cluster ID")


class WorkerRegisterResponse(BaseModel):
    """Worker registration response."""

    id: int
    name: str
    cluster_id: Optional[int]
    token: str = Field(..., description="Worker token for authentication")
    server_config: Dict[str, Any] = Field(default_factory=dict)


class WorkerInfo(BaseModel):
    """Worker information."""

    id: int
    name: str
    cluster_id: Optional[int]
    ip: str
    hostname: Optional[str]
    status: str
    gpu_count: int
    last_heartbeat_at: Optional[str]
    created_at: str


class WorkerListResponse(BaseModel):
    """Worker list response."""

    items: List[WorkerInfo]
    total: int


class HeartbeatRequest(BaseModel):
    """Heartbeat request."""

    timestamp: Optional[str] = None
    status: str = "healthy"
    gpu_count: int = 0
    running_instances: int = 0


class WorkerStatusUpdate(BaseModel):
    """Worker status update."""

    gpus: List[Dict[str, Any]] = Field(default_factory=list)
    instances: List[Dict[str, Any]] = Field(default_factory=list)
    system: Dict[str, Any] = Field(default_factory=dict)


class InstanceListItem(BaseModel):
    """Instance list item."""

    id: int
    model_id: int
    name: str
    status: str
    backend: str
    gpu_ids: List[int]
    port: Optional[int]


class InstanceListResponse(BaseModel):
    """Instance list response."""

    items: List[InstanceListItem]


# ============================================================================
# API Endpoints
# ============================================================================

@router.post("/register", response_model=WorkerRegisterResponse, status_code=status.HTTP_201_CREATED)
async def register_worker(
    request: WorkerRegisterRequest,
    db=Depends(get_db),
):
    """Register a new worker."""
    worker_controller = WorkerController(db)

    # Check if worker with same name already exists in cluster
    existing = worker_controller.get_worker_by_name(request.name, request.cluster_id)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Worker '{request.name}' already exists in this cluster",
        )

    # Generate a token for the worker (simplified - should use proper JWT)
    import secrets
    token = f"worker_{secrets.token_urlsafe(32)}"

    # Hash the token (simplified - should use proper hashing)
    from passlib.context import CryptContext
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    token_hash = pwd_context.hash(token)

    # Create worker
    worker = worker_controller.create_worker(
        name=request.name,
        ip=request.ip,
        ifname=request.ifname,
        hostname=request.hostname,
        cluster_id=request.cluster_id,
        token_hash=token_hash,
    )

    return WorkerRegisterResponse(
        id=worker.id,
        name=worker.name,
        cluster_id=worker.cluster_id,
        token=token,
        server_config={
            "heartbeat_interval": 30,
            "metric_interval": 15,
        },
    )


@router.post("/{worker_id}/heartbeat", status_code=status.HTTP_204_NO_CONTENT)
async def worker_heartbeat(
    worker_id: int,
    request: HeartbeatRequest,
    db=Depends(get_db),
):
    """Receive heartbeat from worker."""
    worker_controller = WorkerController(db)

    worker = worker_controller.get_worker(worker_id)
    if not worker:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Worker {worker_id} not found",
        )

    # Update heartbeat timestamp
    worker_controller.update_worker_heartbeat(worker_id)
    worker_controller.update_worker_gpu_count(worker_id, request.gpu_count)

    return None


@router.post("/{worker_id}/status", status_code=status.HTTP_204_NO_CONTENT)
async def update_worker_status(
    worker_id: int,
    status_update: WorkerStatusUpdate,
    db=Depends(get_db),
):
    """Receive status update from worker."""
    worker_controller = WorkerController(db)

    worker = worker_controller.get_worker(worker_id)
    if not worker:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Worker {worker_id} not found",
        )

    # TODO: Store detailed status information
    # For now, just log it
    logger.info(f"Received status update from worker {worker_id}: {status_update}")

    return None


@router.get("", response_model=WorkerListResponse)
async def list_workers(
    cluster_id: Optional[int] = None,
    status_filter: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    db=Depends(get_db),
    current_user=Depends(get_current_admin_user),
):
    """List all workers (admin only)."""
    worker_controller = WorkerController(db)

    status = None
    if status_filter:
        try:
            status = WorkerStatus(status_filter)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status: {status_filter}",
            )

    workers = worker_controller.list_workers(
        cluster_id=cluster_id,
        status=status,
        limit=limit,
        offset=offset,
    )

    total = len(workers)  # Simplified - should use proper count

    return WorkerListResponse(
        items=[
            WorkerInfo(
                id=w.id,
                name=w.name,
                cluster_id=w.cluster_id,
                ip=w.ip,
                hostname=w.hostname,
                status=w.status.value,
                gpu_count=w.gpu_count,
                last_heartbeat_at=w.last_heartbeat_at.isoformat() if w.last_heartbeat_at else None,
                created_at=w.created_at.isoformat(),
            )
            for w in workers
        ],
        total=total,
    )


@router.get("/{worker_id}")
async def get_worker(
    worker_id: int,
    db=Depends(get_db),
    current_user=Depends(get_current_admin_user),
):
    """Get worker details (admin only)."""
    worker_controller = WorkerController(db)

    worker = worker_controller.get_worker(worker_id)
    if not worker:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Worker {worker_id} not found",
        )

    return WorkerInfo(
        id=worker.id,
        name=worker.name,
        cluster_id=worker.cluster_id,
        ip=worker.ip,
        hostname=worker.hostname,
        status=worker.status.value,
        gpu_count=worker.gpu_count,
        last_heartbeat_at=worker.last_heartbeat_at.isoformat() if worker.last_heartbeat_at else None,
        created_at=worker.created_at.isoformat(),
    )


@router.post("/{worker_id}/drain")
async def drain_worker(
    worker_id: int,
    db=Depends(get_db),
    current_user=Depends(get_current_admin_user),
):
    """Drain a worker (stop accepting new tasks)."""
    worker_controller = WorkerController(db)

    worker = worker_controller.drain_worker(worker_id)
    if not worker:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Worker {worker_id} not found",
        )

    return WorkerInfo(
        id=worker.id,
        name=worker.name,
        cluster_id=worker.cluster_id,
        ip=worker.ip,
        hostname=worker.hostname,
        status=worker.status.value,
        gpu_count=worker.gpu_count,
        last_heartbeat_at=worker.last_heartbeat_at.isoformat() if worker.last_heartbeat_at else None,
        created_at=worker.created_at.isoformat(),
    )


@router.delete("/{worker_id}")
async def delete_worker(
    worker_id: int,
    db=Depends(get_db),
    current_user=Depends(get_current_admin_user),
):
    """Delete a worker (admin only)."""
    worker_controller = WorkerController(db)

    success = worker_controller.delete_worker(worker_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Worker {worker_id} not found",
        )

    return None


@router.get("/{worker_id}/instances", response_model=InstanceListResponse)
async def list_worker_instances(
    worker_id: int,
    db=Depends(get_db),
    current_user=Depends(get_current_admin_user),
):
    """List instances on a worker (admin only)."""
    instance_controller = ModelInstanceController(db)

    instances = instance_controller.get_instances_by_worker(worker_id)

    return InstanceListResponse(
        items=[
            InstanceListItem(
                id=inst.id,
                model_id=inst.model_id,
                name=inst.name,
                status=inst.status.value,
                backend=inst.backend,
                gpu_ids=inst.gpu_ids or [],
                port=inst.port,
            )
            for inst in instances
        ],
    )
