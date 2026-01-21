#!/usr/bin/env python3
"""
测试添加本地模型接口
"""
import sys
import os
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

# 配置测试环境
os.environ['DATABASE_URL'] = 'sqlite:////tmp/tokenmachine_test/tokenmachine.db'
os.environ['MODEL_STORAGE_PATH'] = '/tmp/tokenmachine_test/models'
os.environ['MODELSCOPE_CACHE_DIR'] = '/tmp/tokenmachine_test/cache'
os.environ['LOG_PATH'] = '/tmp/tokenmachine_test/logs'
os.environ['NFS_MOUNT_POINT'] = '/tmp/tokenmachine_test/models'
os.environ['ENVIRONMENT'] = 'development'
os.environ['DEBUG'] = 'true'

# 确保目录存在
for path in ['/tmp/tokenmachine_test/models', '/tmp/tokenmachine_test/cache', '/tmp/tokenmachine_test/logs']:
    Path(path).mkdir(parents=True, exist_ok=True)

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from backend.models.database import Base, Model, User, Organization, ModelSource, ModelCategory, UserRole
from backend.services.model_service import ModelService
from backend.core.security import hash_password
from datetime import datetime, timedelta

print("=" * 70)
print("测试添加本地模型接口")
print("=" * 70)
print()

# 1. 初始化数据库
print("[1/5] 初始化数据库...")
db_url = "sqlite:////tmp/tokenmachine_test/tokenmachine.db"
engine = create_engine(db_url, echo=False)
SessionLocal = sessionmaker(bind=engine)
Base.metadata.drop_all(bind=engine)
Base.metadata.create_all(bind=engine)
print("  ✅ 数据库初始化完成")
print()

# 2. 创建测试数据
print("[2/5] 创建测试组织和用户...")
db: Session = SessionLocal()

org = Organization(
    id=1,
    name='test_org',
    plan='ENTERPRISE',
    quota_tokens=1000000000,
    quota_models=100,
    quota_gpus=10,
    max_workers=5
)
db.add(org)
db.flush()

admin = User(
    id=1,
    username='admin',
    email='admin@test.com',
    password_hash=hash_password('test'),
    organization_id=org.id,
    role='ADMIN',
    is_active=True
)
db.add(admin)
db.flush()
print("  ✅ 测试用户创建完成")
print()

# 3. 测试添加本地模型
print("[3/5] 测试添加本地模型...")
print(f"  本地路径: /home/ht706/Qwen3-Coder-30B-A3B-Instruct-Int4-W4A16")

service = ModelService(db)

try:
    # 验证路径是否存在
    test_path = "/home/ht706/Qwen3-Coder-30B-A3B-Instruct-Int4-W4A16"
    if not os.path.exists(test_path):
        print(f"  ⚠️  警告: 本地路径不存在: {test_path}")
        print(f"  使用模拟路径进行测试...")

        # 创建一个模拟的模型目录
        mock_path = "/tmp/tokenmachine_test/mock_model"
        os.makedirs(mock_path, exist_ok=True)

        # 创建模拟的 config.json
        config_content = {
            "model_type": "qwen",
            "hidden_size": 5120,
            "num_attention_heads": 40
        }
        import json
        with open(os.path.join(mock_path, "config.json"), "w") as f:
            json.dump(config_content, f)

        # 创建模拟的模型权重文件
        with open(os.path.join(mock_path, "model.safetensors"), "wb") as f:
            f.write(b"0" * (100 * 1024 * 1024))  # 100 MB

        print(f"  ✅ 创建模拟模型目录: {mock_path}")
        test_path = mock_path

    # 添加本地模型
    model = service.add_local_model(
        name="Qwen3-Coder-30B-Test",
        version="v1.0.0",
        local_path=test_path,
        category=ModelCategory.LLM,
        quantization="int8"
    )

    print()
    print("[4/5] 验证模型创建结果...")
    print(f"  ✅ 模型创建成功!")
    print(f"     ID: {model.id}")
    print(f"     名称: {model.name}")
    print(f"     版本: {model.version}")
    print(f"     来源: {model.source.value}")
    print(f"     类别: {model.category.value}")
    print(f"     量化: {model.quantization}")
    print(f"     状态: {model.status.value}")
    print(f"     路径: {model.path}")
    print(f"     大小: {model.size_gb} GB")
    print(f"     下载进度: {model.download_progress}%")
    print()

    # 5. 验证数据库记录
    print("[5/5] 验证数据库记录...")
    db.refresh(model)

    # 查询模型
    found_model = service.get_model(model.id)
    assert found_model is not None, "模型未找到"
    assert found_model.name == "Qwen3-Coder-30B-Test", "模型名称不匹配"
    assert found_model.source == ModelSource.LOCAL, "模型来源不匹配"
    assert found_model.status.value == "ready", "模型状态不匹配"

    print("  ✅ 数据库记录验证通过")
    print()

    # 6. 列出所有模型
    print("所有模型列表:")
    all_models = service.list_models()
    for m in all_models:
        print(f"  - {m.name}:{m.version} ({m.source.value}, {m.status.value})")

    print()
    print("=" * 70)
    print("✅ 测试通过!")
    print("=" * 70)
    print()
    print("API 接口示例:")
    print(f"  POST /api/v1/admin/models/local")
    print(f"  {{")
    print(f"    \"name\": \"Qwen3-Coder-30B\",")
    print(f"    \"version\": \"v1.0.0\",")
    print(f"    \"local_path\": \"{test_path}\",")
    print(f"    \"category\": \"llm\",")
    print(f"    \"quantization\": \"int8\"")
    print(f"  }}")

except Exception as e:
    print()
    print("=" * 70)
    print("❌ 测试失败!")
    print("=" * 70)
    print(f"错误: {e}")
    import traceback
    traceback.print_exc()

finally:
    db.close()
