#!/usr/bin/env python3
"""
测试模型下载功能
使用 SQLite 数据库和临时目录进行测试
"""
import os
import sys
import asyncio
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
from backend.models.database import Base, Model, ModelSource, ModelCategory, ModelStatus
from backend.services.model_download_service import ModelDownloadService

print("=" * 70)
print("模型下载功能测试")
print("=" * 70)
print()

# 1. 创建数据库连接
print("[1/6] 创建数据库连接...")
db_url = "sqlite:////tmp/tokenmachine_test/tokenmachine.db"
engine = create_engine(db_url, echo=True)
SessionLocal = sessionmaker(bind=engine)
print(f"  ✅ 数据库: {db_url}")
print()

# 2. 创建所有表
print("[2/6] 创建数据库表...")
Base.metadata.create_all(bind=engine)
print("  ✅ 表创建成功")
print()

# 3. 创建测试模型
print("[3/6] 创建测试模型...")
db: Session = SessionLocal()

# 检查是否已存在
existing = db.query(Model).filter(Model.name == "qwen-1.5b-chat").first()
if existing:
    print(f"  ℹ️  模型已存在 (ID: {existing.id})")
    model = existing
else:
    model = Model(
        name="qwen-1.5b-chat",
        version="v1.0.0",
        source=ModelSource.MODELSCOPE,
        category=ModelCategory.LLM,
        status=ModelStatus.DOWNLOADING
    )
    db.add(model)
    db.commit()
    db.refresh(model)
    print(f"  ✅ 模型创建成功 (ID: {model.id})")
print()

# 4. 创建下载服务并开始下载
print("[4/6] 开始下载模型...")
print(f"  模型ID: {model.id}")
print(f"  ModelScope 仓库: Qwen/Qwen1.5-1.8B-Chat")
print(f"  存储路径: /tmp/tokenmachine_test/models/Qwen--Qwen1.5-1.8B-Chat")
print()

service = ModelDownloadService(db)

async def test_download():
    try:
        task = await service.create_download_task(
            model_id=model.id,
            modelscope_repo_id="Qwen/Qwen1.5-1.8B-Chat",
            revision="master"
        )

        print(f"  ✅ 下载任务创建成功!")
        print(f"     任务ID: {task.id}")
        print(f"     状态: {task.status.value}")
        print(f"     存储路径: {task.model.storage_path}")
        print()

        # 5. 等待下载完成
        print("[5/6] 等待下载完成...")
        print("  提示: 这是一个小模型 (~3.5GB)，可能需要几分钟...")
        print()

        # 轮询状态
        import time
        last_progress = 0
        max_wait_time = 600  # 最多等待10分钟
        start_time = time.time()

        while time.time() - start_time < max_wait_time:
            await asyncio.sleep(10)  # 每10秒检查一次

            status = await service.get_download_status(model.id)
            progress = status['progress']

            if progress != last_progress:
                print(f"  进度: {progress}% | "
                      f"已下载: {status['downloaded_bytes'] / (1024**3):.2f} GB / "
                      f"{status['total_bytes'] / (1024**3):.2f} GB")
                last_progress = progress

            if status['status'] in ['completed', 'failed', 'cancelled']:
                print()
                print(f"  最终状态: {status['status']}")

                if status['status'] == 'completed':
                    print(f"  ✅ 下载完成!")
                    print(f"     总大小: {status['total_bytes'] / (1024**3):.2f} GB")
                    print(f"     存储路径: {status.get('storage_path', 'N/A')}")

                    # 6. 验证文件
                    print()
                    print("[6/6] 验证下载文件...")
                    storage_path = f"/tmp/tokenmachine_test/models/Qwen--Qwen1.5-1.8B-Chat"
                    if os.path.exists(storage_path):
                        files = list(Path(storage_path).rglob("*"))
                        print(f"  ✅ 文件数: {len(files)}")
                        print(f"  主要文件:")
                        for f in sorted(files)[:10]:
                            if f.is_file() and not f.name.startswith('.'):
                                size_mb = f.stat().st_size / (1024**2)
                                print(f"    - {f.name} ({size_mb:.1f} MB)")
                        if len(files) > 10:
                            print(f"    ... 还有 {len(files) - 10} 个文件")
                    else:
                        print(f"  ❌ 文件不存在: {storage_path}")
                else:
                    print(f"  ❌ 下载失败: {status.get('error_message', 'Unknown error')}")

                break

        else:
            print()
            print("  ⏰ 超时: 下载时间超过10分钟")

    except Exception as e:
        print(f"  ❌ 错误: {e}")
        import traceback
        traceback.print_exc()

    finally:
        db.close()

# 运行测试
asyncio.run(test_download())

print()
print("=" * 70)
print("测试完成!")
print("=" * 70)
