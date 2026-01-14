"""
Integration test configuration and fixtures.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from inferx.main import app
from inferx.api.deps import get_current_db


@pytest.fixture
def authenticated_client(client, test_api_key):
    """Create a test client with API key authentication."""
    api_key, raw_key = test_api_key

    def override_auth():
        return api_key

    # Import and override the auth dependency
    from inferx.api.v1 import chat, models, admin

    original_verify = chat.verify_api_key_auth
    original_get_deployment = chat.get_deployment_by_name

    def mock_verify():
        return api_key

    chat.verify_api_key_auth = mock_verify

    yield client

    # Restore original
    chat.verify_api_key_auth = original_verify


@pytest.fixture
def admin_client(client, test_admin_user):
    """Create a test client with admin authentication."""
    from inferx.api.v1 import admin as admin_module
    from inferx.core.security import create_access_token

    token = create_access_token({"sub": str(test_admin_user.id)})

    client.headers["Authorization"] = f"Bearer {token}"
    yield client
    client.headers.pop("Authorization", None)
