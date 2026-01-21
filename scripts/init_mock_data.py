#!/usr/bin/env python3
"""
Initialize mock data for TokenMachine.

This script creates sample data for development and testing environments.
Usage:
    python scripts/init_mock_data.py [--environment {development,test,production}]
"""
import os
import sys
import argparse
from datetime import datetime, timedelta
from decimal import Decimal

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from backend.core.config import get_settings, Environment
from backend.models.database import (
    Base, Organization, User, ApiKey, Model, Deployment, GPU, UsageLog,
    ModelCategory, ModelSource, ModelStatus, ModelQuantization,
    DeploymentStatus, DeploymentEnvironment, GPUStatus,
    UsageLogStatus, UserRole, OrganizationPlan
)


def create_organization(name: str, plan: OrganizationPlan = OrganizationPlan.FREE) -> Organization:
    """Create an organization with default quotas."""
    quotas = {
        OrganizationPlan.FREE: (10000, 1, 1, 2),
        OrganizationPlan.PROFESSIONAL: (1000000, 10, 5, 10),
        OrganizationPlan.ENTERPRISE: (100000000, 100, 50, 100),
    }
    quota_tokens, quota_models, quota_gpus, max_workers = quotas[plan]

    return Organization(
        name=name,
        plan=plan,
        quota_tokens=quota_tokens,
        quota_models=quota_models,
        quota_gpus=quota_gpus,
        max_workers=max_workers
    )


