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
import bcrypt
from loguru import logger

from backend.core.config import get_settings

settings = get_settings()


def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    password_bytes = password.encode('utf-8')[:72]  # Truncate to 72 bytes max
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode('utf-8')


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against a hash using bcrypt."""
    try:
        password_bytes = plain_password.encode('utf-8')[:72]  # Truncate to 72 bytes max
        hash_bytes = hashed_password.encode('utf-8')
        return bcrypt.checkpw(password_bytes, hash_bytes)
    except Exception as e:
        logger.warning(f"Password verification failed: {e}")
        return False


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


# ============================================================================
# Worker Registration Token Management
# ============================================================================

def generate_worker_token() -> str:
    """
    Generate a unique worker registration token.

    Returns:
        str: Token in format "tm_worker_<random>"

    Example:
        >>> token = generate_worker_token()
        >>> print(token)
        tm_worker_abc123xyz789def456
    """
    random_part = secrets.token_urlsafe(24)
    token = f"tm_worker_{random_part}"
    return token


def hash_worker_token(token: str) -> str:
    """
    Hash a worker token for storage in database.

    Args:
        token: Worker registration token

    Returns:
        str: SHA256 hash of the token
    """
    return hashlib.sha256(token.encode()).hexdigest()


def verify_worker_token(token: str, token_hash: str) -> bool:
    """
    Verify a worker token against its hash.

    Args:
        token: Worker registration token to verify
        token_hash: Stored hash of the token

    Returns:
        bool: True if token matches hash
    """
    return hash_worker_token(token) == token_hash
