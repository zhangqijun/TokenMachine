# 模型下载与分发设计

> 基于 ModelScope 的模型下载、存储与分发方案，支持 NFS 共享存储和多 Worker 协同加载

---

## 目录

- [1. 概述](#1-概述)
- [2. 核心设计原则](#2-核心设计原则)
- [3. 存储架构](#3-存储架构)
- [4. 数据库设计](#4-数据库设计)
- [5. 服务层设计](#5-服务层设计)
- [6. API 接口](#6-api-接口)
- [7. Worker 模型加载](#7-worker-模型加载)
- [8. 部署配置](#8-部署配置)
- [9. 工作流程](#9-工作流程)
- [10. 监控与日志](#10-监控与日志)
- [11. 故障处理](#11-故障处理)
- [12. 实施计划](#12-实施计划)

---

## 1. 概述

### 1.1 背景

TokenMachine 是一个分布式模型推理平台，支持多个 Worker 节点协同工作。模型下载与分发是核心功能之一，需要解决以下问题：

- **模型来源**：统一使用 ModelScope 作为模型仓库
- **存储共享**：多个 Worker 需要访问同一份模型文件
- **下载管理**：支持异步下载、进度追踪、断点续传
- **缓存同步**：Worker 需要知道哪些模型可用

### 1.2 设计目标

| 目标 | 说明 |
|------|------|
| **单一来源** | 仅支持 ModelScope，简化实现 |
| **复用 SDK** | 使用 ModelScope 官方 Python 包，不重复造轮子 |
| **共享存储** | 使用 NFS 实现模型文件共享，避免多份副本 |
| **职责分离** | Server 负责下载，Worker 负责加载 |
| **状态同步** | 通过数据库和消息队列实现状态同步 |

### 1.3 系统边界

**包含功能**：
- ✅ 从 ModelScope 下载模型
- ✅ NFS 共享存储管理
- ✅ 下载任务管理和进度追踪
- ✅ Worker 模型缓存同步
- ✅ 模型路径解析和加载

**不包含功能**：
- ❌ 多模型源支持（仅 ModelScope）
- ❌ 模型格式转换
- ❌ 模型微调
- ❌ 模型版本管理（基础版本记录除外）

---

## 2. 核心设计原则

### 2.1 存储方案选型

```
┌─────────────────────────────────────────────────────────────────┐
│                    存储方案对比                                    │
├─────────────────────┬───────────────────┬─────────────────┬──────┤
│ 方案                │ 优点              │ 缺点            │ 推荐  │
├─────────────────────┼───────────────────┼─────────────────┼──────┤
│ NFS 共享存储        │ 单副本；易管理     │ 网络 I/O        │ ⭐⭐⭐⭐⭐ │
│ 本地存储 + 同步     │ I/O 快            │ 浪费空间；复杂  │ ⭐⭐   │
│ 对象存储 (S3/MinIO) │ 高可用；可扩展     │ 需要下载到本地  │ ⭐⭐⭐  │
│ 分布式文件系统 (Ceph)│ 高性能；高可用     │ 运维复杂        │ ⭐⭐⭐⭐ │
└─────────────────────┴───────────────────┴─────────────────┴──────┘
```

**推荐方案：NFS 共享存储**

**理由**：
1. 模型文件大（几十GB 到几百GB），单副本节省存储空间
2. 模型读多写少，适合共享存储
3. 运维简单，统一管理
4. NFS 技术成熟稳定

### 2.2 架构分层

```
┌─────────────────────────────────────────────────────────────────┐
│                        API Layer                                │
│  POST /models/{id}/download                                     │
│  GET  /models/{id}/download/status                              │
└────────────────────────────┬────────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────────┐
│                     Service Layer                               │
│  ModelDownloadService                                           │
│  - create_download_task()                                       │
│  - execute_download()                                           │
│  - monitor_progress()                                           │
│  - notify_workers()                                             │
└────────────────────────────┬────────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────────┐
│                     ModelScope SDK                              │
│  python -m modelscope.hub.cli download                          │
└────────────────────────────┬────────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────────┐
│                  NFS Shared Storage                             │
│  /var/lib/tokenmachine/models/                                 │
│  ├── qwen-72b-chat/                                             │
│  └── llama-3-8b-instruct/                                       │
└─────────────────────────────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Worker Nodes                               │
│  Worker1: /mnt/models/ → WorkerModelLoader                      │
│  Worker2: /mnt/models/ → WorkerModelLoader                      │
│  WorkerN: /mnt/models/ → WorkerModelLoader                      │
└─────────────────────────────────────────────────────────────────┘
```

---

## 3. 存储架构

### 3.1 目录结构

```
/var/lib/tokenmachine/                     # 根目录
├── models/                               # 共享模型存储 (NFS 挂载点)
│   ├── qwen-72b-chat/
│   │   ├── config.json
│   │   ├── model-00001-of-00008.safetensors
│   │   ├── model-00002-of-00008.safetensors
│   │   ├── tokenizer.json
│   │   ├── tokenizer_config.json
│   │   └── .download_metadata.json       # 下载元数据
│   ├── llama-3-8b-instruct/
│   │   └── ...
│   └── .registry.json                    # 模型注册表（可选）
│
├── cache/                                # 下载缓存
│   └── modelscope/                       # ModelScope SDK 缓存
│       ├── hub/
│       └── temp/
│
└── logs/
    └── downloads/                        # 下载日志
        ├── qwen-72b-chat_20250121_143022.log
        └── ...
```

### 3.2 存储路径规范

| 组件 | 路径 | 说明 |
|------|------|------|
| **模型存储** | `/var/lib/tokenmachine/models/` | NFS 共享存储根目录 |
| **单个模型** | `/var/lib/tokenmachine/models/{org--name}/` | 将 `/` 替换为 `--` |
| **ModelScope 缓存** | `/var/lib/tokenmachine/cache/modelscope/` | 下载缓存 |
| **下载日志** | `/var/lib/tokenmachine/logs/downloads/` | 下载任务日志 |

**示例**：
- ModelScope 仓库 ID: `Qwen/qwen-72b-chat`
- 存储路径: `/var/lib/tokenmachine/models/Qwen--qwen-72b-chat/`

### 3.3 部署架构图

```
┌─────────────────────────────────────────────────────────────────┐
│                         Server Node                              │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │  FastAPI Server                                             ││
│  │  - API Gateway                                              ││
│  │  - Model Management                                         ││
│  │  - Download Orchestration                                   ││
│  └─────────────────────────────────────────────────────────────┘│
│  ┌─────────────────────────────────────────────────────────────┐│
│  │  PostgreSQL                                                 ││
│  │  - models 表                                                ││
│  │  - model_download_tasks 表                                 ││
│  │  - worker_model_cache 表                                    ││
│  └─────────────────────────────────────────────────────────────┘│
│  ┌─────────────────────────────────────────────────────────────┐│
│  │  NFS Server (可选)                                          ││
│  │  Export: /var/lib/tokenmachine/models                      ││
│  └─────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ NFS Mount
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Shared Storage (NFS)                         │
│  /var/lib/tokenmachine/models/                                 │
│  ├── Qwen--qwen-72b-chat/                                       │
│  └── meta-llama--Llama-3-8b-Instruct/                          │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ Mounted by each Worker
                              ▼
┌──────────────────────┐  ┌──────────────────────┐  ┌──────────────┐
│   Worker 1           │  │   Worker 2           │  │  Worker N    │
│ ┌──────────────────┐ │  │ ┌──────────────────┐ │  │              │
│ │ vLLM Instance   │ │  │ │ vLLM Instance   │ │  │              │
│ │ └── Load Model  │ │  │ │ └── Load Model  │ │  │              │
│ └──────────────────┘ │  │ └──────────────────┘ │  │              │
│                      │  │                      │  │              │
│ /mnt/models ────────┴──┴── /mnt/models ────────┴──┴── /mnt/models│
│  (NFS Mount)         │     (NFS Mount)           │   (NFS Mount) │
└─────────────────────┴─────────────────────────────┴──────────────┘
```

### 3.4 权限与安全

```bash
# 目录权限设置
/var/lib/tokenmachine/models  → 755 (tokenmachine:tokenmachine)
/var/lib/tokenmachine/cache   → 755 (tokenmachine:tokenmachine)

# NFS 导出配置
/var/lib/tokenmachine/models *(rw,sync,no_subtree_check,no_root_squash)
```

---

## 4. 数据库设计

### 4.1 models 表扩展

```sql
-- 在现有 models 表基础上添加字段
ALTER TABLE models ADD COLUMN IF NOT EXISTS:
    -- ModelScope 特定字段
    modelscope_repo_id VARCHAR(255),          -- ModelScope 仓库 ID (Qwen/qwen-72b-chat)
    modelscope_revision VARCHAR(50) DEFAULT 'master',

    -- 存储信息
    storage_path VARCHAR(1024),               -- /var/lib/tokenmachine/models/Qwen--qwen-72b-chat
    storage_type VARCHAR(50) DEFAULT 'nfs',   -- nfs, local, s3

    -- 下载任务关联
    download_task_id BIGINT REFERENCES model_download_tasks(id);

-- 创建索引
CREATE INDEX idx_models_modelscope_repo ON models(modelscope_repo_id);
CREATE INDEX idx_models_storage_path ON models(storage_path);
```

### 4.2 model_download_tasks 表（新建）

```sql
CREATE TABLE model_download_tasks (
    id BIGSERIAL PRIMARY KEY,
    model_id BIGINT NOT NULL REFERENCES models(id) ON DELETE CASCADE,

    -- ModelScope 配置
    modelscope_repo_id VARCHAR(255) NOT NULL,
    modelscope_revision VARCHAR(50) DEFAULT 'master',

    -- 下载状态
    status VARCHAR(50) DEFAULT 'pending',
        -- pending: 等待执行
        -- downloading: 下载中
        -- completed: 完成
        -- failed: 失败
        -- cancelled: 已取消

    progress INT DEFAULT 0,                   -- 0-100
    current_file VARCHAR(512),                -- 当前下载文件
    error_message TEXT,

    -- 进度追踪（ModelScope SDK 输出解析）
    downloaded_files INT DEFAULT 0,
    total_files INT,
    downloaded_bytes BIGINT DEFAULT 0,
    total_bytes BIGINT,
    download_speed_mbps DECIMAL(10, 2),

    -- 时间戳
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 索引
CREATE INDEX idx_download_tasks_status ON model_download_tasks(status);
CREATE INDEX idx_download_tasks_model ON model_download_tasks(model_id);
CREATE INDEX idx_download_tasks_created ON model_download_tasks(created_at DESC);
```

### 4.3 worker_model_cache 表（新建）

```sql
CREATE TABLE worker_model_cache (
    id BIGSERIAL PRIMARY KEY,
    worker_id BIGINT NOT NULL REFERENCES workers(id) ON DELETE CASCADE,
    model_id BIGINT NOT NULL REFERENCES models(id) ON DELETE CASCADE,

    -- 缓存状态
    is_cached BOOLEAN DEFAULT FALSE,         -- 模型是否在 Worker 上可用
    cache_path VARCHAR(1024),                -- Worker 本地路径（如果支持本地缓存）
    cache_size_gb DECIMAL(10, 2),

    -- 使用情况
    last_loaded_at TIMESTAMP,
    load_count INT DEFAULT 0,

    -- 同步状态
    sync_status VARCHAR(50) DEFAULT 'synced',
        -- synced: 已同步
        -- syncing: 同步中
        -- outdated: 已过期（模型已更新）
    last_synced_at TIMESTAMP,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    UNIQUE (worker_id, model_id)
);

-- 索引
CREATE INDEX idx_worker_cache_worker ON worker_model_cache(worker_id);
CREATE INDEX idx_worker_cache_model ON worker_model_cache(model_id);
CREATE INDEX idx_worker_cache_cached ON worker_model_cache(is_cached);
```

### 4.4 ER 图

```
┌─────────────┐       ┌─────────────────────┐       ┌─────────────────┐
│   Models    │───────│ DownloadTasks       │       │   Workers       │
├─────────────┤ 1   1 ├─────────────────────┤       ├─────────────────┤
│ id (PK)     │       │ id (PK)             │       │ id (PK)         │
│ name        │       │ model_id (FK)       │       │ name            │
│ version     │       │ modelscope_repo_id  │       │ ip              │
│ status      │       │ status              │       │ status          │
│ storage_path│       │ progress            │       └────────┬────────┘
│ download_   │       │ error_message       │                │
│   task_id   │       │ created_at          │                │
└─────────────┘       └─────────────────────┘                │
                                                                │
┌─────────────────────┐                                         │
│ WorkerModelCache    │◄────────────────────────────────────────┘
├─────────────────────┤   N   1
│ id (PK)             │
│ worker_id (FK)      │
│ model_id (FK)       │
│ is_cached           │
│ cache_path          │
│ last_loaded_at      │
│ sync_status         │
└─────────────────────┘
```

---

## 5. 服务层设计

### 5.1 ModelDownloadService

```python
# backend/services/model_download.py
from typing import Optional
from sqlalchemy.orm import Session
from backend.models.database import Model, ModelDownloadTask
from core.config import settings
import subprocess
import asyncio
import json
import os
from datetime import datetime

class ModelDownloadService:
    """模型下载服务 - 基于 ModelScope SDK"""

    def __init__(self, db: Session):
        self.db = db
        self.storage_base = settings.MODEL_STORAGE_PATH
        self.modelscope_cache = settings.MODELSCOPE_CACHE_DIR

    async def create_download_task(
        self,
        model_id: int,
        modelscope_repo_id: str,
        revision: str = "master"
    ) -> ModelDownloadTask:
        """
        创建 ModelScope 模型下载任务

        Args:
            model_id: 数据库模型 ID
            modelscope_repo_id: ModelScope 仓库 ID (e.g., "Qwen/qwen-72b-chat")
            revision: 分支/标签/commit (默认: master)

        Returns:
            ModelDownloadTask: 下载任务对象

        Raises:
            ValueError: 模型不存在或已下载
        """
        # 1. 验证模型
        model = self.db.query(Model).filter(Model.id == model_id).first()
        if not model:
            raise ValueError(f"Model {model_id} not found")

        if model.status == "ready":
            raise ValueError("Model already downloaded")

        # 2. 检查是否已有进行中的任务
        existing_task = self.db.query(ModelDownloadTask).filter(
            ModelDownloadTask.model_id == model_id,
            ModelDownloadTask.status.in_(["pending", "downloading"])
        ).first()

        if existing_task:
            return existing_task

        # 3. 获取模型信息（通过 ModelScope API）
        repo_info = await self._get_modelscope_repo_info(modelscope_repo_id, revision)

        # 4. 计算存储路径
        safe_name = modelscope_repo_id.replace("/", "--")
        storage_path = f"{self.storage_base}/{safe_name}"

        # 5. 创建下载任务
        task = ModelDownloadTask(
            model_id=model_id,
            modelscope_repo_id=modelscope_repo_id,
            modelscope_revision=revision,
            status="pending",
            total_files=repo_info.get("file_count", 0),
            total_bytes=repo_info.get("total_size", 0)
        )

        self.db.add(task)
        self.db.commit()
        self.db.refresh(task)

        # 6. 更新模型记录
        model.modelscope_repo_id = modelscope_repo_id
        model.modelscope_revision = revision
        model.storage_path = storage_path
        model.download_task_id = task.id
        model.status = "downloading"
        self.db.commit()

        # 7. 异步执行下载
        asyncio.create_task(self._execute_download(task.id))

        return task

    async def _get_modelscope_repo_info(
        self,
        repo_id: str,
        revision: str
    ) -> dict:
        """获取 ModelScope 仓库信息"""
        try:
            from modelscope.hub.api import HubApi

            api = HubApi()
            model_info = api.get_model_info(
                model_id=repo_id,
                revision=revision
            )

            # 计算总大小
            siblings = model_info.get("siblings", [])
            total_size = sum(
                f.get("size", 0)
                for f in siblings
                if f.get("rfilename") and not f.get("rfilename", "").endswith("/")
            )

            file_count = len([
                f for f in siblings
                if f.get("rfilename") and not f.get("rfilename", "").endswith("/")
            ])

            return {
                "file_count": file_count,
                "total_size": total_size
            }
        except Exception as e:
            # 如果 API 调用失败，返回默认值
            return {"file_count": 0, "total_size": 0}

    async def _execute_download(self, task_id: int):
        """执行下载任务（在后台运行）"""
        task = self.db.query(ModelDownloadTask).filter(
            ModelDownloadTask.id == task_id
        ).first()

        if not task:
            return

        log_file = None

        try:
            # 更新状态
            task.status = "downloading"
            task.started_at = datetime.now()
            self.db.commit()

            # 创建日志文件
            log_dir = f"{settings.LOG_PATH}/downloads"
            os.makedirs(log_dir, exist_ok=True)
            log_file = f"{log_dir}/{task.modelscope_repo_id.replace('/', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

            # 构建下载命令
            storage_path = task.model.storage_path

            cmd = [
                "python", "-m", "modelscope.hub.cli", "download",
                "--model", task.modelscope_repo_id,
                "--revision", task.modelscope_revision,
                "--local_dir", storage_path,
                "--cache_dir", self.modelscope_cache
            ]

            # 记录日志
            with open(log_file, "w") as log:
                log.write(f"[{datetime.now()}] Starting download: {task.modelscope_repo_id}\n")
                log.write(f"[{datetime.now()}] Command: {' '.join(cmd)}\n")
                log.flush()

                # 执行下载
                process = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    cwd=self.storage_base
                )

                # 监控进度
                await self._monitor_download_progress(task, process, log)

                # 等待完成
                returncode = await process.wait()

                if returncode == 0:
                    log.write(f"[{datetime.now()}] Download completed successfully\n")

                    # 下载成功
                    task.status = "completed"
                    task.completed_at = datetime.now()
                    task.progress = 100

                    # 计算实际大小
                    actual_size = self._calculate_model_size(storage_path)
                    task.total_bytes = actual_size

                    # 更新模型状态
                    model = task.model
                    model.status = "ready"
                    model.size_gb = actual_size / (1024**3)
                    self.db.commit()

                    # 保存下载元数据
                    self._save_download_metadata(storage_path, task)

                    # 通知所有 Worker
                    await self._notify_workers_model_ready(model.id)

                else:
                    stderr = await process.stderr.read()
                    log.write(f"[{datetime.now()}] Download failed: {stderr.decode()}\n")

                    task.status = "failed"
                    task.error_message = stderr.decode()
                    self.db.commit()

        except Exception as e:
            if log_file:
                with open(log_file, "a") as log:
                    log.write(f"[{datetime.now()}] Error: {str(e)}\n")

            task.status = "failed"
            task.error_message = str(e)
            self.db.commit()

    async def _monitor_download_progress(
        self,
        task: ModelDownloadTask,
        process: asyncio.subprocess.Process,
        log_file
    ):
        """监控下载进度（解析 ModelScope 输出）"""
        import re

        # ModelScope 输出模式
        progress_pattern = re.compile(r'Downloading:\s+(\d+)%')
        file_pattern = re.compile(r'Downloading\s+(.+)')

        while True:
            line = await process.stdout.readline()
            if not line:
                break

            line_str = line.decode().strip()

            # 写入日志
            if log_file:
                log_file.write(f"{line_str}\n")
                log_file.flush()

            # 解析进度
            progress_match = progress_pattern.search(line_str)
            if progress_match:
                task.progress = int(progress_match.group(1))
                self.db.commit()

            # 解析当前文件
            file_match = file_pattern.search(line_str)
            if file_match:
                task.current_file = file_match.group(1)
                self.db.commit()

            # TODO: 通过 WebSocket 推送进度到前端
            # await websocket_manager.broadcast(...)

    def _calculate_model_size(self, path: str) -> int:
        """计算模型大小（字节）"""
        total_size = 0
        for dirpath, dirnames, filenames in os.walk(path):
            # 排除隐藏文件和缓存
            dirnames[:] = [d for d in dirnames if not d.startswith(".")]

            for filename in filenames:
                if not filename.startswith("."):
                    filepath = os.path.join(dirpath, filename)
                    if os.path.exists(filepath) and os.path.isfile(filepath):
                        total_size += os.path.getsize(filepath)

        return total_size

    def _save_download_metadata(self, storage_path: str, task: ModelDownloadTask):
        """保存下载元数据"""
        metadata = {
            "modelscope_repo_id": task.modelscope_repo_id,
            "revision": task.modelscope_revision,
            "downloaded_at": datetime.now().isoformat(),
            "task_id": task.id,
            "total_bytes": task.total_bytes,
            "total_files": task.total_files
        }

        metadata_file = f"{storage_path}/.download_metadata.json"
        with open(metadata_file, "w") as f:
            json.dump(metadata, f, indent=2)

    async def _notify_workers_model_ready(self, model_id: int):
        """通知所有 Worker 模型已就绪"""
        from api.deps import redis_client

        # 通过 Redis pub/sub 广播
        message = json.dumps({
            "type": "model_ready",
            "model_id": model_id,
            "timestamp": datetime.now().isoformat()
        })

        await redis_client.publish("model:events", message)

    async def get_download_status(self, model_id: int) -> dict:
        """获取下载状态"""
        model = self.db.query(Model).filter(Model.id == model_id).first()

        if not model or not model.download_task_id:
            raise ValueError("Download task not found")

        task = self.db.query(ModelDownloadTask).filter(
            ModelDownloadTask.id == model.download_task_id
        ).first()

        if not task:
            raise ValueError("Task not found")

        return {
            "task_id": task.id,
            "model_id": model_id,
            "status": task.status,
            "progress": task.progress,
            "current_file": task.current_file,
            "downloaded_files": task.downloaded_files,
            "total_files": task.total_files,
            "downloaded_bytes": task.downloaded_bytes,
            "total_bytes": task.total_bytes,
            "error_message": task.error_message,
            "created_at": task.created_at.isoformat() if task.created_at else None,
            "started_at": task.started_at.isoformat() if task.started_at else None,
            "completed_at": task.completed_at.isoformat() if task.completed_at else None
        }
```

---

## 6. API 接口

### 6.1 下载模型

```http
POST /api/v1/admin/models/{model_id}/download
Authorization: Bearer {admin_token}
Content-Type: application/json

{
  "repo_id": "Qwen/qwen-72b-chat",
  "revision": "master"
}

Response 200:
{
  "task_id": 123,
  "model_id": 1,
  "status": "pending",
  "storage_path": "/var/lib/tokenmachine/models/Qwen--qwen-72b-chat"
}

Response 400:
{
  "error": "model_already_downloaded",
  "message": "Model is already downloaded and ready"
}
```

### 6.2 查询下载状态

```http
GET /api/v1/admin/models/{model_id}/download/status
Authorization: Bearer {admin_token}

Response 200:
{
  "task_id": 123,
  "model_id": 1,
  "status": "downloading",
  "progress": 45,
  "current_file": "model-00002-of-00008.safetensors",
  "downloaded_files": 7,
  "total_files": 15,
  "downloaded_bytes": 7470295040,
  "total_bytes": 16609069056,
  "error_message": null,
  "created_at": "2025-01-21T10:00:00Z",
  "started_at": "2025-01-21T10:00:05Z",
  "completed_at": null
}
```

### 6.3 列出所有下载任务

```http
GET /api/v1/admin/download/tasks?status=downloading
Authorization: Bearer {admin_token}

Response 200:
{
  "tasks": [
    {
      "task_id": 123,
      "model_id": 1,
      "model_name": "qwen-72b-chat",
      "status": "downloading",
      "progress": 45,
      "created_at": "2025-01-21T10:00:00Z"
    }
  ],
  "total": 1
}
```

### 6.4 获取模型下载日志

```http
GET /api/v1/admin/models/{model_id}/download/logs
Authorization: Bearer {admin_token}
Query: ?tail=100

Response 200:
{
  "log_file": "/var/lib/tokenmachine/logs/downloads/qwen-72b-chat_20250121.log",
  "lines": [
    "[2025-01-21 10:00:00] Starting download: Qwen/qwen-72b-chat",
    "[2025-01-21 10:00:01] Downloading: model-00001-of-00008.safetensors",
    "[2025-01-21 10:00:30] Downloading: 25%",
    "..."
  ]
}
```

---

## 7. Worker 模型加载

### 7.1 WorkerModelLoader

```python
# backend/worker/model_loader.py
from typing import Optional
from backend.models.database import Model, Worker, WorkerModelCache
from core.config import settings
import os
from datetime import datetime

class WorkerModelLoader:
    """Worker 模型加载器"""

    def __init__(self, worker_id: int, db: Session):
        self.worker_id = worker_id
        self.db = db
        self.nfs_mount_point = settings.NFS_MOUNT_POINT

    def get_model_path(self, model_id: int) -> Optional[str]:
        """
        获取模型加载路径

        流程：
        1. 查询数据库获取模型 storage_path
        2. 映射到 NFS 挂载点
        3. 验证文件存在
        4. 更新缓存记录
        """
        # 1. 查询模型
        model = self.db.query(Model).filter(Model.id == model_id).first()
        if not model:
            return None

        # 2. 检查模型状态
        if model.status != "ready":
            return None

        # 3. 获取存储路径
        storage_path = model.storage_path
        if not storage_path:
            return None

        # 4. 映射到 NFS 挂载点
        nfs_path = storage_path.replace(
            "/var/lib/tokenmachine/models",
            self.nfs_mount_point
        )

        # 5. 验证路径存在
        if not os.path.exists(nfs_path):
            return None

        # 6. 验证必要文件存在
        required_files = ["config.json"]
        if not all(
            os.path.exists(os.path.join(nfs_path, f))
            for f in required_files
        ):
            return None

        # 7. 更新缓存记录
        self._update_cache(model_id, nfs_path)

        return nfs_path

    def _update_cache(self, model_id: int, cache_path: str):
        """更新 Worker 缓存记录"""
        cache = self.db.query(WorkerModelCache).filter(
            WorkerModelCache.worker_id == self.worker_id,
            WorkerModelCache.model_id == model_id
        ).first()

        if not cache:
            cache = WorkerModelCache(
                worker_id=self.worker_id,
                model_id=model_id,
                is_cached=True,
                cache_path=cache_path,
                sync_status="synced"
            )
            self.db.add(cache)
        else:
            cache.is_cached = True
            cache.cache_path = cache_path
            cache.sync_status = "synced"

        cache.last_loaded_at = datetime.now()
        cache.load_count += 1
        cache.last_synced_at = datetime.now()
        self.db.commit()

    def sync_model_cache(self):
        """同步模型缓存（检查哪些模型可用）"""
        # 获取所有就绪的模型
        ready_models = self.db.query(Model).filter(
            Model.status == "ready"
        ).all()

        for model in ready_models:
            nfs_path = model.storage_path.replace(
                "/var/lib/tokenmachine/models",
                self.nfs_mount_point
            )

            is_available = os.path.exists(nfs_path)

            # 更新或创建缓存记录
            cache = self.db.query(WorkerModelCache).filter(
                WorkerModelCache.worker_id == self.worker_id,
                WorkerModelCache.model_id == model.id
            ).first()

            if not cache:
                cache = WorkerModelCache(
                    worker_id=self.worker_id,
                    model_id=model.id,
                    is_cached=is_available,
                    cache_path=nfs_path if is_available else None,
                    sync_status="synced" if is_available else "outdated"
                )
                self.db.add(cache)
            else:
                cache.is_cached = is_available
                cache.sync_status = "synced" if is_available else "outdated"

        self.db.commit()

    def list_cached_models(self) -> list[dict]:
        """列出所有已缓存的模型"""
        caches = self.db.query(WorkerModelCache).filter(
            WorkerModelCache.worker_id == self.worker_id,
            WorkerModelCache.is_cached == True
        ).all()

        return [
            {
                "model_id": c.model_id,
                "cache_path": c.cache_path,
                "last_loaded_at": c.last_loaded_at.isoformat() if c.last_loaded_at else None,
                "load_count": c.load_count
            }
            for c in caches
        ]
```

### 7.2 模型加载流程

```
1. Server 向 Worker 发送部署请求
   {
     "model_id": 1,
     "backend": "vllm",
     "config": {...}
   }
   ↓
2. Worker 调用 WorkerModelLoader.get_model_path(1)
   ↓
3. 查询数据库:
   SELECT storage_path FROM models WHERE id=1
   → "/var/lib/tokenmachine/models/Qwen--qwen-72b-chat"
   ↓
4. 映射到 NFS:
   "/mnt/models/Qwen--qwen-72b-chat"
   ↓
5. 验证文件存在:
   os.path.exists("/mnt/models/Qwen--qwen-72b-chat/config.json") → True
   ↓
6. 启动 vLLM:
   vllm serve /mnt/models/Qwen--qwen-72b-chat
   ↓
7. 更新 worker_model_cache 表
```

---

## 8. 部署配置

### 8.1 环境变量

```bash
# .env
# ModelScope 配置
MODELSCOPE_CACHE_DIR=/var/lib/tokenmachine/cache/modelscope
MODELSCOPE_SDK_DEBUG=false

# 存储配置
MODEL_STORAGE_PATH=/var/lib/tokenmachine/models
NFS_MOUNT_POINT=/mnt/models

# 下载配置
DOWNLOAD_MAX_CONCURRENT=3
DOWNLOAD_TIMEOUT_SECONDS=7200

# 日志配置
LOG_PATH=/var/lib/tokenmachine/logs
```

### 8.2 Server 初始化

```bash
#!/bin/bash
# scripts/init_model_storage.sh

set -e

echo "Initializing model storage..."

# 1. 创建目录
echo "Creating directories..."
mkdir -p /var/lib/tokenmachine/models
mkdir -p /var/lib/tokenmachine/cache/modelscope
mkdir -p /var/lib/tokenmachine/logs/downloads

# 2. 设置权限
echo "Setting permissions..."
chmod 755 /var/lib/tokenmachine/models
chmod 755 /var/lib/tokenmachine/cache
chmod 755 /var/lib/tokenmachine/logs

chown -R tokenmachine:tokenmachine /var/lib/tokenmachine

# 3. 安装 ModelScope
echo "Installing ModelScope SDK..."
pip install modelscope

# 4. 配置 NFS Server (如果需要)
if [ "$ENABLE_NFS_SERVER" = "true" ]; then
    echo "Configuring NFS server..."
    apt-get install -y nfs-kernel-server

    # 配置导出
    echo "/var/lib/tokenmachine/models *(rw,sync,no_subtree_check,no_root_squash)" >> /etc/exports

    # 启动服务
    systemctl enable nfs-server
    systemctl restart nfs-server

    echo "NFS server configured"
fi

echo "Model storage initialized successfully!"
```

### 8.3 Worker 初始化

```bash
#!/bin/bash
# scripts/init_worker_storage.sh

set -e

NFS_SERVER=${NFS_SERVER:-"nfsserver"}
NFS_MOUNT_POINT=${NFS_MOUNT_POINT:-"/mnt/models"}

echo "Initializing worker storage..."

# 1. 创建挂载点
echo "Creating mount point..."
mkdir -p $NFS_MOUNT_POINT

# 2. 安装 NFS 客户端
echo "Installing NFS client..."
apt-get install -y nfs-common

# 3. 挂载 NFS
echo "Mounting NFS share..."
mount -t nfs $NFS_SERVER:/var/lib/tokenmachine/models $NFS_MOUNT_POINT

# 4. 验证挂载
echo "Verifying mount..."
ls -lh $NFS_MOUNT_POINT

# 5. 添加到 /etc/fstab
if ! grep -q "$NFS_MOUNT_POINT" /etc/fstab; then
    echo "$NFS_SERVER:/var/lib/tokenmachine/models $NFS_MOUNT_POINT nfs defaults,_netdev 0 0" >> /etc/fstab
    echo "Added to /etc/fstab for auto-mount on boot"
fi

echo "Worker storage initialized successfully!"
```

### 8.4 Docker Compose 配置

```yaml
# docker-compose.yml
version: '3.8'

services:
  api:
    build: .
    volumes:
      - model-data:/var/lib/tokenmachine/models
      - cache-data:/var/lib/tokenmachine/cache
      - log-data:/var/lib/tokenmachine/logs
    environment:
      - MODEL_STORAGE_PATH=/var/lib/tokenmachine/models
      - MODELSCOPE_CACHE_DIR=/var/lib/tokenmachine/cache/modelscope
    ports:
      - "8000:8000"

volumes:
  model-data:
    driver: local
    driver_opts:
      type: nfs
      o: addr=nfsserver,rw
      device: ":/var/lib/tokenmachine/models"

  cache-data:
  log-data:
```

---

## 9. 工作流程

### 9.1 模型下载流程

```
┌─────────┐
│ 前端用户 │
└────┬────┘
     │ 1. 点击"下载模型"
     ▼
┌─────────────────────────────────┐
│  POST /api/v1/admin/models/     │
│       {id}/download             │
│  {                              │
│    "repo_id": "Qwen/...",       │
│    "revision": "master"         │
│  }                              │
└────────────┬────────────────────┘
             │
             ▼
┌─────────────────────────────────────┐
│  ModelDownloadService               │
│  - 验证模型                         │
│  - 检查重复任务                     │
│  - 获取 ModelScope 信息             │
│  - 创建下载任务                     │
│  - 更新数据库                       │
└────────────┬────────────────────────┘
             │
             ▼
┌─────────────────────────────────────┐
│  异步执行下载                        │
│  - 调用 ModelScope CLI              │
│  - 监控进度                         │
│  - 更新数据库                       │
│  - 写入日志                         │
└────────────┬────────────────────────┘
             │
             ▼
┌─────────────────────────────────────┐
│  下载完成                            │
│  - 更新模型状态 = ready              │
│  - 计算模型大小                      │
│  - 保存元数据                        │
│  - 通知 Workers                     │
└────────────┬────────────────────────┘
             │
             ▼
┌─────────────────────────────────────┐
│  Redis Pub/Sub                       │
│  channel: "model:events"             │
│  message: {"type": "model_ready"}    │
└─────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────┐
│  Workers 收到通知                    │
│  - 更新本地缓存表                    │
│  - 模型可用                          │
└─────────────────────────────────────┘
```

### 9.2 Worker 加载模型流程

```
┌─────────────────────────────────┐
│  Server 调度器                   │
│  - 选择 Worker                   │
│  - 发送部署请求                  │
└────────────┬────────────────────┘
             │
             ▼
┌─────────────────────────────────────┐
│  Worker 收到部署请求                  │
│  {                                  │
│    "model_id": 1,                   │
│    "backend": "vllm",               │
│    "config": {...}                  │
│  }                                  │
└────────────┬────────────────────────┘
             │
             ▼
┌─────────────────────────────────────┐
│  WorkerModelLoader                   │
│  get_model_path(model_id=1)         │
└────────────┬────────────────────────┘
             │
             ▼
┌─────────────────────────────────────┐
│  查询数据库                          │
│  SELECT * FROM models WHERE id=1    │
│  → storage_path = "/var/lib/..."    │
└────────────┬────────────────────────┘
             │
             ▼
┌─────────────────────────────────────┐
│  映射到 NFS 挂载点                   │
│  /mnt/models/Qwen--qwen-72b-chat    │
└────────────┬────────────────────────┘
             │
             ▼
┌─────────────────────────────────────┐
│  验证文件存在                        │
│  os.path.exists(nfs_path)           │
│  检查 config.json 等                │
└────────────┬────────────────────────┘
             │
             ▼
┌─────────────────────────────────────┐
│  启动 vLLM                           │
│  vllm serve /mnt/models/...          │
└────────────┬────────────────────────┘
             │
             ▼
┌─────────────────────────────────────┐
│  更新缓存表                          │
│  worker_model_cache.last_loaded_at  │
│  load_count += 1                     │
└─────────────────────────────────────┘
```

---

## 10. 监控与日志

### 10.1 Prometheus 指标

```python
# backend/monitoring/metrics.py
from prometheus_client import Counter, Gauge, Histogram

# 下载任务指标
model_download_total = Counter(
    'model_download_total',
    'Total model download tasks',
    ['status']  # success, failed
)

model_download_duration_seconds = Histogram(
    'model_download_duration_seconds',
    'Model download duration',
    buckets=[60, 300, 900, 1800, 3600, 7200]
)

model_download_size_bytes = Gauge(
    'model_download_size_bytes',
    'Model size in bytes',
    ['model_id', 'model_name']
)

# 当前下载数
model_downloading_active = Gauge(
    'model_downloading_active',
    'Number of active download tasks'
)

# 下载进度
model_download_progress = Gauge(
    'model_download_progress',
    'Model download progress percentage',
    ['model_id', 'task_id']
)
```

### 10.2 日志格式

```python
# 使用结构化日志
{
  "timestamp": "2025-01-21T10:00:00Z",
  "level": "INFO",
  "service": "model_download",
  "event": "download_started",
  "model_id": 1,
  "repo_id": "Qwen/qwen-72b-chat",
  "revision": "master",
  "task_id": 123
}

{
  "timestamp": "2025-01-21T10:30:00Z",
  "level": "INFO",
  "service": "model_download",
  "event": "download_completed",
  "model_id": 1,
  "task_id": 123,
  "duration_seconds": 1800,
  "size_bytes": 16609069056
}
```

---

## 11. 故障处理

### 11.1 常见错误处理

| 错误场景 | 处理策略 |
|---------|---------|
| **NFS 挂载失败** | Worker 报错，重试 3 次，仍失败则标记为不可用 |
| **ModelScope API 失败** | 使用默认值继续，不影响下载 |
| **下载超时** | 取消任务，记录日志，允许用户重试 |
| **磁盘空间不足** | 预检查空间，不足则拒绝下载 |
| **网络中断** | ModelScope SDK 自动断点续传 |
| **权限问题** | 检查目录权限，自动修复 |

### 11.2 重试机制

```python
# 自动重试策略
RETRY_POLICY = {
    "network_errors": {
        "max_retries": 3,
        "backoff": "exponential",
        "initial_delay": 60  # seconds
    },
    "api_errors": {
        "max_retries": 2,
        "backoff": "fixed",
        "delay": 30
    }
}
```

---

## 12. 实施计划

### Phase 1: 基础设施（1 周）

- [ ] NFS 服务器配置
- [ ] 目录结构创建
- [ ] 权限设置
- [ ] Worker 挂载测试

### Phase 2: 数据库（1 周）

- [ ] 创建 model_download_tasks 表
- [ ] 创建 worker_model_cache 表
- [ ] 扩展 models 表
- [ ] 数据库迁移脚本

### Phase 3: 服务层（2 周）

- [ ] 实现 ModelDownloadService
- [ ] 实现 WorkerModelLoader
- [ ] 集成 ModelScope SDK
- [ ] 进度监控逻辑

### Phase 4: API 接口（1 周）

- [ ] 下载 API
- [ ] 状态查询 API
- [ ] 日志 API
- [ ] API 测试

### Phase 5: Worker 集成（1 周）

- [ ] Worker 模型加载逻辑
- [ ] 缓存同步
- [ ] 错误处理
- [ ] 集成测试

### Phase 6: 监控与日志（1 周）

- [ ] Prometheus 指标
- [ ] 日志格式化
- [ ] 告警规则
- [ ] Grafana 面板

---

## 附录

### A. 配置文件示例

```python
# core/config.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # ModelScope
    MODELSCOPE_CACHE_DIR: str = "/var/lib/tokenmachine/cache/modelscope"
    MODELSCOPE_SDK_DEBUG: bool = False

    # Storage
    MODEL_STORAGE_PATH: str = "/var/lib/tokenmachine/models"
    NFS_MOUNT_POINT: str = "/mnt/models"

    # Download
    DOWNLOAD_MAX_CONCURRENT: int = 3
    DOWNLOAD_TIMEOUT_SECONDS: int = 7200

    # Logs
    LOG_PATH: str = "/var/lib/tokenmachine/logs"

    class Config:
        env_file = ".env"

settings = Settings()
```

### B. 依赖包

```txt
# requirements.txt
modelscope>=1.0.0
fastapi>=0.109.0
sqlalchemy>=2.0.25
psycopg2-binary>=2.9.9
redis>=5.0.1
prometheus-client>=0.19.0
loguru>=0.7.2
```

---

**文档版本**: v1.0
**最后更新**: 2025-01-21
**维护者**: TokenMachine Team
