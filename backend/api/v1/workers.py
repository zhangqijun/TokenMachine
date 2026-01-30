"""
Worker management API endpoints.

This module provides endpoints for managing GPU workers, which are logical
collections of GPU devices that can span across multiple physical machines.
"""
from typing import Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.core.database import get_db
from backend.core.security import generate_worker_token, hash_worker_token
from backend.models.database import Worker, Cluster, WorkerStatus, GPUDevice, GPUDeviceState
from backend.models.database import ClusterStatus
from backend.models.schemas import (
    WorkerCreate,
    WorkerUpdate,
    WorkerResponse,
    WorkerCreateResponse,
    WorkerListResponse,
    WorkerAddGPUResponse,
    WorkerRegisterResponse,
)

router = APIRouter(prefix="/workers", tags=["workers"])


def get_default_cluster(db: Session) -> Cluster:
    """Get or create default cluster."""
    cluster = db.query(Cluster).filter(Cluster.is_default == True).first()
    if not cluster:
        cluster = Cluster(
            name="default",
            type="standalone",
            is_default=True,
            status=ClusterStatus.RUNNING
        )
        db.add(cluster)
        db.commit()
        db.refresh(cluster)
    return cluster


@router.post("", response_model=WorkerCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_worker(
    request: WorkerCreate,
    db: Session = Depends(get_db)
):
    """
    Create a new Worker.

    Worker is a logical concept that represents a collection of GPU devices.
    GPUs can be from different physical machines but share the same registration token.

    Returns:
        WorkerCreateResponse: Created worker with registration token (only returned once)
    """
    # Get cluster (default or specified)
    if request.cluster_id:
        cluster = db.query(Cluster).filter(Cluster.id == request.cluster_id).first()
        if not cluster:
            raise HTTPException(status_code=404, detail="Cluster not found")
    else:
        cluster = get_default_cluster(db)

    # Check if worker name already exists in this cluster
    existing_worker = db.query(Worker).filter(
        Worker.cluster_id == cluster.id,
        Worker.name == request.name
    ).first()
    if existing_worker:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Worker '{request.name}' already exists in this cluster"
        )

    # Generate registration token
    register_token = generate_worker_token()
    token_hash = hash_worker_token(register_token)

    # Create worker
    worker = Worker(
        name=request.name,
        cluster_id=cluster.id,
        status=WorkerStatus.REGISTERING,
        token_hash=token_hash,
        labels=request.labels,
        expected_gpu_count=request.expected_gpu_count or 0,
        gpu_count=0
    )

    db.add(worker)
    db.commit()
    db.refresh(worker)

    # Construct install command
    install_command = (
        f"TM_TOKEN={register_token} "
        f"TM_GPU_ID=<GPU_ID> "
        f"curl -sfL https://get.tokenmachine.io | bash -"
    )

    return WorkerCreateResponse(
        id=worker.id,
        name=worker.name,
        status=worker.status,
        register_token=register_token,  # Only returned once
        install_command=install_command,
        expected_gpu_count=worker.expected_gpu_count,
        current_gpu_count=0,
        created_at=worker.created_at
    )


