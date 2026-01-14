"""
Worker Health API endpoints.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any
import logging

router = APIRouter()
logger = logging.getLogger(__name__)


class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    worker_info: Dict[str, Any]


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    return HealthResponse(
        status="healthy",
        worker_info={
            "message": "TokenMachine Worker is running",
        },
    )


@router.get("/ready")
async def readiness_check():
    """Readiness check endpoint."""
    # TODO: Check if worker is registered and ready
    return {"status": "ready"}
