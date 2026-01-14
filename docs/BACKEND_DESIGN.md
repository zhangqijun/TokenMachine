# Backend Design - 详细设计方案

## 目录
- [1. 核心功能范围](#1-核心功能范围)
- [2. 系统架构设计](#2-系统架构设计)
- [3. 数据库设计](#3-数据库设计)
- [4. API 设计](#4-api-设计)
- [5. 核心功能模块](#5-核心功能模块)
- [6. 部署架构](#6-部署架构)
- [7. 技术选型](#7-技术选型)
- [8. 开发计划](#8-开发计划)

---

## 1. 核心功能范围

### 1.1 核心功能清单

| 模块 | 功能 | 优先级 | 说明 |
|------|------|--------|------|
| **GPU管理** | GPU 资源发现 | P0 | 自动检测可用 GPU |
| | GPU 状态监控 | P0 | 利用率、温度、显存 |
| | GPU 资源分配 | P0 | 模型部署时自动分配 |
| **模型部署** | 模型仓库集成 | P0 | HuggingFace/ModelScope |
| | 模型下载 | P0 | 支持断点续传 |
| | 模型版本管理 | P1 | 基础版本记录 |
| | vLLM 后端集成 | P0 | 默认推理引擎 |
| | 部署状态管理 | P0 | starting/running/stopped/error |
| | 副本管理 | P1 | 单机多副本 |
| **API 网关** | OpenAI Chat API | P0 | /v1/chat/completions |
| | OpenAI Models API | P0 | /v1/models |
| | OpenAI Embeddings API | P1 | /v1/embeddings |
| | 流式输出 | P0 | SSE 支持 |
| | API Key 认证 | P0 | Bearer Token |
| **监控** | Prometheus 指标 | P0 | GPU/模型/API 指标 |
| | Grafana 面板 | P1 | 基础可视化 |
| | 日志记录 | P0 | 结构化日志 |
| **Web UI** | 仪表盘 | P1 | 基础概览 |
| | 模型管理界面 | P0 | 部署/停止模型 |
| | 监控面板 | P1 | 实时指标 |
| | API Key 管理 | P0 | 创建/撤销 API Key |

### 1.2 功能边界（不包含）

- ❌ 计费系统 (P2)
- ❌ 多租户 (P2)
- ❌ SGLang 后端 (P2)
- ❌ 国产芯片支持 (P2)
- ❌ 模型微调 (P2)
- ❌ 智能路由 (P2)
- ❌ 格式转换 (P2)
- ❌ SSO 登录 (P2)

### 1.3 未来增强功能 (P2)

- ➕ 计费系统（Token 计费）
- ➕ 多租户支持
- ➕ SGLang 后端
- ➕ 模型版本管理增强
- ➕ 灰度发布
- ➕ SSO 登录（OIDC / SAML）

---

## 2. 系统架构设计

### 2.1 整体架构

```
┌─────────────────────────────────────────────────────────────┐
│                        客户端层                              │
│  Web UI (React) │ CLI │ SDK │ cURL / Postman               │
└────────────────────────────┬────────────────────────────────┘
                             │
                             │ HTTPS
                             │
┌────────────────────────────▼────────────────────────────────┐
│                     Nginx / Caddy                            │
│                    (反向代理 + TLS)                         │
└────────────────────────────┬────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────┐
│                   FastAPI 应用层                            │
├─────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       │
│  │  API 网关    │  │  资源管理    │  │  监控服务    │       │
│  │  Router      │  │  Manager     │  │  Metrics     │       │
│  │  • 认证      │  │  • GPU 调度  │  │  • Exporter  │       │
│  │  • 路由      │  │  • 模型管理  │  │              │       │
│  └──────────────┘  └──────────────┘  └──────────────┘       │
└────────────────────────────┬────────────────────────────────┘
                             │
         ┌───────────────────┼───────────────────┐
         │                   │                   │
┌────────▼────────┐  ┌──────▼──────┐  ┌────────▼────────┐
│   PostgreSQL     │  │    Redis    │  │  vLLM Workers   │
│   (数据存储)     │  │   (缓存)    │  │  (推理引擎)     │
│                  │  │             │  │                 │
│  • users        │  │  • 模型元   │  │  Worker 1       │
│  • models       │  │  • API Key  │  │  Worker 2       │
│  • deployments  │  │  • 配额     │  │  Worker N       │
│  • api_keys     │  │  • 队列     │  │                 │
│                  │  │             │  │  GPU 0, 1...   │
└──────────────────┘  └─────────────┘  └─────────────────┘
```

### 2.2 核心组件说明

#### 2.2.1 FastAPI 应用层

**目录结构**:
```
backend/
├── api/
│   ├── v1/
│   │   ├── chat.py          # OpenAI Chat API
│   │   ├── models.py        # OpenAI Models API
│   │   ├── embeddings.py    # Embeddings API (可选)
│   │   └── admin.py         # 管理接口
│   ├── deps.py              # 依赖注入
│   └── middleware.py        # 中间件（认证、限流）
├── core/
│   ├── config.py            # 配置管理
│   ├── security.py          # 安全相关
│   └── gpu.py               # GPU 管理核心
├── models/
│   ├── database.py          # SQLAlchemy 模型
│   └── schemas.py           # Pydantic 模式
├── services/
│   ├── model_service.py     # 模型服务
│   ├── deployment_service.py # 部署服务
│   └── gpu_service.py       # GPU 服务
├── workers/
│   ├── vllm_worker.py       # vLLM 工作进程管理
│   └── worker_pool.py       # 工作进程池
├── monitoring/
│   ├── metrics.py           # Prometheus 指标
│   └── exporter.py          # 指标导出器
├── utils/
│   ├── logger.py            # 日志工具
│   └── validators.py        # 验证工具
└── main.py                  # 应用入口
```

#### 2.2.2 vLLM Workers

**设计要点**:
- 每个 Worker 独立进程
- 使用 `subprocess.Popen` 管理
- 通过 HTTP/gRPC 通信
- 自动重启机制
- 健康检查

---

## 3. 数据库设计

### 3.1 ER 图

```
┌─────────────┐       ┌─────────────┐       ┌─────────────┐
│   Users     │───────│  ApiKeys    │───────│  UsageLogs  │
├─────────────┤ 1   N ├─────────────┤ 1   N ├─────────────┤
│ id (PK)     │       │ id (PK)     │       │ id (PK)     │
│ username    │       │ key_hash    │       │ api_key_id  │
│ email       │       │ user_id (FK)│       │ model_id    │
│ password    │       │ name        │       │ tokens_used │
│ is_admin    │       │ quota_tokens│       │ latency_ms  │
│ created_at  │       │ created_at  │       │ status      │
└─────────────┘       └─────────────┘       │ created_at  │
                                             └─────────────┘
                                             
┌─────────────┐       ┌─────────────┐       ┌─────────────┐
│   Models    │───────│ Deployments │───────│  GPUs       │
├─────────────┤ 1   N ├─────────────┤ N   1 ├─────────────┤
│ id (PK)     │       │ id (PK)     │       │ id (PK)     │
│ name        │       │ model_id(FK)│       │ gpu_id      │
│ version     │       │ name        │       │ name        │
│ source      │       │ status      │       │ memory_total│
│ path        │       │ replicas    │       │ memory_free │
│ size_gb     │       │ gpu_ids(JSON)│       │ utilization│
│ status      │       │ backend     │       │ temperature │
│ created_at  │       │ config(JSON)│       │ updated_at  │
└─────────────┘       │ created_at  │       └─────────────┘
                      │ updated_at  │
                      └─────────────┘
```

### 3.2 表结构定义

```sql
-- 用户表
CREATE TABLE users (
    id BIGSERIAL PRIMARY KEY,
    username VARCHAR(255) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    is_admin BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 模型表
CREATE TABLE models (
    id BIGSERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    version VARCHAR(50) NOT NULL,
    source VARCHAR(50) NOT NULL,  -- huggingface, modelscope, local
    category VARCHAR(50) NOT NULL, -- llm, embedding, reranker
    path VARCHAR(1024) NOT NULL,
    size_gb DECIMAL(10, 2),
    status VARCHAR(50) DEFAULT 'downloading', -- downloading, ready, error
    download_progress INT DEFAULT 0,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (name, version)
);

-- 部署表
CREATE TABLE deployments (
    id BIGSERIAL PRIMARY KEY,
    model_id BIGINT NOT NULL REFERENCES models(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    status VARCHAR(50) DEFAULT 'starting', -- starting, running, stopped, error
    replicas INT DEFAULT 1,
    gpu_ids JSONB,  -- ["gpu:0", "gpu:1"]
    backend VARCHAR(50) DEFAULT 'vllm',
    config JSONB,   -- 后端配置参数
    health_status JSONB,  -- 每个副本的健康状态
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- GPU 表
CREATE TABLE gpus (
    id SERIAL PRIMARY KEY,
    gpu_id VARCHAR(50) UNIQUE NOT NULL,  -- gpu:0, gpu:1
    name VARCHAR(255) NOT NULL,
    memory_total_mb BIGINT,
    memory_free_mb BIGINT,
    utilization_percent DECIMAL(5, 2),
    temperature_celsius DECIMAL(5, 2),
    status VARCHAR(50) DEFAULT 'available', -- available, in_use, error
    deployment_id BIGINT REFERENCES deployments(id),
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- API Key 表
CREATE TABLE api_keys (
    id BIGSERIAL PRIMARY KEY,
    key_hash VARCHAR(255) UNIQUE NOT NULL,
    key_prefix VARCHAR(10) NOT NULL,  -- 用于显示
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    quota_tokens BIGINT DEFAULT 10000000,  -- 10M tokens
    tokens_used BIGINT DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    expires_at TIMESTAMP,
    last_used_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 使用日志表
CREATE TABLE usage_logs (
    id BIGSERIAL PRIMARY KEY,
    api_key_id BIGINT NOT NULL REFERENCES api_keys(id),
    deployment_id BIGINT NOT NULL REFERENCES deployments(id),
    model_id BIGINT NOT NULL REFERENCES models(id),
    input_tokens INT DEFAULT 0,
    output_tokens INT DEFAULT 0,
    total_tokens INT GENERATED ALWAYS AS (input_tokens + output_tokens) STORED,
    latency_ms INT,
    status VARCHAR(50) DEFAULT 'success', -- success, error
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 索引
CREATE INDEX idx_deployments_status ON deployments(status);
CREATE INDEX idx_deployments_model ON deployments(model_id);
CREATE INDEX idx_api_keys_user ON api_keys(user_id);
CREATE INDEX idx_api_keys_active ON api_keys(is_active);
CREATE INDEX idx_usage_logs_api_key ON usage_logs(api_key_id);
CREATE INDEX idx_usage_logs_created ON usage_logs(created_at);
CREATE INDEX idx_usage_logs_deployment ON usage_logs(deployment_id);
```

---

## 4. API 设计

### 4.1 OpenAI 兼容 API

#### 4.1.1 Chat Completions

```http
POST /v1/chat/completions
Authorization: Bearer {api_key}
Content-Type: application/json

{
  "model": "llama-3-8b-instruct",
  "messages": [
    {"role": "user", "content": "Hello!"}
  ],
  "temperature": 0.7,
  "max_tokens": 2048,
  "stream": true
}

Response (non-stream):
{
  "id": "chatcmpl-123",
  "object": "chat.completion",
  "created": 1699012345,
  "model": "llama-3-8b-instruct",
  "choices": [{
    "index": 0,
    "message": {
      "role": "assistant",
      "content": "Hello! How can I help you?"
    },
    "finish_reason": "stop"
  }],
  "usage": {
    "prompt_tokens": 10,
    "completion_tokens": 20,
    "total_tokens": 30
  }
}

Response (stream):
data: {"id":"chatcmpl-123","choices":[{"delta":{"content":"Hello"}}],"finish_reason":null}
data: {"id":"chatcmpl-123","choices":[{"delta":{"content":"!"}}],"finish_reason":null}
data: [DONE]
```

#### 4.1.2 Models

```http
GET /v1/models
Authorization: Bearer {api_key}

Response:
{
  "object": "list",
  "data": [
    {
      "id": "llama-3-8b-instruct",
      "object": "model",
      "created": 1699012345,
      "owned_by": "tokenmachine"
    }
  ]
}
```

#### 4.1.3 Embeddings (可选)

```http
POST /v1/embeddings
Authorization: Bearer {api_key}
Content-Type: application/json

{
  "model": "bge-large-en-v1.5",
  "input": "Hello, world!",
  "encoding_format": "float"
}

Response:
{
  "object": "list",
  "data": [{
    "embedding": [0.1, 0.2, ...],
    "index": 0,
    "object": "embedding"
  }],
  "model": "bge-large-en-v1.5",
  "usage": {
    "prompt_tokens": 4,
    "total_tokens": 4
  }
}
```

### 4.2 管理 API

#### 4.2.1 模型管理

```http
# 下载模型
POST /api/v1/admin/models
Authorization: Bearer {admin_token}
Content-Type: application/json

{
  "name": "meta-llama/Llama-3-8B-Instruct",
  "source": "huggingface",
  "version": "v1.0"
}

# 列出模型
GET /api/v1/admin/models
Authorization: Bearer {admin_token}

Response:
{
  "models": [
    {
      "id": 1,
      "name": "meta-llama/Llama-3-8B-Instruct",
      "version": "v1.0",
      "source": "huggingface",
      "status": "ready",
      "size_gb": 16.5
    }
  ]
}
```

#### 4.2.2 部署管理

```http
# 创建部署
POST /api/v1/admin/deployments
Authorization: Bearer {admin_token}
Content-Type: application/json

{
  "model_id": 1,
  "name": "llama-3-8b-prod",
  "replicas": 2,
  "gpu_ids": ["gpu:0", "gpu:1"],
  "backend": "vllm",
  "config": {
    "tensor_parallel_size": 1,
    "max_model_len": 4096,
    "gpu_memory_utilization": 0.9
  }
}

Response:
{
  "id": 1,
  "model_id": 1,
  "name": "llama-3-8b-prod",
  "status": "starting",
  "endpoints": [
    "http://localhost:8001",
    "http://localhost:8002"
  ]
}

# 列出部署
GET /api/v1/admin/deployments
Authorization: Bearer {admin_token}

# 停止部署
DELETE /api/v1/admin/deployments/{deployment_id}
Authorization: Bearer {admin_token}

# 获取部署详情
GET /api/v1/admin/deployments/{deployment_id}
Authorization: Bearer {admin_token}
```

#### 4.2.3 GPU 管理

```http
# 获取 GPU 状态
GET /api/v1/admin/gpus
Authorization: Bearer {admin_token}

Response:
{
  "gpus": [
    {
      "id": "gpu:0",
      "name": "NVIDIA RTX 3090",
      "memory_total_mb": 24576,
      "memory_free_mb": 20480,
      "utilization_percent": 15.5,
      "temperature_celsius": 45.0,
      "status": "available",
      "deployment_id": null
    },
    {
      "id": "gpu:1",
      "name": "NVIDIA RTX 3090",
      "memory_total_mb": 24576,
      "memory_free_mb": 4096,
      "utilization_percent": 83.2,
      "temperature_celsius": 78.0,
      "status": "in_use",
      "deployment_id": 1
    }
  ]
}
```

#### 4.2.4 API Key 管理

```http
# 创建 API Key
POST /api/v1/admin/api-keys
Authorization: Bearer {admin_token}
Content-Type: application/json

{
  "name": "Production API Key",
  "user_id": 1,
  "quota_tokens": 100000000
}

Response:
{
  "id": 1,
  "key": "tm_sk_abc123...",  # 仅返回一次
  "key_prefix": "tm_sk_abc1",
  "name": "Production API Key",
  "quota_tokens": 100000000,
  "tokens_used": 0
}

# 列出 API Keys
GET /api/v1/admin/api-keys
Authorization: Bearer {admin_token}

# 撤销 API Key
DELETE /api/v1/admin/api-keys/{key_id}
Authorization: Bearer {admin_token}
```

---

## 5. 核心功能模块

### 5.1 GPU 管理模块

```python
# core/gpu.py
import pynvml
from typing import List, Dict
import psutil

class GPUManager:
    """GPU 资源管理器"""
    
    def __init__(self):
        pynvml.nvmlInit()
        self.num_gpus = pynvml.nvmlDeviceGetCount()
    
    def get_gpu_info(self, gpu_id: int) -> Dict:
        """获取单个 GPU 信息"""
        handle = pynvml.nvmlDeviceGetHandleByIndex(gpu_id)
        
        # 基本信息
        name = pynvml.nvmlDeviceGetName(handle)
        
        # 显存信息
        mem_info = pynvml.nvmlDeviceGetMemoryInfo(handle)
        
        # 利用率
        utilization = pynvml.nvmlDeviceGetUtilizationRates(handle)
        
        # 温度
        temperature = pynvml.nvmlDeviceGetTemperature(
            handle, pynvml.NVML_TEMPERATURE_GPU
        )
        
        return {
            "id": f"gpu:{gpu_id}",
            "name": name.decode('utf-8'),
            "memory_total_mb": mem_info.total // (1024 * 1024),
            "memory_free_mb": mem_info.free // (1024 * 1024),
            "memory_used_mb": mem_info.used // (1024 * 1024),
            "utilization_percent": utilization.gpu,
            "temperature_celsius": temperature
        }
    
    def get_all_gpus(self) -> List[Dict]:
        """获取所有 GPU 信息"""
        return [self.get_gpu_info(i) for i in range(self.num_gpus)]
    
    def find_available_gpus(self, required_mb: int, count: int = 1) -> List[str]:
        """查找可用 GPU"""
        available = []
        gpu_infos = self.get_all_gpus()
        
        for gpu_info in gpu_infos:
            if gpu_info["memory_free_mb"] >= required_mb:
                available.append(gpu_info["id"])
                if len(available) >= count:
                    break
        
        return available
    
    def check_gpu_compatibility(self, gpu_id: int, requirements: Dict) -> bool:
        """检查 GPU 兼容性"""
        gpu_info = self.get_gpu_info(gpu_id)
        
        # 检查显存
        if "min_memory_mb" in requirements:
            if gpu_info["memory_total_mb"] < requirements["min_memory_mb"]:
                return False
        
        # 检查计算能力
        if "min_compute_capability" in requirements:
            handle = pynvml.nvmlDeviceGetHandleByIndex(gpu_id)
            major, minor = pynvml.nvmlDeviceGetCudaComputeCapability(handle)
            compute_capability = float(f"{major}.{minor}")
            if compute_capability < requirements["min_compute_capability"]:
                return False
        
        return True
    
    def __del__(self):
        try:
            pynvml.nvmlShutdown()
        except:
            pass
```

### 5.2 模型服务模块

```python
# services/model_service.py
from typing import Optional
from sqlalchemy.orm import Session
from models.database import Model, ModelStatus
import subprocess
import os

class ModelService:
    """模型服务"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def download_model(
        self,
        name: str,
        source: str,
        version: str,
        huggingface_token: Optional[str] = None
    ) -> Model:
        """下载模型"""
        # 创建模型记录
        model = Model(
            name=name,
            version=version,
            source=source,
            category="llm",
            status=ModelStatus.DOWNLOADING,
            download_progress=0
        )
        self.db.add(model)
        self.db.commit()
        self.db.refresh(model)
        
        # 异步下载
        self._async_download(model.id, name, source, huggingface_token)
        
        return model
    
    def _async_download(self, model_id: int, name: str, source: str, token: Optional[str]):
        """异步下载模型"""
        from utils import logger
        
        try:
            storage_path = f"/var/lib/backend/models/{name.replace('/', '--')}"
            
            if source == "huggingface":
                cmd = ["huggingface-cli", "download", name, "--local-dir", storage_path]
                if token:
                    cmd.extend(["--token", token])
                
                process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                
                # 监控下载进度
                while process.poll() is None:
                    # 解析进度（简化版）
                    logger.info(f"Downloading {name}...")
                    import time
                    time.sleep(5)
                
                if process.returncode != 0:
                    raise Exception(f"Download failed: {process.stderr.read()}")
            
            # 更新模型状态
            model = self.db.query(Model).filter(Model.id == model_id).first()
            model.status = ModelStatus.READY
            model.path = storage_path
            model.size_gb = self._calculate_model_size(storage_path)
            model.download_progress = 100
            self.db.commit()
            
        except Exception as e:
            logger.error(f"Model download failed: {e}")
            model = self.db.query(Model).filter(Model.id == model_id).first()
            model.status = ModelStatus.ERROR
            model.error_message = str(e)
            self.db.commit()
    
    def _calculate_model_size(self, path: str) -> float:
        """计算模型大小 (GB)"""
        total_size = 0
        for dirpath, dirnames, filenames in os.walk(path):
            for filename in filenames:
                filepath = os.path.join(dirpath, filename)
                total_size += os.path.getsize(filepath)
        return round(total_size / (1024**3), 2)
    
    def get_model(self, model_id: int) -> Optional[Model]:
        """获取模型"""
        return self.db.query(Model).filter(Model.id == model_id).first()
    
    def list_models(self) -> list:
        """列出所有模型"""
        return self.db.query(Model).all()
```

### 5.3 部署服务模块

```python
# services/deployment_service.py
from typing import List
from sqlalchemy.orm import Session
from models.database import Deployment, DeploymentStatus, GPU
from workers.vllm_worker import VLLMWorkerPool
import asyncio

class DeploymentService:
    """部署服务"""
    
    def __init__(self, db: Session, worker_pool: VLLMWorkerPool):
        self.db = db
        self.worker_pool = worker_pool
    
    async def create_deployment(
        self,
        model_id: int,
        name: str,
        replicas: int,
        gpu_ids: List[str],
        config: dict
    ) -> Deployment:
        """创建部署"""
        # 验证模型
        from services.model_service import ModelService
        model_service = ModelService(self.db)
        model = model_service.get_model(model_id)
        if not model:
            raise ValueError("Model not found")
        if model.status != "ready":
            raise ValueError("Model not ready")
        
        # 创建部署记录
        deployment = Deployment(
            model_id=model_id,
            name=name,
            status=DeploymentStatus.STARTING,
            replicas=replicas,
            gpu_ids=gpu_ids,
            backend=config.get("backend", "vllm"),
            config=config
        )
        self.db.add(deployment)
        self.db.commit()
        self.db.refresh(deployment)
        
        # 启动 Workers
        await self._start_workers(deployment)
        
        return deployment
    
    async def _start_workers(self, deployment: Deployment):
        """启动 Workers"""
        from services.model_service import ModelService
        model_service = ModelService(self.db)
        model = model_service.get_model(deployment.model_id)
        
        workers = []
        for i in range(deployment.replicas):
            gpu_id = deployment.gpu_ids[i % len(deployment.gpu_ids)]
            worker = await self.worker_pool.create_worker(
                deployment_id=deployment.id,
                model_path=model.path,
                model_name=deployment.name,
                gpu_id=gpu_id,
                port=8001 + i,
                config=deployment.config
            )
            workers.append(worker)
        
        # 更新部署状态
        all_healthy = all(worker.is_healthy() for worker in workers)
        deployment.status = DeploymentStatus.RUNNING if all_healthy else DeploymentStatus.ERROR
        self.db.commit()
    
    async def stop_deployment(self, deployment_id: int):
        """停止部署"""
        deployment = self.db.query(Deployment).filter(
            Deployment.id == deployment_id
        ).first()
        
        if not deployment:
            raise ValueError("Deployment not found")
        
        # 停止所有 Workers
        await self.worker_pool.stop_deployment_workers(deployment_id)
        
        # 更新状态
        deployment.status = DeploymentStatus.STOPPED
        self.db.commit()
    
    def get_deployment(self, deployment_id: int) -> Optional[Deployment]:
        """获取部署"""
        return self.db.query(Deployment).filter(
            Deployment.id == deployment_id
        ).first()
```

### 5.4 VLLM Worker 模块

```python
# workers/vllm_worker.py
import subprocess
import asyncio
import httpx
from typing import Optional

class VLLMWorker:
    """vLLM 工作进程"""
    
    def __init__(
        self,
        deployment_id: int,
        model_path: str,
        model_name: str,
        gpu_id: str,
        port: int,
        config: dict
    ):
        self.deployment_id = deployment_id
        self.model_path = model_path
        self.model_name = model_name
        self.gpu_id = gpu_id
        self.port = port
        self.config = config
        self.process: Optional[subprocess.Popen] = None
        self.base_url = f"http://localhost:{port}"
    
    async def start(self):
        """启动 Worker"""
        cmd = [
            "python", "-m", "vllm.entrypoints.openai.api_server",
            "--model", self.model_path,
            "--host", "0.0.0.0",
            "--port", str(self.port),
            "--gpu-memory-utilization", str(self.config.get("gpu_memory_utilization", 0.9)),
            "--max-model-len", str(self.config.get("max_model_len", 4096)),
        ]
        
        if self.config.get("tensor_parallel_size", 1) > 1:
            cmd.extend(["--tensor-parallel-size", str(self.config["tensor_parallel_size"])])
        
        # 设置环境变量
        env = {
            "CUDA_VISIBLE_DEVICES": self.gpu_id.replace("gpu:", ""),
        }
        
        self.process = subprocess.Popen(
            cmd,
            env={**os.environ, **env},
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # 等待服务启动
        await self._wait_for_ready()
    
    async def _wait_for_ready(self, timeout: int = 300):
        """等待服务就绪"""
        start_time = asyncio.get_event_loop().time()
        
        while asyncio.get_event_loop().time() - start_time < timeout:
            if self.is_healthy():
                return
            await asyncio.sleep(2)
        
        raise TimeoutError(f"Worker failed to start within {timeout}s")
    
    def is_healthy(self) -> bool:
        """健康检查"""
        try:
            import httpx
            response = httpx.get(f"{self.base_url}/health", timeout=5)
            return response.status_code == 200
        except:
            return False
    
    async def stop(self):
        """停止 Worker"""
        if self.process:
            self.process.terminate()
            try:
                self.process.wait(timeout=30)
            except subprocess.TimeoutExpired:
                self.process.kill()
            self.process = None
    
    def get_endpoint(self) -> str:
        """获取端点 URL"""
        return self.base_url


class VLLMWorkerPool:
    """vLLM Worker 池"""
    
    def __init__(self):
        self.workers: dict[int, list[VLLMWorker]] = {}
    
    async def create_worker(
        self,
        deployment_id: int,
        model_path: str,
        model_name: str,
        gpu_id: str,
        port: int,
        config: dict
    ) -> VLLMWorker:
        """创建 Worker"""
        worker = VLLMWorker(
            deployment_id=deployment_id,
            model_path=model_path,
            model_name=model_name,
            gpu_id=gpu_id,
            port=port,
            config=config
        )
        await worker.start()
        
        if deployment_id not in self.workers:
            self.workers[deployment_id] = []
        self.workers[deployment_id].append(worker)
        
        return worker
    
    async def stop_deployment_workers(self, deployment_id: int):
        """停止部署的所有 Workers"""
        if deployment_id in self.workers:
            for worker in self.workers[deployment_id]:
                await worker.stop()
            del self.workers[deployment_id]
    
    def get_worker_endpoint(self, deployment_id: int) -> Optional[str]:
        """获取 Worker 端点（简单轮询）"""
        workers = self.workers.get(deployment_id, [])
        if not workers:
            return None
        
        # 简单轮询，可以改为负载均衡
        return workers[len(workers) % len(workers)].get_endpoint()
```

### 5.5 监控模块

```python
# monitoring/metrics.py
from prometheus_client import Counter, Gauge, Histogram, Summary

# API 指标
api_requests_total = Counter(
    'tokenmachine_api_requests_total',
    'Total API requests',
    ['method', 'endpoint', 'status']
)

api_latency_seconds = Histogram(
    'tokenmachine_api_latency_seconds',
    'API latency in seconds',
    ['endpoint']
)

# 模型指标
model_tokens_total = Counter(
    'tokenmachine_model_tokens_total',
    'Total tokens generated',
    ['model_name', 'token_type']  # input, output
)

model_requests_active = Gauge(
    'tokenmachine_model_requests_active',
    'Active model requests',
    ['model_name']
)

# GPU 指标
gpu_utilization_percent = Gauge(
    'tokenmachine_gpu_utilization_percent',
    'GPU utilization percentage',
    ['gpu_id']
)

gpu_memory_used_mb = Gauge(
    'tokenmachine_gpu_memory_used_mb',
    'GPU memory used in MB',
    ['gpu_id']
)

gpu_temperature_celsius = Gauge(
    'tokenmachine_gpu_temperature_celsius',
    'GPU temperature in Celsius',
    ['gpu_id']
)

# Worker 指标
worker_status = Gauge(
    'tokenmachine_worker_status',
    'Worker status (1=running, 0=stopped)',
    ['deployment_id', 'worker_id']
)

worker_requests_total = Counter(
    'tokenmachine_worker_requests_total',
    'Total worker requests',
    ['deployment_id', 'worker_id', 'status']
)

# 系统指标
system_cpu_percent = Gauge('tokenmachine_system_cpu_percent', 'System CPU percentage')
system_memory_used_mb = Gauge('tokenmachine_system_memory_used_mb', 'System memory used in MB')
system_disk_usage_percent = Gauge('tokenmachine_system_disk_usage_percent', 'System disk usage percentage')
```

```python
# monitoring/exporter.py
from fastapi import FastAPI
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
from core.gpu import GPUManager
import psutil

app = FastAPI()

@app.get("/metrics")
async def metrics():
    """Prometheus 指标端点"""
    from monitoring.metrics import *
    
    # 收集 GPU 指标
    gpu_manager = GPUManager()
    for gpu_info in gpu_manager.get_all_gpus():
        gpu_id = gpu_info["id"]
        gpu_utilization_percent.labels(gpu_id=gpu_id).set(gpu_info["utilization_percent"])
        gpu_memory_used_mb.labels(gpu_id=gpu_id).set(gpu_info["memory_used_mb"])
        gpu_temperature_celsius.labels(gpu_id=gpu_id).set(gpu_info["temperature_celsius"])
    
    # 收集系统指标
    system_cpu_percent.set(psutil.cpu_percent())
    system_memory_used_mb.set(psutil.virtual_memory().used / (1024 * 1024))
    system_disk_usage_percent.set(psutil.disk_usage('/').percent)
    
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST
    )

@app.get("/health")
async def health():
    """健康检查"""
    return {"status": "healthy"}
```

---

## 6. 部署架构

### 6.1 Docker Compose 部署

```yaml
version: '3.8'

services:
  # PostgreSQL 数据库
  postgres:
    image: postgres:15-alpine
    container_name: tokenmachine-postgres
    environment:
      POSTGRES_DB: tokenmachine
      POSTGRES_USER: tokenmachine
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U tokenmachine"]
      interval: 10s
      timeout: 5s
      retries: 5

  # Redis 缓存
  redis:
    image: redis:7-alpine
    container_name: tokenmachine-redis
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

  # FastAPI 应用
  api:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: tokenmachine-api
    environment:
      DATABASE_URL: postgresql://tokenmachine:${POSTGRES_PASSWORD}@postgres:5432/tokenmachine
      REDIS_URL: redis://redis:6379/0
      INFERENCE_API_KEY: ${INFERENCE_API_KEY}
      MODEL_STORAGE_PATH: /var/lib/backend/models
    volumes:
      - model_data:/var/lib/backend/models
      - ./logs:/var/log/tokenmachine
    ports:
      - "8000:8000"
      - "9090:9090"  # Prometheus metrics
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: all
              capabilities: [gpu]
    command: uvicorn main:app --host 0.0.0.0 --port 8000

  # Prometheus
  prometheus:
    image: prom/prometheus:latest
    container_name: tokenmachine-prometheus
    ports:
      - "9091:9090"
    volumes:
      - ./config/prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus_data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'

  # Grafana
  grafana:
    image: grafana/grafana:latest
    container_name: tokenmachine-grafana
    ports:
      - "3000:3000"
    environment:
      GF_SECURITY_ADMIN_PASSWORD: ${GRAFANA_PASSWORD}
    volumes:
      - grafana_data:/var/lib/grafana
      - ./config/grafana:/etc/grafana/provisioning
    depends_on:
      - prometheus

volumes:
  postgres_data:
  redis_data:
  model_data:
  prometheus_data:
  grafana_data:
```

### 6.2 Prometheus 配置

```yaml
# config/prometheus.yml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'tokenmachine-api'
    static_configs:
      - targets: ['api:9090']
    metrics_path: '/metrics'

  - job_name: 'tokenmachine-workers'
    static_configs:
      - targets: ['localhost:8001', 'localhost:8002']  # vLLM workers
    metrics_path: '/metrics'

  - job_name: 'prometheus'
    static_configs:
      - targets: ['localhost:9090']
```

### 6.3 Dockerfile

```dockerfile
FROM python:3.11-slim

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    git \
    wget \
    curl \
    nvidia-cuda-toolkit \
    && rm -rf /var/lib/apt/lists/*

# 设置工作目录
WORKDIR /app

# 复制依赖文件
COPY requirements.txt .

# 安装 Python 依赖
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY . .

# 创建模型存储目录
RUN mkdir -p /var/lib/backend/models /var/log/tokenmachine

# 暴露端口
EXPOSE 8000 9090

# 启动命令
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 6.4 requirements.txt

```txt
# Web 框架
fastapi==0.109.0
uvicorn[standard]==0.27.0
pydantic==2.5.3
pydantic-settings==2.1.0

# 数据库
sqlalchemy==2.0.25
psycopg2-binary==2.9.9
alembic==1.13.1

# 缓存
redis==5.0.1
hiredis==2.2.3

# GPU 监控
pynvml==12.535.133

# HTTP 客户端
httpx==0.26.0

# 监控
prometheus-client==0.19.0

# 日志
loguru==0.7.2

# 工具
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
python-multipart==0.0.6

# HuggingFace
huggingface-hub==0.20.3

# vLLM (作为子进程使用)
vllm==0.3.0

# 系统监控
psutil==5.9.8
```

---

## 7. 技术选型

### 7.1 后端技术栈

| 组件 | 技术选型 | 版本 | 说明 |
|------|---------|------|------|
| **Web 框架** | FastAPI | 0.109.0 | 高性能、异步支持、自动文档 |
| **ASGI 服务器** | Uvicorn | 0.27.0 | 快速、支持 HTTP/2 |
| **ORM** | SQLAlchemy | 2.0.25 | 成熟、功能完善 |
| **数据库** | PostgreSQL | 15.0 | 关系型、可靠 |
| **缓存** | Redis | 7.0 | 高性能内存数据库 |
| **GPU 监控** | pynvml | 12.535.133 | NVIDIA 官方 Python SDK |
| **HTTP 客户端** | httpx | 0.26.0 | 异步 HTTP 客户端 |
| **监控** | Prometheus | latest | 指标收集和存储 |
| **日志** | Loguru | 0.7.2 | 简洁的日志库 |
| **认证** | python-jose | 3.3.0 | JWT 支持 |

### 7.2 推理引擎

| 引擎 | 版本 | 用途 | 备注 |
|------|------|------|------|
| **vLLM** | 0.3.0 | 默认推理引擎 | PagedAttention、OpenAI API 兼容 |
| **(预留)** | - | SGLang | P2 支持 |
| **(预留)** | - | TensorRT-LLM | P2 支持 |

### 7.3 前端技术栈（可选）

| 组件 | 技术选型 | 版本 | 说明 |
|------|---------|------|------|
| **框架** | React | 18.2.0 | 组件化开发 |
| **语言** | TypeScript | 5.3.3 | 类型安全 |
| **构建工具** | Vite | 5.0.11 | 快速构建 |
| **UI 组件库** | Ant Design | 5.12.8 | 企业级 UI |
| **状态管理** | Zustand | 4.4.7 | 轻量级状态管理 |
| **HTTP 客户端** | axios | 1.6.5 | HTTP 请求 |
| **图表库** | ECharts | 5.4.3 | 数据可视化 |

---

## 8. 开发计划

### 8.1 迭代计划（12 周）

#### Week 1-2: 基础架构
- [ ] 项目初始化（代码结构、依赖配置）
- [ ] 数据库设计和迁移
- [ ] 配置管理系统
- [ ] 日志系统
- [ ] API 认证中间件

#### Week 3-4: GPU 管理
- [ ] GPU 信息采集
- [ ] GPU 资源分配
- [ ] GPU 健康检查
- [ ] GPU 监控指标

#### Week 5-6: 模型管理
- [ ] 模型下载功能
- [ ] 模型存储管理
- [ ] 模型版本管理
- [ ] 模型状态管理

#### Week 7-8: 部署管理
- [ ] vLLM Worker 封装
- [ ] 部署创建/停止
- [ ] Worker 健康检查
- [ ] 部署状态监控

#### Week 9-10: API 网关
- [ ] OpenAI Chat API 实现
- [ ] OpenAI Models API 实现
- [ ] 流式输出支持
- [ ] 请求路由和负载均衡

#### Week 11: 监控和日志
- [ ] Prometheus 指标收集
- [ ] Grafana 面板配置
- [ ] 结构化日志
- [ ] 告警规则

#### Week 12: 测试和优化
- [ ] 单元测试
- [ ] 集成测试
- [ ] 性能测试
- [ ] 文档完善

### 8.2 里程碑

| 周次 | 里程碑 | 交付物 |
|------|--------|--------|
| Week 2 | 基础架构完成 | 数据库、配置、日志系统 |
| Week 4 | GPU 管理完成 | GPU 信息采集、资源分配 |
| Week 6 | 模型管理完成 | 模型下载、存储、版本管理 |
| Week 8 | 部署管理完成 | vLLM 集成、部署生命周期 |
| Week 10 | API 网关完成 | OpenAI API 兼容 |
| Week 11 | 监控完成 | Prometheus + Grafana |
| Week 12 | MVP 发布 | 可用的最小可行产品 |

### 8.3 质量保证

#### 测试策略
- **单元测试**: 核心逻辑测试（覆盖率 > 80%）
- **集成测试**: API 端到端测试
- **压力测试**: 模拟高并发场景
- **冒烟测试**: 每次发布前的快速验证

#### 代码审查
- 所有代码需要至少 1 人审查
- 使用 Git Flow 分支策略
- CI/CD 自动化测试

---

## 9. MVP 功能演示场景

### 9.1 场景 1: 首次部署

```bash
# 1. 启动服务
docker-compose up -d

# 2. 创建管理员账户
curl -X POST http://localhost:8000/api/v1/admin/users \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin",
    "email": "admin@example.com",
    "password": "secure_password"
  }'

# 3. 获取管理员 Token
curl -X POST http://localhost:8000/api/v1/admin/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin",
    "password": "secure_password"
  }'
# 返回: { "access_token": "eyJ..." }

# 4. 下载模型
curl -X POST http://localhost:8000/api/v1/admin/models \
  -H "Authorization: Bearer eyJ..." \
  -H "Content-Type: application/json" \
  -d '{
    "name": "meta-llama/Llama-3-8B-Instruct",
    "source": "huggingface",
    "version": "v1.0"
  }'
# 返回: { "id": 1, "status": "downloading", "progress": 0 }

# 5. 等待模型下载完成
curl http://localhost:8000/api/v1/admin/models/1 \
  -H "Authorization: Bearer eyJ..."
# 返回: { "status": "ready", "size_gb": 16.5 }

# 6. 创建部署
curl -X POST http://localhost:8000/api/v1/admin/deployments \
  -H "Authorization: Bearer eyJ..." \
  -H "Content-Type: application/json" \
  -d '{
    "model_id": 1,
    "name": "llama-3-8b-prod",
    "replicas": 2,
    "gpu_ids": ["gpu:0", "gpu:1"],
    "backend": "vllm",
    "config": {
      "max_model_len": 4096,
      "gpu_memory_utilization": 0.9
    }
  }'
# 返回: { "id": 1, "status": "starting", "endpoints": [...] }

# 7. 创建 API Key
curl -X POST http://localhost:8000/api/v1/admin/api-keys \
  -H "Authorization: Bearer eyJ..." \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Production Key",
    "user_id": 1,
    "quota_tokens": 100000000
  }'
# 返回: { "key": "tm_sk_abc123...", "key_prefix": "tm_sk_abc1" }

# 8. 使用 OpenAI API 调用
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Authorization: Bearer tm_sk_abc123..." \
  -H "Content-Type: application/json" \
  -d '{
    "model": "llama-3-8b-prod",
    "messages": [{"role": "user", "content": "Hello!"}]
  }'
# 返回: { "choices": [{"message": {"content": "Hello! How can I help you?"}}] }
```

### 9.2 场景 2: 监控查看

```bash
# 访问 Grafana
open http://localhost:3000

# 查看仪表盘
# 1. GPU 利用率
# 2. API 调用量
# 3. 模型 Token 消耗
# 4. 响应延迟
```

---

## 10. 技术风险和应对

### 10.1 已知风险

| 风险 | 影响 | 概率 | 应对措施 |
|------|------|------|----------|
| vLLM 兼容性问题 | 高 | 中 | 充分测试，提供版本兼容列表 |
| GPU 资源竞争 | 中 | 高 | 实现资源分配和调度 |
| 模型下载慢 | 中 | 中 | 支持断点续传、镜像加速 |
| 并发性能问题 | 高 | 低 | 压力测试、异步优化 |
| 内存泄漏 | 中 | 低 | 定期监控、自动重启 |

### 10.2 性能目标

| 指标 | 目标值 | 说明 |
|------|--------|------|
| **API 延迟 (P50)** | < 500ms | 首个 token 生成时间 |
| **API 延迟 (P99)** | < 2000ms | 99% 请求的延迟 |
| **吞吐量** | > 1000 req/min | 单部署副本 |
| **并发连接** | > 100 | 同时处理请求数 |
| **GPU 利用率** | > 80% | 峰值时 |
| **内存占用** | < 4GB | API 进程 |

---

## 附录 A: 快速开始脚本

```bash
#!/bin/bash
# quick-start.sh

set -e

echo "🚀 TokenMachine MVP Quick Start"

# 1. 检查 Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Docker not found. Please install Docker first."
    exit 1
fi

# 2. 检查 NVIDIA GPU
if ! command -v nvidia-smi &> /dev/null; then
    echo "❌ NVIDIA GPU not found. Please install NVIDIA drivers."
    exit 1
fi

# 3. 创建 .env 文件
cat > .env <<EOF
POSTGRES_PASSWORD=secure_postgres_password
INFERENCE_API_KEY=secure_api_key_change_me
GRAFANA_PASSWORD=admin
EOF

# 4. 启动服务
echo "📦 Starting services..."
docker-compose up -d

# 5. 等待服务就绪
echo "⏳ Waiting for services to be ready..."
sleep 30

# 6. 初始化数据库
echo "🗄️  Initializing database..."
docker-compose exec api alembic upgrade head

# 7. 创建默认管理员
echo "👤 Creating default admin user..."
curl -X POST http://localhost:8000/api/v1/admin/users \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin",
    "email": "admin@tokenmachine.local",
    "password": "admin123"
  }'

echo ""
echo "✅ Setup complete!"
echo ""
echo "📝 Credentials:"
echo "   Web UI: http://localhost:3000"
echo "   Username: admin"
echo "   Password: admin"
echo ""
echo "   Grafana: http://localhost:3000"
echo "   Username: admin"
echo "   Password: admin"
echo ""
echo "   API Documentation: http://localhost:8000/docs"
echo ""
```

---

**文档版本**: v1.0
**最后更新**: 2025-01-13
**作者**: TokenMachine Team
