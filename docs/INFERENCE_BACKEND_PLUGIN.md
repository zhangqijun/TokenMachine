# 推理后端插件系统设计

> 设计可插拔的推理引擎架构，支持 vLLM、SGLang、TensorRT-LLM 等多种推理后端

---

## 目录

- [1. 设计概述](#1-设计概述)
- [2. 后端抽象接口](#2-后端抽象接口)
- [3. 后端实现](#3-后端实现)
- [4. 插件管理器](#4-插件管理器)
- [5. 配置管理](#5-配置管理)
- [6. 实施计划](#6-实施计划)

---

## 1. 设计概述

### 1.1 架构图

```
┌─────────────────────────────────────────────────────────────────┐
│                        Worker 服务                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │              InferenceBackendManager                     │   │
│  │                                                         │   │
│  │  • 后端注册表                                            │   │
│  │  • 后端生命周期管理                                      │   │
│  │  • 后端配置缓存                                          │   │
│  └─────────────────────────────────────────────────────────┘   │
│                              │                                  │
│                              ▼                                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │              InferenceBackend (Base)                     │   │
│  │                                                         │   │
│  │  + load_model()                                         │   │
│  │  + generate()                                           │   │
│  │  + health_check()                                       │   │
│  │  + stop()                                               │   │
│  │  + get_metrics()                                        │   │
│  └────────────┬────────────────────────────────────────────┘   │
│               │                                                  │
│      ┌────────┴─────────┬──────────────┬──────────────┐        │
│      ▼                  ▼              ▼              ▼        │
│ ┌─────────┐      ┌─────────┐    ┌─────────┐    ┌─────────┐    │
│ │  vLLM   │      │ SGLang  │    │TensorRT │    │ Chitu   │    │
│ │Backend  │      │Backend  │    │  LLM    │    │Backend  │    │
│ └─────────┘      └─────────┘    └─────────┘    └─────────┘    │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      GPU 资源层                                  │
│  GPU 0 │ GPU 1 │ GPU 2 │ GPU 3 │ ...                           │
└─────────────────────────────────────────────────────────────────┘
```

### 1.2 支持的后端

| 后端 | GPU 支持 | 特性 | 优先级 |
|------|----------|------|--------|
| **vLLM** | NVIDIA, AMD | PagedAttention, 高吞吐 | P0 |
| **SGLang** | NVIDIA | 结构化生成优化 | P1 |
| **TensorRT-LLM** | NVIDIA | 极致性能优化 | P2 |
| **Chitu** | 昇腾, 沐曦, 海光 | 国产芯片支持 | P2 |
| **llama.cpp** | CPU, GPU | CPU 推理 | P3 |

### 1.3 设计原则

| 原则 | 说明 |
|------|------|
| **接口统一** | 所有后端实现相同接口 |
| **热插拔** | 运行时动态加载后端 |
| **配置驱动** | 后端行为通过配置控制 |
| **错误隔离** | 后端故障不影响其他后端 |
| **资源管理** | 后端负责自己的 GPU 分配 |

---

## 2. 后端抽象接口

### 2.1 基础接口

```python
# backend/worker/backends/base.py
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, AsyncGenerator, Any
from dataclasses import dataclass
from enum import Enum

class BackendStatus(Enum):
    """后端状态"""
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    ERROR = "error"

@dataclass
class GenerationRequest:
    """生成请求"""
    prompt: str
    max_tokens: int = 512
    temperature: float = 0.7
    top_p: float = 0.9
    top_k: int = 40
    stream: bool = False
    stop: Optional[List[str]] = None
    presence_penalty: float = 0.0
    frequency_penalty: float = 0.0

@dataclass
class GenerationResponse:
    """生成响应"""
    text: str
    finish_reason: str
    tokens_used: Dict[str, int]  # {"prompt": 10, "completion": 20}
    logprobs: Optional[List[float]] = None

@dataclass
class HealthStatus:
    """健康状态"""
    healthy: bool
    status: BackendStatus
    message: str
    metrics: Dict[str, Any] = None

class InferenceBackend(ABC):
    """推理后端抽象基类"""

    def __init__(
        self,
        model_path: str,
        model_name: str,
        gpu_ids: List[int],
        config: Dict = None,
    ):
        self.model_path = model_path
        self.model_name = model_name
        self.gpu_ids = gpu_ids
        self.config = config or {}
        self._status = BackendStatus.STOPPED
        self._process: Any = None

    @property
    @abstractmethod
    def backend_type(self) -> str:
        """后端类型标识"""
        pass

    @abstractmethod
    async def start(self) -> None:
        """
        启动后端服务

        Raises:
            RuntimeError: 启动失败
        """
        pass

    @abstractmethod
    async def stop(self) -> None:
        """停止后端服务"""
        pass

    @abstractmethod
    async def health_check(self) -> HealthStatus:
        """健康检查"""
        pass

    @abstractmethod
    async def generate(
        self,
        request: GenerationRequest,
    ) -> GenerationResponse:
        """
        生成文本（非流式）

        Args:
            request: 生成请求

        Returns:
            生成响应

        Raises:
            RuntimeError: 生成失败
        """
        pass

    @abstractmethod
    async def generate_stream(
        self,
        request: GenerationRequest,
    ) -> AsyncGenerator[GenerationResponse, None]:
        """
        生成文本（流式）

        Args:
            request: 生成请求

        Yields:
            生成响应片段
        """
        pass

    @abstractmethod
    async def get_metrics(self) -> Dict[str, Any]:
        """获取运行指标"""
        pass

    @abstractmethod
    def get_openai_api_base(self) -> str:
        """获取 OpenAI 兼容 API 地址"""
        pass

    @property
    def status(self) -> BackendStatus:
        """获取当前状态"""
        return self._status

    def _set_status(self, status: BackendStatus):
        """设置状态"""
        self._status = status
```

### 2.2 后端配置

```python
@dataclass
class BackendConfig:
    """后端配置"""
    # 通用配置
    model_path: str
    model_name: str
    gpu_ids: List[int]
    backend_type: str

    # 服务配置
    host: str = "0.0.0.0"
    port: int = 8000
    log_level: str = "info"

    # 推理配置
    max_model_len: int = 4096
    tensor_parallel_size: int = 1
    gpu_memory_utilization: float = 0.9

    # vLLM 特定配置
    disable_log_stats: bool = True
    dtype: str = "auto"
    quantization: Optional[str] = None

    # SGLang 特定配置
    chunked_prefill_size: Optional[int] = None

    @classmethod
    def from_dict(cls, data: Dict) -> "BackendConfig":
        """从字典创建配置"""
        return cls(**data)

    def to_dict(self) -> Dict:
        """转换为字典"""
        from dataclasses import asdict
        return asdict(self)
```

---

## 3. 后端实现

### 3.1 vLLM 后端

```python
# backend/worker/backends/vllm_backend.py
import asyncio
import subprocess
from typing import List, Dict, AsyncGenerator
import httpx

from backend.worker.backends.base import (
    InferenceBackend,
    GenerationRequest,
    GenerationResponse,
    HealthStatus,
    BackendStatus,
)

class VLLMBackend(InferenceBackend):
    """vLLM 推理后端"""

    @property
    def backend_type(self) -> str:
        return "vllm"

    async def start(self) -> None:
        """启动 vLLM 服务"""
        if self._status != BackendStatus.STOPPED:
            return

        self._set_status(BackendStatus.STARTING)

        # 构建命令
        cmd = self._build_command()

        # 设置环境变量
        env = self._build_env()

        try:
            # 启动进程
            self._process = await asyncio.create_subprocess_exec(
                *cmd,
                env=env,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            # 等待服务就绪
            await self._wait_for_ready(timeout=300)

            self._set_status(BackendStatus.RUNNING)
            logger.info(f"vLLM backend started: {self.model_name}")

        except Exception as e:
            self._set_status(BackendStatus.ERROR)
            raise RuntimeError(f"Failed to start vLLM: {e}")

    def _build_command(self) -> List[str]:
        """构建启动命令"""
        cmd = [
            "python", "-m", "vllm.entrypoints.openai.api_server",
            "--model", self.model_path,
            "--served-model-name", self.model_name,
            "--host", self.config.get("host", "0.0.0.0"),
            "--port", str(self.config.get("port", 8000)),
            "--max-model-len", str(self.config.get("max_model_len", 4096)),
            "--gpu-memory-utilization", str(self.config.get("gpu_memory_utilization", 0.9)),
            "--disable-log-stats",
        ]

        # Tensor parallel
        tp_size = self.config.get("tensor_parallel_size", len(self.gpu_ids))
        if tp_size > 1:
            cmd.extend(["--tensor-parallel-size", str(tp_size)])

        # Quantization
        if self.config.get("quantization"):
            cmd.extend(["--quantization", self.config["quantization"]])

        # dtype
        if self.config.get("dtype") and self.config["dtype"] != "auto":
            cmd.extend(["--dtype", self.config["dtype"]])

        return cmd

    def _build_env(self) -> Dict[str, str]:
        """构建环境变量"""
        import os

        env = os.environ.copy()

        # 设置可见 GPU
        gpu_ids = ",".join(map(str, self.gpu_ids))
        env["CUDA_VISIBLE_DEVICES"] = gpu_ids

        return env

    async def _wait_for_ready(self, timeout: int = 300) -> None:
        """等待服务就绪"""
        start_time = asyncio.get_event_loop().time()
        api_base = self.get_openai_api_base()

        while asyncio.get_event_loop().time() - start_time < timeout:
            try:
                async with httpx.AsyncClient(timeout=5) as client:
                    response = await client.get(f"{api_base}/health")
                    if response.status_code == 200:
                        return
            except Exception:
                pass

            await asyncio.sleep(2)

        raise TimeoutError("Backend not ready within timeout")

    async def stop(self) -> None:
        """停止服务"""
        if self._process:
            self._process.terminate()
            try:
                await asyncio.wait_for(self._process.wait(), timeout=30)
            except asyncio.TimeoutError:
                self._process.kill()
                await self._process.wait()

            self._process = None

        self._set_status(BackendStatus.STOPPED)
        logger.info(f"vLLM backend stopped: {self.model_name}")

    async def health_check(self) -> HealthStatus:
        """健康检查"""
        try:
            api_base = self.get_openai_api_base()
            async with httpx.AsyncClient(timeout=5) as client:
                response = await client.get(f"{api_base}/health")
                is_healthy = response.status_code == 200

                return HealthStatus(
                    healthy=is_healthy,
                    status=BackendStatus.RUNNING if is_healthy else BackendStatus.ERROR,
                    message="OK" if is_healthy else "Health check failed",
                )
        except Exception as e:
            return HealthStatus(
                healthy=False,
                status=self._status,
                message=str(e),
            )

    async def generate(
        self,
        request: GenerationRequest,
    ) -> GenerationResponse:
        """生成文本"""
        api_base = self.get_openai_api_base()

        payload = {
            "model": self.model_name,
            "prompt": request.prompt,
            "max_tokens": request.max_tokens,
            "temperature": request.temperature,
            "top_p": request.top_p,
            "top_k": request.top_k,
            "stop": request.stop,
            "presence_penalty": request.presence_penalty,
            "frequency_penalty": request.frequency_penalty,
        }

        async with httpx.AsyncClient(timeout=300) as client:
            response = await client.post(
                f"{api_base}/v1/completions",
                json=payload,
            )
            response.raise_for_status()
            data = response.json()

            choice = data["choices"][0]
            return GenerationResponse(
                text=choice["text"],
                finish_reason=choice["finish_reason"],
                tokens_used=data.get("usage", {}),
            )

    async def generate_stream(
        self,
        request: GenerationRequest,
    ) -> AsyncGenerator[GenerationResponse, None]:
        """流式生成"""
        api_base = self.get_openai_api_base()

        payload = {
            "model": self.model_name,
            "prompt": request.prompt,
            "max_tokens": request.max_tokens,
            "temperature": request.temperature,
            "top_p": request.top_p,
            "top_k": request.top_k,
            "stop": request.stop,
            "stream": True,
        }

        async with httpx.AsyncClient(timeout=300) as client:
            async with client.stream(
                "POST",
                f"{api_base}/v1/completions",
                json=payload,
            ) as response:
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data = line[6:]
                        if data == "[DONE]":
                            break

                        import json
                        chunk = json.loads(data)
                        choice = chunk["choices"][0]

                        if choice["finish_reason"] is None:
                            yield GenerationResponse(
                                text=choice.get("text", ""),
                                finish_reason="",
                                tokens_used={},
                            )

    async def get_metrics(self) -> Dict[str, Any]:
        """获取指标"""
        try:
            health = await self.health_check()
            return {
                "backend_type": self.backend_type,
                "model_name": self.model_name,
                "status": health.status.value,
                "healthy": health.healthy,
            }
        except Exception:
            return {
                "backend_type": self.backend_type,
                "model_name": self.model_name,
                "status": "error",
                "healthy": False,
            }

    def get_openai_api_base(self) -> str:
        """获取 API 地址"""
        port = self.config.get("port", 8000)
        return f"http://localhost:{port}"
```

### 3.2 SGLang 后端

```python
# backend/worker/backends/sglang_backend.py
from backend.worker.backends.vllm_backend import VLLMBackend

class SGLangBackend(VLLMBackend):
    """SGLang 推理后端（兼容 vLLM API）"""

    @property
    def backend_type(self) -> str:
        return "sglang"

    def _build_command(self) -> List[str]:
        """构建 SGLang 启动命令"""
        cmd = [
            "python", "-m", "sglang.launch_server",
            "--model-path", self.model_path,
            "--served-model-name", self.model_name,
            "--host", self.config.get("host", "0.0.0.0"),
            "--port", str(self.config.get("port", 8000)),
            "--context-length", str(self.config.get("max_model_len", 4096)),
        ]

        # Chunked prefill
        if self.config.get("chunked_prefill_size"):
            cmd.extend([
                "--chunked-prefill-size",
                str(self.config["chunked_prefill_size"])
            ])

        return cmd

    async def _wait_for_ready(self, timeout: int = 300) -> None:
        """SGLang 健康检查端点不同"""
        start_time = asyncio.get_event_loop().time()
        api_base = self.get_openai_api_base()

        while asyncio.get_event_loop().time() - start_time < timeout:
            try:
                async with httpx.AsyncClient(timeout=5) as client:
                    # SGLang 使用 /health 端点
                    response = await client.get(f"{api_base}/health")
                    if response.status_code == 200:
                        return
            except Exception:
                pass

            await asyncio.sleep(2)

        raise TimeoutError("Backend not ready within timeout")
```

### 3.3 TensorRT-LLM 后端

```python
# backend/worker/backends/tensorrt_backend.py
class TensorRTBackend(InferenceBackend):
    """TensorRT-LLM 推理后端"""

    @property
    def backend_type(self) -> str:
        return "tensorrt"

    async def start(self) -> None:
        """启动 TensorRT-LLM 服务"""
        self._set_status(BackendStatus.STARTING)

        # 构建 TensorRT-LLM 命令
        cmd = self._build_command()

        try:
            self._process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            await self._wait_for_ready(timeout=300)
            self._set_status(BackendStatus.RUNNING)

        except Exception as e:
            self._set_status(BackendStatus.ERROR)
            raise RuntimeError(f"Failed to start TensorRT-LLM: {e}")

    def _build_command(self) -> List[str]:
        """构建 TensorRT-LLM 启动命令"""
        # TensorRT-LLM 通常通过 Python API 启动
        return [
            "python",
            "examples/llm/example.py",
            "--model_path", self.model_path,
            "--tp_size", str(self.config.get("tensor_parallel_size", 1)),
        ]

    # ... 其他方法实现

    async def generate(self, request: GenerationRequest) -> GenerationResponse:
        """TensorRT-LLM 可能使用不同的 API 格式"""
        # 需要根据实际 API 实现
        pass
```

### 3.4 Chitu 后端（国产芯片）

```python
# backend/worker/backends/chitu_backend.py
class ChituBackend(InferenceBackend):
    """Chitu 推理后端（昇腾、沐曦、海光）"""

    @property
    def backend_type(self) -> str:
        return "chitu"

    async def start(self) -> None:
        """启动 Chitu 服务"""
        self._set_status(BackendStatus.STARTING)

        # Chitu 启动命令
        cmd = self._build_command()

        try:
            self._process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            await self._wait_for_ready(timeout=300)
            self._set_status(BackendStatus.RUNNING)

        except Exception as e:
            self._set_status(BackendStatus.ERROR)
            raise RuntimeError(f"Failed to start Chitu: {e}")

    def _build_command(self) -> List[str]:
        """构建 Chitu 启动命令"""
        gpu_type = self.config.get("gpu_type", "ascend")

        if gpu_type == "ascend":
            return [
                "python", "-m", "chitu.serve",
                "--model", self.model_path,
                "--device", "npu",  # 昇腾 NPU
                "--npus", str(len(self.gpu_ids)),
            ]
        elif gpu_type == "muxi":
            return [
                "python", "-m", "chitu.serve",
                "--model", self.model_path,
                "--device", "gpu",  # 沐曦 GPU
                "--gpus", ",".join(map(str, self.gpu_ids)),
            ]
        else:
            raise ValueError(f"Unsupported GPU type: {gpu_type}")

    # ... 其他方法实现
```

---

## 4. 插件管理器

### 4.1 后端管理器

```python
# backend/worker/inference_backend_manager.py
from typing import Dict, List, Optional, Type
from backend.worker.backends.base import InferenceBackend, BackendConfig

# 后端注册表
BACKEND_REGISTRY: Dict[str, Type[InferenceBackend]] = {}

def register_backend(backend_type: str, backend_class: Type[InferenceBackend]):
    """注册后端"""
    BACKEND_REGISTRY[backend_type] = backend_class

def get_backend_class(backend_type: str) -> Type[InferenceBackend]:
    """获取后端类"""
    if backend_type not in BACKEND_REGISTRY:
        raise ValueError(f"Unknown backend type: {backend_type}")
    return BACKEND_REGISTRY[backend_type]

def list_backends() -> List[str]:
    """列出所有已注册后端"""
    return list(BACKEND_REGISTRY.keys())


# 注册内置后端
from backend.worker.backends.vllm_backend import VLLMBackend
from backend.worker.backends.sglang_backend import SGLangBackend
from backend.worker.backends.tensorrt_backend import TensorRTBackend
from backend.worker.backends.chitu_backend import ChituBackend

register_backend("vllm", VLLMBackend)
register_backend("sglang", SGLangBackend)
register_backend("tensorrt", TensorRTBackend)
register_backend("chitu", ChituBackend)


class InferenceBackendManager:
    """推理后端管理器"""

    def __init__(self):
        # {instance_id: InferenceBackend}
        self._backends: Dict[int, InferenceBackend] = {}

        # 后端配置缓存
        self._config_cache: Dict[str, Dict] = {}

    async def start_backend(
        self,
        instance_id: int,
        config: BackendConfig,
    ) -> InferenceBackend:
        """
        启动后端实例

        Args:
            instance_id: 实例 ID
            config: 后端配置

        Returns:
            后端实例
        """
        if instance_id in self._backends:
            return self._backends[instance_id]

        # 获取后端类
        backend_class = get_backend_class(config.backend_type)

        # 创建后端实例
        backend = backend_class(
            model_path=config.model_path,
            model_name=config.model_name,
            gpu_ids=config.gpu_ids,
            config=config.to_dict(),
        )

        # 启动后端
        await backend.start()

        # 缓存
        self._backends[instance_id] = backend

        return backend

    async def stop_backend(self, instance_id: int) -> None:
        """停止后端实例"""
        if instance_id not in self._backends:
            return

        backend = self._backends.pop(instance_id)
        await backend.stop()

    def get_backend(self, instance_id: int) -> Optional[InferenceBackend]:
        """获取后端实例"""
        return self._backends.get(instance_id)

    async def health_check_all(self) -> Dict[int, bool]:
        """检查所有后端健康状态"""
        results = {}
        for instance_id, backend in self._backends.items():
            health = await backend.health_check()
            results[instance_id] = health.healthy
        return results

    async def cleanup_all(self) -> None:
        """清理所有后端"""
        for instance_id in list(self._backends.keys()):
            await self.stop_backend(instance_id)

    def load_backend_configs(self, configs: Dict[str, Dict]):
        """加载后端配置（从 Server）"""
        self._config_cache = configs

    def get_backend_config(self, backend_type: str) -> Dict:
        """获取后端配置"""
        return self._config_cache.get(backend_type, {})
```

### 4.2 配置同步

```python
# backend/worker/backend_config_sync.py
import asyncio
from typing import Optional
import httpx

class BackendConfigSync:
    """后端配置同步器"""

    def __init__(
        self,
        server_url: str,
        token: str,
        manager: InferenceBackendManager,
    ):
        self.server_url = server_url
        self.token = token
        self.manager = manager
        self._running = False

    async def start(self):
        """启动配置同步"""
        self._running = True

        # 首次同步
        await self._sync_configs()

        # 定期同步
        while self._running:
            try:
                await asyncio.sleep(300)  # 5 分钟
                await self._sync_configs()
            except Exception as e:
                logger.error(f"Config sync error: {e}")

    def stop(self):
        """停止同步"""
        self._running = False

    async def _sync_configs(self):
        """同步配置"""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.server_url}/api/v1/inference-backends/configs",
                headers={"Authorization": f"Bearer {self.token}"},
            )
            response.raise_for_status()
            configs = response.json()

        self.manager.load_backend_configs(configs)
```

---

## 5. 配置管理

### 5.1 后端配置文件

```yaml
# config/inference_backends.yaml
backends:
  vllm:
    # 默认配置
    default:
      host: "0.0.0.0"
      port: 8000
      gpu_memory_utilization: 0.9
      max_model_len: 4096
      tensor_parallel_size: 1
      disable_log_stats: true
      dtype: "auto"

    # 模型特定配置
    model_overrides:
      "qwen2.5-7b":
        max_model_len: 32768
        gpu_memory_utilization: 0.95
      "deepseek-r1":
        max_model_len: 8192
        enable_chunked_context: true

    # GPU 类型配置
    gpu_overrides:
      nvidia:
        dtype: "bfloat16"
      amd:
        dtype: "float16"

  sglang:
    default:
      host: "0.0.0.0"
      port: 8000
      context_length: 4096
      chunked_prefill_size: 4096

  tensorrt:
    default:
      tp_size: 1
      max_batch_size: 32
      max_input_len: 4096

  chitu:
    default:
      device: "npu"  # npu, gpu
      batch_size: 1
    gpu_overrides:
      ascend:
        device: "npu"
        precision: "fp16"
      muxi:
        device: "gpu"
        precision: "fp16"
      hygon:
        device: "gpu"
        precision: "int8"
```

### 5.2 动态后端配置

```python
# backend/worker/backend_config.py
import yaml
from pathlib import Path
from typing import Dict, Any

class BackendConfigLoader:
    """后端配置加载器"""

    def __init__(self, config_path: str = "config/inference_backends.yaml"):
        self.config_path = Path(config_path)
        self._cache: Dict[str, Any] = {}

    def load(self) -> Dict[str, Any]:
        """加载配置"""
        if not self._cache:
            with open(self.config_path) as f:
                self._cache = yaml.safe_load(f)
        return self._cache

    def get_backend_config(
        self,
        backend_type: str,
        model_name: str = None,
        gpu_type: str = None,
    ) -> Dict[str, Any]:
        """
        获取后端配置

        Args:
            backend_type: 后端类型
            model_name: 模型名称（可选）
            gpu_type: GPU 类型（可选）

        Returns:
            合并后的配置
        """
        config = self.load()

        # 获取默认配置
        backend_config = config["backends"].get(backend_type, {})
        default = backend_config.get("default", {}).copy()

        # 合并模型特定配置
        if model_name:
            model_overrides = backend_config.get("model_overrides", {})
            for model_pattern, override in model_overrides.items():
                if model_pattern in model_name.lower():
                    default.update(override)

        # 合并 GPU 类型配置
        if gpu_type:
            gpu_overrides = backend_config.get("gpu_overrides", {})
            gpu_config = gpu_overrides.get(gpu_type, {})
            default.update(gpu_config)

        return default
```

---

## 6. 实施计划

### Phase 1: 基础框架（1 周）

- [ ] 创建 `backend/worker/backends/` 目录
- [ ] 实现基础抽象类 `InferenceBackend`
- [ ] 实现数据结构（Request, Response, Config）
- [ ] 编写单元测试

### Phase 2: vLLM 后端（1 周）

- [ ] 实现 `VLLMBackend`
- [ ] 实现进程启动/停止
- [ ] 实现健康检查
- [ ] 实现生成接口
- [ ] 集成测试

### Phase 3: 其他后端（2 周）

- [ ] 实现 `SGLangBackend`
- [ ] 实现 `TensorRTBackend`
- [ ] 实现 `ChituBackend`（可选）

### Phase 4: 管理器（1 周）

- [ ] 实现 `InferenceBackendManager`
- [ ] 实现后端注册表
- [ ] 实现配置管理
- [ ] 实现配置同步

### Phase 5: 集成（1 周）

- [ ] 与 ServeManager 集成
- [ ] 端到端测试
- [ ] 性能测试

---

**文档版本**: v1.0
**最后更新**: 2025-01-14
