# Gateway Management - Deployment & Configuration Guide

## Overview

This document provides step-by-step instructions for deploying and configuring the Gateway Management System.

## Prerequisites

1. **Redis** - For Celery broker and result backend
2. **PostgreSQL** - Database server running
3. **Python 3.10+** - Python environment
4. **Redis** - For caching

## Deployment Steps

### 1. Apply Database Migration

```bash
cd /home/ht706/Documents/TokenMachine

# Run the gateway management migration
alembic upgrade head
```

Expected output:
```
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume non-transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade 003_add_playground_tables -> 004_add_gateway_management
```

### 2. Verify Tables Created

```bash
# Connect to PostgreSQL and verify
psql -U postgres -d tokenmachine

# List gateway tables
\dt *routing* *gateway* *instance_health* *failover*

# Expected output:
# routing_strategies
# api_key_route_bindings
# gateway_configs
# instance_health
# failover_events
```

### 3. Update Main Application

Edit `backend/main.py` to include the gateway router:

```python
# Add after other router imports
from backend.api.v1 import gateway

# Include the gateway router (after other routers)
app.include_router(gateway.router)
```

### 4. Configure Environment Variables

Ensure these are set in your `.env` file:

```bash
# Database
DATABASE_URL=postgresql://postgres:password@localhost:5432/tokenmachine

# Redis
REDIS_URL=redis://localhost:6379/0

# Celery
CELERY_BROKER_URL=redis://localhost:6379/1
CELERY_RESULT_BACKEND=redis://localhost:6379/2

# Other settings...
```

### 5. Start Services

#### Option A: Development Mode (Separate Terminals)

**Terminal 1 - FastAPI Backend:**
```bash
cd /home/ht706/Documents/TokenMachine
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

**Terminal 2 - Celery Worker:**
```bash
cd /home/ht706/Documents/TokenMachine
celery -A backend.core.celery_app worker --loglevel=info
```

**Terminal 3 - Celery Beat (Scheduler):**
```bash
cd /home/ht706/Documents/TokenMachine
celery -A backend.core.celery_app beat --loglevel=info
```

**Terminal 4 - Redis (if not running):**
```bash
redis-server
```

#### Option B: Using Docker Compose

Create `docker-compose.dev.yml`:

```yaml
version: '3.8'

services:
  api:
    build: .
    command: uvicorn backend.main:app --host 0.0.0.0 --port 8000
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://postgres:password@postgres:5432/tokenmachine
      - REDIS_URL=redis://redis:6379/0
      - CELERY_BROKER_URL=redis://redis:6379/1
      - CELERY_RESULT_BACKEND=redis://redis:6379/2
    depends_on:
      - postgres
      - redis

  celery_worker:
    build: .
    command: celery -A backend.core.celery_app worker --loglevel=info
    environment:
      - DATABASE_URL=postgresql://postgres:password@postgres:5432/tokenmachine
      - CELERY_BROKER_URL=redis://redis:6379/1
      - CELERY_RESULT_BACKEND=redis://redis:6379/2
    depends_on:
      - postgres
      - redis

  celery_beat:
    build: .
    command: celery -A backend.core.celery_app beat --loglevel=info
    environment:
      - CELERY_BROKER_URL=redis://redis:6379/1
      - CELERY_RESULT_BACKEND=redis://redis:6379/2
    depends_on:
      - redis

  postgres:
    image: postgres:15
    environment:
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=password
      - POSTGRES_DB=tokenmachine
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

volumes:
  postgres_data:
```

Start with:
```bash
docker-compose -f docker-compose.dev.yml up -d
```

### 6. Verify Deployment

#### Check API Health
```bash
curl http://localhost:8000/health
```

Expected response:
```json
{
  "status": "healthy",
  "version": "0.1.0",
  "gpu_detected": true,
  "gpu_count": 2
}
```

#### Check Gateway API
```bash
# Get gateway config (requires admin API key)
curl http://localhost:8000/api/v1/gateway/config \
  -H "Authorization: Bearer YOUR_ADMIN_API_KEY"
```

Expected response:
```json
{
  "id": 1,
  "enable_dynamic_lb": true,
  "schedule_strategy": "queue",
  "queue_threshold": 50,
  "enable_failover": true,
  "check_interval": 10
  ...
}
```

#### Check Celery Tasks

In the Celery worker terminal, you should see:
```
[2024-01-21 10:00:00,123: INFO/MainProcess] Connected to redis://localhost:6379/1
[2024-01-21 10:00:05,456: INFO/Tasks] Received task: backend.tasks.gateway_tasks.health_check_task
[2024-01-21 10:00:10,789: INFO/Tasks] Task backend.tasks.gateway_tasks.health_check_task[...] succeeded
```

In the Celery Beat terminal:
```
[2024-01-21 10:00:00,000: INFO/Scheduler] Scheduler: Sending due task gateway-health-check
[2024-01-21 10:01:00,000: INFO/Scheduler] Scheduler: Sending due task gateway-metrics-collection
```

## Running Tests

### Integration Tests

```bash
cd /home/ht706/Documents/TokenMachine

# Run all integration tests
pytest tests/integration/test_gateway_api.py -v

# Run specific test class
pytest tests/integration/test_gateway_api.py::TestRoutingStrategyAPI -v

# Run with coverage
pytest tests/integration/test_gateway_api.py --cov=backend --cov-report=html
```

### Manual Task Testing

```bash
# Test health check task manually
python -m backend.tasks.gateway_tasks health_check

