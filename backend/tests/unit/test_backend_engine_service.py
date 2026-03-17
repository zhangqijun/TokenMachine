"""
Unit tests for BackendEngineService.

Tests cover:
- Install engine (success, duplicate)
- Delete engine (success, with active deployments, not found)
- List engines (all, filtered)
- Get engine stats
"""
import pytest
from unittest.mock import patch
from sqlalchemy.orm import Session

from backend.models.database import (
    BackendEngine,
    BackendEngineType,
    BackendEngineStatus,
)
from backend.models.schemas import BackendEngineInstallRequest
from backend.services.backend_engine_service import BackendEngineService


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def engine_install_request():
    """Create a test install request."""
    return BackendEngineInstallRequest(
        version="0.5.0",
        image_name="registry.tokenmachine.ai/vllm/vllm-openai:v0.5.0",
        registry_url="registry.tokenmachine.ai",
        config={"gpu_memory_utilization": 0.9},
        env_vars={"CUDA_VISIBLE_DEVICES": "0,1"}
    )


@pytest.fixture
def installed_vllm_engine(db_session: Session):
    """Create an installed vLLM engine for testing."""
    engine = BackendEngine(
        engine_type=BackendEngineType.VLLM,
        version="0.4.3",
        status=BackendEngineStatus.INSTALLED,
        registry_url="registry.tokenmachine.ai",
        image_name="registry.tokenmachine.ai/vllm/vllm-openai:v0.4.3",
        size_mb=2048,
        active_deployments=0
    )
    db_session.add(engine)
    db_session.commit()
    db_session.refresh(engine)
    return engine


@pytest.fixture
def installed_mindie_engine(db_session: Session):
    """Create an installed MindIE engine with active deployments."""
    engine = BackendEngine(
        engine_type=BackendEngineType.MINDIE,
        version="1.0.0",
        status=BackendEngineStatus.INSTALLED,
        registry_url="registry.tokenmachine.ai",
        image_name="registry.tokenmachine.ai/mindie/mindie-serving:v1.0.0",
        size_mb=3200,
        active_deployments=2
    )
    db_session.add(engine)
    db_session.commit()
    db_session.refresh(engine)
    return engine


# =============================================================================
# Test: Install Engine
# =============================================================================

class TestInstallEngine:
    """Tests for install_engine method."""

    def test_install_engine_success(self, db_session: Session, engine_install_request):
        """Test installing a new engine successfully."""
        engine = BackendEngineService.install_engine(
            db_session,
            BackendEngineType.VLLM,
            engine_install_request
        )

        assert engine.engine_type == BackendEngineType.VLLM
        assert engine.version == "0.5.0"
        assert engine.status == BackendEngineStatus.INSTALLED
        assert engine.image_name == "registry.tokenmachine.ai/vllm/vllm-openai:v0.5.0"

    def test_install_duplicate_version_fails(self, db_session: Session, installed_vllm_engine, engine_install_request):
        """Test that installing an already installed version raises ValueError."""
        engine_install_request.version = installed_vllm_engine.version

        with pytest.raises(ValueError, match="is already installed"):
            BackendEngineService.install_engine(
                db_session,
                BackendEngineType.VLLM,
                engine_install_request
            )

    def test_install_with_default_image_name(self, db_session: Session):
        """Test that default image name is used when not provided."""
        request = BackendEngineInstallRequest(
            version="0.5.0"
        )

        engine = BackendEngineService.install_engine(
            db_session,
            BackendEngineType.VLLM,
            request
        )

        assert engine.image_name == "registry.tokenmachine.ai/vllm/vllm-openai:v0.5.0"

    def test_install_mindie_default_image(self, db_session: Session):
        """Test default image name for MindIE."""
        request = BackendEngineInstallRequest(
            version="1.0.0"
        )

        engine = BackendEngineService.install_engine(
            db_session,
            BackendEngineType.MINDIE,
            request
        )

        assert engine.image_name == "registry.tokenmachine.ai/mindie/mindie-serving:v1.0.0"

    def test_install_llama_cpp_default_image(self, db_session: Session):
        """Test default image name for llama.cpp."""
        request = BackendEngineInstallRequest(
            version="b4380"
        )

        engine = BackendEngineService.install_engine(
            db_session,
            BackendEngineType.LLAMA_CPP,
            request
        )

        assert engine.image_name == "registry.tokenmachine.ai/llamacpp/llama-cpp-python:b4380"


# =============================================================================
# Test: Delete Engine
# =============================================================================

class TestDeleteEngine:
    """Tests for delete_engine method."""

    def test_delete_engine_success(self, db_session: Session, installed_vllm_engine):
        """Test deleting an engine successfully."""
        result = BackendEngineService.delete_engine(
            db_session,
            BackendEngineType.VLLM,
            installed_vllm_engine.version
        )

        assert result is True

        # Verify engine is deleted
        engines = db_session.query(BackendEngine).filter(
            BackendEngine.engine_type == BackendEngineType.VLLM,
            BackendEngine.version == installed_vllm_engine.version
        ).all()
        assert len(engines) == 0

    def test_delete_engine_not_found(self, db_session: Session):
        """Test that deleting non-existent engine raises ValueError."""
        with pytest.raises(ValueError, match="not found"):
            BackendEngineService.delete_engine(
                db_session,
                BackendEngineType.VLLM,
                "99.99.99"
            )

    def test_delete_engine_with_active_deployments_fails(self, db_session: Session, installed_mindie_engine):
        """Test that deleting engine with active deployments raises ValueError."""
        assert installed_mindie_engine.active_deployments > 0

        with pytest.raises(ValueError, match="active deployments"):
            BackendEngineService.delete_engine(
                db_session,
                BackendEngineType.MINDIE,
                installed_mindie_engine.version
            )


