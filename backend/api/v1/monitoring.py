"""
Monitoring API endpoints for metrics and analytics.
"""
from typing import List, Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from backend.api.deps import get_db
from backend.services.monitoring_service import MonitoringService

router = APIRouter()


# ============================================================================
# Metrics Summary
# ============================================================================

@router.get("/metrics/summary")
async def get_metrics_summary(
    time_range: str = Query("1h", description="Time range: 5m, 15m, 1h, 6h, 24h, 7d"),
    db: Session = Depends(get_db)
):
    """
    Get real-time metrics summary.

    Returns aggregated metrics for API, GPU, and token consumption.
    """
    service = MonitoringService(db)
    return service.get_metrics_summary(time_range=time_range)


# ============================================================================
# Time Series Data
# ============================================================================

@router.get("/metrics/timeseries")
async def get_timeseries_metrics(
    metrics: str = Query("qps,latency,tokens", description="Comma-separated metric names"),
    start: Optional[str] = Query(None, description="Start time (ISO format)"),
    end: Optional[str] = Query(None, description="End time (ISO format)"),
    hours: int = Query(1, description="Hours ago (if start/end not provided)"),
    interval: str = Query("5m", description="Data interval: 1m, 5m, 10m, 1h"),
    db: Session = Depends(get_db)
):
    """
    Get time series data for specified metrics.

    Available metrics:
    - qps: Queries per second
    - latency: Average latency
    - tokens: Token consumption
    - errors: Error count
    - gpu_util: GPU utilization (future)
    """
    # Parse time range
    if end:
        end_time = datetime.fromisoformat(end.replace("Z", "+00:00"))
    else:
        end_time = datetime.utcnow()

    if start:
        start_time = datetime.fromisoformat(start.replace("Z", "+00:00"))
    else:
        start_time = end_time - timedelta(hours=hours)

    metric_list = [m.strip() for m in metrics.split(",")]

    service = MonitoringService(db)
    data = service.get_timeseries_data(
        metrics=metric_list,
        start=start_time,
        end=end_time,
        interval=interval
    )

    return {
        "metrics": metric_list,
        "start": start_time.isoformat(),
        "end": end_time.isoformat(),
        "interval": interval,
        "data": data
    }


# ============================================================================
# GPU Details
# ============================================================================

@router.get("/gpus")
async def get_gpu_details(
    db: Session = Depends(get_db)
):
    """
    Get detailed GPU status and metrics.

    Returns list of all GPUs with utilization, temperature, and memory info.
    """
    service = MonitoringService(db)
    return service.get_gpu_details()


# ============================================================================
# Model Rankings
# ============================================================================

@router.get("/models/rankings")
async def get_model_rankings(
    metric: str = Query("requests", description="Ranking metric: requests, tokens, latency, errors"),
    limit: int = Query(10, description="Maximum number of models", ge=1, le=100),
    time_range: str = Query("24h", description="Time range: 1h, 6h, 24h, 7d"),
    db: Session = Depends(get_db)
):
    """
    Get model performance rankings.

    Rank models by specified metric:
    - requests: Most requested models
    - tokens: Highest token consumption
    - latency: Average latency
    - errors: Most errors
    """
    service = MonitoringService(db)
    return service.get_model_rankings(
        metric=metric,
        limit=limit,
        time_range=time_range
    )


# ============================================================================
# API Statistics
# ============================================================================

@router.get("/api/statistics")
async def get_api_statistics(
    start: Optional[str] = Query(None, description="Start time (ISO format)"),
    end: Optional[str] = Query(None, description="End time (ISO format)"),
    hours: int = Query(24, description="Hours ago (if start/end not provided)", ge=1, le=720),
    group_by: str = Query("deployment", description="Group by: deployment, model"),
    db: Session = Depends(get_db)
):
    """
    Get detailed API request statistics grouped by deployment/model.

    Returns request counts, success rates, latency, and token consumption.
    """
    # Parse time range
    if end:
        end_time = datetime.fromisoformat(end.replace("Z", "+00:00"))
    else:
        end_time = datetime.utcnow()

    if start:
        start_time = datetime.fromisoformat(start.replace("Z", "+00:00"))
    else:
        start_time = end_time - timedelta(hours=hours)

    service = MonitoringService(db)
    data = service.get_api_statistics(
        start=start_time,
        end=end_time,
        group_by=group_by
    )

    return {
        "start": start_time.isoformat(),
        "end": end_time.isoformat(),
        "group_by": group_by,
        "data": data
    }


# ============================================================================
# Dashboard Statistics (enhanced)
# ============================================================================

@router.get("/dashboard/overview")
async def get_dashboard_overview(
    db: Session = Depends(get_db)
):
    """
    Get comprehensive dashboard overview with real-time metrics.

    Combines summary stats with GPU status and top models.
    """
    service = MonitoringService(db)

    # Get current metrics
    summary = service.get_metrics_summary(time_range="1h")

    # Get GPU details
    gpus = service.get_gpu_details()

    # Get top models
    top_models = service.get_model_rankings(metric="requests", limit=5, time_range="24h")

    return {
        "summary": summary,
        "gpus": gpus,
        "top_models": top_models,
        "timestamp": datetime.utcnow().isoformat()
    }
