"""
Unit tests for the configuration module.
"""
import os
import pytest
from pathlib import Path
from unittest.mock import patch

from backend.core.config import Settings, get_settings, ensure_directories


class TestSettings:
    """Test Settings configuration class."""

    def test_default_values(self):
        """Test that default values are correctly set."""
        settings = Settings()
        assert settings.app_name == "TokenMachine"
        assert settings.app_version == "0.1.0"
        assert settings.environment == "development"
        assert settings.debug is True
        assert settings.api_host == "0.0.0.0"
        assert settings.api_port == 8000
        assert settings.redis_url == "redis://localhost:6379/0"

    def test_is_development(self):
        """Test is_development property."""
        settings = Settings(environment="development")
        assert settings.is_development is True
        assert settings.is_production is False

    def test_is_production(self):
        """Test is_production property."""
        settings = Settings(environment="production")
        assert settings.is_development is False
        assert settings.is_production is True

    def test_get_worker_port(self):
        """Test get_worker_port method."""
        settings = Settings(worker_base_port=8000)
        assert settings.get_worker_port(0) == 8000
        assert settings.get_worker_port(1) == 8001
        assert settings.get_worker_port(5) == 8005

    def test_custom_values_from_env(self, monkeypatch):
        """Test that values can be overridden via environment variables."""
        monkeypatch.setenv("APP_NAME", "TestApp")
        monkeypatch.setenv("API_PORT", "9000")
        monkeypatch.setenv("DEBUG", "false")

        settings = Settings(_env_file=None)
        assert settings.app_name == "TestApp"
        assert settings.api_port == 9000
        assert settings.debug is False

    def test_gpu_memory_utilization_validation(self, monkeypatch):
        """Test GPU memory utilization is within valid range."""
        settings = Settings()
        assert 0.0 <= settings.gpu_memory_utilization <= 1.0

    def test_token_expiration_default(self):
        """Test default token expiration."""
        settings = Settings()
        # 7 days in minutes
        assert settings.access_token_expire_minutes == 60 * 24 * 7


class TestEnsureDirectories:
    """Test ensure_directories function."""

    def test_creates_model_storage_directory(self, tmp_path, monkeypatch):
        """Test that model storage directory is created."""
        model_path = tmp_path / "models"
        log_path = tmp_path / "logs"

        monkeypatch.setattr("os.makedirs", lambda p, **kwargs: None)

        settings = Settings(
            model_storage_path=str(model_path),
            log_path=str(log_path)
        )

        # Just verify the function runs without error
        ensure_directories(settings)

    def test_creates_log_subdirectories(self, tmp_path):
        """Test that log subdirectories are created."""
        log_path = tmp_path / "logs"

        settings = Settings(
            log_path=str(log_path),
            model_storage_path=str(tmp_path / "models")
        )

        ensure_directories(settings)

        # Check that directories were created
        assert log_path.exists()
        assert (log_path / "workers").exists()


class TestGetSettings:
    """Test get_settings caching function."""

    def test_returns_settings_instance(self):
        """Test that get_settings returns a Settings instance."""
        settings = get_settings()
        assert isinstance(settings, Settings)

    def test_caching(self):
        """Test that get_settings caches the result."""
        settings1 = get_settings()
        settings2 = get_settings()
        # Should be the same instance due to lru_cache
        assert settings1 is settings2

    def test_reset_cache_for_testing(self, monkeypatch):
        """Test that cache can be reset for testing purposes."""
        # Clear the cache
        get_settings.cache_clear()

        monkeypatch.setenv("APP_NAME", "NewApp")

        settings = get_settings()
        # After clearing cache, new env var should be picked up
        assert settings.app_name == "NewApp"
