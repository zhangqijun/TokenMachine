"""
GPU Metrics API endpoints.

This module provides endpoints for querying GPU metrics from Worker Exporter by worker_id.
"""
from typing import Optional, List
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel

from backend.core.database import get_db
from backend.models.database import Worker, GPUDevice, WorkerStatus
from backend.services.prometheus import get_worker_prometheus_service

router = APIRouter(prefix="/metrics", tags=["metrics"])


class GPUHistoryPoint(BaseModel):
    """Single GPU history data point."""
    timestamp: float
    datetime: str
    utilization: float


class GPUHistoryResponse(BaseModel):
    """GPU history response for a specific GPU."""
    worker_id: int
    gpu_index: int
    duration_seconds: int
    data_points: int
    history: List[GPUHistoryPoint]


class WorkerGPUMetrics(BaseModel):
    """GPU metrics for a single GPU on a worker."""
    gpu_index: int
    name: Optional[str] = None
    memory_total_mb: Optional[float] = None
    memory_used_mb: Optional[float] = None
    memory_utilization_percent: Optional[float] = None
    gpu_utilization_percent: Optional[float] = None
    temperature_celsius: Optional[float] = None


class WorkerMetricsResponse(BaseModel):
    """Worker GPU metrics response."""
    worker_id: int
    worker_name: str
    worker_ip: str
    timestamp: str
    gpu_count: int
    total_memory_gb: float
    used_memory_gb: float
    avg_utilization_percent: float
    gpus: List[WorkerGPUMetrics]
    history: Optional[List[GPUHistoryPoint]] = None


class AllWorkersMetricsResponse(BaseModel):
    """All workers GPU metrics response."""
    timestamp: str
    workers: List[WorkerMetricsResponse]


@router.get("/workers/{worker_id}", response_model=WorkerMetricsResponse)
async def get_worker_metrics(
    worker_id: int,
    duration_seconds: int = Query(60, ge=1, le=3600, description="History duration in seconds"),
    db: Session = Depends(get_db)
) -> WorkerMetricsResponse:
    """
    Get GPU metrics for a specific worker by worker_id.

    Args:
        worker_id: Worker ID
        duration_seconds: Duration for history data (default: 60 seconds)

    Returns:
        WorkerMetricsResponse with all GPU metrics for the worker
    """
    # Get worker from database
    worker = db.query(Worker).filter(Worker.id == worker_id).first()
    if not worker:
        raise HTTPException(status_code=404, detail=f"Worker {worker_id} not found")

    if not worker.ip:
        raise HTTPException(status_code=400, detail=f"Worker {worker_id} has no IP address")

    # Get GPUs for this worker
    gpus = db.query(GPUDevice).filter(GPUDevice.worker_id == worker_id).all()

    # Use worker-specific Prometheus service (direct Exporter query)
    worker_prometheus = get_worker_prometheus_service(worker.ip)

    worker_metrics = {
        "worker_id": worker_id,
        "worker_name": worker.name,
        "worker_ip": worker.ip,
        "timestamp": datetime.utcnow().isoformat(),
        "gpu_count": len(gpus),
        "total_memory_gb": 0,
        "used_memory_gb": 0,
        "avg_utilization_percent": 0,
        "gpus": [],
        "history": []
    }

    # Query each GPU
    total_memory_mb = 0
    total_used_mb = 0
    total_util = 0

    for gpu in gpus:
        gpu_index = gpu.index

        try:
            # Query GPU metrics
            util = worker_prometheus.get_gpu_utilization_1m(gpu_index)
            memory_used = worker_prometheus.get_gpu_memory_used_mb(gpu_index)
            memory_total = worker_prometheus.get_gpu_memory_total_mb(gpu_index)

            gpu_info = WorkerGPUMetrics(
                gpu_index=gpu_index,
                name=gpu.name,
                memory_total_mb=memory_total,
                memory_used_mb=memory_used,
                memory_utilization_percent=util,
            )

            if memory_total:
                total_memory_mb += memory_total
            if memory_used:
                total_used_mb += memory_used
            if util:
                total_util += util

            worker_metrics["gpus"].append(gpu_info)

            # Get history for first GPU (summary)
            if gpu_index == 0:
                history = worker_prometheus.get_gpu_utilization_history(gpu_index, duration_seconds)
                worker_metrics["history"] = [
                    GPUHistoryPoint(**h) for h in history
                ]

        except Exception as e:
            print(f"[Metrics] Error querying GPU {gpu_index}: {e}")
            worker_metrics["gpus"].append(WorkerGPUMetrics(gpu_index=gpu_index))

    # Calculate summary
    if worker_metrics["gpu_count"] > 0:
        worker_metrics["total_memory_gb"] = round(total_memory_mb / 1024, 2)
        worker_metrics["used_memory_gb"] = round(total_used_mb / 1024, 2)
        worker_metrics["avg_utilization_percent"] = round(total_util / len(gpus), 2)

    return WorkerMetricsResponse(**worker_metrics)


