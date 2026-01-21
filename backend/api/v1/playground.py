"""
Playground API routes for dialogue testing.
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.models.database import ApiKey
from backend.models.schemas import (
    PlaygroundSessionCreate,
    PlaygroundSessionResponse,
    PlaygroundMessageCreate,
    PlaygroundMessageResponse
)
from backend.services.playground_service import PlaygroundService
from backend.api.deps import get_current_db, verify_api_key_auth

router = APIRouter()


@router.post("/sessions", response_model=PlaygroundSessionResponse, status_code=status.HTTP_201_CREATED)
async def create_session(
    session_data: PlaygroundSessionCreate,
    api_key: ApiKey = Depends(verify_api_key_auth),
    db: Session = Depends(get_current_db)
):
    """
    Create a dialogue testing session.

    - **deployment_id**: Deployment ID (optional, used to specify model service)
    - **session_name**: Session name
    - **model_config**: Model configuration parameters
    """
    service = PlaygroundService(db)
    return service.create_session(api_key.user_id, session_data)


@router.get("/sessions", response_model=List[PlaygroundSessionResponse])
async def list_sessions(
    skip: int = 0,
    limit: int = 50,
    api_key: ApiKey = Depends(verify_api_key_auth),
    db: Session = Depends(get_current_db)
):
    """
    Get user's dialogue session list.

    - **skip**: Number of records to skip
    - **limit**: Number of records to return (max 100)
    """
    service = PlaygroundService(db)
    return service.list_sessions(api_key.user_id, skip, limit)


@router.get("/sessions/{session_id}", response_model=PlaygroundSessionResponse)
async def get_session(
    session_id: int,
    api_key: ApiKey = Depends(verify_api_key_auth),
    db: Session = Depends(get_current_db)
):
    """Get session details (including message history)."""
    service = PlaygroundService(db)
    session = service.get_session(session_id, api_key.user_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )
    return session


@router.post("/sessions/{session_id}/messages", response_model=PlaygroundMessageResponse)
async def send_message(
    session_id: int,
    message: PlaygroundMessageCreate,
    api_key: ApiKey = Depends(verify_api_key_auth),
    db: Session = Depends(get_current_db)
):
    """
    Send a message and get AI response.

    - **content**: User message content
    - Returns: Assistant's reply message
    """
    service = PlaygroundService(db)
    try:
        return service.send_message(session_id, api_key.user_id, message.content)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except RuntimeError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e)
        )


@router.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_session(
    session_id: int,
    api_key: ApiKey = Depends(verify_api_key_auth),
    db: Session = Depends(get_current_db)
):
    """Delete a dialogue session."""
    service = PlaygroundService(db)
    try:
        service.delete_session(session_id, api_key.user_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    return None
