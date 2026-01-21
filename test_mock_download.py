"""
Test mock download functionality.
"""
import pytest
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


@pytest.fixture
def test_local_model():
    """Path to local test model."""
    return "/home/ht706/Qwen3-Coder-30B-A3B-Instruct-Int4-W4A16"


@pytest.mark.asyncio
async def test_mock_download_full_flow(db_session, test_admin_user, test_model, test_local_model):
    """Test full mock download flow."""
    from backend.services.model_download_service import ModelDownloadService
    
    service = ModelDownloadService(db_session)
    
    # Create mock download task
    task = await service.create_mock_download_task(
        model_id=test_model.id,
        local_path=test_local_model,
        mock_repo_id="Qwen/qwen3-coder-30b-mock"
    )
    
    print(f"✓ Mock download task created: {task.id}")
    print(f"  Status: {task.status}")
    print(f"  Storage path: {task.model.storage_path}")
    print(f"  Total size: {task.total_bytes / (1024**3):.2f} GB")
    print(f"  Total files: {task.total_files}")
    
    # Wait a bit for download to progress
    import asyncio
    await asyncio.sleep(3)
    
    # Check download status
    status = await service.get_download_status(test_model.id)
    print(f"✓ Download status after 3 seconds:")
    print(f"  Progress: {status['progress']}%")
    print(f"  Status: {status['status']}")
    print(f"  Downloaded: {status['downloaded_bytes'] / (1024**3):.2f} GB")
    
    # Wait for download to complete (should take ~10 seconds)
    await asyncio.sleep(10)
    
    # Final status
    final_status = await service.get_download_status(test_model.id)
    print(f"✓ Final download status:")
    print(f"  Progress: {final_status['progress']}%")
    print(f"  Status: {final_status['status']}")
    print(f"  Model status: {final_status.get('model_status', 'N/A')}")
    
    # Verify model is ready
    db_session.refresh(test_model)
    assert test_model.status == "READY", f"Model should be READY, got {test_model.status}"
    assert os.path.exists(test_model.storage_path), f"Model path should exist: {test_model.storage_path}"
    
    print(f"✓ Test passed! Model is ready at {test_model.storage_path}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
