"""
Gateway router and load balancer for request routing.

This module provides the core gateway functionality for routing
incoming requests to appropriate model instances based on
routing strategies and load balancing policies.
"""
from typing import Optional, List, Dict, Any
from loguru import logger
from sqlalchemy.orm import Session

from backend.models.database import (
    ModelInstance, ApiKey, RoutingStrategy, RoutingMode,
    InstanceHealth, InstanceHealthStatus, GatewayConfig
)
from backend.services.routing_service import RoutingService
from backend.services.health_service import HealthCheckService


class LoadBalancer:
    """Load balancer for distributing requests across instances."""

    def __init__(self, db: Session):
        """Initialize load balancer."""
        self.db = db
        self.health_service = HealthCheckService(db)
        self.config = self.health_service.get_config()

    async def select_instance(
        self,
        instances: List[ModelInstance],
        strategy: str = "queue"
    ) -> Optional[ModelInstance]:
        """
        Select the best instance based on load balancing strategy.

        Args:
            instances: List of candidate instances
            strategy: Load balancing strategy (queue/response/resource/combined)

        Returns:
            Selected instance or None
        """
        if not instances:
            return None

        # Filter healthy instances
        healthy_instances = await self._filter_healthy(instances)
        if not healthy_instances:
            logger.warning("No healthy instances available")
            return None

        # Apply strategy
        if strategy == "queue":
            return await self._select_by_queue(healthy_instances)
        elif strategy == "response":
            return await self._select_by_response_time(healthy_instances)
        elif strategy == "resource":
            return await self._select_by_resource(healthy_instances)
        elif strategy == "combined":
            return await self._select_by_combined_score(healthy_instances)
        else:
            logger.warning(f"Unknown strategy: {strategy}, using queue")
            return await self._select_by_queue(healthy_instances)

    async def _filter_healthy(self, instances: List[ModelInstance]) -> List[ModelInstance]:
        """Filter out unhealthy instances."""
        healthy = []
        for instance in instances:
            health = self.health_service.get_instance_health(instance.id)
            if not health or health.status == InstanceHealthStatus.HEALTHY:
                healthy.append(instance)
            elif health.status == InstanceHealthStatus.WARNING:
                # Include warning instances if no healthy ones
                healthy.append(instance)
        return healthy

    async def _select_by_queue(self, instances: List[ModelInstance]) -> Optional[ModelInstance]:
        """Select instance with shortest queue."""
        best = None
        min_queue = float('inf')

        for instance in instances:
            health = self.health_service.get_instance_health(instance.id)
            queue_depth = health.queue_depth if health else 0

            if queue_depth < min_queue:
                min_queue = queue_depth
                best = instance

        return best

    async def _select_by_response_time(self, instances: List[ModelInstance]) -> Optional[ModelInstance]:
        """Select instance with fastest response time."""
        best = None
        min_time = float('inf')

        for instance in instances:
            health = self.health_service.get_instance_health(instance.id)
            response_time = health.response_time_ms if health else 0

            if response_time < min_time:
                min_time = response_time
                best = instance

        return best

    async def _select_by_resource(self, instances: List[ModelInstance]) -> Optional[ModelInstance]:
        """Select instance with lowest GPU utilization."""
        best = None
        min_util = float('inf')

        for instance in instances:
            health = self.health_service.get_instance_health(instance.id)
            utilization = float(health.gpu_utilization) if health and health.gpu_utilization else 0

            if utilization < min_util:
                min_util = utilization
                best = instance

        return best

    async def _select_by_combined_score(self, instances: List[ModelInstance]) -> Optional[ModelInstance]:
        """Select instance based on combined score."""
        config = self.health_service.get_config()

        best = None
        best_score = float('inf')

        for instance in instances:
            health = self.health_service.get_instance_health(instance.id)

            if not health:
                continue

            # Calculate normalized score
            score = 0.0

            # Queue depth score (0-100)
            queue_score = (health.queue_depth / config.queue_threshold) * 100
            score += queue_score * 0.4

            # Response time score (0-100)
            response_score = (health.response_time_ms / config.response_threshold) * 100
            score += response_score * 0.3

            # GPU utilization score (0-100)
            util_score = (float(health.gpu_utilization) / config.gpu_threshold) * 100
            score += util_score * 0.3

            if score < best_score:
                best_score = score
                best = instance

        return best


