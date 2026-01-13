"""
Prometheus metrics for TokenMachine.
"""
from prometheus_client import Counter, Gauge, Histogram, Summary

# ============================================================================
# API Metrics
# ============================================================================

api_requests_total = Counter(
    'tokenmachine_api_requests_total',
    'Total API requests',
    ['method', 'endpoint', 'status']
)

api_latency_seconds = Histogram(
    'tokenmachine_api_latency_seconds',
    'API latency in seconds',
    ['endpoint'],
    buckets=[0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
)

api_requests_active = Gauge(
    'tokenmachine_api_requests_active',
    'Active API requests'
)

# ============================================================================
# Model Metrics
# ============================================================================

model_tokens_total = Counter(
    'tokenmachine_model_tokens_total',
    'Total tokens generated',
    ['model_name', 'token_type']  # input, output
)

model_requests_total = Counter(
    'tokenmachine_model_requests_total',
    'Total model inference requests',
    ['model_name', 'status']
)

model_requests_active = Gauge(
    'tokenmachine_model_requests_active',
    'Active model requests',
    ['model_name']
)

model_latency_seconds = Histogram(
    'tokenmachine_model_latency_seconds',
    'Model inference latency in seconds',
    ['model_name'],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0]
)

# ============================================================================
# GPU Metrics
# ============================================================================

gpu_utilization_percent = Gauge(
    'tokenmachine_gpu_utilization_percent',
    'GPU utilization percentage',
    ['gpu_id']
)

gpu_memory_used_mb = Gauge(
    'tokenmachine_gpu_memory_used_mb',
    'GPU memory used in MB',
    ['gpu_id']
)

gpu_memory_total_mb = Gauge(
    'tokenmachine_gpu_memory_total_mb',
    'GPU total memory in MB',
    ['gpu_id']
)

gpu_memory_free_mb = Gauge(
    'tokenmachine_gpu_memory_free_mb',
    'GPU free memory in MB',
    ['gpu_id']
)

gpu_temperature_celsius = Gauge(
    'tokenmachine_gpu_temperature_celsius',
    'GPU temperature in Celsius',
    ['gpu_id']
)

gpu_power_draw_watts = Gauge(
    'tokenmachine_gpu_power_draw_watts',
    'GPU power draw in watts',
    ['gpu_id']
)

gpu_status = Gauge(
    'tokenmachine_gpu_status',
    'GPU status (1=available, 0=in_use, -1=error)',
    ['gpu_id']
)

# ============================================================================
# Worker Metrics
# ============================================================================

worker_status = Gauge(
    'tokenmachine_worker_status',
    'Worker status (1=running, 0=stopped)',
    ['deployment_id', 'worker_id']
)

worker_requests_total = Counter(
    'tokenmachine_worker_requests_total',
    'Total worker requests',
    ['deployment_id', 'worker_id', 'status']
)

worker_latency_seconds = Histogram(
    'tokenmachine_worker_latency_seconds',
    'Worker latency in seconds',
    ['deployment_id', 'worker_id']
)

# ============================================================================
# Deployment Metrics
# ============================================================================

deployment_status = Gauge(
    'tokenmachine_deployment_status',
    'Deployment status (1=running, 0=stopped, -1=error)',
    ['deployment_id', 'deployment_name']
)

deployment_replicas = Gauge(
    'tokenmachine_deployment_replicas',
    'Number of replicas for a deployment',
    ['deployment_id', 'deployment_name']
)

deployment_requests_total = Counter(
    'tokenmachine_deployment_requests_total',
    'Total deployment requests',
    ['deployment_id', 'deployment_name', 'status']
)

# ============================================================================
# System Metrics
# ============================================================================

system_cpu_percent = Gauge(
    'tokenmachine_system_cpu_percent',
    'System CPU percentage'
)

system_memory_used_mb = Gauge(
    'tokenmachine_system_memory_used_mb',
    'System memory used in MB'
)

system_memory_total_mb = Gauge(
    'tokenmachine_system_memory_total_mb',
    'System total memory in MB'
)

system_disk_usage_percent = Gauge(
    'tokenmachine_system_disk_usage_percent',
    'System disk usage percentage',
    ['mount_point']
)

# ============================================================================
# Database Metrics
# ============================================================================

database_connections_active = Gauge(
    'tokenmachine_database_connections_active',
    'Active database connections'
)

database_query_latency_seconds = Histogram(
    'tokenmachine_database_query_latency_seconds',
    'Database query latency in seconds',
    ['query_type'],
    buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0]
)

# ============================================================================
# Cache Metrics
# ============================================================================

cache_hits_total = Counter(
    'tokenmachine_cache_hits_total',
    'Total cache hits',
    ['cache_type']
)

cache_misses_total = Counter(
    'tokenmachine_cache_misses_total',
    'Total cache misses',
    ['cache_type']
)

cache_size_bytes = Gauge(
    'tokenmachine_cache_size_bytes',
    'Cache size in bytes',
    ['cache_type']
)

# ============================================================================
# API Key Metrics
# ============================================================================

api_key_requests_total = Counter(
    'tokenmachine_api_key_requests_total',
    'Total requests per API key',
    ['api_key_prefix']
)

api_key_tokens_used_total = Counter(
    'tokenmachine_api_key_tokens_used_total',
    'Total tokens used per API key',
    ['api_key_prefix']
)
