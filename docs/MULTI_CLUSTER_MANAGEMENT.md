# 多集群管理设计

> 管理跨地域、跨环境的 GPU 集群资源

---

## 目录

- [1. 概述](#1-概述)
- [2. 集群抽象](#2-集群抽象)
- [3. 集群类型](#3-集群类型)
- [4. 集群管理](#4-集群管理)
- [5. 资源调度](#5-资源调度)
- [6. 实施计划](#6-实施计划)

---

## 1. 概述

### 1.1 架构图

```
┌─────────────────────────────────────────────────────────────────┐
│                        Server (控制平面)                          │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                   ClusterController                      │   │
│  │                                                         │   │
│  │  • 集群注册                                              │   │
│  │  • 集群健康检查                                          │   │
│  │  • 跨集群调度                                            │   │
│  │  • 资源配额管理                                          │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                              │
                ┌─────────────┼─────────────┐
                │             │             │
                ▼             ▼             ▼
┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐
│  Cluster: prod   │ │  Cluster: staging│ │  Cluster: dev    │
├──────────────────┤ ├──────────────────┤ ├──────────────────┤
│ Type: kubernetes │ │ Type: docker      │ │ Type: docker      │
│ Region: us-east  │ │ Region: us-east  │ │ Region: us-west  │
│ Workers: 16      │ │ Workers: 4       │ │ Workers: 2       │
│ GPUs: 64         │ │ GPUs: 8          │ │ GPUs: 4          │
└────────┬─────────┘ └────────┬─────────┘ └────────┬─────────┘
         │                    │                    │
    ┌────┴────┐          ┌────┴────┐          ┌────┴────┐
    ▼         ▼          ▼         ▼          ▼         ▼
┌──────┐ ┌──────┐    ┌──────┐ ┌──────┐    ┌──────┐ ┌──────┐
│ W-1  │ │ W-2  │    │ W-5  │ │ W-6  │    │ W-9  │ │ W-10 │
│4 GPU │ │4 GPU │    │2 GPU │ │2 GPU │    │2 GPU │ │2 GPU │
└──────┘ └──────┘    └──────┘ └──────┘    └──────┘ └──────┘
```

### 1.2 集群类型

| 类型 | 说明 | 适用场景 |
|------|------|----------|
| **Docker** | Docker Compose 部署 | 小规模、边缘节点 |
| **Kubernetes** | K8s 集群 | 大规模、云原生 |
| **Standalone** | 独立进程 | 开发、测试 |

### 1.3 设计目标

| 目标 | 说明 |
|------|------|
| **跨地域** | 支持多地域集群部署 |
| **资源隔离** | 集群间资源隔离 |
| **统一调度** | 跨集群资源调度 |
| **高可用** | 集群故障自动转移 |
| **配额管理** | 集群级资源配额 |

---

## 2. 集群抽象

### 2.1 数据模型

```sql
-- 集群表
CREATE TABLE clusters (
    id BIGSERIAL PRIMARY KEY,
    name VARCHAR(255) UNIQUE NOT NULL,
    description TEXT,
    type VARCHAR(50) NOT NULL,  -- docker, kubernetes, standalone
    config JSONB,                -- 集群配置

    -- 配额
    gpu_quota INT,               -- GPU 配额
    worker_quota INT,            -- Worker 配额

    -- 状态
    status VARCHAR(50) DEFAULT 'active',  -- active, inactive, error
    last_health_check_at TIMESTAMP,

    -- 标签
    labels JSONB,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_clusters_status ON clusters(status);
CREATE INDEX idx_clusters_type ON clusters(type);

-- 集群使用统计
CREATE TABLE cluster_usage (
    id BIGSERIAL PRIMARY KEY,
    cluster_id BIGINT REFERENCES clusters(id) ON DELETE CASCADE,
    gpu_used INT DEFAULT 0,
    gpu_total INT DEFAULT 0,
    worker_count INT DEFAULT 0,
    instance_count INT DEFAULT 0,
    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_cluster_usage_cluster ON cluster_usage(cluster_id);
CREATE INDEX idx_cluster_usage_recorded ON cluster_usage(recorded_at);
```

### 2.2 集群配置

```python
# backend/models/database.py
from typing import Optional, Dict
from sqlalchemy import Column, BigInteger, String, Text, JSON, DateTime, Integer
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class Cluster(Base):
    __tablename__ = "clusters"

    id: int = Column(BigInteger, primary_key=True)
    name: str = Column(String(255), unique=True, nullable=False)
    description: str = Column(Text, nullable=True)
    type: str = Column(String(50), nullable=False)  # docker, kubernetes
    config: dict = Column(JSON, nullable=True)

    # 配额
    gpu_quota: int = Column(Integer, nullable=True)
    worker_quota: int = Column(Integer, nullable=True)

    # 状态
    status: str = Column(String(50), default="active")
    last_health_check_at: datetime = Column(DateTime, nullable=True)

    # 标签
    labels: dict = Column(JSON, nullable=True)

    created_at: datetime = Column(DateTime, default=datetime.utcnow)
    updated_at: datetime = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def get_config(self, key: str, default=None):
        """获取配置值"""
        if self.config is None:
            return default
        return self.config.get(key, default)

    @property
    def is_healthy(self) -> bool:
        """是否健康"""
        return self.status == "active"

    @property
    def resource_usage(self) -> dict:
        """资源使用情况"""
        return {
            "gpu_used": self.gpu_used,
            "gpu_total": self.gpu_total,
            "gpu_available": self.gpu_quota - self.gpu_used if self.gpu_quota else None,
            "worker_count": self.worker_count,
        }
```

---

## 3. 集群类型

### 3.1 Docker 集群

```python
# backend/cluster/docker_cluster.py
from typing import List, Dict
from backend.cluster.base import BaseClusterProvider

class DockerClusterProvider(BaseClusterProvider):
    """Docker 集群提供者"""

    type = "docker"

    def __init__(self, cluster: Cluster):
        self.cluster = cluster
        self.docker_host = cluster.get_config("docker_host", "unix:///var/run/docker.sock")

    async def discover_workers(self) -> List[Dict]:
        """发现 Docker Workers"""
        import docker

        client = docker.DockerClient(base_url=self.docker_host)

        workers = []
        containers = client.containers.list(
            filters={"label": "tokenmachine.worker=true"}
        )

        for container in containers:
            labels = container.labels
            workers.append({
                "name": labels.get("tokenmachine.worker.name"),
                "ip": self._get_container_ip(container),
                "status": "running" if container.status == "running" else "stopped",
            })

        return workers

    def _get_container_ip(self, container) -> str:
        """获取容器 IP"""
        try:
            return container.attrs["NetworkSettings"]["IPAddress"]
        except:
            return "unknown"

    async def add_worker(
        self,
        name: str,
        gpu_ids: List[int],
        config: dict,
    ) -> dict:
        """添加 Worker"""
        import docker

        client = docker.DockerClient(base_url=self.docker_host)

        # 启动 Worker 容器
        container = client.containers.run(
            "tokenmachine-worker:latest",
            name=name,
            detach=True,
            labels={
                "tokenmachine.worker": "true",
                "tokenmachine.worker.name": name,
            },
            environment={
                "TOKENMACHINE_SERVER_URL": config.get("server_url"),
                "TOKENMACHINE_WORKER_TOKEN": config.get("worker_token"),
            },
            device_requests=[
                docker.types.DeviceRequest(
                    device_ids=[str(i) for i in gpu_ids],
                    capabilities=[["gpu"]],
                )
            ] if gpu_ids else None,
        )

        return {
            "container_id": container.id,
            "name": name,
            "status": "starting",
        }

    async def remove_worker(self, worker_name: str):
        """移除 Worker"""
        import docker

        client = docker.DockerClient(base_url=self.docker_host)
        container = client.containers.get(worker_name)
        container.stop()
        container.remove()

    async def get_cluster_metrics(self) -> dict:
        """获取集群指标"""
        import docker

        client = docker.DockerClient(base_url=self.docker_host)

        workers = await self.discover_workers()
        gpu_total = 0
        gpu_used = 0

        for worker in workers:
            container = client.containers.get(worker["name"])
            gpu_count = int(container.labels.get("tokenmachine.worker.gpu_count", 0))
            gpu_total += gpu_count

            if worker["status"] == "running":
                gpu_used += gpu_count

        return {
            "worker_count": len(workers),
            "gpu_total": gpu_total,
            "gpu_used": gpu_used,
            "gpu_available": gpu_total - gpu_used,
        }
```

### 3.2 Kubernetes 集群

```python
# backend/cluster/kubernetes_cluster.py
from typing import List, Dict
from backend.cluster.base import BaseClusterProvider

class KubernetesClusterProvider(BaseClusterProvider):
    """Kubernetes 集群提供者"""

    type = "kubernetes"

    def __init__(self, cluster: Cluster):
        self.cluster = cluster
        self.kubeconfig = cluster.get_config("kubeconfig")
        self.namespace = cluster.get_config("namespace", "tokenmachine")

        # 初始化 Kubernetes 客户端
        from kubernetes import client, config
        if self.kubeconfig:
            config.load_kube_config(config_file=self.kubeconfig)
        else:
            config.load_incluster_config()

        self.core_v1 = client.CoreV1Api()
        self.apps_v1 = client.AppsV1Api()

    async def discover_workers(self) -> List[Dict]:
        """发现 Kubernetes Workers (Pods)"""
        pods = self.core_v1.list_namespaced_pod(
            namespace=self.namespace,
            label_selector="app=tokenmachine-worker",
        )

        workers = []
        for pod in pods.items:
            workers.append({
                "name": pod.metadata.name,
                "ip": pod.status.pod_ip,
                "status": self._map_pod_status(pod.status.phase),
                "node_name": pod.spec.node_name,
            })

        return workers

    def _map_pod_status(self, phase: str) -> str:
        """映射 Pod 状态到 Worker 状态"""
        mapping = {
            "Running": "running",
            "Pending": "starting",
            "Failed": "error",
            "Succeeded": "stopped",
        }
        return mapping.get(phase, "unknown")

    async def add_worker(
        self,
        name: str,
        gpu_ids: List[int],
        config: dict,
    ) -> dict:
        """添加 Worker (Deployment)"""
        from kubernetes import client

        # 创建 Deployment
        deployment = client.V1Deployment(
            metadata=client.V1ObjectMeta(
                name=name,
                labels={"app": "tokenmachine-worker"},
            ),
            spec=client.V1DeploymentSpec(
                replicas=1,
                selector=client.V1LabelSelector(
                    match_labels={"app": "tokenmachine-worker"},
                ),
                template=client.V1PodTemplateSpec(
                    metadata=client.V1ObjectMeta(
                        labels={"app": "tokenmachine-worker"},
                    ),
                    spec=client.V1PodSpec(
                        containers=[client.V1Container(
                            name="worker",
                            image="tokenmachine-worker:latest",
                            env=[
                                client.V1EnvVar(
                                    name="TOKENMACHINE_SERVER_URL",
                                    value=config.get("server_url"),
                                ),
                                client.V1EnvVar(
                                    name="TOKENMACHINE_WORKER_TOKEN",
                                    value=config.get("worker_token"),
                                ),
                            ],
                            resources=client.V1ResourceRequirements(
                                requests={
                                    "nvidia.com/gpu": str(len(gpu_ids)) if gpu_ids else None,
                                },
                                limits={
                                    "nvidia.com/gpu": str(len(gpu_ids)) if gpu_ids else None,
                                },
                            ) if gpu_ids else None,
                        )],
                    ),
                ),
            ),
        )

        self.apps_v1.create_namespaced_deployment(
            namespace=self.namespace,
            body=deployment,
        )

        return {
            "deployment_name": name,
            "status": "starting",
        }

    async def remove_worker(self, worker_name: str):
        """移除 Worker"""
        from kubernetes import client

        self.apps_v1.delete_namespaced_deployment(
            name=worker_name,
            namespace=self.namespace,
        )

    async def get_cluster_metrics(self) -> dict:
        """获取集群指标"""
        workers = await self.discover_workers()

        # 获取节点资源
        nodes = self.core_v1.list_node()
        gpu_total = 0
        gpu_used = 0

        for node in nodes.items:
            # 解析 GPU 资源
            allocatable = node.status.allocatable or {}
            capacity = node.status.capacity or {}

            nvidia_gpu = int(capacity.get("nvidia.com/gpu", 0))
            gpu_total += nvidia_gpu

        # 统计运行的 Worker
        running_workers = [w for w in workers if w["status"] == "running"]
        gpu_used = sum(
            int(w.get("gpu_count", 0))
            for w in running_workers
        )

        return {
            "worker_count": len(workers),
            "gpu_total": gpu_total,
            "gpu_used": gpu_used,
            "gpu_available": gpu_total - gpu_used,
        }
```

---

## 4. 集群管理

### 4.1 集群控制器

```python
# backend/controllers/cluster_controller.py
from typing import List, Optional
from backend.models.database import Cluster, Worker

class ClusterController:
    """集群控制器"""

    def __init__(self, db_session):
        self.db = db_session
        self._providers = {}

    def _get_provider(self, cluster: Cluster):
        """获取集群提供者"""
        from backend.cluster.docker_cluster import DockerClusterProvider
        from backend.cluster.kubernetes_cluster import KubernetesClusterProvider

        if cluster.type not in self._providers:
            if cluster.type == "docker":
                self._providers[cluster.type] = DockerClusterProvider(cluster)
            elif cluster.type == "kubernetes":
                self._providers[cluster.type] = KubernetesClusterProvider(cluster)
            else:
                raise ValueError(f"Unknown cluster type: {cluster.type}")

        return self._providers[cluster.type]

    async def create_cluster(
        self,
        name: str,
        type: str,
        description: str = None,
        config: dict = None,
        gpu_quota: int = None,
        labels: dict = None,
    ) -> Cluster:
        """创建集群"""
        cluster = Cluster(
            name=name,
            type=type,
            description=description,
            config=config or {},
            gpu_quota=gpu_quota,
            labels=labels or {},
            status="active",
        )
        await cluster.save(self.db)

        # 初始化集群
        provider = self._get_provider(cluster)
        await provider.initialize()

        return cluster

    async def update_cluster(
        self,
        cluster_id: int,
        **kwargs
    ) -> Cluster:
        """更新集群"""
        cluster = await Cluster.get(cluster_id)
        if not cluster:
            raise ValueError("Cluster not found")

        for key, value in kwargs.items():
            setattr(cluster, key, value)

        await cluster.save(self.db)
        return cluster

    async def delete_cluster(self, cluster_id: int):
        """删除集群"""
        cluster = await Cluster.get(cluster_id)
        if not cluster:
            raise ValueError("Cluster not found")

        # 检查是否有 Worker
        workers = await Worker.filter(cluster_id=cluster_id)
        if workers:
            raise ValueError("Cluster has workers, cannot delete")

        await cluster.delete(self.db)

    async def discover_workers(self, cluster_id: int) -> List[dict]:
        """发现集群中的 Workers"""
        cluster = await Cluster.get(cluster_id)
        provider = self._get_provider(cluster)
        return await provider.discover_workers()

    async def add_worker(
        self,
        cluster_id: int,
        name: str,
        gpu_ids: List[int],
        config: dict,
    ) -> dict:
        """添加 Worker 到集群"""
        cluster = await Cluster.get(cluster_id)
        provider = self._get_provider(cluster)
        return await provider.add_worker(name, gpu_ids, config)

    async def remove_worker(self, cluster_id: int, worker_name: str):
        """从集群移除 Worker"""
        cluster = await Cluster.get(cluster_id)
        provider = self._get_provider(cluster)
        await provider.remove_worker(worker_name)

    async def get_cluster_metrics(self, cluster_id: int) -> dict:
        """获取集群指标"""
        cluster = await Cluster.get(cluster_id)
        provider = self._get_provider(cluster)
        return await provider.get_cluster_metrics()

    async def health_check_loop(self):
        """健康检查循环"""
        while True:
            try:
                clusters = await Cluster.filter(status="active")

                for cluster in clusters:
                    try:
                        metrics = await self.get_cluster_metrics(cluster.id)

                        # 更新健康检查时间
                        cluster.last_health_check_at = datetime.now()
                        await cluster.save(self.db)

                        # 记录使用统计
                        await self._record_usage(cluster.id, metrics)

                    except Exception as e:
                        logger.error(f"Health check failed for cluster {cluster.id}: {e}")
                        cluster.status = "error"
                        await cluster.save(self.db)

                await asyncio.sleep(60)

            except Exception as e:
                logger.error(f"Health check loop error: {e}")
                await asyncio.sleep(60)

    async def _record_usage(self, cluster_id: int, metrics: dict):
        """记录集群使用情况"""
        from backend.models.database import ClusterUsage

        usage = ClusterUsage(
            cluster_id=cluster_id,
            gpu_used=metrics.get("gpu_used", 0),
            gpu_total=metrics.get("gpu_total", 0),
            worker_count=metrics.get("worker_count", 0),
        )
        await usage.save(self.db)

    async def get_cluster_summary(self, cluster_id: int) -> dict:
        """获取集群摘要"""
        cluster = await Cluster.get(cluster_id)
        metrics = await self.get_cluster_metrics(cluster_id)
        workers = await Worker.filter(cluster_id=cluster_id)

        return {
            "cluster": {
                "id": cluster.id,
                "name": cluster.name,
                "type": cluster.type,
                "status": cluster.status,
                "labels": cluster.labels,
            },
            "metrics": metrics,
            "workers": [
                {
                    "id": w.id,
                    "name": w.name,
                    "status": w.status,
                    "gpu_count": w.gpu_count,
                }
                for w in workers
            ],
        }

    async def list_clusters(
        self,
        status: str = None,
        type: str = None,
    ) -> List[Cluster]:
        """列出集群"""
        filters = {}
        if status:
            filters["status"] = status
        if type:
            filters["type"] = type

        return await Cluster.filter(**filters)
```

### 4.2 集群 API

```python
# backend/api/v1/clusters.py
from fastapi import APIRouter, Depends, HTTPException
from typing import List

router = APIRouter(prefix="/clusters", tags=["clusters"])

@router.get("")
async def list_clusters(
    status: str = None,
    type: str = None,
    controller: ClusterController = Depends(get_cluster_controller),
):
    """列出集群"""
    clusters = await controller.list_clusters(status=status, type=type)
    return {
        "items": [
            {
                "id": c.id,
                "name": c.name,
                "type": c.type,
                "status": c.status,
                "gpu_quota": c.gpu_quota,
                "labels": c.labels,
            }
            for c in clusters
        ]
    }

@router.get("/{cluster_id}")
async def get_cluster(
    cluster_id: int,
    controller: ClusterController = Depends(get_cluster_controller),
):
    """获取集群详情"""
    summary = await controller.get_cluster_summary(cluster_id)
    return summary

@router.post("")
async def create_cluster(
    name: str,
    type: str,
    description: str = None,
    config: dict = None,
    gpu_quota: int = None,
    labels: dict = None,
    controller: ClusterController = Depends(get_cluster_controller),
):
    """创建集群"""
    cluster = await controller.create_cluster(
        name=name,
        type=type,
        description=description,
        config=config,
        gpu_quota=gpu_quota,
        labels=labels,
    )
    return cluster

@router.post("/{cluster_id}/workers")
async def add_cluster_worker(
    cluster_id: int,
    name: str,
    gpu_ids: List[int],
    config: dict,
    controller: ClusterController = Depends(get_cluster_controller),
):
    """添加 Worker 到集群"""
    result = await controller.add_worker(
        cluster_id=cluster_id,
        name=name,
        gpu_ids=gpu_ids,
        config=config,
    )
    return result

@router.delete("/{cluster_id}/workers/{worker_name}")
async def remove_cluster_worker(
    cluster_id: int,
    worker_name: str,
    controller: ClusterController = Depends(get_cluster_controller),
):
    """从集群移除 Worker"""
    await controller.remove_worker(cluster_id, worker_name)
    return {"success": True}
```

---

## 5. 资源调度

### 5.1 跨集群调度

```python
# backend/scheduler/policies/worker_filters/cluster_filter.py
from backend.scheduler.policies.base import WorkerFilter, ScheduleRequest, Worker

class MultiClusterFilter(WorkerFilter):
    """多集群过滤器"""

    def __init__(
        self,
        preferred_clusters: List[int] = None,
        cluster_affinity: dict = None,  # {"region": "us-east"}
    ):
        self.preferred_clusters = preferred_clusters or []
        self.cluster_affinity = cluster_affinity or {}

    async def filter(
        self,
        workers: List[Worker],
        request: ScheduleRequest,
    ) -> Tuple[List[Worker], List[str]]:
        messages = []

        # 优先使用指定集群
        if self.preferred_clusters:
            filtered = [w for w in workers if w.cluster_id in self.preferred_clusters]
            if filtered:
                return filtered, messages

        # 根据亲和性过滤
        if self.cluster_affinity:
            from backend.controllers.cluster_controller import ClusterController
            cluster_ctrl = ClusterController(get_db())

            filtered = []
            for worker in workers:
                cluster = await Cluster.get(worker.cluster_id)
                if not cluster:
                    continue

                # 检查标签匹配
                match = True
                for key, value in self.cluster_affinity.items():
                    if cluster.labels.get(key) != value:
                        match = False
                        break

                if match:
                    filtered.append(worker)
                else:
                    messages.append(
                        f"Worker '{worker.name}' cluster labels don't match affinity"
                    )

            return filtered, messages

        return workers, messages
```

### 5.2 集群配额管理

```python
# backend/scheduler/policies/worker_filters/quota_filter.py
class QuotaFilter(WorkerFilter):
    """配额过滤器"""

    async def filter(
        self,
        workers: List[Worker],
        request: ScheduleRequest,
    ) -> Tuple[List[Worker], List[str]]:
        from backend.controllers.cluster_controller import ClusterController
        cluster_ctrl = ClusterController(get_db())

        messages = []
        filtered = []

        for worker in workers:
            cluster = await Cluster.get(worker.cluster_id)
            if not cluster:
                continue

            # 检查配额
            if cluster.gpu_quota:
                metrics = await cluster_ctrl.get_cluster_metrics(cluster.id)
                if metrics["gpu_used"] >= cluster.gpu_quota:
                    messages.append(
                        f"Worker '{worker.name}' cluster {cluster.name} over quota"
                    )
                    continue

            filtered.append(worker)

        return filtered, messages
```

---

## 6. 实施计划

### Phase 1: 基础设施（1 周）

- [ ] 创建集群数据模型
- [ ] 创建集群使用统计表
- [ ] 编写迁移脚本

### Phase 2: 集群提供者（2 周）

- [ ] 实现 BaseClusterProvider
- [ ] 实现 DockerClusterProvider
- [ ] 实现 KubernetesClusterProvider

### Phase 3: 控制器（1 周）

- [ ] 实现 ClusterController
- [ ] 实现健康检查循环
- [ ] 实现使用统计

### Phase 4: API（1 周）

- [ ] 实现集群管理 API
- [ ] 实现 Worker 管理接口

### Phase 5: 调度集成（1 周）

- [ ] 实现 MultiClusterFilter
- [ ] 实现 QuotaFilter
- [ ] 集成到调度器

### Phase 6: 测试（1 周）

- [ ] 集成测试
- [ ] 多集群调度测试
- [ ] 配额管理测试

---

**文档版本**: v1.0
**最后更新**: 2025-01-14
