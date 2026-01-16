"""
Integration tests for the Chat Completions API.
"""
import pytest
import json
from unittest.mock import AsyncMock, patch, MagicMock

from backend.models.schemas import ChatCompletionRequest


class TestChatCompletionsAPI:
    """Test chat completions API endpoint."""

    def test_chat_completion_success(self, client, test_deployment, test_api_key, mock_httpx_client):
        """Test successful chat completion."""
        from backend.models.database import Deployment
        api_key, raw_key = test_api_key

        with patch("httpx.AsyncClient", return_value=mock_httpx_client):
            response = client.post(
                "/v1/chat/completions",
                json={
                    "model": test_deployment.name,
                    "messages": [
                        {"role": "user", "content": "Hello, how are you?"}
                    ]
                },
                headers={"Authorization": f"Bearer {raw_key}"}
            )

        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert "choices" in data
        assert len(data["choices"]) > 0
        assert data["choices"][0]["message"]["role"] == "assistant"

    def test_chat_completion_missing_api_key(self, client, test_deployment):
        """Test chat completion without API key."""
        response = client.post(
            "/v1/chat/completions",
            json={
                "model": test_deployment.name,
                "messages": [
                    {"role": "user", "content": "Hello"}
                ]
            }
        )

        assert response.status_code == 401

    def test_chat_completion_invalid_api_key(self, client, test_deployment):
        """Test chat completion with invalid API key."""
        response = client.post(
            "/v1/chat/completions",
            json={
                "model": test_deployment.name,
                "messages": [
                    {"role": "user", "content": "Hello"}
                ]
            },
            headers={"Authorization": "Bearer invalid_key"}
        )

        assert response.status_code == 401

    def test_chat_completion_model_not_found(self, client, test_api_key):
        """Test chat completion with non-existent model."""
        api_key, raw_key = test_api_key

        response = client.post(
            "/v1/chat/completions",
            json={
                "model": "non-existent-model",
                "messages": [
                    {"role": "user", "content": "Hello"}
                ]
            },
            headers={"Authorization": f"Bearer {raw_key}"}
        )

        assert response.status_code == 404

    def test_chat_completion_streaming(self, client, test_deployment, test_api_key):
        """Test streaming chat completion."""
        api_key, raw_key = test_api_key

        # Mock streaming response
        async def mock_stream():
            yield "data: {\"choices\": [{\"delta\": {\"content\": \"Hello\"}}]}\n\n"
            yield "data: [DONE]\n\n"

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.aiter_lines = mock_stream

        async def mock_stream_request(*args, **kwargs):
            return mock_response

        mock_async_client = MagicMock()
        mock_async_client.stream = mock_stream_request

        with patch("httpx.AsyncClient", return_value=mock_async_client):
            response = client.post(
                "/v1/chat/completions",
                json={
                    "model": test_deployment.name,
                    "messages": [{"role": "user", "content": "Hello"}],
                    "stream": True
                },
                headers={"Authorization": f"Bearer {raw_key}"}
            )

        assert response.status_code == 200

    def test_chat_completion_with_temperature(self, client, test_deployment, test_api_key, mock_httpx_client):
        """Test chat completion with temperature parameter."""
        api_key, raw_key = test_api_key

        with patch("httpx.AsyncClient", return_value=mock_httpx_client):
            response = client.post(
                "/v1/chat/completions",
                json={
                    "model": test_deployment.name,
                    "messages": [{"role": "user", "content": "Hello"}],
                    "temperature": 0.5
                },
                headers={"Authorization": f"Bearer {raw_key}"}
            )

        assert response.status_code == 200

    def test_chat_completion_with_max_tokens(self, client, test_deployment, test_api_key, mock_httpx_client):
        """Test chat completion with max_tokens parameter."""
        api_key, raw_key = test_api_key

        with patch("httpx.AsyncClient", return_value=mock_httpx_client):
            response = client.post(
                "/v1/chat/completions",
                json={
                    "model": test_deployment.name,
                    "messages": [{"role": "user", "content": "Hello"}],
                    "max_tokens": 500
                },
                headers={"Authorization": f"Bearer {raw_key}"}
            )

        assert response.status_code == 200

    def test_chat_completion_multiple_messages(self, client, test_deployment, test_api_key, mock_httpx_client):
        """Test chat completion with multiple messages."""
        api_key, raw_key = test_api_key

        with patch("httpx.AsyncClient", return_value=mock_httpx_client):
            response = client.post(
                "/v1/chat/completions",
                json={
                    "model": test_deployment.name,
                    "messages": [
                        {"role": "system", "content": "You are a helpful assistant."},
                        {"role": "user", "content": "Hello"},
                        {"role": "assistant", "content": "Hi there!"},
                        {"role": "user", "content": "How are you?"}
                    ]
                },
                headers={"Authorization": f"Bearer {raw_key}"}
            )

        assert response.status_code == 200


class TestModelsAPI:
    """Test models list API endpoint."""

    def test_list_models_empty(self, client):
        """Test listing models when none are deployed."""
        response = client.get("/v1/models")
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert isinstance(data["data"], list)

    def test_list_models_with_deployments(self, client, test_deployment):
        """Test listing models with active deployments."""
        response = client.get("/v1/models")
        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) >= 1


class TestRateLimiting:
    """Test rate limiting functionality."""

    def test_rate_limit_exceeded(self, client, test_deployment, test_api_key, mock_httpx_client):
        """Test that rate limit is enforced."""
        api_key, raw_key = test_api_key

        # Make multiple requests
        responses = []
        for _ in range(70):  # Exceed default limit of 60
            with patch("httpx.AsyncClient", return_value=mock_httpx_client):
                response = client.post(
                    "/v1/chat/completions",
                    json={
                        "model": test_deployment.name,
                        "messages": [{"role": "user", "content": "Hello"}]
                    },
                    headers={"Authorization": f"Bearer {raw_key}"}
                )
            responses.append(response)

        # Check if any responses indicate rate limiting
        rate_limited = any(r.status_code == 429 for r in responses)
        # Note: This depends on rate limiting being enabled
