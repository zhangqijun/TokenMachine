"""
Dependencies for API routes.
"""
from typing import Generator, Optional
from datetime import datetime
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from loguru import logger

from inferx.core.database import get_db
from inferx.core.security import hash_api_key
from inferx.models.database import ApiKey, User, Deployment

security = HTTPBearer(auto_error=False)


async def get_current_db() -> Generator:
    """Get database session."""
    try:
        db = next(get_db())
        yield db
    finally:
        pass  # Session managed by get_db()


async def verify_api_key_auth(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_current_db)
) -> ApiKey:
    """
    Verify API key and return the ApiKey object.

    Args:
        credentials: HTTP Bearer credentials
        db: Database session

    Returns:
        ApiKey object

    Raises:
        HTTPException: If authentication fails
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    api_key = credentials.credentials
    key_hash = hash_api_key(api_key)

    api_key_obj = db.query(ApiKey).filter(
        ApiKey.key_hash == key_hash,
        ApiKey.is_active == True
    ).first()

    if not api_key_obj:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Check expiration
    if api_key_obj.expires_at and api_key_obj.expires_at < datetime.now():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key expired",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Update last used
    from datetime import datetime
    api_key_obj.last_used_at = datetime.now()
    db.commit()

    return api_key_obj


async def verify_admin_access(
    api_key: ApiKey = Depends(verify_api_key_auth),
    db: Session = Depends(get_current_db)
) -> User:
    """
    Verify admin access and return the User object.

    Args:
        api_key: Verified API key
        db: Database session

    Returns:
        User object with admin privileges

    Raises:
        HTTPException: If user is not an admin
    """
    user = db.query(User).filter(User.id == api_key.user_id).first()

    if not user or not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )

    return user


async def get_deployment_by_name(
    model_name: str,
    db: Session = Depends(get_current_db)
) -> Deployment:
    """
    Get deployment by model name.

    Args:
        model_name: Deployment/model name
        db: Database session

    Returns:
        Deployment object

    Raises:
        HTTPException: If deployment not found
    """
    deployment = db.query(Deployment).filter(
        Deployment.name == model_name,
        Deployment.status == "running"
    ).first()

    if not deployment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Model '{model_name}' not found or not running"
        )

    return deployment


# Export get_db for use in main
__all__ = [
    "get_current_db",
    "verify_api_key_auth",
    "verify_admin_access",
    "get_deployment_by_name",
]
