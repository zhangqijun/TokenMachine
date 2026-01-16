# 模型实例管理设计

> Model 与 ModelInstance 分离架构，支持多副本、灰度发布、A/B 测试

---

## 目录

- [1. 概念定义](#1-概念定义)
- [2. 数据模型](#2-数据模型)
- [3. 实例生命周期](#3-实例生命周期)
- [4. 实例调度](#4-实例调度)
- [5. 灰度发布](#5-灰度发布)
- [6. A/B 测试](#6-ab-测试)
- [7. 实施计划](#7-实施计划)

---

## 1. 概念定义

### 1.1 核心概念

| 概念 | 说明 | 示例 |
|------|------|------|
| **Model** | 模型定义，包含元数据、版本信息 | Qwen2.5-7B-Instruct v2.0 |
| **ModelInstance** | 模型实例，Model 在 Worker 上的运行副本 | Worker-1 上的 Qwen 实例 |
| **Deployment** | 部署配置，管理一组 Instance | 生产环境 Qwen 部署 |
| **Replica** | 副本，同一个 Deployment 中的 Instance | 部署中的 3 个副本 |

### 1.2 架构图

```
┌─────────────────────────────────────────────────────────────────┐
│                         Model (模型定义)                          │
│  Name: Qwen2.5-7B-Instruct                                       │
│  Version: v2.0                                                   │
│  Source: huggingface                                            │
│  Path: /models/qwen2.5-7b                                       │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Deployment (部署配置)                        │
│  Name: qwen-prod                                                 │
│  Environment: production                                         │
│  Replicas: 3                                                     │
│  Backend: vllm                                                  │
│  Config: {max_model_len: 4096, ...}                             │
└────────────────────────────┬────────────────────────────────────┘
                             │
        ┌────────────────────┼────────────────────┐
        │                    │                    │
        ▼                    ▼                    ▼
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│ Instance 1   │    │ Instance 2   │    │ Instance 3   │
│ Worker: gpu-1│    │ Worker: gpu-2│    │ Worker: gpu-3│
│ GPU: [0]     │    │ GPU: [0]     │    │ GPU: [0]     │
│ Status: ready │    │ Status: ready │    │ Status: ready│
│ Port: 8001   │    │ Port: 8001   │    │ Port: 8001   │
└──────────────┘    └──────────────┘    └──────────────┘
```

### 1.3 与原设计的区别

| 原设计 | 新设计 | 优势 |
|--------|--------|------|
| Model + Deployment | Model + Deployment + Instance | 更细粒度的管理 |
| Deployment 直接关联 GPU | Instance 作为中间层 | 支持跨节点调度 |
| 单副本概念 | 多副本实例 | 支持负载均衡 |
| 无版本管理 | Instance 绑定 Model 版本 | 支持灰度发布 |

---

## 2. 数据模型

### 2.1 ER 图

```
┌─────────────┐       ┌─────────────────┐       ┌─────────────┐
│   Models    │───────│  Deployments    │───────│  Instances  │
├─────────────┤ 1   N ├─────────────────┤ 1   N ├─────────────┤
│ id (PK)     │       │ id (PK)         │       │ id (PK)     │
│ name        │       │ model_id (FK)   │       │ deployment_id│
│ version     │       │ name            │       │ model_id (FK)│
│ source      │       │ environment     │       │ worker_id(FK)│
│ category    │       │ replicas        │       │ worker_name  │
│ path        │       │ backend         │       │ gpu_ids      │
│ size_gb     │       │ config (JSONB)  │       │ port         │
│ status      │       │ traffic_weights │       │ status       │
│ created_at  │       │ created_at      │       │ health_status│
└─────────────┘       │ updated_at      │       │ created_at   │
                       └─────────────────┘       │ updated_at   │
                                                  └─────────────┘
```

### 2.2 表结构

#### models 表

```sql
CREATE TABLE models (
    id BIGSERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    version VARCHAR(50) NOT NULL,
    source VARCHAR(50) NOT NULL,  -- huggingface, modelscope, local
    category VARCHAR(50) NOT NULL, -- llm, embedding, reranker
    path VARCHAR(1024) NOT NULL,
    size_gb DECIMAL(10, 2),
    status VARCHAR(50) DEFAULT 'downloading',
    download_progress INT DEFAULT 0,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (name, version)
);

CREATE INDEX idx_models_status ON models(status);
CREATE INDEX idx_models_category ON models(category);
```

#### deployments 表

```sql
CREATE TABLE deployments (
    id BIGSERIAL PRIMARY KEY,
    model_id BIGINT NOT NULL REFERENCES models(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    environment VARCHAR(50) NOT NULL,  -- dev, test, staging, prod
    replicas INT DEFAULT 1,
    backend VARCHAR(50) NOT NULL,
    config JSONB,
    traffic_weights JSONB,  -- 灰度发布流量权重
    status VARCHAR(50) DEFAULT 'starting',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (name, environment)
);

CREATE INDEX idx_deployments_env ON deployments(environment);
CREATE INDEX idx_deployments_status ON deployments(status);
```

#### model_instances 表（新增）

```sql
CREATE TABLE model_instances (
    id BIGSERIAL PRIMARY KEY,
    deployment_id BIGINT NOT NULL REFERENCES deployments(id) ON DELETE CASCADE,
    model_id BIGINT NOT NULL REFERENCES models(id) ON DELETE CASCADE,
    worker_id BIGINT REFERENCES workers(id) ON DELETE SET NULL,
    worker_name VARCHAR(255),
    name VARCHAR(255) NOT NULL,
    status VARCHAR(50) DEFAULT 'starting',  -- starting, running, stopping, stopped, error
    backend VARCHAR(50) NOT NULL,
    config JSONB,
    gpu_ids INT[],
    port INT,
    health_status JSONB,  -- {healthy: true, last_check: "...", message: "..."}
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (deployment_id, name)
);

CREATE INDEX idx_instances_deployment ON model_instances(deployment_id);
CREATE INDEX idx_instances_worker ON model_instances(worker_id);
CREATE INDEX idx_instances_status ON model_instances(status);
CREATE INDEX idx_instances_model ON model_instances(model_id);
```

### 2.3 状态定义

#### Model 状态

| 状态 | 说明 |
|------|------|
| `downloading` | 模型下载中 |
| `ready` | 模型就绪，可部署 |
| `error` | 下载失败 |

#### Deployment 状态

| 状态 | 说明 |
|------|------|
| `starting` | 启动中 |
| `running` | 运行中（至少 1 个实例健康）|
| `degraded` | 降级（部分实例不健康）|
| `stopping` | 停止中 |
| `stopped` | 已停止 |
| `error` | 错误 |

#### Instance 状态

| 状态 | 说明 |
|------|------|
| `starting` | 启动中 |
| `running` | 运行中 |
| `stopping` | 停止中 |
| `stopped` | 已停止 |
| `error` | 错误 |

---

## 3. 实例生命周期

### 3.1 状态机

```
     ┌─────────┐
     │  NEW    │ (创建实例)
     └────┬────┘
          │
          ▼
    ┌────────────┐
    │ STARTING   │ ◄────┐
    └─────┬──────┘      │
          │             │
          ▼             │
    ┌────────────┐      │
    │  RUNNING   │ ─────┤ (健康检查失败)
    └─────┬──────┘      │
          │             │
          ▼             │
    ┌────────────┐      │
    │ STOPPING   │ ─────┘
    └─────┬──────┘
          │
          ▼
    ┌────────────┐
    │  STOPPED   │
    └────────────┘
```

### 3.2 生命周期管理

```python
# backend/controllers/instance_controller.py
from typing import List, Optional
from backend.models.database import ModelInstance, Worker, Model, Deployment

class ModelInstanceController:
    """模型实例控制器"""

    def __init__(self, db_session):
        self.db = db_session

    async def create_instance(
        self,
        deployment_id: int,
        worker_id: int,
        gpu_ids: List[int],
        config: dict,
    ) -> ModelInstance:
        """创建模型实例"""
        deployment = await Deployment.get(deployment_id)
        if not deployment:
            raise ValueError("Deployment not found")

        model = await Model.get(deployment.model_id)
        worker = await Worker.get(worker_id)

        instance = ModelInstance(
            deployment_id=deployment_id,
            model_id=model.id,
            worker_id=worker_id,
            worker_name=worker.name,
            name=f"{deployment.name}-{worker.name}",
            backend=deployment.backend,
            config=config,
            gpu_ids=gpu_ids,
            status="starting",
        )
        await instance.save(self.db)

        # 通知 Worker 启动实例
        await self._notify_worker_start(instance)

        return instance

    async def _notify_worker_start(self, instance: ModelInstance):
        """通知 Worker 启动实例"""
        # 通过 Worker API 通知
        # Worker 负责实际启动推理后端
        pass

    async def stop_instance(self, instance_id: int):
        """停止实例"""
        instance = await ModelInstance.get(instance_id)
        if not instance:
            raise ValueError("Instance not found")

        # 更新状态
        instance.status = "stopping"
        await instance.save(self.db)

        # 通知 Worker 停止
        await self._notify_worker_stop(instance)

    async def delete_instance(self, instance_id: int):
        """删除实例"""
        await self.stop_instance(instance_id)
        instance = await ModelInstance.get(instance_id)
        await instance.delete(self.db)

    async def health_check_loop(self):
        """健康检查循环"""
        while True:
            try:
                # 获取运行中的实例
                instances = await ModelInstance.filter(
                    status__in=["starting", "running"]
                )

                for instance in instances:
                    is_healthy = await self._check_instance_health(instance)

                    # 更新状态
                    if is_healthy and instance.status == "starting":
                        instance.status = "running"
                        await instance.save(self.db)
                    elif not is_healthy and instance.status == "running":
                        instance.status = "error"
                        await instance.save(self.db)

                await asyncio.sleep(30)

            except Exception as e:
                logger.error(f"Health check error: {e}")
                await asyncio.sleep(30)

    async def _check_instance_health(self, instance: ModelInstance) -> bool:
        """检查实例健康状态"""
        try:
            # 调用 Worker 健康检查 API
            worker = await Worker.get(instance.worker_id)
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"http://{worker.ip}:{instance.port}/health",
                    timeout=5,
                )
                is_healthy = response.status_code == 200

                # 更新健康状态
                instance.health_status = {
                    "healthy": is_healthy,
                    "last_check": datetime.now().isoformat(),
                    "message": "OK" if is_healthy else "Health check failed",
                }
                await instance.save(self.db)

                return is_healthy

        except Exception as e:
            logger.warning(f"Health check failed for instance {instance.id}: {e}")
            return False

    async def get_deployment_instances(
        self, deployment_id: int
    ) -> List[ModelInstance]:
        """获取部署的所有实例"""
        return await ModelInstance.filter(deployment_id=deployment_id)

    async def scale_deployment(
        self,
        deployment_id: int,
        target_replicas: int,
    ):
        """扩缩容部署"""
        deployment = await Deployment.get(deployment_id)
        current_instances = await self.get_deployment_instances(deployment_id)
        current_count = len(current_instances)

        if target_replicas > current_count:
            # 扩容
            await self._scale_up(deployment, target_replicas - current_count)
        elif target_replicas < current_count:
            # 缩容
            await self._scale_down(deployment, current_count - target_replicas)

    async def _scale_up(self, deployment: Deployment, count: int):
        """扩容"""
        # 调用调度器分配资源
        for _ in range(count):
            # 创建新实例
            pass

    async def _scale_down(self, deployment: Deployment, count: int):
        """缩容"""
        instances = await self.get_deployment_instances(deployment.id)

        # 随机选择要删除的实例
        import random
        to_delete = random.sample(instances, count)

        for instance in to_delete:
            await self.delete_instance(instance.id)
```

---

## 4. 实例调度

### 4.1 调度流程

```
┌─────────────────────────────────────────────────────────────────┐
│  创建部署请求                                                      │
│  Model: Qwen2.5-7B, Replicas: 3, Backend: vllm                 │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│  调度器处理                                                       │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ 1. 获取可用 Workers                                      │   │
│  │ 2. 运行过滤链                                             │   │
│  │ 3. 生成候选配置                                           │   │
│  │ 4. 评分排序                                               │   │
│  │ 5. 选择最优 Workers                                       │   │
│  └─────────────────────────────────────────────────────────┘   │
│                              │                                  │
│                              ▼                                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ 选中 Workers: [worker-1, worker-2, worker-3]             │   │
│  └─────────────────────────────────────────────────────────┘   │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│  创建实例                                                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │ Instance 1   │  │ Instance 2   │  │ Instance 3   │          │
│  │ worker-1     │  │ worker-2     │  │ worker-3     │          │
│  │ GPU: [0]     │  │ GPU: [0]     │  │ GPU: [0]     │          │
│  │ Status:      │  │ Status:      │  │ Status:      │          │
│  │   starting   │  │   starting   │  │   starting   │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
└─────────────────────────────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│  通知 Worker 启动                                                 │
│  worker-1: POST /instances/start                                │
│  worker-2: POST /instances/start                                │
│  worker-3: POST /instances/start                                │
└─────────────────────────────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│  Worker 启动推理后端                                              │
│  worker-1: vLLM started on port 8001                            │
│  worker-2: vLLM started on port 8001                            │
│  worker-3: vLLM started on port 8001                            │
└─────────────────────────────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│  健康检查                                                         │
│  Instance 1: healthy → status: running                         │
│  Instance 2: healthy → status: running                         │
│  Instance 3: healthy → status: running                         │
└─────────────────────────────────────────────────────────────────┘
```

### 4.2 调度与实例创建

```python
# backend/controllers/deployment_controller.py
class DeploymentController:
    """部署控制器"""

    async def create_deployment(
        self,
        model_id: int,
        name: str,
        environment: str,
        replicas: int,
        backend: str,
        config: dict,
    ) -> Deployment:
        """创建部署"""
        # 创建部署记录
        deployment = Deployment(
            model_id=model_id,
            name=name,
            environment=environment,
            replicas=replicas,
            backend=backend,
            config=config,
            status="starting",
        )
        await deployment.save(self.db)

        # 提交调度请求
        from backend.scheduler import ScheduleRequest
        request = ScheduleRequest(
            model=await Model.get(model_id),
            replicas=replicas,
            backend=backend,
            config=config,
        )

        await self.scheduler.submit_schedule(request)

        return deployment

    async def handle_schedule_result(self, result: ScheduleResult):
        """处理调度结果"""
        if not result.success:
            # 调度失败
            logger.error(f"Schedule failed: {result.rejected_workers}")
            return

        # 创建实例
        for candidate in result.candidates:
            await self.instance_controller.create_instance(
                deployment_id=result.deployment_id,
                worker_id=candidate.worker.id,
                gpu_ids=candidate.gpu_ids,
                config=candidate.resource_claim.__dict__,
            )
```

---

## 5. 灰度发布

### 5.1 灰度发布概念

```
Deployment: qwen-prod
├── Instance 1 (v1.0) → 20% 流量
├── Instance 2 (v1.0) → 20% 流量
├── Instance 3 (v2.0) → 60% 流量  ← 新版本
└── Instance 4 (v2.0) → 0% 流量   ← 预热
```

### 5.2 流量权重配置

```python
# backend/models/database.py
class Deployment(Base):
    # ...
    traffic_weights: Dict[str, int] = None  # {"v1.0": 40, "v2.0": 60}

    def get_instance_weights(self) -> Dict[int, int]:
        """获取每个实例的权重"""
        weights = {}

        for instance in self.instances:
            model_version = instance.model.version
            weight = self.traffic_weights.get(model_version, 0)

            # 在同版本实例间平分权重
            same_version_count = sum(
                1 for i in self.instances
                if i.model.version == model_version
            )
            weights[instance.id] = weight // same_version_count

        return weights
```

### 5.3 请求路由

```python
# backend/api/v1/chat.py
import random

async def route_request_to_instance(deployment: Deployment):
    """根据权重路由请求到实例"""
    weights = deployment.get_instance_weights()

    # 加权随机选择
    instance_ids = list(weights.keys())
    weight_values = [weights[i] for i in instance_ids]

    selected_id = random.choices(instance_ids, weights=weight_values)[0]
    return await ModelInstance.get(selected_id)
```

### 5.4 灰度发布流程

```python
# backend/controllers/canary_controller.py
class CanaryController:
    """灰度发布控制器"""

    async def start_canary(
        self,
        deployment_id: int,
        new_model_id: int,
        initial_weight: int = 10,  # 初始权重 10%
    ) -> Deployment:
        """开始灰度发布"""
        deployment = await Deployment.get(deployment_id)
        old_model = await Model.get(deployment.model_id)
        new_model = await Model.get(new_model_id)

        # 设置流量权重
        deployment.traffic_weights = {
            old_model.version: 100 - initial_weight,
            new_model.version: initial_weight,
        }
        await deployment.save(self.db)

        # 创建新版本实例（1 个）
        await self._create_canary_instances(deployment, new_model, count=1)

        return deployment

    async def promote_canary(self, deployment_id: int, weight: int):
        """提升灰度权重"""
        deployment = await Deployment.get(deployment_id)

        # 更新权重
        for version in deployment.traffic_weights:
            if deployment.traffic_weights[version] < 50:  # 假设新版本权重 < 50%
                deployment.traffic_weights[version] = weight
                break

        await deployment.save(self.db)

    async def complete_canary(self, deployment_id: int):
        """完成灰度发布"""
        deployment = await Deployment.get(deployment_id)

        # 新版本获得 100% 流量
        new_version = max(
            deployment.traffic_weights.items(),
            key=lambda x: x[1] if x[0] != deployment.model.version else 0
        )[0]

        deployment.traffic_weights = {new_version: 100}
        await deployment.save(self.db)

        # 停止旧版本实例
        await self._stop_old_instances(deployment)

        # 更新部署的模型 ID
        new_model = await Model.filter(version=new_version).first()
        deployment.model_id = new_model.id
        await deployment.save(self.db)

    async def rollback_canary(self, deployment_id: int):
        """回滚灰度发布"""
        deployment = await Deployment.get(deployment_id)

        # 恢复原版本 100% 流量
        deployment.traffic_weights = {deployment.model.version: 100}
        await deployment.save(self.db)

        # 停止新版本实例
        await self._stop_canary_instances(deployment)
```

---

## 6. A/B 测试

### 6.1 A/B 测试配置

```python
# backend/models/database.py
class ABTest(Base):
    """A/B 测试配置"""
    __tablename__ = "ab_tests"

    id: int = Column(BigInteger, primary_key=True)
    name: str = Column(String(255), nullable=False)
    description: str = Column(Text)

    # A/B 配置
    control_deployment_id: int = Column(BigInteger, ForeignKey("deployments.id"))
    treatment_deployment_id: int = Column(BigInteger, ForeignKey("deployments.id"))
    traffic_split: int = Column(Integer, default=50)  # 控制组流量百分比

    # 状态
    status: str = Column(String(50), default="running")  # running, paused, completed
    start_time: datetime = Column(DateTime)
    end_time: datetime = Column(DateTime, nullable=True)

    # 指标
    metrics: JSON = Column(JSON)  # 指标配置
```

### 6.2 A/B 测试路由

```python
# backend/api/v1/chat.py
async def chat_completion(request: Request):
    """处理聊天请求（支持 A/B 测试）"""
    api_key = await verify_api_key(request)

    # 获取模型部署
    deployment = await get_deployment_by_model(request.model)

    # 检查是否有活跃的 A/B 测试
    ab_test = await get_active_ab_test(deployment.id)

    if ab_test:
        # 根据流量分配选择部署
        if random.random() < ab_test.traffic_split / 100:
            deployment = await Deployment.get(ab_test.control_deployment_id)
        else:
            deployment = await Deployment.get(ab_test.treatment_deployment_id)

        # 记录 A/B 测试指标
        await record_ab_test_metric(ab_test, deployment, request)

    # 路由到实例
    instance = await route_request_to_instance(deployment)

    # 转发请求
    return await forward_to_instance(instance, request)
```

---

## 7. 实施计划

### Phase 1: 数据模型（1 周）

- [ ] 更新数据库 Schema
- [ ] 创建 model_instances 表
- [ ] 创建 ab_tests 表（可选）
- [ ] 编写迁移脚本

### Phase 2: 控制器（2 周）

- [ ] 实现 ModelInstanceController
- [ ] 实现 DeploymentController（更新）
- [ ] 实现健康检查循环
- [ ] 实现扩缩容逻辑

### Phase 3: 灰度发布（1 周）

- [ ] 实现 CanaryController
- [ ] 实现流量权重路由
- [ ] 实现 API 接口

### Phase 4: A/B 测试（1 周，可选）

- [ ] 实现 ABTest 模型
- [ ] 实现 A/B 路由
- [ ] 实现指标收集

### Phase 5: 集成测试（1 周）

- [ ] 端到端测试
- [ ] 灰度发布测试
- [ ] 扩缩容测试

---

**文档版本**: v1.0
**最后更新**: 2025-01-14
