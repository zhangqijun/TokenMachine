"""
GPU device registration and heartbeat API endpoints.

This module provides endpoints for GPU agents to register devices
and send heartbeats to report their status.
"""
from typing import Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from backend.core.database import get_db
from backend.core.security import verify_worker_token
from backend.models.database import Worker, GPUDevice, WorkerStatus, GPUDeviceState, GPUVendor
from backend.models.schemas import (
    GPURegisterRequest,
    GPURegisterResponse,
    GPUHeartbeatRequest,
    GPUHeartbeatResponse,
    BatchHeartbeatRequest,
    BatchHeartbeatResponse,
)

router = APIRouter(prefix="/gpus", tags=["gpus"])
security = HTTPBearer(auto_error=False)


async def verify_token_from_db(token: str, db: Session) -> Optional[Worker]:
    """
    Verify worker token and return associated worker.

    Args:
        token: Worker registration token
        db: Database session

    Returns:
        Worker if token is valid, None otherwise
    """
    # Hash the token for comparison
    from backend.core.security import hash_worker_token
    token_hash = hash_worker_token(token)

    # Find worker by token_hash
    worker = db.query(Worker).filter(Worker.token_hash == token_hash).first()
    return worker


@router.post("/workers/register-gpu", response_model=GPURegisterResponse)
async def register_gpu(
    request: GPURegisterRequest,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    """
    Register a GPU device to a worker (called by agent).

    This endpoint is called by the agent when it first starts on a GPU.
    The agent uses its worker token to authenticate.

    Args:
        request: GPU registration data from agent
        credentials: Bearer token (worker registration token)
        db: Database session

    Returns:
        GPURegisterResponse: Registration result
    """
    # Extract and verify token
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authorization token"
        )

    token = credentials.credentials
    worker = await verify_token_from_db(token, db)

    if not worker:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )

    gpu_info = request.gpu

    # Check if GPU already registered (by UUID)
    existing_gpu = db.query(GPUDevice).filter(
        GPUDevice.worker_id == worker.id,
        GPUDevice.uuid == gpu_info.gpu_uuid
    ).first()

    if existing_gpu:
        # Already registered, just return success
        return GPURegisterResponse(
            success=True,
            gpu_device_id=existing_gpu.id,
            worker_id=worker.id,
            worker_name=worker.name,
            current_gpu_count=worker.gpu_count,
            expected_gpu_count=worker.expected_gpu_count,
            worker_status=worker.status
        )

    # Extract additional info from extra field
    extra = gpu_info.extra or {}
    gpu_name = extra.get("name", "Unknown GPU")
    hostname = extra.get("hostname", None)
    pci_bus = extra.get("pci_bus", None)

    # Create GPU device record
    gpu_device = GPUDevice(
        worker_id=worker.id,
        uuid=gpu_info.gpu_uuid,
        name=gpu_name,
        vendor=GPUVendor.NVIDIA,  # Default to NVIDIA, can be updated from extra
        index=gpu_info.gpu_index,
        ip=gpu_info.ip,
        port=gpu_info.port,
        hostname=hostname,
        pci_bus=pci_bus,
        core_total=extra.get("core_total"),
        memory_total=gpu_info.memory_total,
        memory_allocated=gpu_info.memory_allocated,
        memory_used=0,  # Initial, will be updated by heartbeat
        memory_utilization_rate=gpu_info.memory_utilization_rate,
        temperature=gpu_info.temperature,
        state=GPUDeviceState.IN_USE,
        status_json={
            "agent_pid": gpu_info.agent_pid,
            "vllm_pid": gpu_info.vllm_pid,
            "registered_at": datetime.now().isoformat()
        }
    )

    db.add(gpu_device)

    # Update worker GPU count
    worker.gpu_count += 1

    # Check if worker is ready
    if worker.expected_gpu_count > 0:
        if worker.gpu_count >= worker.expected_gpu_count:
            worker.status = WorkerStatus.READY

    worker.last_heartbeat_at = datetime.now()

    db.commit()
    db.refresh(gpu_device)
    db.refresh(worker)

    return GPURegisterResponse(
        success=True,
        gpu_device_id=gpu_device.id,
        worker_id=worker.id,
        worker_name=worker.name,
        current_gpu_count=worker.gpu_count,
        expected_gpu_count=worker.expected_gpu_count,
        worker_status=worker.status
    )