@router.get("/workers/{worker_id}/history")
async def get_worker_gpu_history(
    worker_id: int,
    gpu_index: int = Query(0, ge=0, description="GPU index"),
    duration_seconds: int = Query(60, ge=1, le=3600, description="History duration in seconds"),
    db: Session = Depends(get_db)
) -> GPUHistoryResponse:
    """
    Get GPU utilization history for a specific GPU on a worker.

    Args:
        worker_id: Worker ID
        gpu_index: GPU index (0-based)
        duration_seconds: Duration for history data

    Returns:
        GPUHistoryResponse with history data points
    """
    worker = db.query(Worker).filter(Worker.id == worker_id).first()
    if not worker:
        raise HTTPException(status_code=404, detail=f"Worker {worker_id} not found")

    if not worker.ip:
        raise HTTPException(status_code=400, detail=f"Worker {worker_id} has no IP address")

    # Use worker-specific Prometheus service
    worker_prometheus = get_worker_prometheus_service(worker.ip)
    history = worker_prometheus.get_gpu_utilization_history(gpu_index, duration_seconds)

    return GPUHistoryResponse(
        worker_id=worker_id,
        gpu_index=gpu_index,
        duration_seconds=duration_seconds,
        data_points=len(history),
        history=[GPUHistoryPoint(**h) for h in history]
    )


@router.get("/workers", response_model=AllWorkersMetricsResponse)
async def get_all_workers_metrics(
    duration_seconds: int = Query(60, ge=1, le=3600, description="History duration in seconds"),
    db: Session = Depends(get_db)
) -> AllWorkersMetricsResponse:
    """
    Get GPU metrics for all workers.

    Returns:
        AllWorkersMetricsResponse with all workers' GPU metrics
    """
    workers = db.query(Worker).filter(Worker.status == WorkerStatus.READY).all()

    result = {
        "timestamp": datetime.utcnow().isoformat(),
        "workers": []
    }

    for worker in workers:
        if not worker.ip:
            continue

        try:
            gpus = db.query(GPUDevice).filter(GPUDevice.worker_id == worker.id).all()
            if not gpus:
                continue

            # Use worker-specific Prometheus service
            worker_prometheus = get_worker_prometheus_service(worker.ip)

            total_memory_mb = 0
            total_used_mb = 0
            total_util = 0
            gpu_list = []

            for gpu in gpus:
                idx = gpu.index
                util = worker_prometheus.get_gpu_utilization_1m(idx)
                mem_used = worker_prometheus.get_gpu_memory_used_mb(idx)
                mem_total = worker_prometheus.get_gpu_memory_total_mb(idx)

                gpu_list.append(WorkerGPUMetrics(
                    gpu_index=idx,
                    name=gpu.name,
                    memory_total_mb=mem_total,
                    memory_used_mb=mem_used,
                    memory_utilization_percent=util,
                ))

                if mem_total:
                    total_memory_mb += mem_total
                if mem_used:
                    total_used_mb += mem_used
                if util:
                    total_util += util

            avg_util = total_util / len(gpu_list) if gpu_list else 0

            result["workers"].append({
                "worker_id": worker.id,
                "worker_name": worker.name,
                "worker_ip": worker.ip,
                "timestamp": datetime.utcnow().isoformat(),
                "gpu_count": len(gpu_list),
                "total_memory_gb": round(total_memory_mb / 1024, 2),
                "used_memory_gb": round(total_used_mb / 1024, 2),
                "avg_utilization_percent": round(avg_util, 2),
                "gpus": gpu_list,
                "history": None
            })

        except Exception as e:
            print(f"[Metrics] Error querying worker {worker.id}: {e}")
            continue

    return AllWorkersMetricsResponse(**result)


@router.get("/health")
async def metrics_health_check(
    db: Session = Depends(get_db)
) -> dict:
    """
    Check metrics service health.

    Returns:
        Dictionary with health status
    """
    # Check if any workers are available
    workers = db.query(Worker).filter(Worker.status == WorkerStatus.READY).count()

    # Try to query first ready worker's exporter
    can_query = False
    if workers > 0:
        worker = db.query(Worker).filter(Worker.status == WorkerStatus.READY).first()
        if worker and worker.ip:
            prometheus = get_worker_prometheus_service(worker.ip)
            can_query = prometheus.is_available()

    return {
        "status": "healthy" if can_query else "degraded",
        "ready_workers": workers,
        "can_query_metrics": can_query
    }
