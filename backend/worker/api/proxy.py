"""
Worker Inference Proxy API endpoints.
"""
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse, JSONResponse
from typing import Dict, Any, Optional
import logging
import httpx

router = APIRouter()
logger = logging.getLogger(__name__)


@router.api_route("/v1/chat/completions", methods=["POST"])
async def chat_completions_proxy(request: Request):
    """Proxy chat completion requests to the appropriate model instance."""
    body = await request.json()

    # Get model name
    model_name = body.get("model")
    if not model_name:
        raise HTTPException(status_code=400, detail="model field is required")

    # TODO: Find the appropriate instance for this model
    # For now, return a placeholder response
    return JSONResponse(
        status_code=501,
        content={
            "error": {
                "message": "Inference proxy not yet implemented",
                "type": "not_implemented",
            }
        },
    )


@router.api_route("/v1/models", methods=["GET"])
async def list_models_proxy():
    """Proxy list models requests."""
    # TODO: Get list of models from running instances
    return JSONResponse(
        status_code=501,
        content={
            "error": {
                "message": "Models listing not yet implemented",
                "type": "not_implemented",
            }
        },
    )


@router.api_route("/v1/completions", methods=["POST"])
async def completions_proxy(request: Request):
    """Proxy completion requests to the appropriate model instance."""
    return JSONResponse(
        status_code=501,
        content={
            "error": {
                "message": "Completion proxy not yet implemented",
                "type": "not_implemented",
            }
        },
    )
