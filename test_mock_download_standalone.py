"""
Standalone test for mock download functionality.
"""
import sys
import os
import asyncio

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


async def main():
    """Main test function."""
    from backend.core.database import SessionLocal, init_db, drop_db
    from backend.models.database import Model, User, Organization, ModelSource, ModelCategory, UserRole
    from backend.services.model_download_service import ModelDownloadService
    from backend.core.security import hash_password, generate_api_key, hash_api_key
    from datetime import datetime, timedelta

    print("=" * 60)
    print("Mock Download Test")
    print("=" * 60)

    # Initialize database
    print("\n[1/6] Initializing database...")
    init_db()
    db = SessionLocal()

    # Create test organization
    print("[2/6] Creating test organization...")
    org = Organization(
        id=1,  # Manually set ID for SQLite compatibility
        name='test_org',
        plan='ENTERPRISE',
        quota_tokens=1000000000,
        quota_models=100,
        quota_gpus=10,
        max_workers=5
    )
    db.add(org)
    db.flush()  # Get the ID without committing
    print(f"  Organization created: {org.name} (ID: {org.id})")

    # Create test admin user
    print("[3/6] Creating test admin user...")
    # Use a pre-hashed password for testing (hash of 'test')
    admin = User(
        id=1,  # Manually set ID for SQLite compatibility
        username='admin',
        email='admin@test.com',
        password_hash='$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYzpLaEmc0i',  # hash of 'test'
        organization_id=org.id,
        role='ADMIN',
        is_active=True
    )
    db.add(admin)
    db.flush()

    # Create API key - generate manually for testing
    api_key = "tmachine_sk_test123456789012345678901234567890"
    prefix = api_key[:10]
    from backend.models.database import ApiKey
    key_record = ApiKey(
        id=1,  # Manually set ID for SQLite compatibility
        key_hash='$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYzpLaEmc0i',  # same hash
        key_prefix=prefix,
        user_id=admin.id,
        organization_id=org.id,
        name='test_key',
        quota_tokens=1000000000,
        tokens_used=0,
        is_active=True,
        expires_at=datetime.now() + timedelta(days=365)
    )
    db.add(key_record)
    db.flush()
    print(f"  User created: {admin.username} (ID: {admin.id})")
    print(f"  API Key: {api_key}")

    # Create test model
    print("[4/6] Creating test model...")
    model = Model(
        id=1,  # Manually set ID for SQLite compatibility
        name='Qwen3-Coder-30B-Int4',
        version='v1.0.0',
        source=ModelSource.MODELSCOPE,
        category=ModelCategory.LLM,
        quantization='int8',  # Use int8 instead of int4
        status='DOWNLOADING'
    )
    db.add(model)
    db.flush()
    print(f"  Model created: {model.name} (ID: {model.id})")

    db.commit()

    # Test mock download
    print("[5/6] Starting mock download...")
    service = ModelDownloadService(db)

    local_model_path = "/home/ht706/Qwen3-Coder-30B-A3B-Instruct-Int4-W4A16"

    try:
        task = await service.create_mock_download_task(
            model_id=model.id,
            local_path=local_model_path,
            mock_repo_id="Qwen/qwen3-coder-30b"
        )

        print(f"\n  ✓ Mock download task created!")
        print(f"    Task ID: {task.id}")
        print(f"    Status: {task.status.value}")
        print(f"    Storage path: {task.model.storage_path}")
        print(f"    Total size: {task.total_bytes / (1024**3):.2f} GB")
        print(f"    Total files: {task.total_files}")
        print(f"    Mock repo ID: {task.modelscope_repo_id}")

        # Wait and show progress
        print("\n[6/6] Monitoring download progress...")
        for i in range(1, 12):
            await asyncio.sleep(1)

            # Refresh task from database
            db.refresh(task)
            progress = task.progress
            status = task.status.value
            downloaded_gb = task.downloaded_bytes / (1024**3)
            total_gb = task.total_bytes / (1024**3)
            speed = task.download_speed_mbps or 0

            print(f"  [{i}s] Progress: {progress}% | "
                  f"Downloaded: {downloaded_gb:.2f}/{total_gb:.2f} GB | "
                  f"Speed: {speed:.2f} MB/s | Status: {status}")

            if status == "COMPLETED":
                print(f"\n  ✓ Download completed successfully!")
                break
            elif status == "FAILED":
                print(f"\n  ✗ Download failed: {task.error_message}")
                break

        # Final check
        db.refresh(model)
        print(f"\n  Final model status: {model.status.value}")
        print(f"  Model path: {model.storage_path}")
        print(f"  Model size: {model.size_gb:.2f} GB")

        if os.path.exists(model.storage_path):
            file_count = sum([len(files) for r, d, files in os.walk(model.storage_path)])
            print(f"  Files in storage: {file_count}")

        print("\n" + "=" * 60)
        print("✓ TEST PASSED!")
        print("=" * 60)
        print(f"\nAPI Credentials:")
        print(f"  URL: http://localhost:8000")
        print(f"  API Key: {api_key}")
        print(f"  Model ID: {model.id}")
        print(f"\nYou can now test the API endpoints:")
        print(f"  GET /api/v1/admin/models/{model.id}/download/status")
        print(f"  GET /api/v1/admin/models/{model.id}/download/logs")

    except Exception as e:
        print(f"\n✗ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(main())
