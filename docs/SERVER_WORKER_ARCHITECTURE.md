# Server-Worker 分离架构设计

> 基于 GPUStack 架构分析，补充 TokenMachine 的 Server-Worker 分离架构设计

---

## 目录

- [1. 架构概述](#1-架构概述)
- [2. 组件设计](#2-组件设计)
- [3. 通信协议](#3-通信协议)
- [4. Worker 生命周期](#4-worker-生命周期)
- [5. 部署模式](#5-部署模式)
- [6. 数据库设计](#6-数据库设计)
- [7. API 设计](#7-api-设计)
- [8. 实施计划](#8-实施计划)

---

## 1. 架构概述

### 1.1 整体架构

```
┌─────────────────────────────────────────────────────────────────┐
│                         客户端层                                  │
│  Web UI │ CLI │ OpenAI API │ SDK                                │
└────────────────────────────┬────────────────────────────────────┘
                             │ HTTPS
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Server (控制平面)                           │
├─────────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │ API Gateway  │  │  Scheduler   │  │ Controllers  │          │
│  │              │  │              │  │              │          │
│  │ • 路由       │  │ • 调度策略   │  │ • Model      │          │
│  │ • 认证       │  │ • 资源分配   │  │ • Instance   │          │
│  │ • 限流       │  │ • 负载均衡   │  │ • Worker     │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
│                                                                   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │   Database   │  │    Cache     │  │   Monitor    │          │
│  │   (PG)       │  │   (Redis)    │  │ (Prometheus) │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
└────────────────────────────┬────────────────────────────────────┘
                             │ gRPC/HTTP
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Worker (数据平面)                           │
├─────────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │ Worker API   │  │Serve Manager │  │  Backends    │          │
│  │              │  │              │  │              │          │
│  │ • 健康检查   │  │ • 模型加载   │  │ • vLLM       │          │
│  │ • 日志流     │  │ • 实例管理   │  │ • SGLang     │          │
│  │ • 指标上报   │  │ • 资源监控   │  │ • TensorRT   │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
│                                                                   │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │                  GPU Resources                           │    │
│  │  GPU 0 │ GPU 1 │ GPU 2 │ GPU 3 │ ...                    │    │
│  └─────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
```

### 1.2 核心概念

| 概念 | 说明 | 示例 |
|------|------|------|
| **Server** | 控制平面，负责任务调度、资源管理、状态维护 | API Server、Scheduler |
| **Worker** | 数据平面，负责模型加载、推理执行、资源上报 | 推理节点 |
| **Cluster** | 逻辑集群，一组 Worker 的集合 | 生产集群、测试集群 |
| **Model** | 模型定义，包含模型元数据 | Qwen2.5-7B-Instruct |
| **ModelInstance** | 模型实例，模型在 Worker 上的运行实例 | worker-1 上的 Qwen 实例 |
| **WorkerPool** | Worker 池，用于调度的一组 Worker | GPU 池、NPU 池 |

### 1.3 设计原则

1. **关注点分离**：Server 负责调度，Worker 负责执行
2. **松耦合**：Server 和 Worker 通过 API 通信，互不依赖
3. **可扩展**：支持动态添加/移除 Worker
4. **高可用**：Server 无状态，支持多副本部署
5. **容错性**：Worker 故障自动检测，实例自动迁移

---

## 2. 组件设计

### 2.1 Server 组件

#### 2.1.1 目录结构

```
backend/server/
├── __init__.py
├── server.py              # Server 主类
├── config.py              # Server 配置
├── api/                   # Server API
│   ├── __init__.py
│   ├── workers.py         # Worker 管理 API
│   ├── models.py          # Model 管理 API
│   └── instances.py       # Instance 管理 API
└── client/                # Worker 客户端
    ├── __init__.py
    └── client.py          # gRPC/HTTP 客户端
```

#### 2.1.2 Server 主类

```python
# backend/server/server.py
from typing import Optional
import asyncio
from backend.core.config import get_settings
from backend.core.database import get_db_session
from backend.server.controllers import (
    ModelController,
    ModelInstanceController,
    WorkerController,
    ClusterController,
)
from backend.server.scheduler import Scheduler
from backend.server.worker_sync import WorkerSyncManager

class Server:
    """Server 控制平面"""

    def __init__(self, config: Optional[dict] = None):
        self.settings = config or get_settings()
        self.db_session = get_db_session()

        # Controllers
        self.model_controller = ModelController(self.db_session)
        self.instance_controller = ModelInstanceController(self.db_session)
        self.worker_controller = WorkerController(self.db_session)
        self.cluster_controller = ClusterController(self.db_session)

        # Scheduler
        self.scheduler = Scheduler(
            worker_controller=self.worker_controller,
            instance_controller=self.instance_controller,
        )

        # Worker Sync Manager
        self.worker_sync = WorkerSyncManager(
            worker_controller=self.worker_controller,
        )

        # Background tasks
        self._background_tasks = []

    async def start(self):
        """启动 Server"""
        logger.info("Starting TokenMachine Server...")

        # 启动 Worker 状态同步
        self._background_tasks.append(
            asyncio.create_task(self.worker_sync.sync_worker_statuses())
        )

        # 启动调度器
        self._background_tasks.append(
            asyncio.create_task(self.scheduler.run())
        )

        # 启动实例健康检查
        self._background_tasks.append(
            asyncio.create_task(self.instance_controller.health_check_loop())
        )

        logger.info("TokenMachine Server started")

    async def stop(self):
        """停止 Server"""
        logger.info("Stopping TokenMachine Server...")

        # 取消后台任务
        for task in self._background_tasks:
            task.cancel()

        # 等待任务结束
        await asyncio.gather(*self._background_tasks, return_exceptions=True)

        logger.info("TokenMachine Server stopped")

    async def serve(self, host: str = "0.0.0.0", port: int = 8000):
        """启动 API 服务"""
        import uvicorn
        from backend.api import create_app

        app = create_app(server=self)

        config = uvicorn.Config(
            app,
            host=host,
            port=port,
            log_level="info",
        )
        server = uvicorn.Server(config)

        await server.serve()
```

### 2.2 Worker 组件

#### 2.2.1 目录结构

```
backend/worker/
├── __init__.py
├── worker.py              # Worker 主类
├── config.py              # Worker 配置
├── api/                   # Worker API
│   ├── __init__.py
│   ├── health.py          # 健康检查
│   ├── logs.py            # 日志流
│   └── proxy.py           # 推理代理
├── serve_manager.py       # 模型服务管理
├── backends/              # 推理后端
│   ├── __init__.py
│   ├── base.py            # 后端抽象
│   ├── vllm_backend.py    # vLLM
│   ├── sglang_backend.py  # SGLang
│   └── tensorrt_backend.py # TensorRT-LLM
├── collector.py           # 指标采集
└── exporter.py            # 指标导出
```

#### 2.2.2 Worker 主类

```python
# backend/worker/worker.py
from typing import Optional
import asyncio
import socket
from backend.worker.config import get_worker_config
from backend.worker.serve_manager import ServeManager
from backend.worker.collector import WorkerStatusCollector
from backend.worker.exporter import MetricExporter

class Worker:
    """Worker 数据平面"""

    def __init__(
        self,
        server_url: str,
        token: str,
        config: Optional[dict] = None,
    ):
        self.config = config or get_worker_config()
        self.server_url = server_url
        self.token = token

        # 检测 Worker 信息
        self.worker_ip, self.worker_ifname = self._detect_worker_info()
        self.worker_name = self.config.worker_name or socket.gethostname()
        self.worker_id: Optional[int] = None
        self.cluster_id: Optional[int] = None

        # 组件
        self.status_collector = WorkerStatusCollector(
            worker_ip=self.worker_ip,
            worker_name=self.worker_name,
        )
        self.serve_manager = ServeManager(
            worker_id_getter=lambda: self.worker_id,
            server_url=server_url,
            token=token,
        )
        self.metric_exporter = MetricExporter(
            collector=self.status_collector,
            server_url=server_url,
            token=token,
        )

        # API 服务
        self.api_app: Optional[FastAPI] = None

    def _detect_worker_info(self) -> tuple[str, str]:
        """检测 Worker IP 和接口名"""
        from backend.utils.network import (
            get_first_non_loopback_ip,
            get_ifname_by_ip,
        )

        ip = get_first_non_loopback_ip()
        ifname = get_ifname_by_ip(ip)

        return ip, ifname

    async def register(self) -> dict:
        """向 Server 注册"""
        import httpx

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.server_url}/api/v1/workers/register",
                headers={"Authorization": f"Bearer {self.token}"},
                json={
                    "name": self.worker_name,
                    "ip": self.worker_ip,
                    "ifname": self.worker_ifname,
                    "hostname": socket.gethostname(),
                },
            )
            response.raise_for_status()
            data = response.json()

            self.worker_id = data["id"]
            self.cluster_id = data.get("cluster_id")

            logger.info(f"Worker registered: {self.worker_id}")
            return data

    async def start(self):
        """启动 Worker"""
        logger.info("Starting TokenMachine Worker...")

        # 注册到 Server
        await self.register()

        # 启动指标采集
        asyncio.create_task(self.metric_exporter.start())

        # 启动模型服务管理
        asyncio.create_task(self.serve_manager.watch_model_instances())
        asyncio.create_task(self.serve_manager.sync_instance_states())

        # 启动心跳
        asyncio.create_task(self._heartbeat_loop())

        # 启动 API 服务
        await self._serve_api()

        logger.info("TokenMachine Worker started")

    async def stop(self):
        """停止 Worker"""
        logger.info("Stopping TokenMachine Worker...")

        # 停止所有模型实例
        await self.serve_manager.stop_all_instances()

        logger.info("TokenMachine Worker stopped")

    async def _heartbeat_loop(self):
        """心跳循环"""
        import httpx

        while True:
            try:
                async with httpx.AsyncClient() as client:
                    await client.post(
                        f"{self.server_url}/api/v1/workers/{self.worker_id}/heartbeat",
                        headers={"Authorization": f"Bearer {self.token}"},
                    )
            except Exception as e:
                logger.warning(f"Heartbeat failed: {e}")

            await asyncio.sleep(30)

    async def _serve_api(self):
        """启动 Worker API 服务"""
        from fastapi import FastAPI
        import uvicorn

        app = FastAPI(title="TokenMachine Worker")

        # 路由
        from backend.worker.api import health, logs, proxy
        app.include_router(health.router)
        app.include_router(logs.router)
        app.include_router(proxy.router)

        self.api_app = app

        config = uvicorn.Config(
            app,
            host="0.0.0.0",
            port=self.config.api_port,
            log_level="info",
        )
        server = uvicorn.Server(config)
        await server.serve()
```

### 2.3 Serve Manager（模型服务管理器）

```python
# backend/worker/serve_manager.py
from typing import Dict, Optional
import asyncio
from backend.worker.backends.base import InferenceBackend
from backend.worker.backends.vllm_backend import VLLMBackend
from backend.worker.backends.sglang_backend import SGLangBackend

class ServeManager:
    """模型服务管理器"""

    def __init__(
        self,
        worker_id_getter: callable,
        server_url: str,
        token: str,
    ):
        self.worker_id_getter = worker_id_getter
        self.server_url = server_url
        self.token = token

        # 模型缓存: {instance_id: ModelInstance}
        self._model_cache_by_instance: Dict[int, dict] = {}

        # 实例缓存: {instance_id: InferenceBackend}
        self._backend_by_instance: Dict[int, InferenceBackend] = {}

    async def watch_model_instances(self):
        """监听模型实例变化"""
        last_seen_ids = set()

        while True:
            try:
                worker_id = self.worker_id_getter()
                if worker_id is None:
                    await asyncio.sleep(5)
                    continue

                # 获取分配给此 Worker 的实例
                instances = await self._get_worker_instances(worker_id)
                current_ids = {inst["id"] for inst in instances}

                # 新增实例
                new_ids = current_ids - last_seen_ids
                for instance_id in new_ids:
                    instance = next(i for i in instances if i["id"] == instance_id)
                    await self._start_instance(instance)

                # 移除实例
                removed_ids = last_seen_ids - current_ids
                for instance_id in removed_ids:
                    await self._stop_instance(instance_id)

                last_seen_ids = current_ids
                await asyncio.sleep(10)

            except Exception as e:
                logger.error(f"Error watching instances: {e}")
                await asyncio.sleep(10)

    async def _get_worker_instances(self, worker_id: int) -> list:
        """获取 Worker 的实例列表"""
        import httpx

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.server_url}/api/v1/workers/{worker_id}/instances",
                headers={"Authorization": f"Bearer {self.token}"},
            )
            response.raise_for_status()
            return response.json()["items"]

    async def _start_instance(self, instance: dict):
        """启动模型实例"""
        instance_id = instance["id"]
        model = instance["model"]
        backend_name = instance.get("backend", "vllm")

        logger.info(f"Starting instance {instance_id}: {model['name']}")

        # 选择后端
        if backend_name == "vllm":
            backend = VLLMBackend(
                model_path=model["path"],
                model_name=model["name"],
                config=instance.get("config", {}),
            )
        elif backend_name == "sglang":
            backend = SGLangBackend(
                model_path=model["path"],
                model_name=model["name"],
                config=instance.get("config", {}),
            )
        else:
            raise ValueError(f"Unsupported backend: {backend_name}")

        # 启动后端
        await backend.start()

        # 缓存
        self._backend_by_instance[instance_id] = backend
        self._model_cache_by_instance[instance_id] = model

        # 更新状态
        await self._update_instance_status(instance_id, "running")

        logger.info(f"Instance {instance_id} started")

    async def _stop_instance(self, instance_id: int):
        """停止模型实例"""
        if instance_id not in self._backend_by_instance:
            return

        logger.info(f"Stopping instance {instance_id}")

        backend = self._backend_by_instance.pop(instance_id)
        await backend.stop()

        self._model_cache_by_instance.pop(instance_id, None)

        logger.info(f"Instance {instance_id} stopped")

    async def _update_instance_status(self, instance_id: int, status: str):
        """更新实例状态"""
        import httpx

        async with httpx.AsyncClient() as client:
            await client.patch(
                f"{self.server_url}/api/v1/instances/{instance_id}/status",
                headers={"Authorization": f"Bearer {self.token}"},
                json={"status": status},
            )

    async def sync_instance_states(self):
        """同步实例状态"""
        while True:
            try:
                for instance_id, backend in self._backend_by_instance.items():
                    is_healthy = await backend.health_check()
                    status = "running" if is_healthy else "error"
                    await self._update_instance_status(instance_id, status)

                await asyncio.sleep(30)

            except Exception as e:
                logger.error(f"Error syncing states: {e}")
                await asyncio.sleep(30)

    async def stop_all_instances(self):
        """停止所有实例"""
        for instance_id in list(self._backend_by_instance.keys()):
            await self._stop_instance(instance_id)
```

---

## 3. 通信协议

### 3.1 协议选择

| 协议 | 用途 | 优势 | 劣势 |
|------|------|------|------|
| **HTTP/REST** | 管理 API | 简单、易调试 | 性能较低 |
| **gRPC** | 数据传输 | 高性能、双向流 | 复杂度高 |
| **WebSocket** | 日志流、监控 | 实时、双向 | 连接管理复杂 |

**推荐**：
- Server-Worker 管理通信：HTTP/REST（简单可靠）
- Worker 日志流：WebSocket（实时性）
- 推理请求：HTTP（兼容 OpenAI API）

### 3.2 Worker 注册 API

```http
POST /api/v1/workers/register
Authorization: Bearer {worker_token}
Content-Type: application/json

{
  "name": "worker-gpu-01",
  "ip": "192.168.1.100",
  "ifname": "eth0",
  "hostname": "gpu-node-01",
  "cluster_id": 1  // 可选
}

Response:
{
  "id": 1,
  "name": "worker-gpu-01",
  "cluster_id": 1,
  "token": "worker_xxx...",  // 用于后续认证
  "server_config": {
    "heartbeat_interval": 30,
    "metric_interval": 15
  }
}
```

### 3.3 心跳 API

```http
POST /api/v1/workers/{worker_id}/heartbeat
Authorization: Bearer {worker_token}
Content-Type: application/json

{
  "timestamp": "2025-01-14T10:30:00Z",
  "status": "healthy",
  "gpu_count": 4,
  "running_instances": 2
}

Response:
204 No Content
```

### 3.4 状态上报 API

```http
POST /api/v1/workers/{worker_id}/status
Authorization: Bearer {worker_token}
Content-Type: application/json

{
  "gpus": [
    {
      "id": 0,
      "name": "NVIDIA A100",
      "memory_total": 81920,
      "memory_used": 45000,
      "memory_free": 36920,
      "utilization": 85.5,
      "temperature": 72
    }
  ],
  "instances": [
    {
      "instance_id": 1,
      "status": "running",
      "gpu_id": 0,
      "port": 8001
    }
  ],
  "system": {
    "cpu_percent": 45.2,
    "memory_used": 32,
    "memory_total": 128
  }
}

Response:
204 No Content
```

---

## 4. Worker 生命周期

### 4.1 生命周期状态机

```
┌─────────┐    注册    ┌──────────┐    就绪    ┌─────────┐
│  NEW    │ ────────> │REGISTERING│ ────────> │  READY  │
└─────────┘            └──────────┘            └────┬────┘
                                                    │
                     ┌──────────────────────────────┘
                     │
                     ▼
            ┌─────────────────┐
            │    RUNNING      │ ◄────┐
            └────────┬────────┘      │
                     │               │ 资源分配
                     ▼               │
            ┌─────────────────┐      │
            │  ALLOCATING      │ ─────┘
            └────────┬─────────┘
                     │
                     ▼
            ┌─────────────────┐
            │  BUSY           │ ◄────┐
            └────────┬────────┘      │
                     │               │ 资源释放
                     ▼               │
            ┌─────────────────┐      │
            │ RELEASING       │ ─────┘
            └────────┬─────────┘
                     │
                     ▼
            ┌─────────────────┐
            │    READY        │ ─────┐
            └─────────────────┘      │
                     ▲                │
                     │                │ 错误/超时
                     └────────────────┘
```

### 4.2 Worker 状态定义

| 状态 | 说明 | 超时 |
|------|------|------|
| `NEW` | 新创建，未注册 | - |
| `REGISTERING` | 注册中 | 30s |
| `READY` | 就绪，可接受任务 | - |
| `ALLOCATING` | 资源分配中 | 60s |
| `BUSY` | 运行中 | - |
| `RELEASING` | 资源释放中 | 30s |
| `UNHEALTHY` | 不健康 | - |
| `DRAINING` | 排空中，不接受新任务 | - |
| `TERMINATED` | 已终止 | - |

### 4.3 健康检查

```python
# Server 端健康检查
class WorkerHealthChecker:
    """Worker 健康检查器"""

    def __init__(self, timeout: int = 90):
        self.timeout = timeout

    async def check_worker_health(self, worker_id: int) -> bool:
        """检查 Worker 健康状态"""
        from backend.models.database import Worker

        worker = await Worker.get(worker_id)
        if not worker:
            return False

        # 检查最后心跳时间
        if worker.last_heartbeat_at:
            elapsed = datetime.now() - worker.last_heartbeat_at
            if elapsed.total_seconds() > self.timeout:
                return False

        return True

    async def mark_unhealthy_workers(self):
        """标记不健康的 Worker"""
        from backend.models.database import Worker

        workers = await Worker.filter(status="running")
        for worker in workers:
            is_healthy = await self.check_worker_health(worker.id)
            if not is_healthy:
                await worker.update(status="unhealthy")
                logger.warning(f"Worker {worker.id} marked as unhealthy")
```

---

## 5. 部署模式

### 5.1 All-in-One 模式（开发/测试）

```yaml
# docker-compose.yml
version: '3.8'

services:
  # Server + Worker 合并部署
  tokenmachine:
    image: tokenmachine:latest
    ports:
      - "80:80"
      - "8000:8000"
    environment:
      - MODE=all-in-one
      - DATABASE_URL=postgresql://...
    volumes:
      - model-data:/var/lib/tokenmachine/models
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: all
              capabilities: [gpu]
```

### 5.2 分布式模式（生产）

```yaml
# docker-compose.yml
version: '3.8'

services:
  # Server (控制平面)
  server:
    image: tokenmachine-server:latest
    ports:
      - "80:80"
      - "8000:8000"
    environment:
      - MODE=server
      - DATABASE_URL=postgresql://...
    volumes:
      - server-data:/var/lib/tokenmachine
    deploy:
      replicas: 3  # 高可用

  # Worker (数据平面)
  worker:
    image: tokenmachine-worker:latest
    environment:
      - MODE=worker
      - SERVER_URL=http://server:8000
      - WORKER_TOKEN=${WORKER_TOKEN}
    volumes:
      - model-data:/var/lib/tokenmachine/models
    deploy:
      mode: global  # 每节点一个
    depends_on:
      - server
```

### 5.3 Kubernetes 部署

```yaml
# charts/tokenmachine/templates/server-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: tokenmachine-server
spec:
  replicas: 3
  selector:
    matchLabels:
      app: tokenmachine-server
  template:
    metadata:
      labels:
        app: tokenmachine-server
    spec:
      containers:
      - name: server
        image: tokenmachine-server:latest
        ports:
        - containerPort: 8000
        env:
        - name: MODE
          value: "server"
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: tokenmachine-secrets
              key: database-url
---
# charts/tokenmachine/templates/worker-daemonset.yaml
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: tokenmachine-worker
spec:
  selector:
    matchLabels:
      app: tokenmachine-worker
  template:
    metadata:
      labels:
        app: tokenmachine-worker
    spec:
      containers:
      - name: worker
        image: tokenmachine-worker:latest
        env:
        - name: MODE
          value: "worker"
        - name: SERVER_URL
          value: "http://tokenmachine-server:8000"
        - name: WORKER_TOKEN
          valueFrom:
            secretKeyRef:
              name: tokenmachine-secrets
              key: worker-token
        resources:
          limits:
            nvidia.com/gpu: 1
```

---

## 6. 数据库设计

### 6.1 新增表

#### clusters 表

```sql
CREATE TABLE clusters (
    id BIGSERIAL PRIMARY KEY,
    name VARCHAR(255) UNIQUE NOT NULL,
    description TEXT,
    type VARCHAR(50) NOT NULL,  -- docker, kubernetes
    config JSONB,                -- 集群配置
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### workers 表（更新）

```sql
CREATE TABLE workers (
    id BIGSERIAL PRIMARY KEY,
    cluster_id BIGINT REFERENCES clusters(id),
    name VARCHAR(255) NOT NULL,
    ip VARCHAR(45) NOT NULL,
    ifname VARCHAR(50),
    hostname VARCHAR(255),
    status VARCHAR(50) DEFAULT 'registering',
    token_hash VARCHAR(255),
    gpu_count INT DEFAULT 0,
    last_heartbeat_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (cluster_id, name)
);

CREATE INDEX idx_workers_cluster ON workers(cluster_id);
CREATE INDEX idx_workers_status ON workers(status);
```

#### model_instances 表（新增）

```sql
CREATE TABLE model_instances (
    id BIGSERIAL PRIMARY KEY,
    model_id BIGINT NOT NULL REFERENCES models(id) ON DELETE CASCADE,
    worker_id BIGINT NOT NULL REFERENCES workers(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    status VARCHAR(50) DEFAULT 'starting',
    backend VARCHAR(50) NOT NULL,
    config JSONB,
    gpu_ids INT[],
    port INT,
    health_status JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_instances_model ON model_instances(model_id);
CREATE INDEX idx_instances_worker ON model_instances(worker_id);
CREATE INDEX idx_instances_status ON model_instances(status);
```

---

## 7. API 设计

### 7.1 Worker 管理 API

```http
# 列出 Workers
GET /api/v1/workers
Authorization: Bearer {admin_token}

Response:
{
  "items": [
    {
      "id": 1,
      "name": "worker-gpu-01",
      "cluster_id": 1,
      "ip": "192.168.1.100",
      "status": "running",
      "gpu_count": 4,
      "last_heartbeat_at": "2025-01-14T10:30:00Z"
    }
  ]
}

# 获取 Worker 详情
GET /api/v1/workers/{worker_id}
Authorization: Bearer {admin_token}

# 排空 Worker（停止接受新任务）
POST /api/v1/workers/{worker_id}/drain
Authorization: Bearer {admin_token}

# 删除 Worker
DELETE /api/v1/workers/{worker_id}
Authorization: Bearer {admin_token}
```

### 7.2 Model Instance 管理 API

```http
# 列出实例
GET /api/v1/instances
Authorization: Bearer {admin_token}

Response:
{
  "items": [
    {
      "id": 1,
      "model_id": 1,
      "worker_id": 1,
      "name": "qwen2.5-7b-inst-1",
      "status": "running",
      "backend": "vllm",
      "gpu_ids": [0],
      "port": 8001
    }
  ]
}

# 创建实例
POST /api/v1/instances
Authorization: Bearer {admin_token}
Content-Type: application/json

{
  "model_id": 1,
  "worker_id": 1,
  "name": "qwen2.5-7b-inst-1",
  "backend": "vllm",
  "gpu_ids": [0],
  "config": {
    "tensor_parallel_size": 1,
    "max_model_len": 4096
  }
}

# 删除实例
DELETE /api/v1/instances/{instance_id}
Authorization: Bearer {admin_token}
```

---

## 8. 实施计划

### Phase 1: 基础架构（2 周）

- [ ] 创建 `backend/server/` 目录结构
- [ ] 创建 `backend/worker/` 目录结构
- [ ] 实现 Worker 注册 API
- [ ] 实现心跳机制
- [ ] 更新数据库模型（clusters, workers, model_instances）

### Phase 2: Worker 实现（3 周）

- [ ] 实现 Worker 主类
- [ ] 实现 ServeManager
- [ ] 实现状态采集器
- [ ] 实现指标导出器
- [ ] 实现 Worker API（健康检查、日志、代理）

### Phase 3: Server 实现（3 周）

- [ ] 实现 Server 主类
- [ ] 实现 WorkerController
- [ ] 实现 ModelInstanceController
- [ ] 实现健康检查循环
- [ ] 实现 Worker 状态同步

### Phase 4: 集成测试（2 周）

- [ ] Server-Worker 通信测试
- [ ] 注册/心跳测试
- [ ] 实例生命周期测试
- [ ] 故障恢复测试

### Phase 5: 部署支持（1 周）

- [ ] Docker Compose 配置
- [ ] Kubernetes Helm Chart
- [ ] 部署文档

---

**文档版本**: v1.0
**最后更新**: 2025-01-14
