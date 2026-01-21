"""
Benchmark API routes for batch testing.
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.models.database import ApiKey
from backend.models.schemas import (
    BenchmarkTaskCreate,
    BenchmarkTaskResponse,
    BenchmarkDatasetResponse
)
from backend.services.benchmark_service import BenchmarkService
from backend.workers.benchmark_tasks import run_eval_task, run_perf_task
from backend.api.deps import get_current_db, verify_api_key_auth

router = APIRouter()


@router.post("/tasks", response_model=BenchmarkTaskResponse, status_code=status.HTTP_201_CREATED)
async def create_benchmark_task(
    task_data: BenchmarkTaskCreate,
    api_key: ApiKey = Depends(verify_api_key_auth),
    db: Session = Depends(get_current_db)
):
    """
    Create a batch testing task (executed asynchronously).

    - **task_name**: Task name
    - **task_type**: Task type (eval=evaluation, perf=performance testing)
    - **deployment_id**: Deployment ID
    - **config**: EvalScope configuration parameters

    Returns task information (task executes asynchronously in background)
    """
    service = BenchmarkService(db)

    # Submit to Celery based on task type
    if task_data.task_type == "eval":
        celery_task = run_eval_task.delay(task_id=0)  # Will update after DB insert
    else:  # perf
        celery_task = run_perf_task.delay(task_id=0)  # Will update after DB insert

    # Create task record with celery_task_id
    task = service.create_task(api_key.user_id, task_data, celery_task.id)

    # Update the Celery task with the correct task_id
    from backend.core.celery_app import celery_app
    celery_task.args = (task.id,)
    celery_task.save()

    return task


@router.get("/tasks", response_model=List[BenchmarkTaskResponse])
async def list_benchmark_tasks(
    status: Optional[str] = Query(None, description="Filter by status (pending/running/completed/failed)"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(50, ge=1, le=100, description="Number of records to return"),
    api_key: ApiKey = Depends(verify_api_key_auth),
    db: Session = Depends(get_current_db)
):
    """
    Get batch testing task list.

    - **status**: Filter by status (pending/running/completed/failed)
    - **skip**: Number of records to skip
    - **limit**: Number of records to return
    """
    service = BenchmarkService(db)
    return service.list_tasks(api_key.user_id, status, skip, limit)


@router.get("/tasks/{task_id}", response_model=BenchmarkTaskResponse)
async def get_benchmark_task(
    task_id: int,
    api_key: ApiKey = Depends(verify_api_key_auth),
    db: Session = Depends(get_current_db)
):
    """
    Get single task details.

    Includes task status, configuration, results, etc.
    """
    service = BenchmarkService(db)
    task = service.get_task(task_id, api_key.user_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )
    return task


@router.delete("/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def cancel_benchmark_task(
    task_id: int,
    api_key: ApiKey = Depends(verify_api_key_auth),
    db: Session = Depends(get_current_db)
):
    """
    Cancel/delete batch testing task.

    - If task is running, attempts to cancel Celery task
    - If task is completed, only deletes the record
    """
    service = BenchmarkService(db)
    task = service.get_task(task_id, api_key.user_id)

    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )

    # Cancel Celery task if running
    if task.celery_task_id:
        from backend.core.celery_app import celery_app
        celery_app.control.revoke(task.celery_task_id, terminate=True)

    service.cancel_task(task_id, api_key.user_id)
    return None


@router.get("/datasets", response_model=List[BenchmarkDatasetResponse])
async def list_benchmark_datasets(
    category: Optional[str] = Query(None, description="Filter by dataset category (mmlu/gsm8k/ceval)"),
    db: Session = Depends(get_current_db)
):
    """
    Get available evaluation dataset list.

    - **category**: Dataset category filter (mmlu/gsm8k/ceval)
    """
    service = BenchmarkService(db)
    return service.list_datasets(category)


@router.get("/datasets/{dataset_id}", response_model=BenchmarkDatasetResponse)
async def get_benchmark_dataset(
    dataset_id: int,
    db: Session = Depends(get_current_db)
):
    """Get dataset details."""
    service = BenchmarkService(db)
    dataset = service.get_dataset(dataset_id)
    if not dataset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dataset not found"
        )
    return dataset