# =============================================================================
# Test: List Engines
# =============================================================================

class TestListEngines:
    """Tests for list_engines method."""

    def test_list_all_engines(self, db_session: Session, installed_vllm_engine, installed_mindie_engine):
        """Test listing all engines."""
        result = BackendEngineService.list_engines(db_session)

        assert len(result) == 2

        # Verify vLLM
        vllm_result = next(e for e in result if e["name"] == "vllm")
        assert vllm_result["display_name"] == "vLLM"
        assert vllm_result["version"] == "0.4.3"
        assert vllm_result["status"] == "installed"

        # Verify MindIE
        mindie_result = next(e for e in result if e["name"] == "mindie")
        assert mindie_result["display_name"] == "MindIE"
        assert mindie_result["stats"]["active_deployments"] == 2

    def test_list_engines_filtered_by_type(self, db_session: Session, installed_vllm_engine, installed_mindie_engine):
        """Test listing engines filtered by type."""
        result = BackendEngineService.list_engines(
            db_session,
            engine_type=BackendEngineType.VLLM
        )

        assert len(result) == 1
        assert result[0]["name"] == "vllm"

    def test_list_engines_empty(self, db_session: Session):
        """Test listing engines when none exist."""
        result = BackendEngineService.list_engines(db_session)

        assert result == []

    def test_list_engines_includes_metadata(self, db_session: Session, installed_vllm_engine):
        """Test that engine metadata is included in list."""
        result = BackendEngineService.list_engines(db_session)

        assert len(result) == 1
        engine = result[0]

        # Check metadata fields
        assert "features" in engine
        assert "compatibility" in engine
        assert engine["features"]["tensor_parallel"] is True
        assert "nvidia" in engine["compatibility"]["gpu_vendors"]


# =============================================================================
# Test: Get Engine Stats
# =============================================================================

class TestGetEngineStats:
    """Tests for get_engine_stats method."""

    def test_get_engine_stats_success(self, db_session: Session, installed_vllm_engine):
        """Test getting engine statistics."""
        result = BackendEngineService.get_engine_stats(
            db_session,
            BackendEngineType.VLLM,
            installed_vllm_engine.version
        )

        assert result["engine_type"] == "vllm"
        assert result["version"] == "0.4.3"
        assert result["status"] == "installed"
        assert result["size_mb"] == 2048
        assert result["active_deployments"] == 0

    def test_get_engine_stats_not_found(self, db_session: Session):
        """Test getting stats for non-existent engine."""
        with pytest.raises(ValueError, match="not found"):
            BackendEngineService.get_engine_stats(
                db_session,
                BackendEngineType.VLLM,
                "99.99.99"
            )

    def test_get_engine_stats_includes_all_fields(self, db_session: Session, installed_vllm_engine):
        """Test that stats include all expected fields."""
        result = BackendEngineService.get_engine_stats(
            db_session,
            BackendEngineType.VLLM,
            installed_vllm_engine.version
        )

        expected_fields = [
            "engine_type", "version", "status", "active_deployments",
            "size_mb", "installed_at", "image_name"
        ]
        for field in expected_fields:
            assert field in result, f"Missing field: {field}"


# =============================================================================
# Test: Edge Cases
# =============================================================================

class TestEdgeCases:
    """Edge case tests."""

    def test_install_multiple_versions_same_type(self, db_session: Session):
        """Test installing multiple versions of the same engine type."""
        engine1 = BackendEngineService.install_engine(
            db_session,
            BackendEngineType.VLLM,
            BackendEngineInstallRequest(version="0.4.3")
        )

        engine2 = BackendEngineService.install_engine(
            db_session,
            BackendEngineType.VLLM,
            BackendEngineInstallRequest(version="0.5.0")
        )

        assert engine1.version == "0.4.3"
        assert engine2.version == "0.5.0"

        # List all vLLM versions
        result = BackendEngineService.list_engines(db_session, BackendEngineType.VLLM)
        assert len(result) == 2

    def test_delete_and_reinstall(self, db_session: Session):
        """Test deleting and reinstalling the same version."""
        # Install
        engine = BackendEngineService.install_engine(
            db_session,
            BackendEngineType.LLAMA_CPP,
            BackendEngineInstallRequest(version="b4380")
        )

        # Delete
        result = BackendEngineService.delete_engine(
            db_session,
            BackendEngineType.LLAMA_CPP,
            "b4380"
        )
        assert result is True

        # Reinstall should succeed
        engine2 = BackendEngineService.install_engine(
            db_session,
            BackendEngineType.LLAMA_CPP,
            BackendEngineInstallRequest(version="b4380")
        )

        assert engine2.version == "b4380"

    def test_install_different_engine_types(self, db_session: Session):
        """Test installing different engine types."""
        engines = [
            (BackendEngineType.VLLM, "0.5.0", "vllm"),
            (BackendEngineType.MINDIE, "1.0.0", "mindie"),
            (BackendEngineType.LLAMA_CPP, "b4380", "llamacpp"),
        ]

        for engine_type, version, name in engines:
            engine = BackendEngineService.install_engine(
                db_session,
                engine_type,
                BackendEngineInstallRequest(version=version)
            )
            assert engine.engine_type == engine_type
            assert engine.version == version

        # All three should be in the list
        result = BackendEngineService.list_engines(db_session)
        assert len(result) == 3