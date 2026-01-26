"""
Monitoring service for querying and aggregating metrics.
"""
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, desc
from loguru import logger

from backend.models.database import (
    UsageLog, Deployment, Model, GPUDevice, Worker,
    DeploymentStatus, GPUDeviceState
)


class MonitoringService:
    """Service for monitoring metrics and analytics."""

    def __init__(self, db: Session):
        self.db = db

    # ========================================================================
    # Real-time Metrics Summary
    # ========================================================================

    def get_metrics_summary(self, time_range: str = "1h") -> Dict[str, Any]:
        """
        Get real-time metrics summary.

        Args:
            time_range: Time range for metrics (5m, 15m, 1h, 6h, 24h, 7d)

        Returns:
            Dictionary with metrics summary
        """
        # Calculate time range
        time_delta = self._parse_time_range(time_range)
        start_time = datetime.utcnow() - time_delta

        # API metrics from UsageLog
        api_stats = self._get_api_stats(start_time)

        # GPU metrics
        gpu_stats = self._get_gpu_stats()

        # Token consumption
        token_stats = self._get_token_stats(start_time)

        return {
            "api": api_stats,
            "gpu": gpu_stats,
            "tokens": token_stats,
            "timestamp": datetime.utcnow().isoformat()
        }

    def _get_api_stats(self, start_time: datetime) -> Dict[str, Any]:
        """Get API statistics."""
        # Total requests
        total_requests = self.db.query(UsageLog).filter(
            UsageLog.created_at >= start_time
        ).count()

        # Successful requests
        successful_requests = self.db.query(UsageLog).filter(
            and_(
                UsageLog.created_at >= start_time,
                UsageLog.status == "success"
            )
        ).count()

        # Error rate
        error_rate = 0
        if total_requests > 0:
            error_rate = ((total_requests - successful_requests) / total_requests) * 100

        # Latency statistics
        latency_stats = self.db.query(
            func.avg(UsageLog.latency_ms),
            func.max(UsageLog.latency_ms),
            func.min(UsageLog.latency_ms)
        ).filter(
            and_(
                UsageLog.created_at >= start_time,
                UsageLog.status == "success"
            )
        ).first()

        avg_latency = float(latency_stats[0]) if latency_stats[0] else 0
        max_latency = float(latency_stats[1]) if latency_stats[1] else 0
        min_latency = float(latency_stats[2]) if latency_stats[2] else 0

        # Calculate QPS (queries per second)
        duration_seconds = (datetime.utcnow() - start_time).total_seconds()
        qps = total_requests / duration_seconds if duration_seconds > 0 else 0

        # Get percentiles from recent logs
        recent_latencies = self.db.query(UsageLog.latency_ms).filter(
            and_(
                UsageLog.created_at >= start_time,
                UsageLog.status == "success",
                UsageLog.latency_ms.isnot(None)
            )
        ).order_by(UsageLog.latency_ms).all()

        latencies = [l[0] for l in recent_latencies]
        p95_latency = self._percentile(latencies, 95)
        p99_latency = self._percentile(latencies, 99)

        return {
            "qps": round(qps, 2),
            "peak_qps": round(qps * 1.5, 2),  # Estimate peak
            "avg_latency_ms": round(avg_latency, 2),
            "p95_latency_ms": round(p95_latency, 2),
            "p99_latency_ms": round(p99_latency, 2),
            "min_latency_ms": round(min_latency, 2),
            "max_latency_ms": round(max_latency, 2),
            "error_rate": round(error_rate, 2),
            "total_requests": total_requests,
            "successful_requests": successful_requests,
            "failed_requests": total_requests - successful_requests
        }

    def _get_gpu_stats(self) -> Dict[str, Any]:
        """Get GPU statistics."""
        gpus = self.db.query(GPUDevice).all()

        total_gpus = len(gpus)
        available_gpus = sum(1 for g in gpus if g.state == GPUDeviceState.AVAILABLE)
        in_use_gpus = sum(1 for g in gpus if g.state == GPUDeviceState.IN_USE)

        # Calculate average utilization
        utilizations = [float(g.core_utilization_rate) for g in gpus
                       if g.core_utilization_rate is not None]
        avg_utilization = sum(utilizations) / len(utilizations) if utilizations else 0

        # Calculate average memory utilization
        memory_utilizations = [float(g.memory_utilization_rate) for g in gpus
                              if g.memory_utilization_rate is not None]
        avg_memory_util = sum(memory_utilizations) / len(memory_utilizations) if memory_utilizations else 0

        # Temperature statistics
        temperatures = [float(g.temperature) for g in gpus if g.temperature is not None]
        avg_temperature = sum(temperatures) / len(temperatures) if temperatures else 0
        max_temperature = max(temperatures) if temperatures else 0

        return {
            "total": total_gpus,
            "available": available_gpus,
            "in_use": in_use_gpus,
            "utilization_percent": round(avg_utilization, 2),
            "memory_utilization_percent": round(avg_memory_util, 2),
            "avg_temperature_celsius": round(avg_temperature, 2),
            "max_temperature_celsius": round(max_temperature, 2)
        }

    def _get_token_stats(self, start_time: datetime) -> Dict[str, Any]:
        """Get token consumption statistics."""
        token_result = self.db.query(
            func.sum(UsageLog.input_tokens + UsageLog.output_tokens).label("total")
        ).filter(
            UsageLog.created_at >= start_time
        ).first()

        total_tokens = int(token_result.total) if token_result.total else 0

        # Per-minute average
        duration_minutes = (datetime.utcnow() - start_time).total_seconds() / 60
        tokens_per_minute = int(total_tokens / duration_minutes) if duration_minutes > 0 else 0

        return {
            "total": total_tokens,
            "per_minute": tokens_per_minute,
            "per_hour": tokens_per_minute * 60
        }

    # ========================================================================
    # Time Series Data
    # ========================================================================

    def get_timeseries_data(
        self,
        metrics: List[str],
        start: datetime,
        end: datetime,
        interval: str = "5m"
    ) -> List[Dict[str, Any]]:
        """
        Get time series data for specified metrics.

        Args:
            metrics: List of metric names (qps, latency, tokens, errors, gpu_util)
            start: Start time
            end: End time
            interval: Data interval (1m, 5m, 10m, 1h)

        Returns:
            List of time series data points
        """
        interval_seconds = self._parse_interval(interval)
        timestamps = []
        current = start

        # Generate time buckets
        while current <= end:
            timestamps.append(current)
            current += timedelta(seconds=interval_seconds)

        # Get data for each metric
        result = []
        for ts in timestamps:
            ts_end = ts + timedelta(seconds=interval_seconds)

            point = {"timestamp": ts.isoformat()}

            # QPS
            if "qps" in metrics:
                count = self.db.query(UsageLog).filter(
                    and_(
                        UsageLog.created_at >= ts,
                        UsageLog.created_at < ts_end
                    )
                ).count()
                point["qps"] = round(count / (interval_seconds / 60), 2) if interval_seconds > 0 else 0

            # Latency
            if "latency" in metrics:
                avg_lat = self.db.query(
                    func.avg(UsageLog.latency_ms)
                ).filter(
                    and_(
                        UsageLog.created_at >= ts,
                        UsageLog.created_at < ts_end,
                        UsageLog.status == "success"
                    )
                ).scalar()
                point["latency"] = round(float(avg_lat), 2) if avg_lat else 0

            # Tokens
            if "tokens" in metrics:
                total = self.db.query(
                    func.sum(UsageLog.input_tokens + UsageLog.output_tokens)
                ).filter(
                    and_(
                        UsageLog.created_at >= ts,
                        UsageLog.created_at < ts_end
                    )
                ).scalar()
                point["tokens"] = int(total) if total else 0

            # Errors
            if "errors" in metrics:
                errors = self.db.query(UsageLog).filter(
                    and_(
                        UsageLog.created_at >= ts,
                        UsageLog.created_at < ts_end,
                        UsageLog.status == "error"
                    )
                ).count()
                point["errors"] = errors

            result.append(point)

        return result

    # ========================================================================
    # GPU Details
    # ========================================================================

    def get_gpu_details(self) -> List[Dict[str, Any]]:
        """Get detailed GPU status."""
        gpus = self.db.query(GPUDevice).all()

        result = []
        for gpu in gpus:
            result.append({
                "id": gpu.id,
                "gpu_id": gpu.gpu_id,
                "name": gpu.device_name or gpu.gpu_id,
                "vendor": gpu.vendor,
                "memory_total_mb": gpu.memory_total,
                "memory_used_mb": gpu.memory_used,
                "memory_free_mb": gpu.memory_total - gpu.memory_used if gpu.memory_total else 0,
                "memory_utilization_percent": round(float(gpu.memory_utilization_rate), 2) if gpu.memory_utilization_rate else 0,
                "core_utilization_percent": round(float(gpu.core_utilization_rate), 2) if gpu.core_utilization_rate else 0,
                "temperature_celsius": gpu.temperature,
                "power_draw_watts": gpu.power_draw,
                "status": gpu.state.value if hasattr(gpu.state, 'value') else str(gpu.state),
                "worker_id": gpu.worker_id,
                "deployment_id": gpu.deployment_id,
                "updated_at": gpu.updated_at.isoformat() if gpu.updated_at else None
            })

        return result

    # ========================================================================
    # Model Performance Rankings
    # ========================================================================

    def get_model_rankings(
        self,
        metric: str = "requests",
        limit: int = 10,
        time_range: str = "24h"
    ) -> List[Dict[str, Any]]:
        """
        Get model performance rankings.

        Args:
            metric: Ranking metric (requests, tokens, latency, errors)
            limit: Maximum number of models
            time_range: Time range filter (1h, 6h, 24h, 7d)

        Returns:
            List of ranked models
        """
        time_delta = self._parse_time_range(time_range)
        start_time = datetime.utcnow() - time_delta

        if metric == "requests":
            query = self.db.query(
                Model.id,
                Model.name,
                Model.version,
                func.count(UsageLog.id).label("count")
            ).join(
                Deployment, Model.id == Deployment.model_id
            ).join(
                UsageLog, Deployment.id == UsageLog.deployment_id
            ).filter(
                UsageLog.created_at >= start_time
            ).group_by(
                Model.id, Model.name, Model.version
            ).order_by(
                desc("count")
            ).limit(limit)

            return [
                {
                    "model_id": row.id,
                    "model_name": row.name,
                    "model_version": row.version,
                    "request_count": row.count
                }
                for row in query.all()
            ]

        elif metric == "tokens":
            query = self.db.query(
                Model.id,
                Model.name,
                Model.version,
                func.sum(UsageLog.input_tokens + UsageLog.output_tokens).label("total_tokens")
            ).join(
                Deployment, Model.id == Deployment.model_id
            ).join(
                UsageLog, Deployment.id == UsageLog.deployment_id
            ).filter(
                UsageLog.created_at >= start_time
            ).group_by(
                Model.id, Model.name, Model.version
            ).order_by(
                desc("total_tokens")
            ).limit(limit)

            return [
                {
                    "model_id": row.id,
                    "model_name": row.name,
                    "model_version": row.version,
                    "total_tokens": int(row.total_tokens) if row.total_tokens else 0
                }
                for row in query.all()
            ]

        elif metric == "latency":
            query = self.db.query(
                Model.id,
                Model.name,
                Model.version,
                func.avg(UsageLog.latency_ms).label("avg_latency"),
                func.count(UsageLog.id).label("count")
            ).join(
                Deployment, Model.id == Deployment.model_id
            ).join(
                UsageLog, Deployment.id == UsageLog.deployment_id
            ).filter(
                and_(
                    UsageLog.created_at >= start_time,
                    UsageLog.status == "success"
                )
            ).group_by(
                Model.id, Model.name, Model.version
            ).order_by(
                desc("count")
            ).limit(limit)

            return [
                {
                    "model_id": row.id,
                    "model_name": row.name,
                    "model_version": row.version,
                    "avg_latency_ms": round(float(row.avg_latency), 2) if row.avg_latency else 0,
                    "request_count": row.count
                }
                for row in query.all()
            ]

        elif metric == "errors":
            query = self.db.query(
                Model.id,
                Model.name,
                Model.version,
                func.count(UsageLog.id).label("total"),
                func.sum(
                    func.case(
                        (UsageLog.status == "error", 1),
                        else_=0
                    )
                ).label("errors")
            ).join(
                Deployment, Model.id == Deployment.model_id
            ).join(
                UsageLog, Deployment.id == UsageLog.deployment_id
            ).filter(
                UsageLog.created_at >= start_time
            ).group_by(
                Model.id, Model.name, Model.version
            ).having(
                func.sum(
                    func.case(
                        (UsageLog.status == "error", 1),
                        else_=0
                    )
                ) > 0
            ).order_by(
                desc("errors")
            ).limit(limit)

            return [
                {
                    "model_id": row.id,
                    "model_name": row.name,
                    "model_version": row.version,
                    "total_requests": row.total,
                    "error_count": int(row.errors) if row.errors else 0,
                    "error_rate": round((row.errors / row.total) * 100, 2) if row.total > 0 else 0
                }
                for row in query.all()
            ]

        return []

    # ========================================================================
    # API Statistics Details
    # ========================================================================

    def get_api_statistics(
        self,
        start: datetime,
        end: datetime,
        group_by: str = "endpoint"
    ) -> List[Dict[str, Any]]:
        """
        Get detailed API statistics.

        Args:
            start: Start time
            end: End time
            group_by: Group by field (endpoint, model, deployment)

        Returns:
            List of API statistics
        """
        # This is a simplified version - in production you'd track actual endpoints
        # Currently grouping by deployment/model
        query = self.db.query(
            Deployment.id.label("deployment_id"),
            Deployment.name.label("deployment_name"),
            Model.name.label("model_name"),
            func.count(UsageLog.id).label("total_requests"),
            func.sum(
                func.case(
                    (UsageLog.status == "success", 1),
                    else_=0
                )
            ).label("success_count"),
            func.sum(
                func.case(
                    (UsageLog.status == "error", 1),
                    else_=0
                )
            ).label("error_count"),
            func.avg(UsageLog.latency_ms).label("avg_latency"),
            func.sum(UsageLog.input_tokens + UsageLog.output_tokens).label("total_tokens")
        ).join(
            Model, Deployment.model_id == Model.id
        ).join(
            UsageLog, Deployment.id == UsageLog.deployment_id
        ).filter(
            UsageLog.created_at >= start,
            UsageLog.created_at <= end
        ).group_by(
            Deployment.id, Deployment.name, Model.name
        ).order_by(
            desc("total_requests")
        ).all()

        return [
            {
                "deployment_id": row.deployment_id,
                "deployment_name": row.deployment_name,
                "model_name": row.model_name,
                "total_requests": row.total_requests,
                "success_count": int(row.success_count) if row.success_count else 0,
                "error_count": int(row.error_count) if row.error_count else 0,
                "success_rate": round((row.success_count / row.total_requests) * 100, 2) if row.total_requests > 0 else 0,
                "avg_latency_ms": round(float(row.avg_latency), 2) if row.avg_latency else 0,
                "total_tokens": int(row.total_tokens) if row.total_tokens else 0
            }
            for row in query
        ]

    # ========================================================================
    # Helper Methods
    # ========================================================================

    def _parse_time_range(self, time_range: str) -> timedelta:
        """Parse time range string to timedelta."""
        mapping = {
            "5m": timedelta(minutes=5),
            "15m": timedelta(minutes=15),
            "1h": timedelta(hours=1),
            "6h": timedelta(hours=6),
            "24h": timedelta(hours=24),
            "7d": timedelta(days=7),
            "30d": timedelta(days=30)
        }
        return mapping.get(time_range, timedelta(hours=1))

    def _parse_interval(self, interval: str) -> int:
        """Parse interval string to seconds."""
        mapping = {
            "1m": 60,
            "5m": 300,
            "10m": 600,
            "1h": 3600,
            "1d": 86400
        }
        return mapping.get(interval, 300)

    @staticmethod
    def _percentile(data: List[float], p: int) -> float:
        """Calculate percentile."""
        if not data:
            return 0
        k = (len(data) - 1) * (p / 100)
        f = int(k)
        c = k - f
        if f + 1 < len(data):
            return data[f] + c * (data[f + 1] - data[f])
        return data[f]
