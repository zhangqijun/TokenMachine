"""
Security utilities for TokenMachine.
"""
import os
import re
import secrets
import hashlib
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext

from backend.core.config import get_settings

settings = get_settings()

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """Hash a password."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against a hash."""
    return pwd_context.verify(plain_password, hashed_password)


def generate_api_key(user_id: int) -> str:
    """Generate a unique API key."""
    random_part = secrets.token_urlsafe(settings.api_key_length)
    key_material = f"{user_id}:{random_part}:{datetime.now().timestamp()}"
    hash_part = hashlib.sha256(key_material.encode()).hexdigest()[:8]
    api_key = f"{settings.api_key_prefix}{random_part[:16]}{hash_part}"
    return api_key


def hash_api_key(api_key: str) -> str:
    """Hash an API key for storage."""
    return hashlib.sha256(api_key.encode()).hexdigest()


def verify_api_key(api_key: str, key_hash: str) -> bool:
    """Verify an API key against its hash."""
    return hash_api_key(api_key) == key_hash


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.access_token_expire_minutes)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm="HS256")
    return encoded_jwt


def decode_access_token(token: str) -> Optional[dict]:
    """Decode and verify a JWT access token."""
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=["HS256"])
        return payload
    except JWTError:
        return None


def generate_request_id() -> str:
    """Generate a unique request ID."""
    return f"req_{secrets.token_hex(16)}"


def sanitize_filename(filename: str) -> str:
    """Sanitize a filename for safe storage."""
    # Remove any path components
    filename = os.path.basename(filename)
    # Replace special characters with underscores
    filename = re.sub(r'[^\w\-_\.]', '_', filename)
    return filename
