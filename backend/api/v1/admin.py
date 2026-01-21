"""
Admin API endpoints for managing models, deployments, GPUs, and API keys.
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from loguru import logger

from backend.api.deps import get_current_db, verify_admin_access
from backend.models.database import User, ApiKey, Deployment, Model
from backend.models.schemas import (
    ModelCreate,
    ModelResponse,
    DeploymentCreate,
    DeploymentResponse,
    DeploymentUpdate,
    ApiKeyCreate,
    ApiKeyResponse,
    ApiKeyCreateResponse,
    GPUsResponse,
    SystemStats,
)
from backend.services.model_service import ModelService
from backend.services.deployment_service import DeploymentService
from backend.services.gpu_service import GPUService

router = APIRouter(prefix="/api/v1/admin", tags=["Admin"])


# ============================================================================
# Model Management
# ============================================================================

@router.post("/models", response_model=ModelResponse, status_code=status.HTTP_201_CREATED)
async def create_model(
    data: ModelCreate,
    admin: User = Depends(verify_admin_access),
    db: Session = Depends(get_current_db),
):
    """Create a new model and start downloading."""
    from backend.models.database import ModelSource, ModelCategory

    service = ModelService(db)

    try:
        model = service.create_model(
            name=data.name,
            version=data.version,
            source=ModelSource(data.source.value),
            category=ModelCategory(data.category.value),
            huggingface_token=data.huggingface_token
        )
        return ModelResponse.model_validate(model)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/models", response_model=List[ModelResponse])
async def list_models(
    admin: User = Depends(verify_admin_access),
    db: Session = Depends(get_current_db),
):
    """List all models."""
    service = ModelService(db)
    models = service.list_models()
    return [ModelResponse.model_validate(m) for m in models]


@router.get("/models/{model_id}", response_model=ModelResponse)
async def get_model(
    model_id: int,
    admin: User = Depends(verify_admin_access),
    db: Session = Depends(get_current_db),
):
    """Get a specific model."""
    service = ModelService(db)
    model = service.get_model(model_id)
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")
    return ModelResponse.model_validate(model)


@router.delete("/models/{model_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_model(
    model_id: int,
    admin: User = Depends(verify_admin_access),
    db: Session = Depends(get_current_db),
):
    """Delete a model."""
    service = ModelService(db)
    if not service.delete_model(model_id):
        raise HTTPException(status_code=404, detail="Model not found")


# ============================================================================
# Model Download Management (ModelScope)
# ============================================================================

class ModelDownloadRequest(BaseModel):
    """Request body for model download."""
    repo_id: str = Field(..., description="ModelScope repository ID (e.g., Qwen/qwen-72b-chat)")
    revision: str = Field(default="master", description="Git revision (branch/tag/commit)")


@router.post("/models/{model_id}/download")
async def download_model(
    model_id: int,
    data: ModelDownloadRequest,
    admin: User = Depends(verify_admin_access),
    db: Session = Depends(get_current_db),
):
    """
    Download a model from ModelScope.

    This creates a download task and starts downloading the model asynchronously.
    The model will be stored in shared storage and accessible by all workers.
    """
    from backend.services.model_download_service import ModelDownloadService

    service = ModelDownloadService(db)

    try:
        task = await service.create_download_task(
            model_id=model_id,
            modelscope_repo_id=data.repo_id,
            revision=data.revision
        )

        return {
            "task_id": task.id,
            "model_id": model_id,
            "status": task.status.value,
            "storage_path": task.model.storage_path,
            "message": "Download task created successfully"
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/models/{model_id}/download/status")
async def get_download_status(
    model_id: int,
    admin: User = Depends(verify_admin_access),
    db: Session = Depends(get_current_db),
):
    """Get the download status for a model."""
    from backend.services.model_download_service import ModelDownloadService

    service = ModelDownloadService(db)

    try:
        status = await service.get_download_status(model_id)
        return status
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/download/tasks")
async def list_download_tasks(
    status_filter: str = Query(None, alias="status", description="Filter by status"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of tasks"),
    admin: User = Depends(verify_admin_access),
    db: Session = Depends(get_current_db),
):
    """List all download tasks."""
    from backend.services.model_download_service import ModelDownloadService

    service = ModelDownloadService(db)
    tasks = service.list_download_tasks(status=status_filter, limit=limit)

    return {
        "tasks": tasks,
        "total": len(tasks)
    }


@router.get("/models/{model_id}/download/logs")
async def get_download_logs(
    model_id: int,
    tail: int = Query(100, ge=1, le=10000, description="Number of lines to return"),
    admin: User = Depends(verify_admin_access),
    db: Session = Depends(get_current_db),
):
    """Get download logs for a model."""
    import os

    model = db.query(Model).filter(Model.id == model_id).first()
    if not model or not model.download_task_id:
        raise HTTPException(status_code=404, detail="Download task not found")

    # Find log file
    log_dir = f"{os.getenv('LOG_PATH', '/var/lib/tokenmachine/logs')}/downloads"
    log_pattern = f"{model.modelscope_repo_id.replace('/', '_')}_"
    log_files = [
        f for f in os.listdir(log_dir)
        if f.startswith(log_pattern) and f.endswith(".log")
    ]

    if not log_files:
        raise HTTPException(status_code=404, detail="Log file not found")

    # Get the most recent log file
    log_file = sorted(log_files)[-1]
    log_path = os.path.join(log_dir, log_file)

    # Read last N lines
    try:
        with open(log_path, "r") as f:
            lines = f.readlines()
            lines_tail = lines[-tail:] if len(lines) > tail else lines

        return {
            "log_file": log_path,
            "lines": [line.strip() for line in lines_tail]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read log file: {str(e)}")


# ============================================================================
# Deployment Management
# ============================================================================

@router.post("/deployments", response_model=DeploymentResponse, status_code=status.HTTP_201_CREATED)
async def create_deployment(
    data: DeploymentCreate,
    admin: User = Depends(verify_admin_access),
    db: Session = Depends(get_current_db),
):
    """Create a new deployment."""
    service = DeploymentService(db)

    try:
        deployment = await service.create_deployment(data)
        return DeploymentResponse.model_validate(deployment)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/deployments", response_model=List[DeploymentResponse])
async def list_deployments(
    status_filter: str = Query(None, alias="status"),
    admin: User = Depends(verify_admin_access),
    db: Session = Depends(get_current_db),
):
    """List all deployments."""
    from backend.models.database import DeploymentStatus

    service = DeploymentService(db)
    deployments = service.list_deployments(
        status=DeploymentStatus(status_filter) if status_filter else None
    )
    return [DeploymentResponse.model_validate(d) for d in deployments]


@router.get("/deployments/{deployment_id}", response_model=DeploymentResponse)
async def get_deployment(
    deployment_id: int,
    admin: User = Depends(verify_admin_access),
    db: Session = Depends(get_current_db),
):
    """Get a specific deployment."""
    service = DeploymentService(db)
    deployment = service.get_deployment(deployment_id)
    if not deployment:
        raise HTTPException(status_code=404, detail="Deployment not found")
    return DeploymentResponse.model_validate(deployment)


@router.patch("/deployments/{deployment_id}", response_model=DeploymentResponse)
async def update_deployment(
    deployment_id: int,
    data: DeploymentUpdate,
    admin: User = Depends(verify_admin_access),
    db: Session = Depends(get_current_db),
):
    """Update a deployment."""
    service = DeploymentService(db)

    if data.replicas is not None:
        deployment = service.update_deployment(deployment_id, replicas=data.replicas)
    else:
        deployment = service.get_deployment(deployment_id)

    if not deployment:
        raise HTTPException(status_code=404, detail="Deployment not found")

    return DeploymentResponse.model_validate(deployment)


@router.delete("/deployments/{deployment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def stop_deployment(
    deployment_id: int,
    admin: User = Depends(verify_admin_access),
    db: Session = Depends(get_current_db),
):
    """Stop a deployment."""
    service = DeploymentService(db)
    await service.stop_deployment(deployment_id)


# ============================================================================
# GPU Management
# ============================================================================

@router.get("/gpus", response_model=GPUsResponse)
async def list_gpus(
    refresh: bool = Query(False, description="Refresh GPU status from hardware"),
    admin: User = Depends(verify_admin_access),
    db: Session = Depends(get_current_db),
):
    """List all GPUs and their status."""
    service = GPUService(db)

    if refresh:
        service.refresh_gpu_status()

    return service.get_gpu_stats()


# ============================================================================
# API Key Management
# ============================================================================

@router.post("/api-keys", response_model=ApiKeyCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_api_key(
    data: ApiKeyCreate,
    admin: User = Depends(verify_admin_access),
    db: Session = Depends(get_current_db),
):
    """Create a new API key."""
    from backend.core.security import generate_api_key, hash_api_key

    # Generate API key
    raw_key = generate_api_key(data.user_id)
    key_hash = hash_api_key(raw_key)
    key_prefix = raw_key[:10]

    api_key = ApiKey(
        key_hash=key_hash,
        key_prefix=key_prefix,
        user_id=data.user_id,
        name=data.name,
        quota_tokens=data.quota_tokens
    )
    db.add(api_key)
    db.commit()
    db.refresh(api_key)

    return ApiKeyCreateResponse(
        id=api_key.id,
        key=raw_key,  # Only shown once
        key_prefix=key_prefix,
        name=api_key.name,
        quota_tokens=api_key.quota_tokens,
        tokens_used=api_key.tokens_used
    )


@router.get("/api-keys", response_model=List[ApiKeyResponse])
async def list_api_keys(
    admin: User = Depends(verify_admin_access),
    db: Session = Depends(get_current_db),
):
    """List all API keys."""
    api_keys = db.query(ApiKey).all()
    return [ApiKeyResponse.model_validate(k) for k in api_keys]


@router.delete("/api-keys/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_api_key(
    key_id: int,
    admin: User = Depends(verify_admin_access),
    db: Session = Depends(get_current_db),
):
    """Revoke an API key."""
    api_key = db.query(ApiKey).filter(
        ApiKey.id == key_id
    ).first()

    if not api_key:
        raise HTTPException(status_code=404, detail="API key not found")

    api_key.is_active = False
    db.commit()


# ============================================================================
# System Statistics
# ============================================================================

@router.get("/stats/system", response_model=SystemStats)
async def get_system_stats(
    admin: User = Depends(verify_admin_access),
    db: Session = Depends(get_current_db),
):
    """Get system statistics."""
    from backend.models.database import DeploymentStatus, ModelStatus

    gpu_service = GPUService(db)
    gpu_stats = gpu_service.get_gpu_stats()

    models_total = db.query(Model).count()
    models_ready = db.query(Model).filter(
        Model.status == ModelStatus.READY
    ).count()

    deployments_total = db.query(Deployment).count()
    deployments_running = db.query(Deployment).filter(
        Deployment.status == DeploymentStatus.RUNNING
    ).count()

    api_keys_total = db.query(ApiKey).count()
    api_keys_active = db.query(ApiKey).filter(ApiKey.is_active == True).count()

    return SystemStats(
        gpu_total=gpu_stats.total,
        gpu_used=gpu_stats.in_use,
        gpu_available=gpu_stats.available,
        models_total=models_total,
        models_ready=models_ready,
        deployments_total=deployments_total,
        deployments_running=deployments_running,
        api_keys_total=api_keys_total,
        api_keys_active=api_keys_active
    )