def create_mock_data(session: Session, environment: Environment) -> None:
    """Create mock data based on environment."""

    # Create organizations
    org_dev = create_organization("DevCorp", OrganizationPlan.PROFESSIONAL)
    org_test = create_organization("TestLab", OrganizationPlan.ENTERPRISE)

    session.add_all([org_dev, org_test])
    session.flush()

    # Create users
    admin_user = User(
        username="admin",
        email="admin@tokenmachine.dev",
        password_hash="$2b$12$dummy_hash_for_admin",  # Dummy hash
        organization_id=org_dev.id,
        role=UserRole.ADMIN,
        is_active=True
    )

    dev_user = User(
        username="developer",
        email="dev@tokenmachine.dev",
        password_hash="$2b$12$dummy_hash_for_dev",  # Dummy hash
        organization_id=org_dev.id,
        role=UserRole.USER,
        is_active=True
    )

    session.add_all([admin_user, dev_user])
    session.flush()

    # Create API keys
    api_key_prod = ApiKey(
        key_hash="hash_prod_key_a7b3c9d4",
        key_prefix="tmachine_sk_a7b3",
        user_id=admin_user.id,
        organization_id=org_dev.id,
        name="Production API Key",
        quota_tokens=100000000,
        tokens_used=12543000,
        is_active=True,
        expires_at=datetime.now() + timedelta(days=365),
        last_used_at=datetime.now() - timedelta(hours=1)
    )

    api_key_dev = ApiKey(
        key_hash="hash_dev_key_c9d4e1f5",
        key_prefix="tmachine_sk_c9d4",
        user_id=dev_user.id,
        organization_id=org_dev.id,
        name="Development Key",
        quota_tokens=10000000,
        tokens_used=2340000,
        is_active=True,
        expires_at=datetime.now() + timedelta(days=180),
        last_used_at=datetime.now() - timedelta(hours=4)
    )

    api_key_test = ApiKey(
        key_hash="hash_test_key_e1f5g2h6",
        key_prefix="tmachine_sk_e1f5",
        user_id=admin_user.id,
        organization_id=org_test.id,
        name="Testing Key",
        quota_tokens=5000000,
        tokens_used=4875000,
        is_active=True,
        expires_at=datetime.now() + timedelta(days=90),
        last_used_at=datetime.now() - timedelta(minutes=30)
    )

    session.add_all([api_key_prod, api_key_dev, api_key_test])
    session.flush()

    # Create models
    models = [
        Model(
            name="Qwen2.5-7B-Instruct",
            version="v2.0",
            source=ModelSource.HUGGINGFACE,
            category=ModelCategory.LLM,
            quantization=ModelQuantization.FP8,
            path="/models/qwen2.5-7b-instruct",
            size_gb=Decimal("14.5"),
            status=ModelStatus.READY
        ),
        Model(
            name="DeepSeek-R1-Distill-Qwen-32B",
            version="v1.0",
            source=ModelSource.HUGGINGFACE,
            category=ModelCategory.LLM,
            quantization=ModelQuantization.FP8,
            path="/models/deepseek-r1-distill-qwen-32b",
            size_gb=Decimal("32.0"),
            status=ModelStatus.READY
        ),
        Model(
            name="GLM-4-9B-Chat",
            version="v3.0",
            source=ModelSource.HUGGINGFACE,
            category=ModelCategory.LLM,
            quantization=ModelQuantization.INT8,
            path="/models/glm-4-9b-chat",
            size_gb=Decimal("18.0"),
            status=ModelStatus.READY
        ),
        Model(
            name="Llama-3-8B-Instruct",
            version="v1.0",
            source=ModelSource.HUGGINGFACE,
            category=ModelCategory.LLM,
            quantization=ModelQuantization.FP16,
            path="/models/llama-3-8b-instruct",
            size_gb=Decimal("16.0"),
            status=ModelStatus.READY
        ),
        Model(
            name="bge-large-zh-v1.5",
            version="v1.5",
            source=ModelSource.HUGGINGFACE,
            category=ModelCategory.EMBEDDING,
            quantization=ModelQuantization.FP16,
            path="/models/bge-large-zh-v1.5",
            size_gb=Decimal("2.5"),
            status=ModelStatus.DOWNLOADING,
            download_progress=75
        ),
        Model(
            name="jina-reranker-v1-base",
            version="v1.0",
            source=ModelSource.HUGGINGFACE,
            category=ModelCategory.RERANKER,
            quantization=ModelQuantization.FP16,
            path="/models/jina-reranker-v1-base",
            size_gb=Decimal("1.2"),
            status=ModelStatus.READY
        ),
    ]

    session.add_all(models)
    session.flush()

    # Create deployments
    deploy_qwen = Deployment(
        model_id=models[0].id,
        name="qwen2.5-7b-prod",
        environment=DeploymentEnvironment.PRODUCTION,
        status=DeploymentStatus.RUNNING,
        replicas=2,
        gpu_ids=["gpu:0", "gpu:1"],
        backend="vllm",
        health_status={"replica_0": "healthy", "replica_1": "healthy"}
    )

    deploy_deepseek = Deployment(
        model_id=models[1].id,
        name="deepseek-r1-prod",
        environment=DeploymentEnvironment.PRODUCTION,
        status=DeploymentStatus.RUNNING,
        replicas=4,
        gpu_ids=["gpu:2", "gpu:3", "gpu:4", "gpu:5"],
        backend="vllm",
        health_status={
            "replica_0": "healthy",
            "replica_1": "healthy",
            "replica_2": "healthy",
            "replica_3": "healthy"
        }
    )

    deploy_glm = Deployment(
        model_id=models[2].id,
        name="glm-4-staging",
        environment=DeploymentEnvironment.STAGING,
        status=DeploymentStatus.RUNNING,
        replicas=1,
        gpu_ids=["gpu:6"],
        backend="vllm",
        health_status={"replica_0": "healthy"}
    )

    deploy_llama = Deployment(
        model_id=models[3].id,
        name="llama-3-dev",
        environment=DeploymentEnvironment.DEV,
        status=DeploymentStatus.STARTING,
        replicas=1,
        gpu_ids=["gpu:7"],
        backend="sglang",
        health_status={}
    )

    session.add_all([deploy_qwen, deploy_deepseek, deploy_glm, deploy_llama])
    session.flush()

    # Create GPUs
    gpus = [
        GPU(gpu_id="gpu:0", name="NVIDIA RTX 4090", memory_total_mb=24576,
            memory_free_mb=8192, memory_used_mb=16384,
            utilization_percent=Decimal("78.5"), temperature_celsius=Decimal("68"),
            status=GPUStatus.IN_USE, deployment_id=deploy_qwen.id),
        GPU(gpu_id="gpu:1", name="NVIDIA RTX 4090", memory_total_mb=24576,
            memory_free_mb=7680, memory_used_mb=16896,
            utilization_percent=Decimal("82.3"), temperature_celsius=Decimal("71"),
            status=GPUStatus.IN_USE, deployment_id=deploy_qwen.id),
        GPU(gpu_id="gpu:2", name="NVIDIA RTX 4090", memory_total_mb=24576,
            memory_free_mb=2048, memory_used_mb=22528,
            utilization_percent=Decimal("91.5"), temperature_celsius=Decimal("79"),
            status=GPUStatus.IN_USE, deployment_id=deploy_deepseek.id),
        GPU(gpu_id="gpu:3", name="NVIDIA RTX 4090", memory_total_mb=24576,
            memory_free_mb=1024, memory_used_mb=23552,
            utilization_percent=Decimal("95.2"), temperature_celsius=Decimal("82"),
            status=GPUStatus.IN_USE, deployment_id=deploy_deepseek.id),
        GPU(gpu_id="gpu:4", name="NVIDIA RTX 4090", memory_total_mb=24576,
            memory_free_mb=3072, memory_used_mb=21504,
            utilization_percent=Decimal("88.0"), temperature_celsius=Decimal("76"),
            status=GPUStatus.IN_USE, deployment_id=deploy_deepseek.id),
        GPU(gpu_id="gpu:5", name="NVIDIA RTX 4090", memory_total_mb=24576,
            memory_free_mb=2560, memory_used_mb=22016,
            utilization_percent=Decimal("89.5"), temperature_celsius=Decimal("77"),
            status=GPUStatus.IN_USE, deployment_id=deploy_deepseek.id),
        GPU(gpu_id="gpu:6", name="NVIDIA RTX 4090", memory_total_mb=24576,
            memory_free_mb=15360, memory_used_mb=9216,
            utilization_percent=Decimal("45.2"), temperature_celsius=Decimal("55"),
            status=GPUStatus.IN_USE, deployment_id=deploy_glm.id),
        GPU(gpu_id="gpu:7", name="NVIDIA RTX 4090", memory_total_mb=24576,
            memory_free_mb=24576, memory_used_mb=0,
            utilization_percent=Decimal("0"), temperature_celsius=Decimal("38"),
            status=GPUStatus.AVAILABLE, deployment_id=None),
    ]

    session.add_all(gpus)
    session.flush()

    # Create usage logs
    now = datetime.now()
    usage_logs = [
        UsageLog(
            api_key_id=api_key_prod.id,
            deployment_id=deploy_qwen.id,
            model_id=models[0].id,
            input_tokens=150,
            output_tokens=300,
            latency_ms=250,
            status=UsageLogStatus.SUCCESS,
            created_at=now - timedelta(minutes=30)
        ),
        UsageLog(
            api_key_id=api_key_prod.id,
            deployment_id=deploy_deepseek.id,
            model_id=models[1].id,
            input_tokens=2000,
            output_tokens=1500,
            latency_ms=800,
            status=UsageLogStatus.SUCCESS,
            created_at=now - timedelta(minutes=25)
        ),
        UsageLog(
            api_key_id=api_key_dev.id,
            deployment_id=deploy_glm.id,
            model_id=models[2].id,
            input_tokens=100,
            output_tokens=200,
            latency_ms=420,
            status=UsageLogStatus.SUCCESS,
            created_at=now - timedelta(minutes=20)
        ),
        UsageLog(
            api_key_id=api_key_prod.id,
            deployment_id=deploy_qwen.id,
            model_id=models[0].id,
            input_tokens=50,
            output_tokens=0,
            latency_ms=0,
            status=UsageLogStatus.ERROR,
            error_message="Model timeout",
            created_at=now - timedelta(minutes=15)
        ),
    ]

    session.add_all(usage_logs)

    # Commit all changes
    session.commit()

    print(f"✓ Mock data created for {environment.value} environment")
    print(f"  - Organizations: 2")
    print(f"  - Users: 2")
    print(f"  - API Keys: 3")
    print(f"  - Models: {len(models)}")
    print(f"  - Deployments: 4")
    print(f"  - GPUs: {len(gpus)}")
    print(f"  - Usage Logs: {len(usage_logs)}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Initialize mock data for TokenMachine")
    parser.add_argument(
        "--environment", "-e",
        choices=["development", "test", "production"],
        default=None,
        help="Environment to initialize (default: from settings or development)"
    )
    parser.add_argument(
        "--force", "-f",
        action="store_true",
        help="Force initialization even in production"
    )
    parser.add_argument(
        "--clear", "-c",
        action="store_true",
        help="Clear existing data before creating mock data"
    )

    args = parser.parse_args()

    # Get settings
    settings = get_settings()

    # Determine environment
    environment = Environment(args.environment) if args.environment else settings.environment

    # Safety check for production
    if environment == Environment.PRODUCTION and not args.force:
        print("⚠ WARNING: Attempting to initialize mock data in production environment!")
        print("This will add sample data to your production database.")
        confirm = input("Are you sure you want to continue? (type 'yes' to confirm): ")
        if confirm.lower() != "yes":
            print("✗ Initialization cancelled")
            return 1

    # Create database engine
    print(f"Connecting to database: {settings.database_url}")
    engine = create_engine(settings.database_url, echo=False)

    # Create tables
    print("Creating tables...")
    Base.metadata.create_all(bind=engine)

    # Create session
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()

    try:
        # Clear existing data if requested
        if args.clear:
            print("Clearing existing data...")
            session.query(UsageLog).delete()
            session.query(GPU).delete()
            session.query(Deployment).delete()
            session.query(Model).delete()
            session.query(ApiKey).delete()
            session.query(User).delete()
            session.query(Organization).delete()
            session.commit()
            print("✓ Existing data cleared")

        # Check if data already exists
        existing_orgs = session.query(Organization).count()
        if existing_orgs > 0 and not args.clear:
            print(f"⚠ Database already contains data ({existing_orgs} organizations)")
            print("Use --clear to remove existing data before initialization")
            return 1

        # Create mock data
        print(f"Initializing mock data for {environment.value} environment...")
        create_mock_data(session, environment)

        print("\n✓ Mock data initialization completed successfully!")
        return 0

    except Exception as e:
        session.rollback()
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        session.close()


if __name__ == "__main__":
    sys.exit(main())
