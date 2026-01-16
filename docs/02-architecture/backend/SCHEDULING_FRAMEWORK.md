# 调度策略框架设计

> 基于 GPUStack 调度系统分析，设计可插拔的调度策略框架

---

## 目录

- [1. 设计概述](#1-设计概述)
- [2. 核心抽象](#2-核心抽象)
- [3. 过滤器设计](#3-过滤器设计)
- [4. 选择器设计](#4-选择器设计)
- [5. 评分器设计](#5-评分器设计)
- [6. 调度器实现](#6-调度器实现)
- [7. 策略配置](#7-策略配置)
- [8. 实施计划](#8-实施计划)

---

## 1. 设计概述

### 1.1 调度流程

```
┌─────────────────────────────────────────────────────────────────┐
│                        调度请求                                  │
│  Model: Qwen2.5-7B, Replicas: 2, GPU Memory: 16GB               │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                      1. WorkerFilterChain                        │
│  过滤不合适的 Worker                                              │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐      │
│  │ Cluster  │→│  Status  │→│   GPU    │→│ Backend  │      │
│  │ Filter   │  │ Filter   │  │ Filter   │  │ Filter   │      │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘      │
│                              │                                    │
│                              ▼                                    │
│                      可用 Workers: [3, 5, 7, 9]                  │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                      2. CandidateSelector                        │
│  为每个 Worker 选择候选配置                                        │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ Worker 3: GPU=[0,1], offload_layers=28, score=0.8     │   │
│  │ Worker 5: GPU=[2], offload_layers=20, score=0.7       │   │
│  │ Worker 7: GPU=[3,4], offload_layers=32, score=0.9    │   │
│  │ Worker 9: GPU=[5], offload_layers=18, score=0.6      │   │
│  └─────────────────────────────────────────────────────────┘   │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                      3. PlacementScorer                          │
│  对候选进行评分和排序                                              │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ 1. Worker 7: score=0.95 (高可用 + 资源匹配)             │   │
│  │ 2. Worker 3: score=0.85 (资源匹配)                      │   │
│  │ 3. Worker 5: score=0.75 (低负载)                        │   │
│  │ 4. Worker 9: score=0.65 (低优先级)                      │   │
│  └─────────────────────────────────────────────────────────┘   │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                      4. 最终决策                                  │
│  选择最优的 2 个 Workers 部署 2 个副本                             │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ Instance 1 → Worker 7, GPU=[3,4]                       │   │
│  │ Instance 2 → Worker 3, GPU=[0,1]                       │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

### 1.2 设计原则

| 原则 | 说明 |
|------|------|
| **可插拔** | 每个策略组件都可独立替换 |
| **可组合** | 多个过滤器可以串联使用 |
| **可扩展** | 新增策略无需修改核心代码 |
| **可配置** | 策略参数可通过配置调整 |
| **可观测** | 每步决策都有日志记录 |

### 1.3 核心组件

```
backend/scheduler/
├── __init__.py
├── scheduler.py           # 主调度器
├── policies/              # 策略模块
│   ├── __init__.py
│   ├── base.py            # 抽象基类
│   ├── worker_filters/    # Worker 过滤器
│   │   ├── __init__.py
│   │   ├── cluster_filter.py
│   │   ├── status_filter.py
│   │   ├── gpu_filter.py
│   │   ├── label_filter.py
│   │   └── backend_filter.py
│   ├── candidate_selectors/  # 候选选择器
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── vllm_selector.py
│   │   ├── sglang_selector.py
│   │   └── gguf_selector.py
│   └── scorers/           # 评分器
│       ├── __init__.py
│       ├── placement_scorer.py
│       └── offload_scorer.py
└── config.py              # 策略配置
```

---

## 2. 核心抽象

### 2.1 基础数据结构

```python
# backend/scheduler/policies/base.py
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Dict, Optional, Tuple
from backend.models.database import Worker, Model, ModelInstance

@dataclass
class ComputeResource:
    """计算资源需求"""
    vram_mb: int              # 显存需求 (MB)
    ram_mb: int               # 内存需求 (MB)
    gpu_count: int            # GPU 数量
    tensor_parallel: int = 1  # 张量并行度

@dataclass
class ModelInstanceCandidate:
    """模型实例候选"""
    worker: Worker
    gpu_ids: List[int]
    resource_claim: ComputeResource
    gpu_type: Optional[str] = None
    score: Optional[float] = None
    overcommit: bool = False

    # 配置
    offload_layers: Optional[int] = None
    tensor_split: Optional[List[int]] = None

    def to_log_string(self) -> str:
        """转换为日志字符串"""
        parts = [
            f"worker: '{self.worker.name}'",
            f"gpus: {self.gpu_ids}",
        ]
        if self.offload_layers is not None:
            parts.append(f"offload_layers: {self.offload_layers}")
        if self.tensor_split:
            parts.append(f"tensor_split: {self.tensor_split}")
        if self.overcommit:
            parts.append("overcommit: true")
        return ", ".join(parts)


@dataclass
class ScheduleRequest:
    """调度请求"""
    model: Model
    replicas: int = 1
    backend: str = "vllm"
    config: Dict = None
    cluster_id: Optional[int] = None
    worker_ids: Optional[List[int]] = None  # 指定 Workers

    def __post_init__(self):
        if self.config is None:
            self.config = {}


@dataclass
class ScheduleResult:
    """调度结果"""
    success: bool
    candidates: List[ModelInstanceCandidate]
    rejected_workers: List[Tuple[Worker, str]]  # (worker, reason)
    placement: Optional[List[Tuple[int, ModelInstanceCandidate]]] = None
```

### 2.2 Worker 过滤器接口

```python
class WorkerFilter(ABC):
    """Worker 过滤器基类"""

    @abstractmethod
    async def filter(
        self,
        workers: List[Worker],
        request: ScheduleRequest,
    ) -> Tuple[List[Worker], List[str]]:
        """
        过滤 Workers

        Args:
            workers: 候选 Worker 列表
            request: 调度请求

        Returns:
            (通过的 Workers, 拒绝原因列表)
        """
        pass

    def _add_rejection(
        self,
        messages: List[str],
        worker: Worker,
        reason: str,
    ):
        """记录拒绝原因"""
        messages.append(f"Worker '{worker.name}': {reason}")


class WorkerFilterChain:
    """Worker 过滤器链"""

    def __init__(self, filters: List[WorkerFilter]):
        self.filters = filters

    async def filter(
        self,
        workers: List[Worker],
        request: ScheduleRequest,
    ) -> Tuple[List[Worker], List[str]]:
        """
        依次应用所有过滤器

        Args:
            workers: 初始 Worker 列表
            request: 调度请求

        Returns:
            (最终通过的 Workers, 所有拒绝原因)
        """
        candidates = workers
        all_messages = []

        for filter_obj in self.filters:
            candidates, messages = await filter_obj.filter(
                candidates, request
            )
            all_messages.extend(messages)

            # 没有候选了，提前终止
            if not candidates:
                break

        return candidates, all_messages
```

### 2.3 候选选择器接口

```python
class CandidateSelector(ABC):
    """候选选择器基类"""

    @abstractmethod
    async def select(
        self,
        workers: List[Worker],
        request: ScheduleRequest,
    ) -> List[ModelInstanceCandidate]:
        """
        为每个 Worker 选择候选配置

        Args:
            workers: 可用 Worker 列表
            request: 调度请求

        Returns:
            候选列表（可能包含多个候选/Worker）
        """
        pass

    @abstractmethod
    def supports_backend(self, backend: str) -> bool:
        """是否支持指定后端"""
        pass
```

### 2.4 评分器接口

```python
class CandidateScorer(ABC):
    """候选评分器基类"""

    @abstractmethod
    async def score(
        self,
        candidates: List[ModelInstanceCandidate],
        request: ScheduleRequest,
    ) -> List[ModelInstanceCandidate]:
        """
        对候选进行评分

        Args:
            candidates: 候选列表
            request: 调度请求

        Returns:
            评分后的候选列表（score 字段已填充）
        """
        pass
```

---

## 3. 过滤器设计

### 3.1 集群过滤器

```python
# backend/scheduler/policies/worker_filters/cluster_filter.py
from typing import List, Tuple
from backend.scheduler.policies.base import WorkerFilter, ScheduleRequest, Worker

class ClusterFilter(WorkerFilter):
    """集群过滤器 - 根据集群 ID 过滤"""

    def __init__(self, cluster_id: Optional[int] = None):
        self.cluster_id = cluster_id

    async def filter(
        self,
        workers: List[Worker],
        request: ScheduleRequest,
    ) -> Tuple[List[Worker], List[str]]:
        messages = []

        # 请求指定的集群优先
        target_cluster = request.cluster_id or self.cluster_id

        if target_cluster is None:
            return workers, messages

        filtered = []
        for worker in workers:
            if worker.cluster_id == target_cluster:
                filtered.append(worker)
            else:
                messages.append(
                    f"Worker '{worker.name}' is in cluster {worker.cluster_id}, "
                    f"expected {target_cluster}"
                )

        return filtered, messages
```

### 3.2 状态过滤器

```python
# backend/scheduler/policies/worker_filters/status_filter.py
from typing import List, Tuple
from backend.scheduler.policies.base import WorkerFilter, ScheduleRequest, Worker

class StatusFilter(WorkerFilter):
    """状态过滤器 - 过滤不健康的 Worker"""

    # 允许的状态
    ALLOWED_STATUSES = {"ready", "busy"}

    # 超时时间（秒）
    HEARTBEAT_TIMEOUT = 90

    async def filter(
        self,
        workers: List[Worker],
        request: ScheduleRequest,
    ) -> Tuple[List[Worker], List[str]]:
        messages = []
        filtered = []
        now = datetime.now()

        for worker in workers:
            # 检查状态
            if worker.status not in self.ALLOWED_STATUSES:
                messages.append(
                    f"Worker '{worker.name}' status is {worker.status}, "
                    f"expected one of {self.ALLOWED_STATUSES}"
                )
                continue

            # 检查心跳
            if worker.last_heartbeat_at:
                elapsed = (now - worker.last_heartbeat_at).total_seconds()
                if elapsed > self.HEARTBEAT_TIMEOUT:
                    messages.append(
                        f"Worker '{worker.name}' last heartbeat {elapsed:.0f}s ago"
                    )
                    continue

            filtered.append(worker)

        return filtered, messages
```

### 3.3 GPU 过滤器

```python
# backend/scheduler/policies/worker_filters/gpu_filter.py
from typing import List, Tuple
from backend.scheduler.policies.base import (
    WorkerFilter,
    ScheduleRequest,
    Worker,
    ComputeResource,
)

class GPUFilter(WorkerFilter):
    """GPU 过滤器 - 检查 GPU 资源是否满足需求"""

    def __init__(
        self,
        min_memory_mb: Optional[int] = None,
        min_count: int = 1,
        require_same_type: bool = False,
    ):
        self.min_memory_mb = min_memory_mb
        self.min_count = min_count
        self.require_same_type = require_same_type

    async def filter(
        self,
        workers: List[Worker],
        request: ScheduleRequest,
    ) -> Tuple[List[Worker], List[str]]:
        messages = []
        filtered = []

        # 计算资源需求
        required = self._compute_required(request)

        for worker in workers:
            # 检查 GPU 数量
            if worker.gpu_count < self.min_count:
                messages.append(
                    f"Worker '{worker.name}' has {worker.gpu_count} GPUs, "
                    f"required at least {self.min_count}"
                )
                continue

            # 检查显存
            if self.min_memory_mb:
                available_memory = self._get_available_memory(worker)
                if available_memory < required.vram_mb:
                    messages.append(
                        f"Worker '{worker.name}' has {available_memory}MB available, "
                        f"required {required.vram_mb}MB"
                    )
                    continue

            # 检查 GPU 类型一致性
            if self.require_same_type:
                gpu_types = self._get_gpu_types(worker)
                if len(set(gpu_types)) > 1:
                    messages.append(
                        f"Worker '{worker.name}' has mixed GPU types: {gpu_types}"
                    )
                    continue

            filtered.append(worker)

        return filtered, messages

    def _compute_required(self, request: ScheduleRequest) -> ComputeResource:
        """计算资源需求"""
        # 从模型配置或请求中获取
        min_memory = self.min_memory_mb or request.config.get(
            "min_memory_mb", 8192
        )
        gpu_count = request.config.get("gpu_count", self.min_count)
        tensor_parallel = request.config.get("tensor_parallel_size", 1)

        return ComputeResource(
            vram_mb=min_memory,
            ram_mb=0,  # 暂不计算
            gpu_count=gpu_count,
            tensor_parallel=tensor_parallel,
        )

    def _get_available_memory(self, worker: Worker) -> int:
        """获取可用显存"""
        # 从 Worker 状态中获取
        total = sum(gpu.get("memory_total", 0) for gpu in worker.gpu_status)
        used = sum(gpu.get("memory_used", 0) for gpu in worker.gpu_status)
        return total - used

    def _get_gpu_types(self, worker: Worker) -> List[str]:
        """获取 GPU 类型列表"""
        return [gpu.get("name", "") for gpu in worker.gpu_status]
```

### 3.4 标签过滤器

```python
# backend/scheduler/policies/worker_filters/label_filter.py
from typing import List, Tuple, Dict
from backend.scheduler.policies.base import WorkerFilter, ScheduleRequest, Worker

class LabelFilter(WorkerFilter):
    """标签过滤器 - 根据标签匹配 Worker"""

    def __init__(self, required_labels: Optional[Dict[str, str]] = None):
        self.required_labels = required_labels or {}

    async def filter(
        self,
        workers: List[Worker],
        request: ScheduleRequest,
    ) -> Tuple[List[Worker], List[str]]:
        messages = []
        filtered = []

        # 合并请求中的标签要求
        required = {**self.required_labels}
        if request.config.get("required_labels"):
            required.update(request.config["required_labels"])

        if not required:
            return workers, messages

        for worker in workers:
            worker_labels = worker.labels or {}

            # 检查所有必需标签
            match = True
            for key, value in required.items():
                if worker_labels.get(key) != value:
                    match = False
                    messages.append(
                        f"Worker '{worker.name}' label mismatch: "
                        f"{key}={worker_labels.get(key)}, expected {value}"
                    )
                    break

            if match:
                filtered.append(worker)

        return filtered, messages
```

### 3.5 后端过滤器

```python
# backend/scheduler/policies/worker_filters/backend_filter.py
from typing import List, Tuple
from backend.scheduler.policies.base import WorkerFilter, ScheduleRequest, Worker

class BackendFilter(WorkerFilter):
    """后端过滤器 - 检查 Worker 是否支持指定后端"""

    # 每个后端支持的 GPU 类型
    BACKEND_GPU_SUPPORT = {
        "vllm": ["nvidia", "amd"],
        "sglang": ["nvidia"],
        "tensorrt": ["nvidia"],
        "ascend-mindie": ["ascend"],
        "chitu": ["ascend", "muxi", "hygon"],
    }

    def __init__(self, backend: Optional[str] = None):
        self.backend = backend

    async def filter(
        self,
        workers: List[Worker],
        request: ScheduleRequest,
    ) -> Tuple[List[Worker], List[str]]:
        messages = []
        filtered = []

        backend = request.backend or self.backend
        if not backend:
            return workers, messages

        supported_gpus = self.BACKEND_GPU_SUPPORT.get(backend, [])

        for worker in workers:
            worker_gpu_type = worker.gpu_type or "nvidia"

            if worker_gpu_type not in supported_gpus:
                messages.append(
                    f"Worker '{worker.name}' has {worker_gpu_type} GPU, "
                    f"backend '{backend}' requires {supported_gpus}"
                )
                continue

            filtered.append(worker)

        return filtered, messages
```

---

## 4. 选择器设计

### 4.1 基础选择器

```python
# backend/scheduler/policies/candidate_selectors/base.py
from abc import abstractmethod
from typing import List
from backend.scheduler.policies.base import (
    CandidateSelector,
    Worker,
    ScheduleRequest,
    ModelInstanceCandidate,
    ComputeResource,
)

class BaseCandidateSelector(CandidateSelector):
    """候选选择器基类"""

    def _calculate_offload_layers(
        self,
        total_layers: int,
        available_vram: int,
        model_size: int,
    ) -> int:
        """计算 offload 层数"""
        # 简化计算：根据可用显存计算可以加载的层数
        vram_per_layer = model_size / total_layers
        can_load = int(available_vram / vram_per_layer)
        return min(total_layers, can_load)

    def _calculate_tensor_split(
        self,
        gpu_count: int,
        total_memory: int,
    ) -> List[int]:
        """计算 tensor_split"""
        split = total_memory // gpu_count
        return [split] * gpu_count

    @abstractmethod
    async def select(
        self,
        workers: List[Worker],
        request: ScheduleRequest,
    ) -> List[ModelInstanceCandidate]:
        pass

    def supports_backend(self, backend: str) -> bool:
        return backend in self.supported_backends()
```

### 4.2 vLLM 选择器

```python
# backend/scheduler/policies/candidate_selectors/vllm_selector.py
from typing import List
from backend.scheduler.policies.candidate_selectors.base import (
    BaseCandidateSelector,
    Worker,
    ScheduleRequest,
    ModelInstanceCandidate,
)

class VLLMSelector(BaseCandidateSelector):
    """vLLM 候选选择器"""

    # vLLM 模型参数
    MODEL_PARAMS = {
        # 模型名 -> (总层数, 模型大小 MB)
        "qwen2.5-7b": (28, 14000),
        "qwen2.5-14b": (28, 28000),
        "qwen2.5-32b": (64, 64000),
        "llama-3-8b": (32, 16000),
        "deepseek-r1": (61, 67000),
    }

    def supported_backends(self) -> List[str]:
        return ["vllm"]

    async def select(
        self,
        workers: List[Worker],
        request: ScheduleRequest,
    ) -> List[ModelInstanceCandidate]:
        candidates = []

        # 获取模型参数
        model_key = self._get_model_key(request.model)
        total_layers, model_size = self.MODEL_PARAMS.get(
            model_key, (32, 16000)  # 默认值
        )

        # 每个需要的副本生成候选
        for replica in range(request.replicas):
            for worker in workers:
                candidate = await self._select_for_worker(
                    worker, request, total_layers, model_size
                )
                if candidate:
                    candidates.append(candidate)

        return candidates

    def _get_model_key(self, model) -> str:
        """获取模型参数键"""
        # 从模型名称或配置中获取
        name = model.name.lower()
        for key in self.MODEL_PARAMS:
            if key in name:
                return key
        return "llama-3-8b"  # 默认

    async def _select_for_worker(
        self,
        worker: Worker,
        request: ScheduleRequest,
        total_layers: int,
        model_size: int,
    ) -> ModelInstanceCandidate:
        """为单个 Worker 选择配置"""

        # 获取可用 GPU
        available_gpus = self._get_available_gpus(worker)
        if not available_gpus:
            return None

        # 计算 tensor_parallel_size
        tp_size = request.config.get("tensor_parallel_size", 1)
        if tp_size > len(available_gpus):
            tp_size = len(available_gpus)

        # 选择 GPU
        gpu_ids = available_gpus[:tp_size]

        # 计算可用显存
        available_vram = sum(
            worker.gpu_status[gid]["memory_free"]
            for gid in gpu_ids
        )

        # 计算 offload 层数
        offload_layers = self._calculate_offload_layers(
            total_layers, available_vram, model_size
        )

        # 计算 tensor_split
        total_memory = sum(
            worker.gpu_status[gid]["memory_total"]
            for gid in gpu_ids
        )
        tensor_split = self._calculate_tensor_split(tp_size, total_memory)

        return ModelInstanceCandidate(
            worker=worker,
            gpu_ids=gpu_ids,
            resource_claim=ComputeResource(
                vram_mb=model_size,
                ram_mb=0,
                gpu_count=tp_size,
                tensor_parallel=tp_size,
            ),
            gpu_type=worker.gpu_type,
            offload_layers=offload_layers if offload_layers < total_layers else None,
            tensor_split=tensor_split if tp_size > 1 else None,
        )

    def _get_available_gpus(self, worker: Worker) -> List[int]:
        """获取可用 GPU 列表"""
        available = []
        for i, gpu in enumerate(worker.gpu_status):
            if gpu.get("status") == "available":
                available.append(i)
        return available
```

### 4.3 SGLang 选择器

```python
# backend/scheduler/policies/candidate_selectors/sglang_selector.py
from backend.scheduler.policies.candidate_selectors.vllm_selector import (
    VLLMSelector,
)

class SGLangSelector(VLLMSelector):
    """SGLang 候选选择器"""

    def supported_backends(self) -> List[str]:
        return ["sglang"]

    # SGLang 可能有不同的模型参数
    MODEL_PARAMS = {
        "qwen2.5-7b": (28, 14000),
        "llama-3-8b": (32, 16000),
    }
```

---

## 5. 评分器设计

### 5.1 放置评分器

```python
# backend/scheduler/policies/scorers/placement_scorer.py
from typing import List
from backend.scheduler.policies.base import (
    CandidateScorer,
    ModelInstanceCandidate,
    ScheduleRequest,
)

class PlacementScorer(CandidateScorer):
    """放置评分器 - 根据多个因素对候选评分"""

    def __init__(
        self,
        weights: dict = None,
    ):
        # 评分权重
        self.weights = weights or {
            "resource_fit": 0.3,      # 资源匹配度
            "load_balance": 0.3,      # 负载均衡
            "availability": 0.2,      # 可用性
            "affinity": 0.2,          # 亲和性
        }

    async def score(
        self,
        candidates: List[ModelInstanceCandidate],
        request: ScheduleRequest,
    ) -> List[ModelInstanceCandidate]:
        """对候选进行评分"""

        for candidate in candidates:
            scores = {}

            # 资源匹配度
            scores["resource_fit"] = self._score_resource_fit(candidate)

            # 负载均衡
            scores["load_balance"] = self._score_load_balance(candidate)

            # 可用性
            scores["availability"] = self._score_availability(candidate)

            # 亲和性
            scores["affinity"] = self._score_affinity(candidate, request)

            # 加权总分
            total_score = sum(
                scores[k] * self.weights[k]
                for k in scores
            )
            candidate.score = total_score

        # 按分数排序
        return sorted(candidates, key=lambda c: c.score or 0, reverse=True)

    def _score_resource_fit(self, candidate: ModelInstanceCandidate) -> float:
        """资源匹配度评分"""
        # 获取 GPU 可用显存
        worker = candidate.worker
        gpu_memory = sum(
            worker.gpu_status[gid].get("memory_free", 0)
            for gid in candidate.gpu_ids
        )

        required = candidate.resource_claim.vram_mb

        if gpu_memory < required:
            return 0.0

        # 匹配度：正好匹配分数最高
        ratio = required / gpu_memory
        if ratio > 0.9:
            return 1.0
        elif ratio > 0.7:
            return 0.8
        elif ratio > 0.5:
            return 0.6
        else:
            return 0.4

    def _score_load_balance(self, candidate: ModelInstanceCandidate) -> float:
        """负载均衡评分"""
        worker = candidate.worker

        # 运行中的实例数越少，分数越高
        running_instances = len([
            inst for inst in worker.model_instances
            if inst.status == "running"
        ])

        if running_instances == 0:
            return 1.0
        elif running_instances < 3:
            return 0.7
        elif running_instances < 5:
            return 0.4
        else:
            return 0.2

    def _score_availability(self, candidate: ModelInstanceCandidate) -> float:
        """可用性评分"""
        worker = candidate.worker

        # 检查是否有错误实例
        has_error = any(
            inst.status == "error"
            for inst in worker.model_instances
        )

        if has_error:
            return 0.5
        else:
            return 1.0

    def _score_affinity(
        self,
        candidate: ModelInstanceCandidate,
        request: ScheduleRequest,
    ) -> float:
        """亲和性评分"""
        worker = candidate.worker

        # 检查标签亲和性
        worker_labels = worker.labels or {}
        required = request.config.get("preferred_labels", {})

        if not required:
            return 1.0

        match_count = sum(
            1 for k, v in required.items()
            if worker_labels.get(k) == v
        )

        return match_count / len(required) if required else 1.0
```

---

## 6. 调度器实现

### 6.1 主调度器

```python
# backend/scheduler/scheduler.py
from typing import Optional
import asyncio
from loguru import logger

from backend.scheduler.policies.base import (
    ScheduleRequest,
    ScheduleResult,
    ModelInstanceCandidate,
)
from backend.scheduler.policies.worker_filters import (
    WorkerFilterChain,
    ClusterFilter,
    StatusFilter,
    GPUFilter,
    LabelFilter,
    BackendFilter,
)
from backend.scheduler.policies.candidate_selectors import (
    VLLMSelector,
    SGLangSelector,
)
from backend.scheduler.policies.scorers import PlacementScorer
from backend.controllers import WorkerController, ModelInstanceController

class Scheduler:
    """主调度器"""

    def __init__(
        self,
        worker_controller: WorkerController,
        instance_controller: ModelInstanceController,
    ):
        self.worker_controller = worker_controller
        self.instance_controller = instance_controller

        # 默认策略
        self.filter_chain = self._default_filter_chain()
        self.selector = self._default_selector()
        self.scorer = PlacementScorer()

        # 调度队列
        self.schedule_queue: asyncio.Queue[ScheduleRequest] = asyncio.Queue()
        self._running = False

    def _default_filter_chain(self) -> WorkerFilterChain:
        """默认过滤器链"""
        return WorkerFilterChain([
            StatusFilter(),
            ClusterFilter(),
            GPUFilter(min_count=1),
            BackendFilter(),
            LabelFilter(),
        ])

    def _default_selector(self):
        """默认选择器"""
        return VLLMSelector()

    def set_filter_chain(self, chain: WorkerFilterChain):
        """设置过滤器链"""
        self.filter_chain = chain

    def set_selector(self, selector):
        """设置选择器"""
        self.selector = selector

    def set_scorer(self, scorer: PlacementScorer):
        """设置评分器"""
        self.scorer = scorer

    async def schedule(self, request: ScheduleRequest) -> ScheduleResult:
        """
        执行调度

        Args:
            request: 调度请求

        Returns:
            调度结果
        """
        logger.info(f"Scheduling: {request.model.name} x{request.replicas}")

        # 1. 获取所有可用 Workers
        workers = await self.worker_controller.get_all_workers()

        # 2. 应用过滤器链
        filtered_workers, filter_messages = await self.filter_chain.filter(
            workers, request
        )

        rejected = []
        for worker in workers:
            if worker not in filtered_workers:
                reason = next(
                    (m for m in filter_messages if f"'{worker.name}'" in m),
                    "Unknown reason"
                )
                rejected.append((worker, reason))

        logger.info(f"Filter: {len(filtered_workers)} workers available")

        if not filtered_workers:
            return ScheduleResult(
                success=False,
                candidates=[],
                rejected_workers=rejected,
            )

        # 3. 选择候选配置
        candidates = await self.selector.select(filtered_workers, request)
        logger.info(f"Select: {len(candidates)} candidates generated")

        if not candidates:
            return ScheduleResult(
                success=False,
                candidates=[],
                rejected_workers=rejected,
            )

        # 4. 评分排序
        scored_candidates = await self.scorer.score(candidates, request)

        # 5. 选择最优的 N 个候选
        selected = scored_candidates[:request.replicas]

        logger.info(
            f"Schedule: selected {[c.worker.name for c in selected]}"
        )

        return ScheduleResult(
            success=True,
            candidates=selected,
            rejected_workers=rejected,
        )

    async def run(self):
        """运行调度循环"""
        self._running = True

        while self._running:
            try:
                # 从队列获取请求（带超时）
                request = await asyncio.wait_for(
                    self.schedule_queue.get(),
                    timeout=1.0,
                )

                # 执行调度
                result = await self.schedule(request)

                # 处理结果
                if result.success:
                    await self._create_instances(result)

            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Schedule error: {e}")

    async def _create_instances(self, result: ScheduleResult):
        """创建模型实例"""
        for candidate in result.candidates:
            await self.instance_controller.create_instance(
                worker_id=candidate.worker.id,
                model_id=result.request.model.id,
                gpu_ids=candidate.gpu_ids,
                backend=result.request.backend,
                config=result.request.config,
            )

    def stop(self):
        """停止调度器"""
        self._running = False

    async def submit_schedule(self, request: ScheduleRequest):
        """提交调度请求"""
        await self.schedule_queue.put(request)
```

---

## 7. 策略配置

### 7.1 配置文件

```yaml
# config/scheduler.yaml
scheduler:
  # 过滤器配置
  filters:
    - type: StatusFilter
      params:
        allowed_statuses: ["ready", "busy"]
        heartbeat_timeout: 90

    - type: ClusterFilter
      params:
        cluster_id: null  # 从请求获取

    - type: GPUFilter
      params:
        min_memory_mb: 8192
        min_count: 1
        require_same_type: false

    - type: LabelFilter
      params:
        required_labels:
          env: production

    - type: BackendFilter
      params:
        backend: null  # 从请求获取

  # 选择器配置
  selector:
    type: VLLMSelector  # VLLMSelector, SGLangSelector, etc.
    params:
      model_params_file: config/model_params.yaml

  # 评分器配置
  scorer:
    type: PlacementScorer
    params:
      weights:
        resource_fit: 0.3
        load_balance: 0.3
        availability: 0.2
        affinity: 0.2
```

### 7.2 动态策略加载

```python
# backend/scheduler/config.py
import yaml
from pathlib import Path

def load_scheduler_config(config_path: str = "config/scheduler.yaml"):
    """加载调度器配置"""
    with open(config_path) as f:
        config = yaml.safe_load(f)

    return config["scheduler"]

def create_filter_chain(config: dict):
    """从配置创建过滤器链"""
    filters = []

    for filter_config in config["filters"]:
        filter_type = filter_config["type"]
        params = filter_config.get("params", {})

        filter_class = FILTER_REGISTRY[filter_type]
        filters.append(filter_class(**params))

    return WorkerFilterChain(filters)

def create_selector(config: dict):
    """从配置创建选择器"""
    selector_type = config["selector"]["type"]
    params = config["selector"].get("params", {})

    selector_class = SELECTOR_REGISTRY[selector_type]
    return selector_class(**params)

# 注册表
FILTER_REGISTRY = {
    "StatusFilter": StatusFilter,
    "ClusterFilter": ClusterFilter,
    "GPUFilter": GPUFilter,
    "LabelFilter": LabelFilter,
    "BackendFilter": BackendFilter,
}

SELECTOR_REGISTRY = {
    "VLLMSelector": VLLMSelector,
    "SGLangSelector": SGLangSelector,
}
```

---

## 8. 实施计划

### Phase 1: 基础框架（1 周）

- [ ] 创建 `backend/scheduler/` 目录
- [ ] 实现基础抽象类（base.py）
- [ ] 实现数据结构
- [ ] 编写单元测试

### Phase 2: 过滤器（1 周）

- [ ] 实现 StatusFilter
- [ ] 实现 ClusterFilter
- [ ] 实现 GPUFilter
- [ ] 实现 LabelFilter
- [ ] 实现 BackendFilter
- [ ] 实现 WorkerFilterChain

### Phase 3: 选择器（1 周）

- [ ] 实现 BaseCandidateSelector
- [ ] 实现 VLLMSelector
- [ ] 实现 SGLangSelector

### Phase 4: 评分器（1 周）

- [ ] 实现 PlacementScorer
- [ ] 实现 OffloadScorer（可选）

### Phase 5: 调度器（1 周）

- [ ] 实现 Scheduler 主类
- [ ] 实现调度循环
- [ ] 集成控制器

### Phase 6: 配置与测试（1 周）

- [ ] 实现配置加载
- [ ] 集成测试
- [ ] 性能测试

---

**文档版本**: v1.0
**最后更新**: 2025-01-14
