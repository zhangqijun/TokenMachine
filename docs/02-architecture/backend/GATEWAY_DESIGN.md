# Gateway Management System Design

## Overview

The Gateway Management System provides intelligent request routing, health checking, failover, and load balancing capabilities for TokenMachine. It serves as the entry point for all incoming API requests, routing them to appropriate model instances based on configurable strategies.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Client Request                          │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                     Gateway Router                              │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  1. Verify API Key                                      │   │
│  │  2. Get Routing Strategies (from API Key bindings)     │   │
│  │  3. Select Target Instance                             │   │
│  └─────────────────────────────────────────────────────────┘   │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                   Routing Strategy Layer                        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │   Semantic   │  │    Weight    │  │ Round Robin  │         │
│  │   (regex)    │  │  (traffic %) │  │   (queue)    │         │
│  └──────────────┘  └──────────────┘  └──────────────┘         │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │              Least Connection (min queue)                 │  │
│  └──────────────────────────────────────────────────────────┘  │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                   Load Balancer                                 │
│  Strategy: queue / response / resource / combined               │
│  Metrics: queue depth, response time, GPU utilization           │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                   Model Instances                               │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐      │
│  │Instance 1│  │Instance 2│  │Instance 3│  │Instance 4│      │
│  │ (qwen)   │  │ (llama)  │  │ (qwen)   │  │ (llama)  │      │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘      │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                   Health Check Service                          │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  • Active Check: Probe /health endpoint                  │  │
│  │  • Passive Check: Monitor error rates                    │  │
│  │  • Metrics: queue depth, response time, GPU util, errors │  │
│  │  • Status: healthy / warning / failed                     │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                   Failover Manager                              │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  • Automatic: Triggered on health check failure          │  │
│  │  • Manual: Admin triggered via API                       │  │
│  │  • Target Selection: Healthy instance of same model      │  │
│  │  • Event Logging: All failovers recorded                │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

## Components

### 1. Database Models

#### RoutingStrategy
Stores routing strategy configuration:
- `name`: Unique strategy name
- `mode`: Routing mode (semantic/weight/round-robin/least-conn)
- `rules`: List of routing rules with pattern, target, weight, priority
- `is_enabled`: Active status
- `enable_aggregation`: API aggregation flag
- `unified_endpoint`: Unified API endpoint path
- `response_mode`: Aggregation response mode (best/all/custom)
- Statistics: `bound_keys_count`, `today_requests`, `p95_latency_ms`

#### ApiKeyRouteBinding
Binds routing strategies to API keys:
- `api_key_id`: Reference to API key
- `routing_strategy_id`: Reference to routing strategy
- `traffic_weight`: Traffic distribution weight (0-100)

#### GatewayConfig
Global gateway configuration:
- Load balancing: `enable_dynamic_lb`, `schedule_strategy`, thresholds
- Health check: `enable_failover`, `check_method`, intervals, thresholds
- Recovery: `auto_recover`, `recover_threshold`

#### InstanceHealth
Per-instance health tracking:
- `status`: Current health status (healthy/warning/failed)
- `fail_count`: Consecutive failure count
- `consecutive_success_count`: Recovery tracking
- Metrics: `queue_depth`, `response_time_ms`, `gpu_utilization`, `error_rate`

#### FailoverEvent
Failover event history:
- `source_instance_id`: Original instance
- `target_instance_id`: New instance
- `event_type`: Cause (timeout/error/overload/manual/health_check_failed)
- `triggered_by`: auto/manual

### 2. Routing Service

**File**: `backend/services/routing_service.py`

**Key Methods**:
- `create_strategy()`: Create new routing strategy
- `select_instance()`: Main routing logic
- `_route_semantic()`: Regex-based pattern matching
- `_route_weight()`: Weighted random selection
- `_route_round_robin()`: Round-robin distribution
- `_route_least_conn()`: Minimum queue depth selection

**Routing Flow**:
1. Get API key's bound routing strategies
2. For each strategy:
   - Match model name against rule patterns
   - Filter healthy instances
   - Apply routing mode to select instance
3. Return first successfully routed instance

### 3. Health Check Service

**File**: `backend/services/health_service.py`

**Key Methods**:
- `check_instance_health()`: Check single instance
- `check_all_instances()`: Batch health check
- `_handle_failover()`: Trigger automatic failover
- `manual_failover()`: Manual failover trigger
- `update_instance_metrics()`: Update real-time metrics