@router.post("/heartbeat", response_model=GPUHeartbeatResponse)
async def gpu_heartbeat(
    request: GPUHeartbeatRequest,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    """
    Receive heartbeat from a GPU device (called by agent).

    This endpoint is called periodically (every 30s) by the agent to report
    GPU status and utilization.

    Args:
        request: GPU heartbeat data from agent
        credentials: Bearer token (worker registration token)
        db: Database session

    Returns:
        GPUHeartbeatResponse: Heartbeat acknowledgment
    """
    # Extract and verify token
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authorization token"
        )

    token = credentials.credentials
    worker = await verify_token_from_db(token, db)

    if not worker:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )

    # Find GPU by UUID
    gpu = db.query(GPUDevice).filter(
        GPUDevice.uuid == request.gpu_uuid
    ).first()

    if not gpu:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"GPU {request.gpu_uuid} not found"
        )

    # Update GPU status
    gpu.memory_used = request.memory_used
    gpu.memory_utilization_rate = request.memory_utilization_rate
    gpu.core_utilization_rate = request.core_utilization_rate
    gpu.temperature = request.temperature
    gpu.updated_at = datetime.now()

    # Update status JSON
    status_json = gpu.status_json or {}
    status_json.update({
        "agent_pid": request.agent_pid,
        "vllm_pid": request.vllm_pid,
        "ip": request.ip,
        "port": request.port,
        "last_heartbeat": request.timestamp
    })
    gpu.status_json = status_json

    # Reset state to IN_USE if it was ERROR
    if gpu.state == GPUDeviceState.ERROR:
        gpu.state = GPUDeviceState.IN_USE

    db.commit()

    # Check for alerts (temperature, memory leak)
    await _check_gpu_alerts(gpu)

    return GPUHeartbeatResponse(
        success=True,
        message="Heartbeat received"
    )


@router.post("/heartbeat/batch", response_model=BatchHeartbeatResponse)
async def batch_gpu_heartbeat(
    request: BatchHeartbeatRequest,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    """
    Receive batch heartbeats from multiple GPUs (called by agent).

    Optimized for scenarios where one agent manages multiple GPUs
    on the same physical machine.

    Args:
        request: Batch heartbeat data from agent
        credentials: Bearer token (worker registration token)
        db: Database session

    Returns:
        BatchHeartbeatResponse: Batch heartbeat acknowledgment
    """
    # Extract and verify token
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authorization token"
        )

    token = credentials.credentials
    worker = await verify_token_from_db(token, db)

    if not worker:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )

    updated_count = 0
    worker_id = worker.id

    # Process each heartbeat
    for heartbeat in request.heartbeats:
        # Find GPU by UUID
        gpu = db.query(GPUDevice).filter(
            GPUDevice.uuid == heartbeat.gpu_uuid,
            GPUDevice.worker_id == worker_id
        ).first()

        if not gpu:
            continue  # Skip if GPU not found

        # Update GPU status
        gpu.memory_used = heartbeat.memory_used
        gpu.memory_utilization_rate = heartbeat.memory_utilization_rate
        gpu.core_utilization_rate = heartbeat.core_utilization_rate
        gpu.temperature = heartbeat.temperature
        gpu.updated_at = datetime.now()

        # Update status JSON
        status_json = gpu.status_json or {}
        status_json.update({
            "agent_pid": heartbeat.agent_pid,
            "vllm_pid": heartbeat.vllm_pid,
            "ip": heartbeat.ip,
            "port": heartbeat.port,
            "last_heartbeat": heartbeat.timestamp
        })
        gpu.status_json = status_json

        # Reset state to IN_USE if it was ERROR
        if gpu.state == GPUDeviceState.ERROR:
            gpu.state = GPUDeviceState.IN_USE

        updated_count += 1

    # Update worker heartbeat timestamp
    worker.last_heartbeat_at = datetime.now()

    db.commit()

    return BatchHeartbeatResponse(
        success=True,
        updated_count=updated_count
    )


async def _check_gpu_alerts(gpu: GPUDevice):
    """
    Check for GPU alerts and send notifications if needed.

    Args:
        gpu: GPU device to check
    """
    # Temperature alert
    if gpu.temperature and gpu.temperature > 85:
        await _send_alert(
            alert_type="gpu_overheat",
            severity="critical" if gpu.temperature > 90 else "warning",
            message=f"GPU {gpu.uuid} temperature too high: {gpu.temperature}°C",
            gpu_id=gpu.id
        )

    # Memory leak alert (high utilization but no vLLM running)
    if gpu.memory_utilization_rate and gpu.memory_utilization_rate > 0.95:
        vllm_pid = gpu.status_json.get("vllm_pid") if gpu.status_json else None
        if not vllm_pid:
            await _send_alert(
                alert_type="gpu_memory_leak",
                severity="warning",
                message=f"GPU {gpu.uuid} possible memory leak: {gpu.memory_utilization_rate:.2%}",
                gpu_id=gpu.id
            )


async def _send_alert(
    alert_type: str,
    severity: str,
    message: str,
    gpu_id: int
):
    """
    Send an alert notification.

    This is a placeholder - integrate with your alert system
    (e.g., Prometheus AlertManager, Slack, email, etc.)

    Args:
        alert_type: Type of alert
        severity: Alert severity (info, warning, critical)
        message: Alert message
        gpu_id: Associated GPU ID
    """
    # TODO: Implement alert integration
    # For now, just log the alert
    import logging
    logger = logging.getLogger(__name__)
    logger.warning(
        f"GPU Alert: type={alert_type}, severity={severity}, "
        f"gpu_id={gpu_id}, message={message}"
    )

    # Example integrations:
    # - Send to Slack webhook
    # - Send email via SMTP
    # - Send to Prometheus AlertManager
    # - Write to alerts table for dashboard display
