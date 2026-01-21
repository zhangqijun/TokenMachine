"""
TokenMachine - AI Model Deployment and Management Platform

Main application entry point.
"""
import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.openapi.utils import get_openapi
from loguru import logger
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
from fastapi.responses import Response
import psutil

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.core.config import get_settings, ensure_directories
from backend.core.database import init_db, get_db
from backend.core.gpu import get_gpu_manager
from backend.api.middleware import setup_middleware
from backend.monitoring import metrics as prom_metrics
from backend.monitoring.metrics import (
    system_cpu_percent,
    system_memory_used_mb,
    system_memory_total_mb,
)


# Initialize settings
settings = get_settings()
ensure_directories(settings)

# Configure logging
logger.remove()
logger.add(
    sys.stderr,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    level=settings.log_level,
)
logger.add(
    os.path.join(settings.log_path, "tokenmachine.log"),
    rotation=settings.log_rotation,
    retention=settings.log_retention,
    level=settings.log_level,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    logger.info(f"Starting {settings.app_name} v{settings.app_version}")

    # Initialize database
    logger.info("Initializing database...")
    init_db()

    # Initialize GPU manager
    gpu_manager = get_gpu_manager()
    if gpu_manager.is_available():
        logger.info(f"GPU Manager initialized with {gpu_manager.num_gpus} GPUs")
    else:
        logger.warning("GPU Manager not available - running in CPU-only mode")

    logger.info(f"{settings.app_name} started successfully")

    yield

    # Cleanup
    logger.info("Shutting down...")

    # Cleanup worker pool
    from backend.workers.worker_pool import get_worker_pool
    worker_pool = get_worker_pool()
    await worker_pool.cleanup()

    logger.info(f"{settings.app_name} stopped")


# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="AI Model Deployment and Management Platform",
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
    lifespan=lifespan,
)

# Setup middleware
setup_middleware(app)


# ============================================================================
# Health Check
# ============================================================================

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    gpu_manager = get_gpu_manager()

    return {
        "status": "healthy",
        "version": settings.app_version,
        "gpu_detected": gpu_manager.is_available(),
        "gpu_count": gpu_manager.num_gpus if gpu_manager.is_available() else 0,
    }


# ============================================================================
# Prometheus Metrics
# ============================================================================

@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint."""
    # Update system metrics
    system_cpu_percent.set(psutil.cpu_percent())
    memory = psutil.virtual_memory()
    system_memory_used_mb.set(memory.used / (1024 * 1024))
    system_memory_total_mb.set(memory.total / (1024 * 1024))

    # Update GPU metrics
    gpu_manager = get_gpu_manager()
    if gpu_manager.is_available():
        for gpu in gpu_manager.get_all_gpus():
            gpu_id = gpu["id"]
            prom_metrics.gpu_utilization_percent.labels(gpu_id=gpu_id).set(gpu["utilization_percent"])
            prom_metrics.gpu_memory_used_mb.labels(gpu_id=gpu_id).set(gpu["memory_used_mb"])
            prom_metrics.gpu_memory_total_mb.labels(gpu_id=gpu_id).set(gpu["memory_total_mb"])
            prom_metrics.gpu_memory_free_mb.labels(gpu_id=gpu_id).set(gpu["memory_free_mb"])
            prom_metrics.gpu_temperature_celsius.labels(gpu_id=gpu_id).set(gpu["temperature_celsius"])

    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


# ============================================================================
# Include Routers
# ============================================================================

from backend.api.v1 import chat, models, admin, playground, benchmark

app.include_router(chat.router)
app.include_router(models.router)
app.include_router(admin.router)
app.include_router(playground.router, prefix="/api/v1/playground", tags=["playground"])
app.include_router(benchmark.router, prefix="/api/v1/benchmark", tags=["benchmark"])


# ============================================================================
# Exception Handlers
# ============================================================================

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)

    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "message": str(exc) if settings.debug else "An unexpected error occurred",
            "request_id": getattr(request.state, "request_id", None),
        }
    )


# ============================================================================
# OpenAPI Configuration
# ============================================================================

def custom_openapi():
    """Custom OpenAPI schema."""
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title=settings.app_name,
        version=settings.app_version,
        description="AI Model Deployment and Management Platform",
        routes=app.routes,
    )

    # Add security scheme for API key authentication
    openapi_schema["components"]["securitySchemes"] = {
        "ApiKeyAuth": {
            "type": "apiKey",
            "in": "header",
            "name": "Authorization",
            "description": "API key authentication using Bearer token format. Example: `Bearer tmachine_sk_...`"
        }
    }

    # Apply security to all routes except health and metrics
    for path, path_item in openapi_schema["paths"].items():
        for method in path_item.values():
            if method.get("operationId"):
                method["security"] = [{"ApiKeyAuth": []}]

    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi


# ============================================================================
# Root Endpoint
# ============================================================================

@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "status": "running",
        "docs": "/docs" if settings.debug else None,
        "health": "/health",
        "metrics": "/metrics",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "backend.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.api_reload,
        log_level=settings.log_level.lower(),
    )
