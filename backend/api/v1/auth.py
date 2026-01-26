"""
Authentication API endpoints for user login and API key management.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from loguru import logger

from backend.api.deps import get_current_db
from backend.core.security import verify_password, generate_api_key, hash_api_key
from backend.models.database import User, ApiKey
from backend.models.schemas import ApiKeyResponse

router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])


# ============================================================================
# Request/Response Schemas
# ============================================================================

class LoginRequest(BaseModel):
    """Login request schema."""
    username: str = Field(..., min_length=1, max_length=255)
    password: str = Field(..., min_length=1)


class LoginResponse(BaseModel):
    """Login response schema."""
    access_token: str
    token_type: str = "bearer"
    user: dict


class CreateApiKeyRequest(BaseModel):
    """Create API key request schema."""
    name: str = Field(..., min_length=1, max_length=100)
    quota_tokens: int = Field(default=100000, ge=0)


# ============================================================================
# Login Endpoint
# ============================================================================

@router.post("/login", response_model=LoginResponse)
async def login(
    data: LoginRequest,
    db: Session = Depends(get_current_db)
):
    """
    Authenticate user with username and password.

    Returns an API key that can be used for subsequent requests.
    """
    # Find user by username
    user = db.query(User).filter(User.username == data.username).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password"
        )

    # Verify password
    if not verify_password(data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password"
        )

    # Check if user is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled"
        )

    # Get or create default API key for this user
    api_key = db.query(ApiKey).filter(
        ApiKey.user_id == user.id,
        ApiKey.name == f"{user.username}-default-key"
    ).first()

    if not api_key or not api_key.is_active:
        # Generate new API key
        raw_key = generate_api_key(user.id)
        key_hash = hash_api_key(raw_key)
        # Extract prefix from the key (first 8 chars for display)
        key_prefix = raw_key[:8]

        api_key = ApiKey(
            user_id=user.id,
            organization_id=user.organization_id,
            name=f"{user.username}-default-key",
            key_hash=key_hash,
            key_prefix=key_prefix,
            quota_tokens=1000000,
            is_active=True
        )
        db.add(api_key)
        db.commit()
        db.refresh(api_key)

        # Return the raw key (only shown once)
        access_token = raw_key
    else:
        # Return a placeholder (key already exists)
        # In production, you might want to create a new key or show a different approach
        raw_key = generate_api_key(user.id)
        key_hash = hash_api_key(raw_key)
        key_prefix = raw_key[:8]

        api_key.key_hash = key_hash
        api_key.key_prefix = key_prefix
        api_key.is_active = True
        db.commit()
        access_token = raw_key

    logger.info(f"User {user.username} logged in successfully")

    return LoginResponse(
        access_token=access_token,
        user={
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "role": user.role.value,
            "organization_id": user.organization_id
        }
    )


# ============================================================================
# API Key Management
# ============================================================================

@router.post("/api-keys", response_model=ApiKeyResponse, status_code=status.HTTP_201_CREATED)
async def create_api_key(
    data: CreateApiKeyRequest,
    db: Session = Depends(get_current_db)
):
    """
    Create a new API key for authenticated user.

    Note: This endpoint requires authentication via existing API key.
    For creating the first API key, use the /login endpoint.
    """
    from backend.api.deps import verify_api_key_auth

    # Verify existing API key
    existing_key = await verify_api_key_auth(db=db)
    user = db.query(User).filter(User.id == existing_key.user_id).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Generate new API key
    raw_key = generate_api_key(user.id)
    key_hash = hash_api_key(raw_key)

    api_key = ApiKey(
        user_id=user.id,
        name=data.name,
        key_hash=key_hash,
        quota_tokens=data.quota_tokens,
        is_active=True
    )
    db.add(api_key)
    db.commit()
    db.refresh(api_key)

    logger.info(f"User {user.username} created new API key: {data.name}")

    # Return response with the raw key (only shown once)
    return ApiKeyResponse(
        id=api_key.id,
        name=api_key.name,
        key=raw_key,  # Only shown on creation
        prefix=raw_key[:20] + "...",
        quota_tokens=api_key.quota_tokens,
        used_tokens=api_key.used_tokens,
        is_active=api_key.is_active,
        created_at=api_key.created_at,
        expires_at=api_key.expires_at,
        last_used_at=api_key.last_used_at
    )


@router.get("/api-keys", response_model=list[ApiKeyResponse])
async def list_api_keys(
    db: Session = Depends(get_current_db)
):
    """List all API keys for authenticated user."""
    from backend.api.deps import verify_api_key_auth

    existing_key = await verify_api_key_auth(db=db)

    api_keys = db.query(ApiKey).filter(ApiKey.user_id == existing_key.user_id).all()

    return [
        ApiKeyResponse(
            id=key.id,
            name=key.name,
            key=None,  # Never show full key in list
            prefix=f"tmachine_sk_{key.id}_...",
            quota_tokens=key.quota_tokens,
            used_tokens=key.used_tokens,
            is_active=key.is_active,
            created_at=key.created_at,
            expires_at=key.expires_at,
            last_used_at=key.last_used_at
        )
        for key in api_keys
    ]