@router.get("", response_model=WorkerListResponse)
async def list_workers(
    cluster_id: Optional[int] = None,
    status: Optional[WorkerStatus] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """
    List all workers with optional filtering.

    Args:
        cluster_id: Filter by cluster ID
        status: Filter by worker status
        page: Page number (1-indexed)
        page_size: Number of items per page

    Returns:
        WorkerListResponse: Paginated list of workers
    """
    query = db.query(Worker)

    # Apply filters
    if cluster_id:
        query = query.filter(Worker.cluster_id == cluster_id)
    if status:
        query = query.filter(Worker.status == status)

    # Get total count
    total = query.count()

    # Apply pagination
    workers = query.offset((page - 1) * page_size).limit(page_size).all()

    return WorkerListResponse(
        items=workers,
        total=total,
        page=page,
        page_size=page_size
    )


@router.get("/{worker_id}", response_model=WorkerResponse)
async def get_worker(
    worker_id: int,
    db: Session = Depends(get_db)
):
    """
    Get worker details by ID.

    Args:
        worker_id: Worker ID

    Returns:
        WorkerResponse: Worker details with GPU list
    """
    worker = db.query(Worker).filter(Worker.id == worker_id).first()
    if not worker:
        raise HTTPException(status_code=404, detail="Worker not found")

    return worker


@router.post("/{worker_id}/add-gpu", response_model=WorkerAddGPUResponse)
async def get_add_gpu_token(
    worker_id: int,
    db: Session = Depends(get_db)
):
    """
    Get token for adding more GPUs to an existing worker.

    This allows dynamically adding GPUs to a worker that's already registered.

    Args:
        worker_id: Worker ID

    Returns:
        WorkerAddGPUResponse: Token and install command for adding GPUs
    """
    worker = db.query(Worker).filter(Worker.id == worker_id).first()
    if not worker:
        raise HTTPException(status_code=404, detail="Worker not found")

    # Generate new token (reuses existing token_hash logic)
    # For security, we could create a new token, but for simplicity we reuse
    # The token_hash would be updated in the database
    register_token = generate_worker_token()
    worker.token_hash = hash_worker_token(register_token)
    db.commit()

    install_command = (
        f"TM_TOKEN={register_token} "
        f"TM_GPU_ID=<GPU_ID> "
        f"curl -sfL https://get.tokenmachine.io | bash -"
    )

    return WorkerAddGPUResponse(
        register_token=register_token,
        install_command=install_command,
        message=f"Use this token to add more GPUs to worker '{worker.name}'"
    )


@router.put("/{worker_id}", response_model=WorkerResponse)
async def update_worker(
    worker_id: int,
    request: WorkerUpdate,
    db: Session = Depends(get_db)
):
    """
    Update worker details.

    Args:
        worker_id: Worker ID
        request: Update data

    Returns:
        WorkerResponse: Updated worker details
    """
    worker = db.query(Worker).filter(Worker.id == worker_id).first()
    if not worker:
        raise HTTPException(status_code=404, detail="Worker not found")

    # Update fields
    if request.labels is not None:
        worker.labels = request.labels
    if request.status is not None:
        worker.status = request.status
    if request.expected_gpu_count is not None:
        worker.expected_gpu_count = request.expected_gpu_count

    db.commit()
    db.refresh(worker)

    return worker


@router.delete("/{worker_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_worker(
    worker_id: int,
    db: Session = Depends(get_db)
):
    """
    Delete a worker.

    This will also delete all associated GPU devices.
    Worker with running model instances cannot be deleted.

    Args:
        worker_id: Worker ID
    """
    worker = db.query(Worker).filter(Worker.id == worker_id).first()
    if not worker:
        raise HTTPException(status_code=404, detail="Worker not found")

    # Check if worker has GPUs in use
    active_gpus = db.query(GPUDevice).filter(
        GPUDevice.worker_id == worker_id,
        GPUDevice.state == GPUDeviceState.IN_USE
    ).count()

    if active_gpus > 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot delete worker with {active_gpus} active GPUs. "
                   f"Please stop all GPUs before deleting the worker."
        )

    db.delete(worker)
    db.commit()

    return None


@router.post("/{worker_id}/set-status")
async def set_worker_status(
    worker_id: int,
    new_status: WorkerStatus,
    db: Session = Depends(get_db)
):
    """
    Manually set worker status.

    Useful for maintenance or recovery operations.

    Args:
        worker_id: Worker ID
        new_status: New worker status

    Returns:
        dict: Success message
    """
    worker = db.query(Worker).filter(Worker.id == worker_id).first()
    if not worker:
        raise HTTPException(status_code=404, detail="Worker not found")

    worker.status = new_status
    db.commit()

    return {
        "success": True,
        "message": f"Worker status updated to {new_status}",
        "worker_id": worker.id,
        "new_status": new_status
    }


