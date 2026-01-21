"""
Worker management API endpoints.

This module provides endpoints for managing GPU workers, which are logical
collections of GPU devices that can span across multiple physical machines.
"""
from typing import Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.core.database import get_db
from backend.core.security import generate_worker_token, hash_worker_token
from backend.models.database import Worker, Cluster, WorkerStatus, GPUDevice, GPUDeviceState
from backend.models.schemas import (
    WorkerCreate,
    WorkerUpdate,
    WorkerResponse,
    WorkerCreateResponse,
    WorkerListResponse,
    WorkerAddGPUResponse,
)

router = APIRouter(prefix="/workers", tags=["workers"])


def get_default_cluster(db: Session) -> Cluster:
    """Get or create default cluster."""
    cluster = db.query(Cluster).filter(Cluster.is_default == True).first()
    if not cluster:
        cluster = Cluster(
            name="default",
            type="standalone",
            is_default=True,
            status=ClusterStatus.RUNNING
        )
        db.add(cluster)
        db.commit()
        db.refresh(cluster)
    return cluster


@router.post("", response_model=WorkerCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_worker(
    request: WorkerCreate,
    db: Session = Depends(get_db)
):
    """
    Create a new Worker.

    Worker is a logical concept that represents a collection of GPU devices.
    GPUs can be from different physical machines but share the same registration token.

    Returns:
        WorkerCreateResponse: Created worker with registration token (only returned once)
    """
    # Get cluster (default or specified)
    if request.cluster_id:
        cluster = db.query(Cluster).filter(Cluster.id == request.cluster_id).first()
        if not cluster:
            raise HTTPException(status_code=404, detail="Cluster not found")
    else:
        cluster = get_default_cluster(db)

    # Check if worker name already exists in this cluster
    existing_worker = db.query(Worker).filter(
        Worker.cluster_id == cluster.id,
        Worker.name == request.name
    ).first()
    if existing_worker:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Worker '{request.name}' already exists in this cluster"
        )

    # Generate registration token
    register_token = generate_worker_token()
    token_hash = hash_worker_token(register_token)

    # Create worker
    worker = Worker(
        name=request.name,
        cluster_id=cluster.id,
        status=WorkerStatus.REGISTERING,
        token_hash=token_hash,
        labels=request.labels,
        expected_gpu_count=request.expected_gpu_count or 0,
        gpu_count=0
    )

    db.add(worker)
    db.commit()
    db.refresh(worker)

    # Construct install command
    install_command = (
        f"TM_TOKEN={register_token} "
        f"TM_GPU_ID=<GPU_ID> "
        f"curl -sfL https://get.tokenmachine.io | bash -"
    )

    return WorkerCreateResponse(
        id=worker.id,
        name=worker.name,
        status=worker.status,
        register_token=register_token,  # Only returned once
        install_command=install_command,
        expected_gpu_count=worker.expected_gpu_count,
        current_gpu_count=0,
        created_at=worker.created_at
    )