class GatewayRouter:
    """
    Gateway router for incoming request routing.

    This is the main entry point for routing incoming API requests
    to the appropriate model instances based on routing strategies
    and load balancing policies.
    """

    def __init__(self, db: Session):
        """Initialize gateway router."""
        self.db = db
        self.routing_service = RoutingService(db)
        self.load_balancer = LoadBalancer(db)
        self.health_service = HealthCheckService(db)
        self.config = self.health_service.get_config()

    async def route_request(
        self,
        api_key_id: int,
        model_name: str
    ) -> Optional[ModelInstance]:
        """
        Route a request to the appropriate model instance.

        Args:
            api_key_id: API key ID from the request
            model_name: Requested model name

        Returns:
            Selected ModelInstance or None

        Raises:
            ValueError: If routing fails
        """
        # Get API key to verify it exists
        api_key = self.db.query(ApiKey).filter(
            ApiKey.id == api_key_id,
            ApiKey.is_active == True
        ).first()
        if not api_key:
            logger.warning(f"API key {api_key_id} not found or inactive")
            return None

        # Use routing service to select instance
        try:
            instance = await self.routing_service.select_instance(
                api_key_id=api_key_id,
                model_name=model_name
            )

            if not instance:
                # Fallback: try to find any running instance for this model
                instance = await self._fallback_routing(model_name)

            return instance

        except Exception as e:
            logger.error(f"Routing error: {e}")
            # Try fallback routing
            return await self._fallback_routing(model_name)

    async def _fallback_routing(
        self,
        model_name: str
    ) -> Optional[ModelInstance]:
        """
        Fallback routing when no routing strategy is configured.

        Args:
            model_name: Requested model name

        Returns:
            Selected ModelInstance or None
        """
        # Find running instances for the model
        instances = self.db.query(ModelInstance).filter(
            ModelInstance.name == model_name,
            ModelInstance.status == "running"
        ).all()

        if not instances:
            logger.warning(f"No running instances found for model '{model_name}'")
            return None

        # Use load balancer to select best instance
        config = self.health_service.get_config()
        selected = await self.load_balancer.select_instance(
            instances=instances,
            strategy=config.schedule_strategy
        )

        if selected:
            logger.info(f"Fallback routing: {model_name} -> {selected.name}")
        else:
            logger.warning(f"Fallback routing failed for model '{model_name}'")

        return selected

    async def route_with_load_balancing(
        self,
        model_name: str,
        instances: Optional[List[ModelInstance]] = None
    ) -> Optional[ModelInstance]:
        """
        Route request using load balancing only (no routing strategy).

        Args:
            model_name: Requested model name
            instances: Optional list of candidate instances

        Returns:
            Selected ModelInstance or None
        """
        if not instances:
            instances = self.db.query(ModelInstance).filter(
                ModelInstance.name == model_name,
                ModelInstance.status == "running"
            ).all()

        if not instances:
            return None

        config = self.health_service.get_config()
        return await self.load_balancer.select_instance(
            instances=instances,
            strategy=config.schedule_strategy
        )

    def get_routing_stats(self) -> Dict[str, Any]:
        """Get routing statistics."""
        # Count instances by status
        from backend.models.database import ModelInstanceStatus

        total_instances = self.db.query(ModelInstance).count()
        running_instances = self.db.query(ModelInstance).filter(
            ModelInstance.status == ModelInstanceStatus.RUNNING
        ).count()

        # Health summary
        health_summary = self.health_service.get_health_summary()

        # Routing strategies
        routing_service = RoutingService(self.db)
        strategies = routing_service.list_strategies(enabled_only=True)

        return {
            "total_instances": total_instances,
            "running_instances": running_instances,
            "health_summary": health_summary,
            "active_strategies": len(strategies),
            "load_balancing_enabled": self.config.enable_dynamic_lb,
            "schedule_strategy": self.config.schedule_strategy
        }


# Singleton instance
_gateway_router: Optional[GatewayRouter] = None


def get_gateway_router(db: Session) -> GatewayRouter:
    """Get or create the gateway router singleton."""
    global _gateway_router
    if _gateway_router is None:
        _gateway_router = GatewayRouter(db)
    return _gateway_router