@router.post("/register", response_model=WorkerRegisterResponse)
async def register_worker_with_token(
    request: dict,
    db: Session = Depends(get_db),
):
    """
    Register worker with IP connectivity verification.

    This endpoint allows workers to register themselves using a pre-generated token
    or auto-creates a worker if the token doesn't exist yet.
    """
    # Extract required fields from request
    token = request.get("token")
    if not token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token is required"
        )

    hostname = request.get("hostname", "")
    ip = request.get("ip", "")
    total_gpu_count = request.get("total_gpu_count", 0)
    selected_gpu_count = request.get("selected_gpu_count", 0)
    gpu_models = request.get("gpu_models", [])
    gpu_memorys = request.get("gpu_memorys", [])
    selected_indices = request.get("selected_indices", [])
    capabilities = request.get("capabilities", ["vLLM", "SGLang"])
    agent_type = request.get("agent_type", "gpu")
    agent_version = request.get("agent_version", "1.0.0")

    # Find worker by token hash
    import hashlib
    from backend.core.security import hash_worker_token

    token_hash = hash_worker_token(token)
    worker = db.query(Worker).filter(Worker.token_hash == token_hash).first()

    # Auto-create worker if not found (for easier testing and deployment)
    if not worker:
        print(f"[Worker Registration] Worker not found with token, auto-creating...")

        # Get default cluster
        cluster = get_default_cluster(db)

        # Generate worker name from hostname
        worker_name = f"{hostname or 'unknown'}-gpu-{token[:8]}"

        # Check if worker name already exists
        existing_worker = db.query(Worker).filter(
            Worker.cluster_id == cluster.id,
            Worker.name == worker_name
        ).first()

        if existing_worker:
            # Use existing worker
            worker = existing_worker
            print(f"[Worker Registration] Found existing worker: {worker_name}")
        else:
            # Create new worker
            worker = Worker(
                name=worker_name,
                cluster_id=cluster.id,
                status=WorkerStatus.REGISTERING,
                token_hash=token_hash,
                labels={},
                expected_gpu_count=selected_gpu_count,
                gpu_count=0
            )

            db.add(worker)
            db.commit()
            db.refresh(worker)

            print(f"[Worker Registration] Auto-created worker: {worker_name} (ID: {worker.id})")

    # Verify worker IP connectivity (basic check)
    if not ip:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="IP address is required"
        )

    # Update worker information
    worker.hostname = hostname
    worker.status = WorkerStatus.READY
    worker.ip = ip
    worker.gpu_count = selected_gpu_count
    worker.capabilities = capabilities
    worker.agent_type = agent_type
    worker.agent_version = agent_version
    worker.last_heartbeat_at = datetime.utcnow()

    # Update GPU information
    # Remove existing GPUs first
    existing_gpus = db.query(GPUDevice).filter(GPUDevice.worker_id == worker.id).all()
    for gpu in existing_gpus:
        db.delete(gpu)

    # Add selected GPUs
    for i, idx in enumerate(selected_indices):
        if i < len(gpu_models) and i < len(gpu_memorys):
            # Convert MB to bytes
            memory_bytes = int(gpu_memorys[i]) * 1024 * 1024 if gpu_memorys[i].isdigit() else 0

            gpu = GPUDevice(
                worker_id=worker.id,
                uuid=f"gpu-{worker.id}-{idx}",
                name=gpu_models[i],  # GPU model name (e.g., "RTX3090")
                index=idx,
                ip=ip,
                port=9001,
                hostname=hostname,
                memory_total=memory_bytes,
                memory_utilization_rate=0.0,
                core_utilization_rate=0.0,
                temperature=0.0,
                state=GPUDeviceState.AVAILABLE
            )
            db.add(gpu)

    db.commit()
    db.refresh(worker)

    # Generate worker secret for authentication
    import secrets
    worker_secret = f"worker_{secrets.token_urlsafe(32)}"

    return WorkerRegisterResponse(
        worker_id=worker.id,
        worker_secret=worker_secret
    )


