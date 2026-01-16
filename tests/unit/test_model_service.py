"""
Unit tests for the ModelService.
"""
import os
import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from backend.services.model_service import ModelService
from backend.models.database import ModelCategory, ModelSource, ModelStatus


class TestModelService:
    """Test ModelService class."""

    def test_create_model_success(self, db_session, patch_gpu_manager):
        """Test successfully creating a new model."""
        service = ModelService(db_session)

        with patch.object(service, '_start_download'):
            model = service.create_model(
                name="meta-llama/Llama-3-8B-Instruct",
                version="v1.0.0",
                source=ModelSource.HUGGINGFACE,
                category=ModelCategory.LLM
            )

        assert model.id is not None
        assert model.name == "meta-llama/Llama-3-8B-Instruct"
        assert model.version == "v1.0.0"
        assert model.source == ModelSource.HUGGINGFACE
        assert model.category == ModelCategory.LLM
        assert model.status == ModelStatus.DOWNLOADING
        assert model.download_progress == 0

    def test_create_model_duplicate(self, db_session, test_model, patch_gpu_manager):
        """Test creating a duplicate model raises error."""
        service = ModelService(db_session)

        with pytest.raises(ValueError, match="already exists"):
            service.create_model(
                name=test_model.name,
                version=test_model.version,
                source=ModelSource.HUGGINGFACE,
                category=ModelCategory.LLM
            )

    def test_get_model(self, db_session, test_model, patch_gpu_manager):
        """Test getting a model by ID."""
        service = ModelService(db_session)
        model = service.get_model(test_model.id)
        assert model is not None
        assert model.id == test_model.id
        assert model.name == test_model.name

    def test_get_model_not_found(self, db_session, patch_gpu_manager):
        """Test getting a non-existent model."""
        service = ModelService(db_session)
        model = service.get_model(99999)
        assert model is None

    def test_get_model_by_name_version(self, db_session, test_model, patch_gpu_manager):
        """Test getting a model by name and version."""
        service = ModelService(db_session)
        model = service.get_model_by_name_version(test_model.name, test_model.version)
        assert model is not None
        assert model.id == test_model.id

    def test_list_models_all(self, db_session, test_model, patch_gpu_manager):
        """Test listing all models."""
        service = ModelService(db_session)
        models = service.list_models()
        assert len(models) >= 1
        assert test_model in models

    def test_list_models_with_filters(self, db_session, test_model, patch_gpu_manager):
        """Test listing models with filters."""
        service = ModelService(db_session)

        # Filter by category
        llm_models = service.list_models(category=ModelCategory.LLM)
        assert all(m.category == ModelCategory.LLM for m in llm_models)

        # Filter by status
        ready_models = service.list_models(status=ModelStatus.READY)
        assert all(m.status == ModelStatus.READY for m in ready_models)

    def test_update_model_status(self, db_session, test_model, patch_gpu_manager):
        """Test updating model status."""
        service = ModelService(db_session)
        updated = service.update_model_status(
            test_model.id,
            ModelStatus.ERROR,
            "Download failed"
        )
        assert updated.status == ModelStatus.ERROR
        assert updated.error_message == "Download failed"

    def test_delete_model_success(self, db_session, test_model, monkeypatch, patch_gpu_manager):
        """Test deleting a model."""
        service = ModelService(db_session)

        # Mock shutil.rmtree
        mock_rmtree = MagicMock()
        monkeypatch.setattr("inferx.services.model_service.shutil.rmtree", mock_rmtree)

        result = service.delete_model(test_model.id)
        assert result is True

        # Verify model is removed from database
        model = service.get_model(test_model.id)
        assert model is None

    def test_delete_model_not_found(self, db_session, patch_gpu_manager):
        """Test deleting a non-existent model."""
        service = ModelService(db_session)
        result = service.delete_model(99999)
        assert result is False

    def test_delete_model_with_active_deployment(
        self,
        db_session,
        test_model,
        test_deployment,
        patch_gpu_manager
    ):
        """Test deleting a model with active deployments raises error."""
        service = ModelService(db_session)

        with pytest.raises(ValueError, match="active deployments"):
            service.delete_model(test_model.id)

    def test_estimate_gpu_memory_7b_model(self, db_session, patch_gpu_manager):
        """Test GPU memory estimation for 7B/8B models."""
        service = ModelService(db_session)

        model = Mock(spec=Model)
        model.name = "llama-7b"
        memory_mb = service.estimate_gpu_memory(model)
        assert memory_mb == 16 * 1024  # 16 GB

    def test_estimate_gpu_memory_13b_model(self, db_session, patch_gpu_manager):
        """Test GPU memory estimation for 13B/14B models."""
        service = ModelService(db_session)

        model = Mock(spec=Model)
        model.name = "llama-13b"
        memory_mb = service.estimate_gpu_memory(model)
        assert memory_mb == 24 * 1024  # 24 GB

    def test_estimate_gpu_memory_70b_model(self, db_session, patch_gpu_manager):
        """Test GPU memory estimation for 70B models."""
        service = ModelService(db_session)

        model = Mock(spec=Model)
        model.name = "llama-70b"
        memory_mb = service.estimate_gpu_memory(model)
        assert memory_mb == 140 * 1024  # 140 GB

    def test_estimate_gpu_memory_unknown_model(self, db_session, patch_gpu_manager):
        """Test GPU memory estimation for unknown model (default)."""
        service = ModelService(db_session)

        model = Mock(spec=Model)
        model.name = "unknown-model"
        memory_mb = service.estimate_gpu_memory(model)
        assert memory_mb == 16 * 1024  # Default 16 GB

    def test_calculate_model_size(self, db_session, tmp_path, patch_gpu_manager):
        """Test calculating model size from directory."""
        service = ModelService(db_session)

        # Create a temporary directory with some files
        model_dir = tmp_path / "model"
        model_dir.mkdir()

        # Create test files
        (model_dir / "file1.bin").write_bytes(b"0" * (100 * 1024 * 1024))  # 100 MB
        (model_dir / "file2.bin").write_bytes(b"0" * (200 * 1024 * 1024))  # 200 MB

        size_gb = service._calculate_model_size(str(model_dir))
        assert 0.29 < size_gb < 0.31  # ~300 MB in GB

    def test_download_already_active(self, db_session, test_model, patch_gpu_manager):
        """Test that duplicate download requests are ignored."""
        service = ModelService(db_session)
        service._active_downloads[test_model.id] = True

        with patch("inferx.services.model_service.threading.Thread") as mock_thread:
            service._start_download(
                test_model.id,
                test_model.name,
                test_model.source
            )
            # Should not start a new thread
            mock_thread.assert_not_called()


