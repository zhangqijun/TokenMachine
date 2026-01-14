"""
OpenAI Chat Completions API endpoint.
"""
import time
import json
from typing import AsyncGenerator
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from loguru import logger
import httpx

from backend.api.deps import get_current_db, verify_api_key_auth, get_deployment_by_name
from backend.models.database import ApiKey, UsageLog, UsageLogStatus
from backend.models.schemas import (
    ChatCompletionRequest,
    ChatCompletionResponse,
    ChatCompletionStreamResponse,
)
from backend.workers.worker_pool import get_worker_pool
from backend.monitoring.metrics import (
    model_tokens_total,
    model_requests_total,
    api_key_requests_total,
    api_key_tokens_used_total,
)

router = APIRouter(tags=["Chat"])


@router.post("/v1/chat/completions")
async def chat_completions(
    request: ChatCompletionRequest,
    api_key: ApiKey = Depends(verify_api_key_auth),
    db: Session = Depends(get_current_db),
):
    """
    OpenAI-compatible chat completions endpoint.

    Supports both streaming and non-streaming responses.
    """
    deployment = await get_deployment_by_name(request.model, db)

    # Get worker endpoint
    worker_pool = get_worker_pool()
    endpoint = worker_pool.get_healthy_worker_endpoint(deployment.id)

    if not endpoint:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="No healthy workers available for this model"
        )

    start_time = time.time()

    try:
        if request.stream:
            return StreamingResponse(
                _stream_chat_completion(
                    request, endpoint, deployment.id, api_key.id, db
                ),
                media_type="text/event-stream"
            )
        else:
            return await _non_stream_chat_completion(
                request, endpoint, deployment.id, api_key.id, db, start_time
            )

    except httpx.HTTPError as e:
        logger.error(f"Worker request failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to communicate with inference backend"
        )


async def _non_stream_chat_completion(
    request: ChatCompletionRequest,
    endpoint: str,
    deployment_id: int,
    api_key_id: int,
    db: Session,
    start_time: float
) -> ChatCompletionResponse:
    """Handle non-streaming chat completion."""
    async with httpx.AsyncClient(timeout=300.0) as client:
        response = await client.post(
            f"{endpoint}/v1/chat/completions",
            json=request.model_dump(exclude_none=True),
            headers={"Content-Type": "application/json"}
        )
        response.raise_for_status()
        data = response.json()

    latency_ms = int((time.time() - start_time) * 1000)
    input_tokens = data.get("usage", {}).get("prompt_tokens", 0)
    output_tokens = data.get("usage", {}).get("completion_tokens", 0)

    # Record usage
    await _record_usage(
        db=db,
        api_key_id=api_key_id,
        deployment_id=deployment_id,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        latency_ms=latency_ms,
        status=UsageLogStatus.SUCCESS
    )

    # Update metrics
    model_tokens_total.labels(
        model_name=request.model,
        token_type="input"
    ).inc(input_tokens)
    model_tokens_total.labels(
        model_name=request.model,
        token_type="output"
    ).inc(output_tokens)
    model_requests_total.labels(
        model_name=request.model,
        status="success"
    ).inc()
    api_key_requests_total.labels(api_key_prefix=f"sk_{api_key_id:04d}").inc()
    api_key_tokens_used_total.labels(api_key_prefix=f"sk_{api_key_id:04d}").inc(input_tokens + output_tokens)

    return ChatCompletionResponse(**data)


async def _stream_chat_completion(
    request: ChatCompletionRequest,
    endpoint: str,
    deployment_id: int,
    api_key_id: int,
    db: Session
) -> AsyncGenerator[str, None]:
    """Handle streaming chat completion."""
    input_tokens = 0
    output_tokens = 0
    start_time = time.time()
    chunk_id = f"chatcmpl_{int(time.time())}"

    try:
        async with httpx.AsyncClient(timeout=300.0) as client:
            async with client.stream(
                "POST",
                f"{endpoint}/v1/chat/completions",
                json=request.model_dump(exclude_none=True),
                headers={"Content-Type": "application/json"}
            ) as response:
                response.raise_for_status()

                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data_str = line[6:]
                        if data_str == "[DONE]":
                            yield f"data: [DONE]\n\n"
                            break

                        try:
                            data = json.loads(data_str)
                            # Update output tokens estimate
                            output_tokens += 1
                            yield f"data: {data_str}\n\n"
                        except json.JSONDecodeError:
                            pass

    except Exception as e:
        logger.error(f"Streaming error: {e}")
        yield f"data: {{'error': '{str(e)}'}}\n\n"

    # Record usage after stream ends
    latency_ms = int((time.time() - start_time) * 1000)

    # Estimate input tokens (rough approximation)
    input_tokens = sum(len(m.content) // 4 for m in request.messages)

    await _record_usage(
        db=db,
        api_key_id=api_key_id,
        deployment_id=deployment_id,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        latency_ms=latency_ms,
        status=UsageLogStatus.SUCCESS
    )


async def _record_usage(
    db: Session,
    api_key_id: int,
    deployment_id: int,
    input_tokens: int,
    output_tokens: int,
    latency_ms: int,
    status: UsageLogStatus
):
    """Record usage log."""
    try:
        # Get model_id from deployment
        deployment = db.query(Deployment).filter(Deployment.id == deployment_id).first()

        usage_log = UsageLog(
            api_key_id=api_key_id,
            deployment_id=deployment_id,
            model_id=deployment.model_id,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            latency_ms=latency_ms,
            status=status
        )
        db.add(usage_log)

        # Update API key token usage
        api_key = db.query(ApiKey).filter(ApiKey.id == api_key_id).first()
        if api_key:
            api_key.tokens_used += (input_tokens + output_tokens)

        db.commit()
    except Exception as e:
        logger.error(f"Failed to record usage: {e}")
