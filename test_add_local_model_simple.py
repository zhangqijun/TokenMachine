#!/usr/bin/env python3
"""
测试添加本地模型接口 - 简化版
"""
import sys
import os
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

# 配置测试环境
os.environ['DATABASE_URL'] = 'sqlite:////tmp/tokenmachine_test_add_local/tokenmachine.db'
os.environ['MODEL_STORAGE_PATH'] = '/tmp/tokenmachine_test_add_local/models'
os.environ['MODELSCOPE_CACHE_DIR'] = '/tmp/tokenmachine_test_add_local/cache'
os.environ['LOG_PATH'] = '/tmp/tokenmachine_test_add_local/logs'
os.environ['NFS_MOUNT_POINT'] = '/tmp/tokenmachine_test_add_local/models'
os.environ['ENVIRONMENT'] = 'development'
os.environ['DEBUG'] = 'true'

# 确保目录存在
for path in ['/tmp/tokenmachine_test_add_local/models', '/tmp/tokenmachine_test_add_local/cache', '/tmp/tokenmachine_test_add_local/logs']:
    Path(path).mkdir(parents=True, exist_ok=True)

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from backend.models.database import Base, Model, ModelSource, ModelCategory
from backend.services.model_service import ModelService

print("=" * 70)
print("测试添加本地模型接口")
print("=" * 70)
print()

# 1. 初始化数据库
print("[1/4] 初始化数据库...")
db_url = "sqlite:////tmp/tokenmachine_test_add_local/tokenmachine.db"
engine = create_engine(db_url, echo=False)
SessionLocal = sessionmaker(bind=engine)
Base.metadata.create_all(bind=engine)
print("  ✅ 数据库初始化完成")
print()

# 2. 创建测试会话
print("[2/4] 创建测试会话...")
db: Session = SessionLocal()
print("  ✅ 测试会话创建完成")
print()

# 3. 测试添加本地模型
print("[3/4] 测试添加本地模型...")
service = ModelService(db)

# 检查真实路径是否存在
test_path = "/home/ht706/Qwen3-Coder-30B-A3B-Instruct-Int4-W4A16"
use_real_path = False

if os.path.exists(test_path):
    print(f"  ✅ 找到真实路径: {test_path}")
    use_real_path = True
else:
    print(f"  ⚠️  警告: 真实路径不存在: {test_path}")
    print(f"  创建模拟模型用于测试...")

    # 创建一个模拟的模型目录
    mock_path = "/tmp/tokenmachine_test_add_local/mock_model"
    os.makedirs(mock_path, exist_ok=True)

    # 创建模拟的 config.json
    import json
    config_content = {
        "model_type": "qwen",
        "hidden_size": 5120,
        "num_attention_heads": 40,
        "num_hidden_layers": 40
    }
    with open(os.path.join(mock_path, "config.json"), "w") as f:
        json.dump(config_content, f)

    # 创建模拟的模型权重文件
    with open(os.path.join(mock_path, "model.safetensors"), "wb") as f:
        f.write(b"0" * (100 * 1024 * 1024))  # 100 MB

    # 创建 tokenizer 文件
    with open(os.path.join(mock_path, "tokenizer_config.json"), "w") as f:
        json.dump({"tokenizer_type": "qwen"}, f)

    test_path = mock_path
    print(f"  ✅ 创建模拟模型目录: {mock_path}")

print()

try:
    # 添加本地模型
    print("  调用 add_local_model...")
    model = service.add_local_model(
        name="Qwen3-Coder-30B-Test",
        version="v1.0.0",
        local_path=test_path,
        category=ModelCategory.LLM,
        quantization="int8"
    )

    print()
    print("[4/4] 验证模型创建结果...")
    print(f"  ✅ 模型创建成功!")
    print(f"     ID: {model.id}")
    print(f"     名称: {model.name}")
    print(f"     版本: {model.version}")
    print(f"     来源: {model.source.value}")
    print(f"     类别: {model.category.value}")
    print(f"     量化: {model.quantization}")
    print(f"     状态: {model.status.value}")
    print(f"     路径: {model.path}")
    print(f"     存储路径: {model.storage_path}")
    print(f"     存储类型: {model.storage_type}")
    print(f"     大小: {model.size_gb} GB")
    print(f"     下载进度: {model.download_progress}%")
    print()

    # 验证数据库记录
    print("  验证数据库记录...")
    db.refresh(model)

    # 查询模型
    found_model = service.get_model(model.id)
    assert found_model is not None, "模型未找到"
    assert found_model.name == "Qwen3-Coder-30B-Test", "模型名称不匹配"
    assert found_model.source == ModelSource.LOCAL, "模型来源不匹配"
    assert found_model.status.value == "ready", "模型状态不匹配"
    assert found_model.path == test_path, "模型路径不匹配"
    assert found_model.storage_path == test_path, "存储路径不匹配"
    assert found_model.storage_type == "local", "存储类型不匹配"

    print("  ✅ 数据库记录验证通过")
    print()

    # 列出所有模型
    print("  所有模型列表:")
    all_models = service.list_models()
    for m in all_models:
        print(f"    - {m.name}:{m.version} ({m.source.value}, {m.status.value}, {m.size_gb} GB)")

    print()
    print("=" * 70)
    print("✅ 所有测试通过!")
    print("=" * 70)
    print()
    print("📋 API 接口使用说明:")
    print(f"  URL: POST /api/v1/admin/models/local")
    print(f"  请求体:")
    print(f"  {{")
    print(f"    \"name\": \"Qwen3-Coder-30B\",")
    print(f"    \"version\": \"v1.0.0\",")
    print(f"    \"local_path\": \"{test_path}\",")
    print(f"    \"category\": \"llm\",")
    print(f"    \"quantization\": \"int8\"")
    print(f"  }}")
    print()
    print(f"  使用真实路径: {use_real_path}")
    if use_real_path:
        print(f"  真实模型大小: {model.size_gb} GB")

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
