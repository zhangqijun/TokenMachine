"""
Gateway Management API endpoints.

Provides endpoints for managing routing strategies, health checks,
failover, and load balancing configuration.
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from loguru import logger

from backend.api.deps import get_current_db, verify_admin_access, verify_api_key_auth
from backend.models.database import (
    ApiKey, RoutingMode, InstanceHealthStatus, FailoverEventType
)
from backend.models.schemas import (
    RoutingStrategyCreate, RoutingStrategyUpdate, RoutingStrategyResponse,
    ApiKeyRouteBindingCreate, ApiKeyRouteBindingResponse,
    GatewayConfigUpdate, GatewayConfigResponse,
    InstanceHealthResponse, FailoverEventResponse,
    ManualFailoverRequest
)
from backend.services.routing_service import RoutingService
from backend.services.health_service import HealthCheckService

router = APIRouter(prefix="/api/v1/gateway", tags=["Gateway"])


# ============================================================================
# Routing Strategy Endpoints
# ============================================================================

@router.get("/strategies", response_model=List[RoutingStrategyResponse])
async def list_routing_strategies(
    enabled_only: bool = False,
    db: Session = Depends(get_current_db),
    current_admin = Depends(verify_admin_access),
):
    """
    Get all routing strategies.

    Args:
        enabled_only: Only return enabled strategies

    Returns:
        List of routing strategies
    """
    service = RoutingService(db)
    strategies = service.list_strategies(enabled_only=enabled_only)
    return strategies


@router.post("/strategies", response_model=RoutingStrategyResponse)
async def create_routing_strategy(
    strategy: RoutingStrategyCreate,
    db: Session = Depends(get_current_db),
    current_admin = Depends(verify_admin_access),
):
    """
    Create a new routing strategy.

    Args:
        strategy: Routing strategy creation request

    Returns:
        Created routing strategy
    """
    service = RoutingService(db)
    try:
        result = service.create_strategy(
            name=strategy.name,
            description=strategy.description,
            mode=strategy.mode,
            rules=[r.model_dump() for r in strategy.rules],
            enable_aggregation=strategy.enable_aggregation,
            unified_endpoint=strategy.unified_endpoint,
            response_mode=strategy.response_mode
        )
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/strategies/{strategy_id}", response_model=RoutingStrategyResponse)
async def get_routing_strategy(
    strategy_id: int,
    db: Session = Depends(get_current_db),
    current_admin = Depends(verify_admin_access),
):
    """Get a specific routing strategy by ID."""
    service = RoutingService(db)
    strategy = service.get_strategy(strategy_id)
    if not strategy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Routing strategy {strategy_id} not found"
        )
    return strategy


@router.put("/strategies/{strategy_id}", response_model=RoutingStrategyResponse)
async def update_routing_strategy(
    strategy_id: int,
    strategy: RoutingStrategyUpdate,
    db: Session = Depends(get_current_db),
    current_admin = Depends(verify_admin_access),
):
    """Update a routing strategy."""
    service = RoutingService(db)
    try:
        # Convert rules to dict if provided
        update_data = strategy.model_dump(exclude_unset=True)
        if "rules" in update_data and update_data["rules"] is not None:
            update_data["rules"] = [r.model_dump() for r in strategy.rules]

        result = service.update_strategy(strategy_id, **update_data)
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Routing strategy {strategy_id} not found"
            )
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.delete("/strategies/{strategy_id}")
async def delete_routing_strategy(
    strategy_id: int,
    db: Session = Depends(get_current_db),
    current_admin = Depends(verify_admin_access),
):
    """Delete a routing strategy."""
    service = RoutingService(db)
    try:
        success = service.delete_strategy(strategy_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Routing strategy {strategy_id} not found"
            )
        return {"message": "Routing strategy deleted successfully"}
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/strategies/{strategy_id}/toggle", response_model=RoutingStrategyResponse)
async def toggle_routing_strategy(
    strategy_id: int,
    db: Session = Depends(get_current_db),
    current_admin = Depends(verify_admin_access),
):
    """Toggle routing strategy enabled status."""
    service = RoutingService(db)
    strategy = service.toggle_strategy(strategy_id)
    if not strategy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Routing strategy {strategy_id} not found"
        )
    return strategy


# ============================================================================
# API Key Route Binding Endpoints
# ============================================================================

@router.post("/api-keys/{api_key_id}/bind-strategy", response_model=ApiKeyRouteBindingResponse)
async def bind_routing_strategy(
    api_key_id: int,
    routing_strategy_id: int,
    traffic_weight: int = 100,
    db: Session = Depends(get_current_db),
    current_admin = Depends(verify_admin_access),
):
    """
    Bind a routing strategy to an API key.

    Args:
        api_key_id: API key ID
        routing_strategy_id: Routing strategy ID
        traffic_weight: Traffic weight (0-100)

    Returns:
        Created binding
    """
    # Verify API key exists
    api_key = db.query(ApiKey).filter(ApiKey.id == api_key_id).first()
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"API key {api_key_id} not found"
        )

    service = RoutingService(db)
    binding = service.bind_api_key_strategy(
        api_key_id=api_key_id,
        routing_strategy_id=routing_strategy_id,
        traffic_weight=traffic_weight
    )
    return binding


@router.get("/api-keys/{api_key_id}/strategies", response_model=List[RoutingStrategyResponse])
async def get_api_key_strategies(
    api_key_id: int,
    db: Session = Depends(get_current_db),
    current_admin = Depends(verify_admin_access),
):
    """Get all routing strategies bound to an API key."""
    # Verify API key exists
    api_key = db.query(ApiKey).filter(ApiKey.id == api_key_id).first()
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"API key {api_key_id} not found"
        )

    service = RoutingService(db)
    strategies = service.get_api_key_strategies(api_key_id)
    return strategies


@router.delete("/api-keys/{api_key_id}/strategies/{strategy_id}")
async def unbind_routing_strategy(
    api_key_id: int,
    strategy_id: int,
    db: Session = Depends(get_current_db),
    current_admin = Depends(verify_admin_access),
):
    """Unbind a routing strategy from an API key."""
    service = RoutingService(db)
    success = service.unbind_api_key_strategy(api_key_id, strategy_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Binding not found for API key {api_key_id} and strategy {strategy_id}"
        )
    return {"message": "Routing strategy unbound successfully"}


# ============================================================================
# Gateway Configuration Endpoints
# ============================================================================

@router.get("/config", response_model=GatewayConfigResponse)
async def get_gateway_config(
    db: Session = Depends(get_current_db),
    current_admin = Depends(verify_admin_access),
):
    """Get gateway global configuration."""
    service = HealthCheckService(db)
    config = service.get_config()
    return config


@router.put("/config", response_model=GatewayConfigResponse)
async def update_gateway_config(
    config: GatewayConfigUpdate,
    db: Session = Depends(get_current_db),
    current_admin = Depends(verify_admin_access),
):
    """Update gateway global configuration."""
    service = HealthCheckService(db)
    update_data = config.model_dump(exclude_unset=True)
    updated_config = service.update_config(**update_data)
    return updated_config


# ============================================================================
# Health Check Endpoints
# ============================================================================

@router.get("/health/instances", response_model=List[InstanceHealthResponse])
async def get_instance_health(
    status_filter: Optional[InstanceHealthStatus] = None,
    db: Session = Depends(get_current_db),
    current_admin = Depends(verify_admin_access),
):
    """Get health status of all instances."""
    service = HealthCheckService(db)
    health_list = service.list_instance_health(status=status_filter)
    return health_list


@router.get("/health/instances/{instance_id}", response_model=InstanceHealthResponse)
async def get_instance_health_detail(
    instance_id: int,
    db: Session = Depends(get_current_db),
    current_admin = Depends(verify_admin_access),
):
    """Get health status for a specific instance."""
    service = HealthCheckService(db)
    health = service.get_instance_health(instance_id)
    if not health:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Health record for instance {instance_id} not found"
        )
    return health


@router.post("/health/check")
async def trigger_health_check(
    instance_id: Optional[int] = None,
    db: Session = Depends(get_current_db),
    current_admin = Depends(verify_admin_access),
):
    """
    Manually trigger health check for one or all instances.

    Args:
        instance_id: Specific instance ID (None for all instances)

    Returns:
        Health check results
    """
    service = HealthCheckService(db)

    if instance_id:
        health_status = await service.check_instance_health(instance_id)
        return {
            "instance_id": instance_id,
            "status": health_status
        }
    else:
        results = await service.check_all_instances()
        return results


@router.get("/health/summary")
async def get_health_summary(
    db: Session = Depends(get_current_db),
    current_admin = Depends(verify_admin_access),
):
    """Get health summary statistics."""
    service = HealthCheckService(db)
    summary = service.get_health_summary()
    return summary


@router.get("/health/failover-events", response_model=List[FailoverEventResponse])
async def get_failover_events(
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_current_db),
    current_admin = Depends(verify_admin_access),
):
    """Get failover event history."""
    service = HealthCheckService(db)
    events = service.get_failover_events(limit=limit, offset=offset)
    return events


@router.post("/health/failover/manual", response_model=FailoverEventResponse)
async def manual_failover(
    request: ManualFailoverRequest,
    db: Session = Depends(get_current_db),
    current_admin = Depends(verify_admin_access),
):
    """
    Manually trigger failover from one instance to another.

    Args:
        request: Manual failover request

    Returns:
        Created failover event
    """
    service = HealthCheckService(db)
    try:
        event = await service.manual_failover(
            source_instance_id=request.source_instance_id,
            target_instance_id=request.target_instance_id,
            reason=request.reason
        )
        return event
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/health/unhealthy")
async def get_unhealthy_instances(
    db: Session = Depends(get_current_db),
    current_admin = Depends(verify_admin_access),
):
    """Get all unhealthy instances with details."""
    service = HealthCheckService(db)
    unhealthy = service.get_unhealthy_instances()
    return {"unhealthy_instances": unhealthy}


# ============================================================================
# Load Balancing Endpoints
# ============================================================================

@router.get("/load-balancing/instances")
async def get_instance_load(
    db: Session = Depends(get_current_db),
    current_admin = Depends(verify_admin_access),
):
    """Get load information for all instances."""
    service = HealthCheckService(db)
    health_list = service.list_instance_health()

    from backend.models.database import ModelInstance
    result = []
    for health in health_list:
        instance = db.query(ModelInstance).filter(
            ModelInstance.id == health.model_instance_id
        ).first()
        if instance:
            result.append({
                "model_instance_id": health.model_instance_id,
                "instance_name": instance.name,
                "queue_depth": health.queue_depth,
                "response_time_ms": health.response_time_ms,
                "gpu_utilization": float(health.gpu_utilization) if health.gpu_utilization else 0,
                "status": health.status
            })

    return {"instances": result}


@router.post("/load-balancing/rebalance")
async def rebalance_load(
    db: Session = Depends(get_current_db),
    current_admin = Depends(verify_admin_access),
):
    """
    Manually trigger load rebalancing.

    This endpoint triggers a health check for all instances,
    which may cause automatic failover if needed.
    """
    service = HealthCheckService(db)
    results = await service.check_all_instances()
    logger.info(f"Manual load rebalance triggered: {results}")
    return {
        "message": "Load rebalancing completed",
        "results": results
    }


# ============================================================================
# Instance Metrics Update (Internal Use)
# ============================================================================

@router.post("/metrics/update")
async def update_instance_metrics(
    instance_id: int,
    queue_depth: int,
    response_time_ms: int,
    gpu_utilization: float,
    error_rate: float,
    db: Session = Depends(get_current_db),
):
    """
    Update real-time metrics for an instance.

    This endpoint is typically called by the instance itself or a monitoring agent.
    """
    service = HealthCheckService(db)
    await service.update_instance_metrics(
        instance_id=instance_id,
        queue_depth=queue_depth,
        response_time_ms=response_time_ms,
        gpu_utilization=gpu_utilization,
        error_rate=error_rate
    )
    return {"message": "Metrics updated successfully"}
