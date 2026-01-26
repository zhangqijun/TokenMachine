"""
Integration tests for Authentication API.

Tests admin user login and API key generation.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session


pytestmark = pytest.mark.integration


class TestAdminLogin:
    """Tests for admin user login via /api/v1/auth/login."""

    def test_admin_login_success(self, client: TestClient):
        """Test successful admin login with correct credentials."""
        response = client.post(
            "/api/v1/auth/login",
            json={
                "username": "admin",
                "password": "admin123"
            }
        )

        assert response.status_code == 200
        data = response.json()

        # Verify response structure
        assert "access_token" in data
        assert "token_type" in data
        assert "user" in data

        # Verify token type
        assert data["token_type"] == "bearer"

        # Verify access token format (should start with prefix)
        assert len(data["access_token"]) > 20
        assert "tmachine" in data["access_token"]

        # Verify user info
        user = data["user"]
        assert user["username"] == "admin"
        assert user["email"] == "admin@tokenmachine.local"
        assert user["role"] == "admin"
        assert "id" in user
        assert "organization_id" in user

        print(f"✓ Admin login successful. API Key: {data['access_token'][:20]}...")

    def test_admin_login_wrong_password(self, client: TestClient):
        """Test admin login with incorrect password."""
        response = client.post(
            "/api/v1/auth/login",
            json={
                "username": "admin",
                "password": "wrongpassword"
            }
        )

        assert response.status_code == 401
        data = response.json()
        assert "detail" in data
        assert "Invalid username or password" in data["detail"]

    def test_admin_login_nonexistent_user(self, client: TestClient):
        """Test login with non-existent user."""
        response = client.post(
            "/api/v1/auth/login",
            json={
                "username": "nonexistent",
                "password": "password123"
            }
        )

        assert response.status_code == 401
        data = response.json()
        assert "detail" in data

    def test_admin_login_missing_fields(self, client: TestClient):
        """Test login with missing required fields."""
        # Missing password
        response = client.post(
            "/api/v1/auth/login",
            json={
                "username": "admin"
            }
        )
        assert response.status_code == 422  # Validation error

        # Missing username
        response = client.post(
            "/api/v1/auth/login",
            json={
                "password": "admin123"
            }
        )
        assert response.status_code == 422


class TestAPIKeyUsage:
    """Tests for using API key to access protected endpoints."""

    def test_use_api_key_for_admin_endpoint(self, client: TestClient):
        """Test using the API key to access admin-protected endpoints."""
        # First, login to get API key
        login_response = client.post(
            "/api/v1/auth/login",
            json={
                "username": "admin",
                "password": "admin123"
            }
        )
        assert login_response.status_code == 200
        api_key = login_response.json()["access_token"]

        # Use API key to access admin endpoint (list models)
        models_response = client.get(
            "/api/v1/admin/models",
            headers={"Authorization": f"Bearer {api_key}"}
        )

        # Should succeed (may be empty list)
        assert models_response.status_code == 200
        data = models_response.json()
        assert isinstance(data, list)

        print(f"✓ API key authentication successful")

    def test_invalid_api_key_rejected(self, client: TestClient):
        """Test that invalid API key is rejected."""
        response = client.get(
            "/api/v1/admin/models",
            headers={"Authorization": "Bearer invalid_key_12345"}
        )

        assert response.status_code == 401

    def test_missing_api_key_rejected(self, client: TestClient):
        """Test that missing API key is rejected."""
        response = client.get("/api/v1/admin/models")

        assert response.status_code == 401


class TestAPIKeyManagement:
    """Tests for API key CRUD operations."""

    def test_create_api_key(self, client: TestClient):
        """Test creating a new API key."""
        # First, login
        login_response = client.post(
            "/api/v1/auth/login",
            json={
                "username": "admin",
                "password": "admin123"
            }
        )
        assert login_response.status_code == 200
        api_key = login_response.json()["access_token"]

        # Create new API key
        create_response = client.post(
            "/api/v1/auth/api-keys",
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "name": "test-key",
                "quota_tokens": 50000
            }
        )

        assert create_response.status_code == 201
        data = create_response.json()

        assert "id" in data
        assert data["name"] == "test-key"
        assert data["quota_tokens"] == 50000
        assert "key" in data  # New key is shown
        assert data["is_active"] is True

        # Can use the new key immediately
        new_key = data["key"]
        test_response = client.get(
            "/api/v1/admin/models",
            headers={"Authorization": f"Bearer {new_key}"}
        )
        assert test_response.status_code == 200

        print(f"✓ New API key created: {new_key[:20]}...")

    def test_list_api_keys(self, client: TestClient):
        """Test listing all API keys for a user."""
        # Login
        login_response = client.post(
            "/api/v1/auth/login",
            json={
                "username": "admin",
                "password": "admin123"
            }
        )
        api_key = login_response.json()["access_token"]

        # List API keys
        list_response = client.get(
            "/api/v1/auth/api-keys",
            headers={"Authorization": f"Bearer {api_key}"}
        )

        assert list_response.status_code == 200
        keys = list_response.json()
        assert isinstance(keys, list)
        assert len(keys) >= 1  # At least the default key

        # Verify key structure (should not expose full key)
        for key in keys:
            assert "id" in key
            assert "name" in key
            assert key["key"] is None  # Full key never shown in list
            assert "prefix" in key
            assert "is_active" in key


# ============================================================================
# Test Fixtures
# ============================================================================

@pytest.fixture(scope="module")
def client():
    """Create test client."""
    from fastapi import FastAPI
    import sys
    sys.path.insert(0, "/home/ht706/Documents/TokenMachine")

    from backend.main import app

    with TestClient(app) as test_client:
        yield test_client
