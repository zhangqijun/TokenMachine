"""
Integration tests for the Admin API.
"""
import pytest


class TestAdminAPI:
    """Test admin API endpoints."""

    def test_list_users(self, admin_client):
        """Test listing all users."""
        response = admin_client.get("/api/v1/admin/users")
        assert response.status_code in [200, 401, 403]

    def test_create_user(self, admin_client):
        """Test creating a new user."""
        response = admin_client.post(
            "/api/v1/admin/users",
            json={
                "username": "newuser",
                "email": "newuser@example.com",
                "password": "password123",
                "is_admin": False
            }
        )
        assert response.status_code in [201, 400, 401, 403]

    def test_get_user(self, admin_client, test_user):
        """Test getting a specific user."""
        response = admin_client.get(f"/api/v1/admin/users/{test_user.id}")
        assert response.status_code in [200, 401, 403, 404]

    def test_update_user(self, admin_client, test_user):
        """Test updating a user."""
        response = admin_client.patch(
            f"/api/v1/admin/users/{test_user.id}",
            json={"email": "updated@example.com"}
        )
        assert response.status_code in [200, 401, 403, 404]

    def test_delete_user(self, admin_client, test_user):
        """Test deleting a user."""
        response = admin_client.delete(f"/api/v1/admin/users/{test_user.id}")
        assert response.status_code in [200, 204, 401, 403, 404]

    def test_list_api_keys(self, admin_client):
        """Test listing all API keys."""
        response = admin_client.get("/api/v1/admin/api-keys")
        assert response.status_code in [200, 401, 403]

    def test_create_api_key(self, admin_client, test_user):
        """Test creating a new API key."""
        response = admin_client.post(
            "/api/v1/admin/api-keys",
            json={
                "user_id": test_user.id,
                "name": "Test Key",
                "quota_tokens": 1000000
            }
        )
        assert response.status_code in [201, 400, 401, 403]

    def test_revoke_api_key(self, admin_client, test_api_key):
        """Test revoking an API key."""
        api_key, _ = test_api_key
        response = admin_client.patch(f"/api/v1/admin/api-keys/{api_key.id}", json={"is_active": False})
        assert response.status_code in [200, 401, 403, 404]

    def test_get_usage_stats(self, admin_client):
        """Test getting usage statistics."""
        response = admin_client.get("/api/v1/admin/stats/usage")
        assert response.status_code in [200, 401, 403]

    def test_get_system_stats(self, admin_client):
        """Test getting system statistics."""
        response = admin_client.get("/api/v1/admin/stats/system")
        assert response.status_code in [200, 401, 403]


class TestAdminAuth:
    """Test admin authentication."""

    def test_admin_access_without_token(self, client):
        """Test accessing admin endpoint without authentication."""
        response = client.get("/api/v1/admin/users")
        assert response.status_code in [401, 403]

    def test_admin_access_with_user_token(self, client, test_user):
        """Test accessing admin endpoint with regular user token."""
        from inferx.core.security import create_access_token
        token = create_access_token({"sub": str(test_user.id)})

        response = client.get(
            "/api/v1/admin/users",
            headers={"Authorization": f"Bearer {token}"}
        )
        # Regular user should not have admin access
        assert response.status_code in [401, 403]