class TestModelServiceDownload:
    """Test model download functionality."""

    def test_download_from_huggingface_success(
        self,
        db_session,
        tmp_path,
        monkeypatch,
        patch_gpu_manager
    ):
        """Test successful download from HuggingFace."""
        service = ModelService(db_session)

        # Mock subprocess.run
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_process.stdout = "Download complete"
        mock_process.stderr = ""
        mock_popen = MagicMock(return_value=mock_process)

        monkeypatch.setattr("inferx.services.model_service.subprocess.Popen", mock_popen)

        storage_path = str(tmp_path / "model")

        # Should not raise an exception
        service._download_from_huggingface(
            "meta-llama/Llama-3-8B-Instruct",
            storage_path,
            None
        )

        mock_popen.assert_called_once()

    def test_download_from_huggingface_with_token(
        self,
        db_session,
        tmp_path,
        monkeypatch,
        patch_gpu_manager
    ):
        """Test download from HuggingFace with authentication token."""
        service = ModelService(db_session)

        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_process.communicate = MagicMock(return_value=("", ""))

        monkeypatch.setattr("inferx.services.model_service.subprocess.Popen", MagicMock(return_value=mock_process))

        storage_path = str(tmp_path / "model")
        service._download_from_huggingface("org/model", storage_path, "hf_token_123")

    def test_download_from_huggingface_failure(
        self,
        db_session,
        tmp_path,
        monkeypatch,
        patch_gpu_manager
    ):
        """Test failed download from HuggingFace."""
        service = ModelService(db_session)

        mock_process = MagicMock()
        mock_process.returncode = 1
        mock_process.communicate = MagicMock(return_value=("", "Download failed"))
        mock_process.stderr = "Download failed"

        monkeypatch.setattr("inferx.services.model_service.subprocess.Popen", MagicMock(return_value=mock_process))

        storage_path = str(tmp_path / "model")

        with pytest.raises(Exception, match="HuggingFace download failed"):
            service._download_from_huggingface("org/model", storage_path, None)

    def test_download_from_local(
        self,
        db_session,
        tmp_path,
        patch_gpu_manager
    ):
        """Test using local model path."""
        service = ModelService(db_session)

        # Create a temporary model directory
        model_dir = tmp_path / "local_model"
        model_dir.mkdir()
        (model_dir / "config.json").write_text("{}")

        # Should not raise an exception
        service._download_model(
            model_id=1,
            name=str(model_dir),
            source=ModelSource.LOCAL
        )