@router.post("/verify-ips")
async def verify_ip_connectivity(
    request: dict,
    db: Session = Depends(get_db),
):
    """
    Verify connectivity to multiple IP addresses.

    This endpoint tests connectivity to multiple IP addresses and returns
    a list of IPs that are reachable from the server.

    Args:
        request: Dictionary containing a list of IPs to test
            - "ips": List of IP addresses to test
            - "timeout": Test timeout in seconds (default: 5)
            - "port": Port to test (default: 80)

    Returns:
        Dictionary with connectivity results
    """
    import asyncio
    from concurrent.futures import ThreadPoolExecutor
    import socket
    import struct

    # Extract parameters from request
    ips_to_test = request.get("ips", [])
    timeout = request.get("timeout", 5)

    if not ips_to_test:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="IP list is required"
        )

    log_info = f"Testing connectivity to {len(ips_to_test)} IPs with {timeout}s timeout (using ping)"
    print(f"[IP Verification] {log_info}")

    # Function to test a single IP using ping
    def test_single_ip(ip, timeout):
        """Test connectivity to a single IP address using ping."""
        try:
            import subprocess
            import re

            # Build ping command
            ping_cmd = ["ping", "-c", "1", "-W", str(timeout), ip]

            # Run ping command
            result = subprocess.run(
                ping_cmd,
                capture_output=True,
                text=True,
                timeout=timeout + 2
            )

            # Parse ping output to get response time
            response_time = None
            if result.returncode == 0:
                # Extract response time from ping output
                # Example: "rtt min/avg/max/mdev = 0.045/0.045/0.045/0.000 ms"
                time_match = re.search(r'rtt min/avg/max/mdev = [\d.]+/([\d.]+)/', result.stdout)
                if time_match:
                    response_time = float(time_match.group(1))

            return {
                "ip": ip,
                "reachable": result.returncode == 0,
                "response_time": response_time,
                "ping_output": result.stdout if result.returncode == 0 else result.stderr
            }

        except Exception as e:
            return {
                "ip": ip,
                "reachable": False,
                "error": str(e),
                "response_time": None
            }

    # Test all IPs in parallel
    results = []
    with ThreadPoolExecutor(max_workers=10) as executor:
        # Submit all tasks
        future_to_ip = {
            executor.submit(test_single_ip, ip, timeout): ip
            for ip in ips_to_test
        }

        # Collect results as they complete
        for future in future_to_ip:
            result = future.result()
            results.append(result)

    # Separate reachable and unreachable IPs
    reachable_ips = [r["ip"] for r in results if r["reachable"]]
    unreachable_ips = [r["ip"] for r in results if not r["reachable"]]

    # Calculate statistics
    total_ips = len(ips_to_test)
    reachable_count = len(reachable_ips)
    success_rate = (reachable_count / total_ips) * 100 if total_ips > 0 else 0

    # Log results
    print(f"[IP Verification] Complete: {reachable_count}/{total_ips} IPs reachable ({success_rate:.1f}%)")
    print(f"[IP Verification] Reachable: {reachable_ips}")
    print(f"[IP Verification] Unreachable: {unreachable_ips}")

    return {
        "total_ips": total_ips,
        "reachable_count": reachable_count,
        "unreachable_count": len(unreachable_ips),
        "success_rate": success_rate,
        "reachable_ips": reachable_ips,
        "unreachable_ips": unreachable_ips,
        "test_details": results,
        "timeout": timeout,
        "test_method": "ping"
    }


@router.get("/{worker_id}/stats")
async def get_worker_stats(
    worker_id: int,
    db: Session = Depends(get_db)
):
    """
    Get worker statistics including GPU utilization.

    Args:
        worker_id: Worker ID

    Returns:
        dict: Worker statistics
    """
    worker = db.query(Worker).filter(Worker.id == worker_id).first()
    if not worker:
        raise HTTPException(status_code=404, detail="Worker not found")

    # Get GPU stats
    gpus = db.query(GPUDevice).filter(GPUDevice.worker_id == worker_id).all()

    total_gpus = len(gpus)
    in_use_gpus = len([g for g in gpus if g.state == GPUDeviceState.IN_USE])
    error_gpus = len([g for g in gpus if g.state == GPUDeviceState.ERROR])

    # Calculate average utilization
    if gpus:
        avg_memory_util = sum(g.memory_utilization_rate or 0 for g in gpus) / len(gpus)
        avg_core_util = sum(g.core_utilization_rate or 0 for g in gpus) / len(gpus)
        avg_temperature = sum(g.temperature or 0 for g in gpus) / len(gpus)
    else:
        avg_memory_util = 0.0
        avg_core_util = 0.0
        avg_temperature = 0.0

    return {
        "worker_id": worker.id,
        "worker_name": worker.name,
        "status": worker.status,
        "total_gpus": total_gpus,
        "in_use_gpus": in_use_gpus,
        "error_gpus": error_gpus,
        "avg_memory_utilization": round(avg_memory_util, 2),
        "avg_core_utilization": round(avg_core_util, 2),
        "avg_temperature": round(avg_temperature, 2),
        "last_heartbeat_at": worker.last_heartbeat_at
    }