# Test metrics collection
python -m backend.tasks.gateway_tasks metrics

# Test aggregation
python -m backend.tasks.gateway_tasks aggregate

# Test alert check
python -m backend.tasks.gateway_tasks alert
```

## Configuration Tuning

### Gateway Configuration

Update via API or directly in database:

```bash
curl -X PUT http://localhost:8000/api/v1/gateway/config \
  -H "Authorization: Bearer YOUR_ADMIN_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "enable_dynamic_lb": true,
    "schedule_strategy": "combined",
    "queue_threshold": 75,
    "response_threshold": 3000,
    "gpu_threshold": 90,
    "check_interval": 15,
    "fail_threshold": 5
  }'
```

### Celery Schedule Adjustment

Edit `backend/core/celery_app.py`:

```python
beat_schedule={
    # Faster health checks (every 5 seconds)
    'gateway-health-check': {
        'task': 'backend.tasks.gateway_tasks.health_check_task',
        'schedule': 5.0,  # Changed from 10.0
    },
    # Less frequent metrics (every 5 minutes)
    'gateway-metrics-collection': {
        'task': 'backend.tasks.gateway_tasks.metrics_collection_task',
        'schedule': 300.0,  # Changed from 60.0
    },
}
```

Restart Celery Beat after changes.

## Monitoring

### View Celery Tasks

```bash
# List active tasks
celery -A backend.core.celery_app inspect active

# View registered tasks
celery -A backend.core.celery_app inspect registered

# View scheduled tasks
celery -A backend.core.celery_app inspect scheduled
```

### Check Logs

```bash
# Gateway API logs
tail -f logs/tokenmachine.log | grep -i gateway

# Celery worker logs
tail -f logs/celery.log

# Health check logs
grep "Health check completed" logs/tokenmachine.log
```

### Prometheus Metrics

Access metrics endpoint:
```bash
curl http://localhost:8000/metrics
```

Key gateway metrics to watch:
- `gateway_health_check_total` - Total health checks performed
- `gateway_failover_total` - Total failovers triggered
- `gateway_routing_requests_total` - Total routing requests

## Troubleshooting

### Issue: Health checks not running

**Symptoms**: No health check logs, instance health not updating

**Solutions**:
1. Verify Celery Beat is running
   ```bash
   celery -A backend.core.celery_app inspect active
   ```
2. Check Redis connection
   ```bash
   redis-cli ping
   ```
3. Verify task is registered
   ```bash
   celery -A backend.core.celery_app inspect registered | grep gateway
   ```

### Issue: Gateway API returns 404

**Symptoms**: `/api/v1/gateway/*` endpoints return 404

**Solutions**:
1. Verify gateway router is included in `main.py`
2. Check for import errors in logs
3. Verify migration was applied

### Issue: Routing not working

**Symptoms**: Chat requests fail with "No available instances"

**Solutions**:
1. Verify instances have `status='running'`
2. Check instance health records exist
3. Verify routing strategy is bound to API key
4. Check instance endpoints are accessible

### Issue: Failover not triggering

**Symptoms**: Failed instances stay failed, no automatic recovery

**Solutions**:
1. Check `enable_failover=true` in gateway config
2. Verify `fail_threshold` is set appropriately
3. Check health check task is running
4. Verify there are healthy alternative instances

## Performance Tuning

### Database Indexes

Ensure indexes are created:
```sql
-- Check existing indexes
SELECT indexname, tablename
FROM pg_indexes
WHERE tablename LIKE '%routing%'
   OR tablename LIKE '%gateway%'
   OR tablename LIKE '%instance_health%';
```

### Redis Caching

For high-traffic deployments, consider caching:
- Routing strategy lookups
- Instance health status
- Gateway configuration

Example:
```python
# In routing_service.py
@app.cache(cache_expire=60)
def get_routing_strategy(strategy_id: int):
    return db.query(RoutingStrategy).filter(...).first()
```

### Connection Pooling

Adjust database pool size in `backend/core/database.py`:
```python
engine = create_engine(
    settings.database_url,
    pool_size=20,  # Increase from default
    max_overflow=40,
    pool_pre_ping=True
)
```

## Production Checklist

- [ ] Database migrations applied
- [ ] Gateway router included in main.py
- [ ] Redis running and accessible
- [ ] Celery worker running
- [ ] Celery Beat running
- [ ] Health checks executing (check logs)
- [ ] Gateway configuration set
- [ ] At least one routing strategy created
- [ ] API keys bound to strategies
- [ ] Monitoring configured (Prometheus)
- [ ] Log aggregation configured
- [ ] Failover tested
- [ ] Load balancer tested
- [ ] Integration tests passing

## Maintenance

### Daily
- Monitor health check logs
- Check failover events
- Review instance health summary

### Weekly
- Review routing strategy performance
- Adjust thresholds based on metrics
- Check for stale health records

### Monthly
- Archive old failover events
- Review and optimize routing rules
- Update documentation

## Support

For issues or questions:
1. Check logs: `logs/tokenmachine.log`
2. Review design doc: `docs/02-architecture/backend/GATEWAY_DESIGN.md`
3. Review implementation: `docs/02-architecture/backend/GATEWAY_IMPLEMENTATION.md`
4. Run tests: `pytest tests/integration/test_gateway_api.py`
