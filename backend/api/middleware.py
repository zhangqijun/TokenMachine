"""
Middleware for API routes.
"""
import time
from typing import Callable
from fastapi import Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from loguru import logger
from prometheus_client import Counter, Histogram

from backend.monitoring.metrics import api_requests_total, api_latency_seconds
from backend.core.security import generate_request_id


# Request ID middleware
async def request_id_middleware(request: Request, call_next: Callable) -> Response:
    """Add unique request ID to each request."""
    request_id = generate_request_id()
    request.state.request_id = request_id

    start_time = time.time()

    response = await call_next(request)

    # Add request ID to response headers
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Request-ID"] = request_id

    # Log request
    duration = time.time() - start_time
    logger.info(
        f"{request.method} {request.url.path} "
        f"{response.status_code} {duration:.3f}s"
    )

    return response


# Metrics middleware
async def metrics_middleware(request: Request, call_next: Callable) -> Response:
    """Collect Prometheus metrics for each request."""
    start_time = time.time()

    response = await call_next(request)

    # Record metrics
    duration = time.time() - start_time
    endpoint = request.url.path
    method = request.method
    status = response.status_code

    api_requests_total.labels(
        method=method,
        endpoint=endpoint,
        status=str(status)
    ).inc()

    api_latency_seconds.labels(endpoint=endpoint).observe(duration)

    return response


def setup_middleware(app):
    """Setup all middleware for the application."""
    from fastapi.middleware import Middleware
    from fastapi.middleware.trustedhost import TrustedHostMiddleware

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure appropriately for production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # GZip middleware
    app.add_middleware(GZipMiddleware, minimum_size=1000)

    # Trusted host middleware (for production)
    # app.add_middleware(
    #     TrustedHostMiddleware,
    #     allowed_hosts=["*"]  # Configure for production
    # )

    # Custom middleware
    app.middleware("http")(request_id_middleware)
    app.middleware("http")(metrics_middleware)

    logger.info("Middleware configured")
