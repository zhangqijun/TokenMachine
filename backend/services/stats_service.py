"""
Statistics service for dashboard and monitoring.
"""
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, case
from datetime import datetime, date, timedelta

from models.database import (
    Worker, Model, Deployment, ModelInstance, GPUDevice,
    UsageLog, Cluster, Organization, APIKey,
    WorkerStatus, DeploymentStatus, ModelInstanceStatus, GPUDeviceState
)


class StatsService:
    """Service for generating statistics and metrics."""

    def __init__(self, db: Session):
        self.db = db

    # ========================================================================
    # Dashboard Statistics
    # ========================================================================

    def get_dashboard_stats(self) -> Dict[str, Any]:
        """
        Get comprehensive dashboard statistics.

        Returns:
            Dictionary with dashboard statistics
        """
        today = date.today()
        today_start = datetime.combine(today, datetime.min.time())
        month_start = today.replace(day=1)

        # GPU statistics
        gpu_total = self.db.query(GPUDevice).count()
        gpu_available = self.db.query(GPUDevice).filter(
            GPUDevice.state == GPUDeviceState.AVAILABLE
        ).count()
        gpu_in_use = gpu_total - gpu_available

        # Model statistics
        model_total = self.db.query(Model).count()
        model_ready = self.db.query(Model).filter(
            Model.status == "ready"
        ).count()

        # Deployment statistics
        deployment_total = self.db.query(Deployment).count()
        deployment_running = self.db.query(Deployment).filter(
            Deployment.status == DeploymentStatus.RUNNING
        ).count()

        # Worker statistics
        worker_total = self.db.query(Worker).count()

        # Count workers by status
        worker_status_counts = self.db.query(
            Worker.status, func.count(Worker.id)
        ).group_by(Worker.status).all()

        worker_by_status = {}
        for status, count in worker_status_counts:
            status_str = status.value if hasattr(status, 'value') else str(status)
            worker_by_status[status_str] = count

        worker_running = worker_by_status.get("ready", 0) + worker_by_status.get("busy", 0)

        # Cluster statistics
        cluster_total = self.db.query(Cluster).count()

        # Organization statistics
        org_total = self.db.query(Organization).count()

        # API call statistics (today)
        api_calls_today = self.db.query(UsageLog).filter(
            UsageLog.created_at >= today_start
        ).count()

        api_calls_success = self.db.query(UsageLog).filter(
            and_(
                UsageLog.created_at >= today_start,
                UsageLog.status == "success"
            )
        ).count()

        api_calls_error = api_calls_today - api_calls_success

        # Average latency (today)
        avg_latency = self.db.query(
            func.avg(UsageLog.latency_ms)
        ).filter(
            and_(
                UsageLog.created_at >= today_start,
                UsageLog.status == "success"
            )
        ).scalar() or 0

        # Token usage statistics
        token_today = self.db.query(
            func.sum(UsageLog.input_tokens + UsageLog.output_tokens)
        ).filter(
            UsageLog.created_at >= today_start
        ).scalar() or 0

        token_month = self.db.query(
            func.sum(UsageLog.input_tokens + UsageLog.output_tokens)
        ).filter(
            UsageLog.created_at >= month_start
        ).scalar() or 0

        # Total tokens all time
        token_total = self.db.query(
            func.sum(UsageLog.input_tokens + UsageLog.output_tokens)
        ).scalar() or 0

        return {
            "gpu": {
                "total": gpu_total,
                "available": gpu_available,
                "in_use": gpu_in_use
            },
            "model": {
                "total": model_total,
                "ready": model_ready
            },
            "deployment": {
                "total": deployment_total,
                "running": deployment_running
            },
            "worker": {
                "total": worker_total,
                "running": worker_running,
                "by_status": worker_by_status
            },
            "cluster": {
                "total": cluster_total
            },
            "organization": {
                "total": org_total
            },
            "api_calls": {
                "today": api_calls_today,
                "success": api_calls_success,
                "error": api_calls_error,
                "avg_latency_ms": float(avg_latency) if avg_latency else 0
            },
            "token_usage": {
                "today": token_today,
                "this_month": token_month,
                "total": token_total
            }
        }

    # ========================================================================
    # System Health
    # ========================================================================

    def get_system_health(self) -> Dict[str, Any]:
        """
        Get overall system health status.

        Returns:
            Dictionary with health status
        """
        # Check worker health
        timeout_threshold = datetime.utcnow() - timedelta(seconds=60)

        worker_total = self.db.query(Worker).count()
        worker_healthy = self.db.query(Worker).filter(
            Worker.last_heartbeat_at >= timeout_threshold
        ).count()
        worker_unhealthy = worker_total - worker_healthy

        # Determine overall worker status
        if worker_total == 0:
            worker_status = "unknown"
            worker_message = "No workers configured"
        elif worker_healthy == worker_total:
            worker_status = "healthy"
            worker_message = f"All {worker_total} workers healthy"
        elif worker_healthy > worker_total * 0.5:
            worker_status = "degraded"
            worker_message = f"{worker_healthy}/{worker_total} workers healthy"
        else:
            worker_status = "critical"
            worker_message = f"Only {worker_healthy}/{worker_total} workers healthy"

        # Check deployment health
        deployment_total = self.db.query(Deployment).count()
        deployment_running = self.db.query(Deployment).filter(
            Deployment.status == DeploymentStatus.RUNNING
        ).count()

        # Check model instance health
        instance_total = self.db.query(ModelInstance).count()
        instance_running = self.db.query(ModelInstance).filter(
            ModelInstance.status == ModelInstanceStatus.RUNNING
        ).count()

        # Determine overall status
        if worker_status == "healthy":
            overall_status = "healthy"
        elif worker_status == "degraded":
            overall_status = "degraded"
        else:
            overall_status = "critical"

        return {
            "status": overall_status,
            "timestamp": datetime.utcnow().isoformat(),
            "components": {
                "workers": {
                    "status": worker_status,
                    "message": worker_message,
                    "total": worker_total,
                    "healthy": worker_healthy,
                    "unhealthy": worker_unhealthy
                },
                "deployments": {
                    "total": deployment_total,
                    "running": deployment_running
                },
                "model_instances": {
                    "total": instance_total,
                    "running": instance_running
                }
            }
        }

    # ========================================================================
    # Resource Utilization
    # ========================================================================

    def get_resource_utilization(self) -> Dict[str, Any]:
        """
        Get current resource utilization.

        Returns:
            Dictionary with resource utilization
        """
        # GPU utilization
        gpu_devices = self.db.query(GPUDevice).all()

        gpu_utilization = {
            "total_devices": len(gpu_devices),
            "available": 0,
            "in_use": 0,
            "error": 0,
            "avg_memory_utilization": 0.0,
            "avg_core_utilization": 0.0
        }

        total_mem_util = 0.0
        total_core_util = 0.0
        devices_with_stats = 0

        for gpu in gpu_devices:
            state = gpu.state.value if hasattr(gpu.state, 'value') else str(gpu.state)
            if state == "available":
                gpu_utilization["available"] += 1
            elif state == "in_use":
                gpu_utilization["in_use"] += 1
            else:
                gpu_utilization["error"] += 1

            if gpu.memory_utilization_rate is not None:
                total_mem_util += float(gpu.memory_utilization_rate)
                devices_with_stats += 1
            if gpu.core_utilization_rate is not None:
                total_core_util += float(gpu.core_utilization_rate)

        if devices_with_stats > 0:
            gpu_utilization["avg_memory_utilization"] = total_mem_util / devices_with_stats
            gpu_utilization["avg_core_utilization"] = total_core_util / devices_with_stats

        # Worker utilization (based on status)
        worker_stats = self.db.query(
            Worker.status, func.count(Worker.id)
        ).group_by(Worker.status).all()

        worker_utilization = {
            "total": 0,
            "ready": 0,
            "busy": 0,
            "allocating": 0,
            "other": 0
        }

        for status, count in worker_stats:
            status_str = status.value if hasattr(status, 'value') else str(status)
            worker_utilization["total"] += count

            if status_str in ["ready", "busy", "allocating"]:
                worker_utilization[status_str] = count
            else:
                worker_utilization["other"] += count

        # Calculate utilization percentage
        if worker_utilization["total"] > 0:
            worker_utilization["utilization_percent"] = int(
                (worker_utilization["busy"] + worker_utilization["allocating"]) /
                worker_utilization["total"] * 100
            )
        else:
            worker_utilization["utilization_percent"] = 0

        return {
            "gpu": gpu_utilization,
            "worker": worker_utilization
        }

    # ========================================================================
    # Top Statistics
    # ========================================================================

    def get_top_models(self, limit: int = 10) -> list:
        """
        Get top models by usage.

        Args:
            limit: Maximum number of models to return

        Returns:
            List of top models
        """
        # Get models sorted by usage count
        model_usage = self.db.query(
            Model.id,
            Model.name,
            Model.version,
            Model.category,
            func.count(UsageLog.id).label("usage_count"),
            func.sum(UsageLog.input_tokens + UsageLog.output_tokens).label("total_tokens")
        ).join(
            Deployment, Model.id == Deployment.model_id
        ).join(
            UsageLog, Deployment.id == UsageLog.deployment_id
        ).group_by(
            Model.id, Model.name, Model.version, Model.category
        ).order_by(
            func.count(UsageLog.id).desc()
        ).limit(limit).all()

        return [
            {
                "id": m.id,
                "name": m.name,
                "version": m.version,
                "category": m.category.value if hasattr(m.category, 'value') else str(m.category),
                "usage_count": m.usage_count,
                "total_tokens": m.total_tokens or 0
            }
            for m in model_usage
        ]

    def get_top_deployments(self, limit: int = 10) -> list:
        """
        Get top deployments by usage.

        Args:
            limit: Maximum number of deployments to return

        Returns:
            List of top deployments
        """
        deployment_usage = self.db.query(
            Deployment.id,
            Deployment.name,
            Deployment.status,
            Model.name.label("model_name"),
            func.count(UsageLog.id).label("usage_count"),
            func.sum(UsageLog.input_tokens + UsageLog.output_tokens).label("total_tokens"),
            func.avg(UsageLog.latency_ms).label("avg_latency")
        ).join(
            Model, Deployment.model_id == Model.id
        ).join(
            UsageLog, Deployment.id == UsageLog.deployment_id
        ).group_by(
            Deployment.id, Deployment.name, Deployment.status, Model.name
        ).order_by(
            func.count(UsageLog.id).desc()
        ).limit(limit).all()

        return [
            {
                "id": d.id,
                "name": d.name,
                "model_name": d.model_name,
                "status": d.status.value if hasattr(d.status, 'value') else str(d.status),
                "usage_count": d.usage_count,
                "total_tokens": d.total_tokens or 0,
                "avg_latency_ms": float(d.avg_latency) if d.avg_latency else 0
            }
            for d in deployment_usage
        ]

    def get_top_organizations(self, limit: int = 10) -> list:
        """
        Get top organizations by token usage.

        Args:
            limit: Maximum number of organizations to return

        Returns:
            List of top organizations
        """
        org_usage = self.db.query(
            Organization.id,
            Organization.name,
            Organization.plan,
            func.sum(APIKey.tokens_used).label("total_tokens")
        ).join(
            APIKey, Organization.id == APIKey.organization_id
        ).group_by(
            Organization.id, Organization.name, Organization.plan
        ).order_by(
            func.sum(APIKey.tokens_used).desc()
        ).limit(limit).all()

        return [
            {
                "id": o.id,
                "name": o.name,
                "plan": o.plan.value if hasattr(o.plan, 'value') else str(o.plan),
                "total_tokens": o.total_tokens or 0
            }
            for o in org_usage
        ]

    # ========================================================================
    # Time Series Statistics
    # ========================================================================

    def get_time_series_stats(
        self,
        metric: str,
        days: int = 30
    ) -> list:
        """
        Get time series data for a metric.

        Args:
            metric: Metric to track (tokens, requests, errors, latency)
            days: Number of days to retrieve

        Returns:
            List of daily values
        """
        end_date = date.today()
        start_date = end_date - timedelta(days=days - 1)

        if metric == "tokens":
            query = self.db.query(
                func.date(UsageLog.created_at).label("date"),
                func.sum(UsageLog.input_tokens + UsageLog.output_tokens).label("value")
            ).filter(
                UsageLog.created_at >= datetime.combine(start_date, datetime.min.time())
            ).group_by(
                func.date(UsageLog.created_at)
            ).all()

        elif metric == "requests":
            query = self.db.query(
                func.date(UsageLog.created_at).label("date"),
                func.count(UsageLog.id).label("value")
            ).filter(
                UsageLog.created_at >= datetime.combine(start_date, datetime.min.time())
            ).group_by(
                func.date(UsageLog.created_at)
            ).all()

        elif metric == "errors":
            query = self.db.query(
                func.date(UsageLog.created_at).label("date"),
                func.count(UsageLog.id).label("value")
            ).filter(
                and_(
                    UsageLog.created_at >= datetime.combine(start_date, datetime.min.time()),
                    UsageLog.status == "error"
                )
            ).group_by(
                func.date(UsageLog.created_at)
            ).all()

        elif metric == "latency":
            query = self.db.query(
                func.date(UsageLog.created_at).label("date"),
                func.avg(UsageLog.latency_ms).label("value")
            ).filter(
                and_(
                    UsageLog.created_at >= datetime.combine(start_date, datetime.min.time()),
                    UsageLog.status == "success"
                )
            ).group_by(
                func.date(UsageLog.created_at)
            ).all()
        else:
            return []

        return [
            {
                "date": str(row.date),
                "value": float(row.value) if row.value else 0
            }
            for row in query
        ]