**Health Checks**:
1. **Endpoint Availability**: HTTP GET /health endpoint
2. **Response Time**: Measure request latency
3. **Thresholds**: Compare against configured thresholds
4. **Status Update**: healthy → warning → failed
5. **Auto Recovery**: failed → warning → healthy

### 4. Gateway Router

**File**: `backend/core/gateway.py`

**Key Methods**:
- `route_request()`: Main entry point for routing
- `_fallback_routing()`: Fallback when no strategy configured
- `get_routing_stats()`: Routing statistics

**Load Balancer**:
- `select_instance()`: Select based on strategy
- `_select_by_queue()`: Minimum queue depth
- `_select_by_response_time()`: Fastest response
- `_select_by_resource()`: Lowest GPU utilization
- `_select_by_combined_score()`: Weighted composite score

### 5. API Endpoints

**File**: `backend/api/v1/gateway.py`

**Routing Strategy Endpoints**:
- `GET /api/v1/gateway/strategies` - List strategies
- `POST /api/v1/gateway/strategies` - Create strategy
- `GET /api/v1/gateway/strategies/{id}` - Get strategy
- `PUT /api/v1/gateway/strategies/{id}` - Update strategy
- `DELETE /api/v1/gateway/strategies/{id}` - Delete strategy
- `POST /api/v1/gateway/strategies/{id}/toggle` - Toggle enabled

**API Key Binding Endpoints**:
- `POST /api/v1/gateway/api-keys/{id}/bind-strategy` - Bind strategy
- `GET /api/v1/gateway/api-keys/{id}/strategies` - List bindings
- `DELETE /api/v1/gateway/api-keys/{id}/strategies/{id}` - Unbind

**Configuration Endpoints**:
- `GET /api/v1/gateway/config` - Get gateway config
- `PUT /api/v1/gateway/config` - Update config

**Health Check Endpoints**:
- `GET /api/v1/gateway/health/instances` - List all health
- `GET /api/v1/gateway/health/instances/{id}` - Get instance health
- `POST /api/v1/gateway/health/check` - Trigger health check
- `GET /api/v1/gateway/health/summary` - Health summary
- `GET /api/v1/gateway/health/failover-events` - Event history
- `POST /api/v1/gateway/health/failover/manual` - Manual failover
- `GET /api/v1/gateway/health/unhealthy` - List unhealthy instances

**Load Balancing Endpoints**:
- `GET /api/v1/gateway/load-balancing/instances` - Instance load
- `POST /api/v1/gateway/load-balancing/rebalance` - Manual rebalance

**Metrics Endpoints**:
- `POST /api/v1/gateway/metrics/update` - Update instance metrics

## Routing Modes

### 1. Semantic Routing (Regex Match)
Routes based on model name patterns:
```json
{
  "mode": "semantic",
  "rules": [
    {"pattern": "qwen.*", "target": "qwen-2.5-7b-primary", "weight": 90, "priority": 1},
    {"pattern": "qwen.*", "target": "qwen-2.5-7b-canary", "weight": 10, "priority": 2}
  ]
}
```
- Priority 1 rules checked first
- Falls back to priority 2 if priority 1 instances unhealthy

### 2. Weight Routing (Traffic Split)
Routes based on weighted distribution:
```json
{
  "mode": "weight",
  "rules": [
    {"pattern": "llama.*", "target": "llama-3-v2", "weight": 80, "priority": 1},
    {"pattern": "llama.*", "target": "llama-3-v1", "weight": 20, "priority": 1}
  ]
}
```
- 80% traffic to v2, 20% to v1
- Useful for canary deployments

### 3. Round Robin Routing
Distributes requests evenly:
```json
{
  "mode": "round-robin",
  "rules": [
    {"pattern": "*", "target": "instance-1", "weight": 25, "priority": 1},
    {"pattern": "*", "target": "instance-2", "weight": 25, "priority": 1},
    {"pattern": "*", "target": "instance-3", "weight": 25, "priority": 1},
    {"pattern": "*", "target": "instance-4", "weight": 25, "priority": 1}
  ]
}
```

### 4. Least Connection Routing
Routes to instance with minimum queue:
```json
{
  "mode": "least-conn",
  "rules": [
    {"pattern": "*", "target": "instance-1", "weight": 100, "priority": 1}
  ]
}
```
- Selects instance with lowest `queue_depth`
- Best for varying request processing times

## Load Balancing Strategies