@router.get("", response_model=WorkerListResponse)
async def list_workers(
    cluster_id: Optional[int] = None,
    status: Optional[WorkerStatus] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """
    List all workers with optional filtering.

    Args:
        cluster_id: Filter by cluster ID
        status: Filter by worker status
        page: Page number (1-indexed)
        page_size: Number of items per page

    Returns:
        WorkerListResponse: Paginated list of workers
    """
    query = db.query(Worker)

    # Apply filters
    if cluster_id:
        query = query.filter(Worker.cluster_id == cluster_id)
    if status:
        query = query.filter(Worker.status == status)

    # Get total count
    total = query.count()

    # Apply pagination
    workers = query.offset((page - 1) * page_size).limit(page_size).all()

    return WorkerListResponse(
        items=workers,
        total=total,
        page=page,
        page_size=page_size
    )


@router.get("/{worker_id}", response_model=WorkerResponse)
async def get_worker(
    worker_id: int,
    db: Session = Depends(get_db)
):
    """
    Get worker details by ID.

    Args:
        worker_id: Worker ID

    Returns:
        WorkerResponse: Worker details with GPU list
    """
    worker = db.query(Worker).filter(Worker.id == worker_id).first()
    if not worker:
        raise HTTPException(status_code=404, detail="Worker not found")

    return worker


@router.post("/{worker_id}/add-gpu", response_model=WorkerAddGPUResponse)
async def get_add_gpu_token(
    worker_id: int,
    db: Session = Depends(get_db)
):
    """
    Get token for adding more GPUs to an existing worker.

    This allows dynamically adding GPUs to a worker that's already registered.

    Args:
        worker_id: Worker ID

    Returns:
        WorkerAddGPUResponse: Token and install command for adding GPUs
    """
    worker = db.query(Worker).filter(Worker.id == worker_id).first()
    if not worker:
        raise HTTPException(status_code=404, detail="Worker not found")

    # Generate new token (reuses existing token_hash logic)
    # For security, we could create a new token, but for simplicity we reuse
    # The token_hash would be updated in the database
    register_token = generate_worker_token()
    worker.token_hash = hash_worker_token(register_token)
    db.commit()

    install_command = (
        f"TM_TOKEN={register_token} "
        f"TM_GPU_ID=<GPU_ID> "
        f"curl -sfL https://get.tokenmachine.io | bash -"
    )

    return WorkerAddGPUResponse(
        register_token=register_token,
        install_command=install_command,
        message=f"Use this token to add more GPUs to worker '{worker.name}'"
    )


@router.put("/{worker_id}", response_model=WorkerResponse)
async def update_worker(
    worker_id: int,
    request: WorkerUpdate,
    db: Session = Depends(get_db)
):
    """
    Update worker details.

    Args:
        worker_id: Worker ID
        request: Update data

    Returns:
        WorkerResponse: Updated worker details
    """
    worker = db.query(Worker).filter(Worker.id == worker_id).first()
    if not worker:
        raise HTTPException(status_code=404, detail="Worker not found")

    # Update fields
    if request.labels is not None:
        worker.labels = request.labels
    if request.status is not None:
        worker.status = request.status
    if request.expected_gpu_count is not None:
        worker.expected_gpu_count = request.expected_gpu_count

    db.commit()
    db.refresh(worker)

    return worker


@router.delete("/{worker_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_worker(
    worker_id: int,
    db: Session = Depends(get_db)
):
    """
    Delete a worker.

    This will also delete all associated GPU devices.
    Worker with running model instances cannot be deleted.

    Args:
        worker_id: Worker ID
    """
    worker = db.query(Worker).filter(Worker.id == worker_id).first()
    if not worker:
        raise HTTPException(status_code=404, detail="Worker not found")

    # Check if worker has GPUs in use
    active_gpus = db.query(GPUDevice).filter(
        GPUDevice.worker_id == worker_id,
        GPUDevice.state == GPUDeviceState.IN_USE
    ).count()

    if active_gpus > 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot delete worker with {active_gpus} active GPUs. "
                   f"Please stop all GPUs before deleting the worker."
        )

    db.delete(worker)
    db.commit()

    return None


@router.post("/{worker_id}/set-status")
async def set_worker_status(
    worker_id: int,
    new_status: WorkerStatus,
    db: Session = Depends(get_db)
):
    """
    Manually set worker status.

    Useful for maintenance or recovery operations.

    Args:
        worker_id: Worker ID
        new_status: New worker status

    Returns:
        dict: Success message
    """
    worker = db.query(Worker).filter(Worker.id == worker_id).first()
    if not worker:
        raise HTTPException(status_code=404, detail="Worker not found")

    worker.status = new_status
    db.commit()

    return {
        "success": True,
        "message": f"Worker status updated to {new_status}",
        "worker_id": worker.id,
        "new_status": new_status
    }


@router.get("/{worker_id}/stats")
async def get_worker_stats(
    worker_id: int,
    db: Session = Depends(get_db)
):
    """
    Get worker statistics including GPU utilization.

    Args:
        worker_id: Worker ID

    Returns:
        dict: Worker statistics
    """
    worker = db.query(Worker).filter(Worker.id == worker_id).first()
    if not worker:
        raise HTTPException(status_code=404, detail="Worker not found")

    # Get GPU stats
    gpus = db.query(GPUDevice).filter(GPUDevice.worker_id == worker_id).all()

    total_gpus = len(gpus)
    in_use_gpus = len([g for g in gpus if g.state == GPUDeviceState.IN_USE])
    error_gpus = len([g for g in gpus if g.state == GPUDeviceState.ERROR])

    # Calculate average utilization
    if gpus:
        avg_memory_util = sum(g.memory_utilization_rate or 0 for g in gpus) / len(gpus)
        avg_core_util = sum(g.core_utilization_rate or 0 for g in gpus) / len(gpus)
        avg_temperature = sum(g.temperature or 0 for g in gpus) / len(gpus)
    else:
        avg_memory_util = 0.0
        avg_core_util = 0.0
        avg_temperature = 0.0

    return {
        "worker_id": worker.id,
        "worker_name": worker.name,
        "status": worker.status,
        "total_gpus": total_gpus,
        "in_use_gpus": in_use_gpus,
        "error_gpus": error_gpus,
        "avg_memory_utilization": round(avg_memory_util, 2),
        "avg_core_utilization": round(avg_core_util, 2),
        "avg_temperature": round(avg_temperature, 2),
        "last_heartbeat_at": worker.last_heartbeat_at
    }
