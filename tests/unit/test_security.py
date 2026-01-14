"""
Unit tests for the security module.
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import patch

from inferx.core.security import (
    hash_password,
    verify_password,
    generate_api_key,
    hash_api_key,
    verify_api_key,
    create_access_token,
    decode_access_token,
    generate_request_id,
    sanitize_filename
)


class TestPasswordHashing:
    """Test password hashing and verification."""

    def test_hash_password_returns_different_hashes(self):
        """Test that hashing the same password twice produces different hashes (salt)."""
        password = "testpassword123"
        hash1 = hash_password(password)
        hash2 = hash_password(password)
        assert hash1 != hash2

    def test_verify_password_correct(self):
        """Test verifying a correct password."""
        password = "testpassword123"
        hashed = hash_password(password)
        assert verify_password(password, hashed) is True

    def test_verify_password_incorrect(self):
        """Test verifying an incorrect password."""
        password = "testpassword123"
        wrong_password = "wrongpassword"
        hashed = hash_password(password)
        assert verify_password(wrong_password, hashed) is False

    def test_verify_empty_password(self):
        """Test verifying against empty password hash."""
        assert verify_password("", hash_password("")) is True
        assert verify_password("test", hash_password("")) is False


class TestAPIKeyGeneration:
    """Test API key generation and verification."""

    def test_generate_api_key_has_prefix(self):
        """Test that generated API key has correct prefix."""
        with patch("inferx.core.security.settings.api_key_prefix", "test_sk_"):
            api_key = generate_api_key(123)
            assert api_key.startswith("test_sk_")

    def test_generate_api_key_length(self):
        """Test that generated API key has expected length."""
        with patch("inferx.core.security.settings.api_key_length", 16):
            api_key = generate_api_key(123)
            # prefix + 16 chars + 8 char hash
            assert len(api_key) >= 20

    def test_generate_api_keys_are_unique(self):
        """Test that generating multiple keys produces different values."""
        key1 = generate_api_key(123)
        key2 = generate_api_key(123)
        assert key1 != key2

    def test_hash_api_key_is_consistent(self):
        """Test that hashing the same API key produces the same result."""
        api_key = "test_api_key_12345"
        hash1 = hash_api_key(api_key)
        hash2 = hash_api_key(api_key)
        assert hash1 == hash2

    def test_hash_api_key_is_deterministic(self):
        """Test that hash is deterministic."""
        api_key = "test_api_key_12345"
        expected_hash = "9f7356300a79e330e174c9e870a297067e27a35102138666782b6e76e75b0e6e"
        assert hash_api_key(api_key) == expected_hash

    def test_verify_api_key_correct(self):
        """Test verifying a correct API key."""
        api_key = "test_api_key_12345"
        key_hash = hash_api_key(api_key)
        assert verify_api_key(api_key, key_hash) is True

    def test_verify_api_key_incorrect(self):
        """Test verifying an incorrect API key."""
        api_key = "test_api_key_12345"
        wrong_key = "wrong_api_key_67890"
        key_hash = hash_api_key(api_key)
        assert verify_api_key(wrong_key, key_hash) is False


class TestJWTTokens:
    """Test JWT token creation and verification."""

    def test_create_access_token(self):
        """Test creating an access token."""
        data = {"sub": "123", "username": "testuser"}
        token = create_access_token(data)
        assert isinstance(token, str)
        assert len(token) > 0

    def test_create_access_token_with_custom_expiration(self):
        """Test creating a token with custom expiration."""
        data = {"sub": "123"}
        expires = timedelta(minutes=30)
        token = create_access_token(data, expires)
        assert isinstance(token, str)

    def test_decode_valid_token(self):
        """Test decoding a valid token."""
        data = {"sub": "123", "username": "testuser"}
        token = create_access_token(data)
        decoded = decode_access_token(token)
        assert decoded is not None
        assert decoded["sub"] == "123"
        assert decoded["username"] == "testuser"
        assert "exp" in decoded

    def test_decode_invalid_token(self):
        """Test decoding an invalid token."""
        invalid_token = "invalid.token.here"
        decoded = decode_access_token(invalid_token)
        assert decoded is None

    def test_decode_expired_token(self, monkeypatch):
        """Test decoding an expired token."""
        # Create a token that's already expired
        data = {"sub": "123"}
        expires = timedelta(seconds=-1)  # Already expired
        token = create_access_token(data, expires)
        decoded = decode_access_token(token)
        assert decoded is None


class TestUtilityFunctions:
    """Test utility functions."""

    def test_generate_request_id(self):
        """Test generating a request ID."""
        request_id = generate_request_id()
        assert isinstance(request_id, str)
        assert request_id.startswith("req_")
        assert len(request_id) > 4  # "req_" + hex characters

    def test_generate_request_ids_are_unique(self):
        """Test that request IDs are unique."""
        id1 = generate_request_id()
        id2 = generate_request_id()
        assert id1 != id2

    def test_sanitize_filename_removes_path(self):
        """Test that sanitize_filename removes path components."""
        filename = sanitize_filename("/etc/passwd")
        assert "etc" not in filename or filename == "passwd"
        assert "/" not in filename

    def test_sanitize_filename_replaces_special_chars(self):
        """Test that sanitize_filename replaces special characters."""
        filename = sanitize_filename("test@#$%file.txt")
        assert "@" not in filename
        assert "#" not in filename
        assert "$" not in filename
        assert "%" not in filename

    def test_sanitize_filename_keeps_safe_chars(self):
        """Test that sanitize_filename keeps safe characters."""
        filename = sanitize_filename("test_file-123.txt")
        assert "test_file-123.txt" == filename

    def test_sanitize_filename_handles_windows_paths(self):
        """Test that sanitize_filename handles Windows paths."""
        filename = sanitize_filename("C:\\Users\\Test\\file.txt")
        assert "\\" not in filename
        assert ":" not in filename


class TestSecurityEdgeCases:
    """Test edge cases in security functions."""

    def test_hash_empty_string(self):
        """Test hashing an empty string."""
        result = hash_api_key("")
        assert isinstance(result, str)
        assert len(result) == 64  # SHA-256 hex length

    def test_verify_with_empty_hash(self):
        """Test verification with empty hash."""
        assert verify_api_key("test", "") is False

    def test_token_with_empty_data(self):
        """Test creating token with empty data."""
        token = create_access_token({})
        assert isinstance(token, str)
        decoded = decode_access_token(token)
        assert decoded is not None
        assert "exp" in decoded