### Queue-Based (Default)
Prioritizes instances with shortest queue:
```python
score = queue_depth / queue_threshold * 100 * 0.4
```

### Response Time-Based
Prioritizes fastest responding instances:
```python
score = response_time_ms / response_threshold * 100 * 0.3
```

### Resource-Based
Prioritizes instances with lowest GPU utilization:
```python
score = gpu_utilization / gpu_threshold * 100 * 0.3
```

### Combined Score
Weighted composite of all metrics:
```python
total_score = (queue_score * 0.4) + (response_score * 0.3) + (util_score * 0.3)
```

## Health Check Process

### Active Health Check
1. Send HTTP GET to `{instance.endpoint}/health`
2. Measure response time
3. Update health status based on thresholds

### Passive Health Check
1. Monitor error rates from requests
2. Track consecutive failures
3. Mark as failed if threshold exceeded

### Status Transitions
```
[HEALTHY] --fail_threshold--> [FAILED]
   ^                            |
   |                            v
[RECOVERED] --recover_threshold--+

[HEALTHY] --warning_threshold--> [WARNING]
   ^                            |
   |                            v
[RECOVERED] --recover_threshold--+
```

### Failover Trigger
When instance marked as FAILED:
1. Find alternative instances for same model
2. Select based on load balancing strategy
3. Record failover event
4. Update routing tables

## Configuration Example

### Global Config
```json
{
  "enable_dynamic_lb": true,
  "schedule_strategy": "queue",
  "queue_threshold": 50,
  "response_threshold": 5000,
  "gpu_threshold": 95,
  "enable_failover": true,
  "check_method": "active",
  "check_interval": 10,
  "timeout": 5,
  "fail_threshold": 3,
  "response_time_threshold": 5000,
  "error_rate_threshold": 10,
  "queue_depth_threshold": 100,
  "auto_recover": true,
  "recover_threshold": 3
}
```

### Routing Strategy Example
```json
{
  "name": "qwen-intelligent-routing",
  "description": "Smart routing for Qwen models",
  "mode": "semantic",
  "is_enabled": true,
  "rules": [
    {
      "pattern": "^qwen-2\\.5-7b$",
      "target": "qwen-2.5-7b-instance-1",
      "weight": 70,
      "priority": 1
    },
    {
      "pattern": "^qwen-2\\.5-7b$",
      "target": "qwen-2.5-7b-instance-2",
      "weight": 30,
      "priority": 2
    }
  ],
  "enable_aggregation": false
}
```

## Integration with Chat API

The gateway integrates with the existing chat API (`/v1/chat/completions`):

```python
# In backend/api/v1/chat.py

from backend.core.gateway import get_gateway_router

@router.post("/v1/chat/completions")
async def create_chat_completion(
    request: ChatCompletionRequest,
    api_key: ApiKey = Depends(verify_api_key_auth),
    db: Session = Depends(get_current_db),
):
    # Use gateway to select instance
    gateway = get_gateway_router(db)
    instance = await gateway.route_request(
        api_key_id=api_key.id,
        model_name=request.model
    )

    if not instance:
        raise HTTPException(
            status_code=404,
            detail=f"No available instance for model '{request.model}'"
        )

    # Forward request to selected instance
    response = await forward_to_instance(instance, request)
    return response
```

## Database Migration

```bash
# Create migration
alembic revision --autogenerate -m "Add gateway management tables"

# Apply migration
alembic upgrade head
```

## Monitoring and Observability

### Metrics Exposed
- Routing strategy selection counts
- Instance health status counts
- Failover event rate
- Average response time per instance
- Queue depth trends

### Logging
- Routing decisions: `INFO` level
- Health check failures: `WARNING` level
- Failover events: `ERROR` level
- Configuration changes: `INFO` level

## Future Enhancements

1. **Circuit Breaker**: Temporarily stop routing to repeatedly failing instances
2. **Retry with Backoff**: Automatic retry with exponential backoff
3. **Geo-Routing**: Route to nearest instance based on location
4. **A/B Testing**: Route requests for experiments
5. **Metrics Dashboard**: Real-time visualization of gateway metrics
6. **Dynamic Config Updates**: Update config without restart
7. **Bulk Operations**: Batch health checks and config updates

## References

- Related: `docs/02-architecture/backend/MODEL_INSTANCE_MANAGEMENT.md`
- Related: `docs/02-architecture/backend/BACKEND_DESIGN.md`
- API Reference: `/docs` endpoint (Swagger UI)
