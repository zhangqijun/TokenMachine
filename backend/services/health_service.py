"""
Health Check and Failover Service

Manages instance health monitoring, failover logic, and gateway configuration.
"""
import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, func

from backend.models.database import (
    GatewayConfig,
    InstanceHealth,
    InstanceHealthStatus,
    FailoverEvent,
    FailoverEventType,
    ModelInstance,
)

logger = logging.getLogger(__name__)


class HealthCheckService:
    """
    Service for managing instance health checks and failover operations.

    This service provides:
    - Gateway configuration management
    - Instance health monitoring
    - Automatic failover detection and execution
    - Health metrics collection and reporting
    """

    def __init__(self, db: Session):
        self.db = db

    # ========================================================================
    # Gateway Configuration Management
    # ========================================================================

    def get_config(self) -> Dict[str, Any]:
        """
        Get current gateway configuration.

        Returns:
            Gateway configuration dictionary
        """
        config = self.db.query(GatewayConfig).first()

        if not config:
            # Create default configuration
            config = GatewayConfig()
            self.db.add(config)
            self.db.commit()
            self.db.refresh(config)

        return {
            "id": config.id,
            "enable_dynamic_lb": config.enable_dynamic_lb,
            "schedule_strategy": config.schedule_strategy,
            "queue_threshold": config.queue_threshold,
            "response_threshold": config.response_threshold,
            "gpu_threshold": config.gpu_threshold,
            "enable_failover": config.enable_failover,
            "check_method": config.check_method,
            "check_interval": config.check_interval,
            "timeout": config.timeout,
            "fail_threshold": config.fail_threshold,
            "response_time_threshold": config.response_time_threshold,
            "error_rate_threshold": config.error_rate_threshold,
            "queue_depth_threshold": config.queue_depth_threshold,
            "auto_recover": config.auto_recover,
            "recover_threshold": config.recover_threshold,
            "updated_at": config.updated_at.isoformat() if config.updated_at else None,
        }

    def update_config(self, **kwargs) -> Dict[str, Any]:
        """
        Update gateway configuration.

        Args:
            **kwargs: Configuration fields to update

        Returns:
            Updated configuration dictionary
        """
        config = self.db.query(GatewayConfig).first()

        if not config:
            config = GatewayConfig()
            self.db.add(config)

        # Update provided fields
        for key, value in kwargs.items():
            if hasattr(config, key):
                setattr(config, key, value)

        self.db.commit()
        self.db.refresh(config)

        return self.get_config()

    # ========================================================================
    # Instance Health Management
    # ========================================================================

    def list_instance_health(self, status: Optional[InstanceHealthStatus] = None) -> List[InstanceHealth]:
        """
        List health status of all instances.

        Args:
            status: Optional filter by health status

        Returns:
            List of InstanceHealth records
        """
        query = self.db.query(InstanceHealth)

        if status:
            query = query.filter(InstanceHealth.status == status)

        return query.all()

    def get_instance_health(self, instance_id: int) -> Optional[InstanceHealth]:
        """
        Get health status for a specific instance.

        Args:
            instance_id: Model instance ID

        Returns:
            InstanceHealth record or None
        """
        return (
            self.db.query(InstanceHealth)
            .filter(InstanceHealth.model_instance_id == instance_id)
            .first()
        )

    async def check_instance_health(self, instance_id: int) -> Dict[str, Any]:
        """
        Perform health check for a specific instance.

        This method:
        1. Retrieves the instance
        2. Checks current health metrics
        3. Updates health status based on thresholds
        4. Records failover event if needed

        Args:
            instance_id: Model instance ID

        Returns:
            Health check result dictionary
        """
        # Get instance
        instance = self.db.query(ModelInstance).filter(ModelInstance.id == instance_id).first()
        if not instance:
            logger.error(f"Instance {instance_id} not found")
            return {"instance_id": instance_id, "status": "error", "message": "Instance not found"}

        # Get or create health record
        health = self.get_instance_health(instance_id)
        if not health:
            health = InstanceHealth(
                model_instance_id=instance_id,
                status=InstanceHealthStatus.HEALTHY,
            )
            self.db.add(health)

        # Get gateway config for thresholds
        config = self.db.query(GatewayConfig).first()
        if not config:
            config = GatewayConfig()

        # Check health based on metrics
        is_healthy = True
        reasons = []

        # Check response time
        if health.response_time_ms > config.response_time_threshold:
            is_healthy = False
            reasons.append(f"Response time {health.response_time_ms}ms exceeds threshold {config.response_time_threshold}ms")

        # Check error rate
        if float(health.error_rate) > config.error_rate_threshold:
            is_healthy = False
            reasons.append(f"Error rate {health.error_rate}% exceeds threshold {config.error_rate_threshold}%")

        # Check queue depth
        if health.queue_depth > config.queue_depth_threshold:
            is_healthy = False
            reasons.append(f"Queue depth {health.queue_depth} exceeds threshold {config.queue_depth_threshold}")

        # Update health status
        old_status = health.status
        if is_healthy:
            health.status = InstanceHealthStatus.HEALTHY
            health.consecutive_success_count += 1
            health.fail_count = 0
        else:
            health.fail_count += 1
            health.consecutive_success_count = 0

            if health.fail_count >= config.fail_threshold:
                health.status = InstanceHealthStatus.FAILED
            else:
                health.status = InstanceHealthStatus.WARNING

        health.last_check_at = datetime.now()

        # Trigger failover if instance failed
        if health.status == InstanceHealthStatus.FAILED and old_status != InstanceHealthStatus.FAILED:
            if config.enable_failover:
                await self._trigger_auto_failover(instance, health, reasons)

        self.db.commit()
        self.db.refresh(health)

        return {
            "instance_id": instance_id,
            "status": health.status.value,
            "is_healthy": is_healthy,
            "reasons": reasons if not is_healthy else [],
            "metrics": {
                "queue_depth": health.queue_depth,
                "response_time_ms": health.response_time_ms,
                "gpu_utilization": float(health.gpu_utilization),
                "error_rate": float(health.error_rate),
            },
            "fail_count": health.fail_count,
            "last_check_at": health.last_check_at.isoformat(),
        }

    async def _trigger_auto_failover(self, failed_instance: ModelInstance, health: InstanceHealth, reasons: List[str]):
        """
        Trigger automatic failover from a failed instance.

        Args:
            failed_instance: The failed instance
            health: Health record for the failed instance
            reasons: List of reasons for failure
        """
        # Find healthy instances with the same model
        healthy_instances = (
            self.db.query(ModelInstance)
            .join(InstanceHealth, ModelInstance.id == InstanceHealth.model_instance_id)
            .filter(
                ModelInstance.model_id == failed_instance.model_id,
                ModelInstance.id != failed_instance.id,
                InstanceHealth.status == InstanceHealthStatus.HEALTHY,
                ModelInstance.status == "running",
            )
            .all()
        )

        if not healthy_instances:
            logger.warning(f"No healthy instances available for failover from instance {failed_instance.id}")
            return

        # Select instance with lowest load
        target_instance = min(healthy_instances, key=lambda i: i.model_id)

        # Create failover event
        event = FailoverEvent(
            source_instance_id=failed_instance.id,
            target_instance_id=target_instance.id,
            event_type=FailoverEventType.HEALTH_CHECK_FAILED,
            reason=f"Automatic failover: {', '.join(reasons)}",
            triggered_by="auto",
        )
        self.db.add(event)
        self.db.commit()

        logger.info(
            f"Auto failover triggered: instance {failed_instance.id} -> {target_instance.id} "
            f"(reasons: {reasons})"
        )

    async def update_instance_metrics(
        self,
        instance_id: int,
        queue_depth: Optional[int] = None,
        response_time_ms: Optional[int] = None,
        gpu_utilization: Optional[float] = None,
        error_rate: Optional[float] = None,
    ) -> InstanceHealth:
        """
        Update real-time metrics for an instance.

        Args:
            instance_id: Model instance ID
            queue_depth: Current queue depth
            response_time_ms: Average response time in milliseconds
            gpu_utilization: GPU utilization percentage (0-100)
            error_rate: Error rate percentage (0-100)

        Returns:
            Updated InstanceHealth record
        """
        health = self.get_instance_health(instance_id)

        if not health:
            health = InstanceHealth(
                model_instance_id=instance_id,
                status=InstanceHealthStatus.HEALTHY,
            )
            self.db.add(health)

        # Update metrics
        if queue_depth is not None:
            health.queue_depth = queue_depth
        if response_time_ms is not None:
            health.response_time_ms = response_time_ms
        if gpu_utilization is not None:
            health.gpu_utilization = gpu_utilization
        if error_rate is not None:
            health.error_rate = error_rate

        health.updated_at = datetime.now()

        self.db.commit()
        self.db.refresh(health)

        return health

    async def check_all_instances(self) -> List[Dict[str, Any]]:
        """
        Perform health check for all instances.

        Returns:
            List of health check results for all instances
        """
        instances = self.db.query(ModelInstance).filter(ModelInstance.status == "running").all()

        results = []
        for instance in instances:
            try:
                result = await self.check_instance_health(instance.id)
                results.append(result)
            except Exception as e:
                logger.error(f"Error checking health for instance {instance.id}: {e}")
                results.append({
                    "instance_id": instance.id,
                    "status": "error",
                    "message": str(e),
                })

        return results

    # ========================================================================
    # Health Statistics and Monitoring
    # ========================================================================

    def get_health_summary(self) -> Dict[str, Any]:
        """
        Get health summary statistics.

        Returns:
            Health summary dictionary
        """
        total = self.db.query(InstanceHealth).count()
        healthy = self.db.query(InstanceHealth).filter(InstanceHealth.status == InstanceHealthStatus.HEALTHY).count()
        warning = self.db.query(InstanceHealth).filter(InstanceHealth.status == InstanceHealthStatus.WARNING).count()
        failed = self.db.query(InstanceHealth).filter(InstanceHealth.status == InstanceHealthStatus.FAILED).count()

        # Get average metrics
        avg_metrics = self.db.query(
            func.avg(InstanceHealth.response_time_ms).label("avg_response_time"),
            func.avg(InstanceHealth.queue_depth).label("avg_queue_depth"),
            func.avg(InstanceHealth.gpu_utilization).label("avg_gpu_util"),
            func.avg(InstanceHealth.error_rate).label("avg_error_rate"),
        ).first()

        return {
            "total_instances": total,
            "healthy": healthy,
            "warning": warning,
            "failed": failed,
            "avg_response_time_ms": float(avg_metrics.avg_response_time or 0),
            "avg_queue_depth": float(avg_metrics.avg_queue_depth or 0),
            "avg_gpu_utilization": float(avg_metrics.avg_gpu_util or 0),
            "avg_error_rate": float(avg_metrics.avg_error_rate or 0),
        }

    def get_unhealthy_instances(self) -> List[Dict[str, Any]]:
        """
        Get all unhealthy instances with details.

        Returns:
            List of unhealthy instance details
        """
        unhealthy_health_records = (
            self.db.query(InstanceHealth)
            .filter(
                or_(
                    InstanceHealth.status == InstanceHealthStatus.WARNING,
                    InstanceHealth.status == InstanceHealthStatus.FAILED,
                )
            )
            .all()
        )

        result = []
        for health in unhealthy_health_records:
            instance = (
                self.db.query(ModelInstance)
                .filter(ModelInstance.id == health.model_instance_id)
                .first()
            )

            if instance:
                result.append({
                    "instance_id": instance.id,
                    "model_id": instance.model_id,
                    "endpoint": instance.endpoint,
                    "status": health.status.value,
                    "fail_count": health.fail_count,
                    "queue_depth": health.queue_depth,
                    "response_time_ms": health.response_time_ms,
                    "gpu_utilization": float(health.gpu_utilization),
                    "error_rate": float(health.error_rate),
                    "last_check_at": health.last_check_at.isoformat(),
                })

        return result

    # ========================================================================
    # Failover Event Management
    # ========================================================================

    def get_failover_events(self, limit: int = 50, offset: int = 0) -> List[FailoverEvent]:
        """
        Get failover event history.

        Args:
            limit: Maximum number of events to return
            offset: Number of events to skip

        Returns:
            List of FailoverEvent records
        """
        return (
            self.db.query(FailoverEvent)
            .order_by(desc(FailoverEvent.created_at))
            .limit(limit)
            .offset(offset)
            .all()
        )

    async def manual_failover(
        self,
        source_instance_id: int,
        target_instance_id: int,
        reason: str,
    ) -> FailoverEvent:
        """
        Manually trigger a failover from source to target instance.

        Args:
            source_instance_id: Source instance ID to failover from
            target_instance_id: Target instance ID to failover to
            reason: Reason for manual failover

        Returns:
            Created FailoverEvent record
        """
        # Verify instances exist
        source = self.db.query(ModelInstance).filter(ModelInstance.id == source_instance_id).first()
        target = self.db.query(ModelInstance).filter(ModelInstance.id == target_instance_id).first()

        if not source:
            raise ValueError(f"Source instance {source_instance_id} not found")
        if not target:
            raise ValueError(f"Target instance {target_instance_id} not found")

        # Create failover event
        event = FailoverEvent(
            source_instance_id=source_instance_id,
            target_instance_id=target_instance_id,
            event_type=FailoverEventType.MANUAL,
            reason=reason,
            triggered_by="manual",
        )
        self.db.add(event)
        self.db.commit()
        self.db.refresh(event)

        logger.info(
            f"Manual failover triggered: instance {source_instance_id} -> {target_instance_id} "
            f"(reason: {reason})"
        )

        return event
