"""
Backend Engine Management API - inference engine management endpoints.

This module provides REST API endpoints for managing backend inference engines,
including listing, installing, and deleting engine versions.
"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.core.database import get_db
from backend.models.database import BackendEngineType
from backend.models.schemas import (
    BackendEngineInfo,
    BackendEngineListResponse,
    BackendEngineInstallRequest,
    BackendEngineInstallResponse,
    BackendEngineStatsResponse,
)
from backend.services.backend_engine_service import BackendEngineService

router = APIRouter(prefix="/backends", tags=["backends"])


@router.get("", response_model=BackendEngineListResponse)
async def list_backends(
    engine_type: Optional[BackendEngineType] = None,
    db: Session = Depends(get_db)
):
    """
    List all installed inference engines.

    Args:
        engine_type: Optional filter by engine type (vllm, sglang, llama_cpp)
        db: Database session

    Returns:
        BackendEngineListResponse: List of engines with metadata
    """
    try:
        engines = BackendEngineService.list_engines(db, engine_type)
        return BackendEngineListResponse(
            items=engines,
            total=len(engines)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list backends: {str(e)}"
        )


@router.post("/{engine_type}/install", response_model=BackendEngineInstallResponse)
async def install_backend(
    engine_type: BackendEngineType,
    request: BackendEngineInstallRequest,
    db: Session = Depends(get_db)
):
    """
    Install a specific version of an inference engine.

    This creates a fake tarball file for now. In production, it would:
    - Pull the Docker image
    - Save it as a tarball
    - Store metadata in database

    Args:
        engine_type: Type of engine to install (vllm, sglang, llama_cpp)
        request: Installation request with version and optional configuration
        db: Database session

    Returns:
        BackendEngineInstallResponse: Installation result with install command

    Raises:
        HTTPException 400: If engine is already installed or installation fails
        HTTPException 500: If server error occurs
    """
    try:
        engine = BackendEngineService.install_engine(db, engine_type, request)

        # Generate install command for display purposes
        install_command = None
        if engine_type == BackendEngineType.VLLM:
            install_command = f"docker pull {engine.image_name}"
        elif engine_type == BackendEngineType.SGLANG:
            install_command = f"docker pull {engine.image_name}"
        elif engine_type == BackendEngineType.LLAMA_CPP:
            install_command = f"pip install llama-cpp-python=={request.version}"

        return BackendEngineInstallResponse(
            id=engine.id,
            engine_type=engine.engine_type.value,
            version=engine.version,
            status=engine.status.value,
            install_command=install_command,
            message=f"Successfully installed {engine_type.value} {request.version}"
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Installation failed: {str(e)}"
        )


@router.delete("/{engine_type}/{version}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_backend(
    engine_type: BackendEngineType,
    version: str,
    db: Session = Depends(get_db)
):
    """
    Delete a specific version of an inference engine.

    The engine cannot be deleted if it has active deployments.

    Args:
        engine_type: Type of engine to delete (vllm, sglang, llama_cpp)
        version: Version string to delete
        db: Database session

    Raises:
        HTTPException 400: If engine has active deployments or not found
        HTTPException 500: If server error occurs
    """
    try:
        BackendEngineService.delete_engine(db, engine_type, version)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Deletion failed: {str(e)}"
        )


@router.get("/{engine_type}/{version}/stats", response_model=BackendEngineStatsResponse)
async def get_backend_stats(
    engine_type: BackendEngineType,
    version: str,
    db: Session = Depends(get_db)
):
    """
    Get statistics for a specific engine version.

    Args:
        engine_type: Type of engine (vllm, sglang, llama_cpp)
        version: Version string
        db: Database session

    Returns:
        BackendEngineStatsResponse: Engine statistics

    Raises:
        HTTPException 404: If engine not found
        HTTPException 500: If server error occurs
    """
    try:
        stats = BackendEngineService.get_engine_stats(db, engine_type, version)
        return BackendEngineStatsResponse(**stats)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get stats: {str(e)}"
        )
