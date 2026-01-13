# AI 模型部署与管理平台 - 产品设计方案

> 基于 GPUStack、New API、Chitu、KTransformers 四个开源项目的综合分析

---

## 目录

- [1. 产品定位](#1-产品定位)
- [2. 核心架构](#2-核心架构)
- [3. 功能模块](#3-功能模块)
  - [3.1 模型部署管理](#31-模型部署管理)
  - [3.2 GPU 集群调度](#32-gpu-集群调度)
  - [3.3 统一 API 网关](#33-统一-api-网关)
  - [3.4 计费系统](#34-计费系统)
  - [3.5 模型微调](#35-模型微调)
  - [3.6 监控与可观测性](#36-监控与可观测性)
  - [3.7 多租户与权限](#37-多租户与权限)
- [4. 技术栈](#4-技术栈)
- [5. 部署方案](#5-部署方案)
- [6. 实施路线](#6-实施路线)
- [7. 商业模式](#7-商业模式)
- [8. 竞争优势](#8-竞争优势)

---

## 1. 产品定位

### 1.1 基本信息

| 项目 | 内容 |
|------|------|
| **产品名称** | TokenMachine |
| **产品定位** | 一站式 AI 模型部署、调度、计费和管理平台 |
| **目标用户** | 企业 IT 部门、AI 创业公司、研究机构、需要私有化部署的中大型企业 |
| **核心价值** | 降本（私有化部署）、灵活（多硬件多模型）、可控（数据自主）、易用（一键部署） |

### 1.2 核心优势来源

| 来源项目 | 核心贡献 |
|----------|----------|
| **GPUStack** | GPU 集群管理、多推理引擎支持、OpenAI 兼容 API |
| **New API** | 计费系统、多渠道智能路由、格式转换 |
| **Chitu** | 国产芯片支持（昇腾、沐曦、海光）、生产级稳定性 |
| **KTransformers** | CPU-GPU 异构计算、MoE 优化、模型微调 |

---

## 2. 核心架构

### 2.1 系统架构图

```
┌─────────────────────────────────────────────────────────────────┐
│                        用户/应用层                               │
│  Web UI │ CLI │ API (OpenAI Compatible) │ SDK                  │
└────────────────────────────┬────────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────────┐
│                     统一 API 网关层                              │
│  • 格式转换 (OpenAI/Claude/Gemini)                              │
│  • 渠道路由 (本地模型 / 外部 API)                                │
│  • 认证鉴权 (API Key / OAuth / SSO)                             │
│  • 限流熔断                                                      │
└────────────────────────────┬────────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────────┐
│                   核心功能层                                    │
├──────────────┬──────────────┬──────────────┬──────────────────┤
│ 模型部署管理  │  GPU 集群   │  计费系统    │  模型微调       │
│              │  调度       │              │                 │
│ • 版本管理   │ • 资源分配  │ • Token计费  │ • LoRA 训练     │
│ • 灰度发布   │ • 负载均衡  │ • 在线充值   │ • 分布式训练    │
│ • A/B 测试   │ • 异构计算  │ • 账单管理   │ • 任务调度      │
└──────────────┴──────────────┴──────────────┴──────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────────┐
│                  推理引擎层                                     │
├──────────────┬──────────────┬──────────────┬──────────────────┤
│  vLLM        │  SGLang      │  Chitu       │  自定义后端     │
│  TensorRT    │  内置引擎    │  kt-kernel   │                 │
└──────────────┴──────────────┴──────────────┴──────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────────┐
│                 硬件资源层                                      │
│  NVIDIA GPU │ 昇腾 NPU │ 沐曦 GPU │ 海光 GPU │ CPU 内存       │
└─────────────────────────────────────────────────────────────────┘
```

---

## 3. 功能模块

### 3.1 模型部署管理

#### 3.1.1 模型版本管理

```
模型 → 版本 → 变体
   ↓      ↓       ↓
  LLM   v1.0   FP16/INT8/FP4
              (量化)
```

**核心功能**:
- ✅ 模型仓库（支持 HuggingFace、ModelScope、本地）
- ✅ 版本控制（Git-like 模型版本管理）
- ✅ 量化变体（FP16、INT8、FP4、FP8）
- ✅ 灰度发布（逐步切换版本）
- ✅ 一键回滚
- ✅ 模型指纹校验

**界面示例**:
```
┌──────────────────────────────────────────────────┐
│  模型: Qwen2.5-7B-Instruct                       │
├──────────────────────────────────────────────────┤
│  版本    │ 变体   │ 状态 │ 流量 │ 操作          │
│  v2.0    │ FP8   │ 🟢   │ 100% │ [编辑][回滚]  │
│  v1.5    │ INT8  │ 🟡   │ 0%   │ [编辑][发布]  │
│  v1.0    │ FP16  │ ⚪   │ 0%   │ [编辑][归档]  │
└──────────────────────────────────────────────────┘
```

#### 3.1.2 多环境部署

| 环境 | 用途 | 资源配额 |
|------|------|----------|
| **开发** | 功能验证 | 1 GPU / 32GB RAM |
| **测试** | 集成测试 | 2 GPU / 64GB RAM |
| **预发** | 性能压测 | 4 GPU / 128GB RAM |
| **生产** | 正式服务 | 弹性扩缩容 |

#### 3.1.3 模型类型支持

| 模型类型 | 支持格式 | 应用场景 |
|----------|----------|----------|
| **LLM** | GGUF, GGUF, SafeTensors | 对话、文本生成 |
| **Embedding** | SafeTensors, GGUF | 向量检索、RAG |
| **Reranker** | SafeTensors | 搜索结果重排序 |
| **图像生成** | Diffusers, SafeTensors | 文生图、图像编辑 |
| **语音** | SafeTensors, WAV | TTS、STT |

---

### 3.2 GPU 集群调度

#### 3.2.1 异构资源调度

**调度策略代码示例**:
```python
class HeterogeneousScheduler:
    def schedule(self, model: Model):
        # 1. 检测硬件类型
        hw_type = detect_hardware()  # NVIDIA / ASCEND / MUXI

        # 2. 选择引擎
        if hw_type == "ASCEND":
            engine = ChituEngine(backend="ascend")
        elif hw_type == "NVIDIA":
            engine = VLLMEngine() if model.is_moe else SGLangEngine()

        # 3. CPU+GPU 异构
        if model.vram > available_vram:
            # 热专家 GPU，冷专家 CPU
            return HeterogeneousPlacement(
                gpu_experts=32,
                cpu_fallback=True,
                offload_ratio=0.7
            )
```

#### 3.2.2 智能资源分配策略

| 策略 | 场景 | 配置示例 |
|------|------|----------|
| **Spread** | 高可用 | 每节点 1 副本 |
| **Binpack** | 节省资源 | 单节点填满 |
| **异构** | 超大模型 | GPU+CPU 混合 |
| **动态** | 弹性负载 | 基于队列深度扩容 |

#### 3.2.3 资源池隔离

```
┌─────────────────────────────────────────────┐
│              资源池管理                      │
├─────────────────────────────────────────────┤
│  资源池     │ GPU │ 租户   │ 优先级 │ 配额   │
│  production│ 64  │ 客服   │ 高    │ 无限制  │
│  development│ 8  │ 研发   │ 中    │ 50%    │
│  experiment│ 4  │ 实验   │ 低    │ 20%    │
└─────────────────────────────────────────────┘
```

#### 3.2.4 支持的硬件

| 硬件厂商 | 支持状态 | 推理引擎 |
|----------|----------|----------|
| **NVIDIA** | ✅ 完整支持 | vLLM, SGLang, TensorRT-LLM |
| **华为昇腾** | ✅ 完整支持 | Chitu (MindIE) |
| **沐曦** | ✅ 完整支持 | Chitu |
| **海光** | ✅ 完整支持 | Chitu |
| **AMD** | ✅ 支持 | ROCm (vLLM/SGLang) |
| **Intel CPU** | ✅ 支持 | kt-kernel (AMX/AVX) |

---

### 3.3 统一 API 网关

#### 3.3.1 格式转换引擎

```python
# 自动格式转换
class FormatConverter:
    converters = {
        "openai": "claude": OpenAIToClaudeConverter(),
        "claude": "openai": ClaudeToOpenAIConverter(),
        "gemini": "openai": GeminiToOpenAIConverter(),
    }

    def convert(self, request, target_format):
        # 自动检测源格式
        source = detect_format(request)
        # 转换为目标格式
        return self.converters[source][target_format].convert(request)
```

#### 3.3.2 智能路由

```
请求 → 认证 → [路由决策] → 后端

路由决策依据:
├── 模型类型 (LLM / Embedding / Rerank)
├── 用户配额 (剩余额度)
├── 后端健康度 (响应时间 / 错误率)
├── 成本考虑 (本地模型 / 外部 API)
└── 策略规则 (固定路由 / 加权随机)
```

#### 3.3.3 多渠道支持

| 渠道类型 | 配置 | 用途 | 成本 |
|----------|------|------|------|
| **本地模型** | GPU/NPU | 成本低、隐私高 | 固定成本 |
| **OpenAI** | API Key | 高质量模型 | 按次计费 |
| **Claude** | API Key | 长文本能力 | 按次计费 |
| **国内 API** | API Key | 网络优化 | 按次计费 |

#### 3.3.4 API 格式支持

| API 类型 | 状态 | 文档 |
|----------|------|------|
| OpenAI Chat Completions | ✅ | [文档](https://docs.newapi.pro/zh/docs/api/ai-model/chat/openai/create-chat-completion) |
| OpenAI Responses | ✅ | [文档](https://docs.newapi.pro/zh/docs/api/ai-model/chat/openai/create-response) |
| Claude Messages | ✅ | [文档](https://docs.newapi.pro/zh/docs/api/ai-model/chat/create-message) |
| Google Gemini | ✅ | [文档](https://doc.newapi.pro/api/google-gemini-chat) |
| Rerank API | ✅ | [文档](https://docs.newapi.pro/zh/docs/api/ai-model/rerank/create-rerank) |
| Realtime API | ✅ | [文档](https://docs.newapi.pro/zh/docs/api/ai-model/realtime/create-realtime-session) |

---

### 3.4 计费系统

#### 3.4.1 计费模型

```
计费维度:
├── Token 计费 (按使用量)
│   ├── 输入 Token: $0.001 / 1K
│   └── 输出 Token: $0.002 / 1K
├── 按次计费 (API 调用)
│   └── 单价: $0.01 / 次
├── 资源占用计费 (GPU 时间)
│   └── 单价: $0.50 / GPU 小时
└── 订阅制 (包月包年)
    └── 套餐: $99 / 月 (含 10M Token)
```

#### 3.4.2 配额管理

```
用户 → 配额组 → 配额规则

配额组示例:
├── 免费用户
│   ├── 10K Token / 天
│   ├── 3 RPM (每分钟请求数)
│   └── 1 模型
├── 专业版
│   ├── 1M Token / 月
│   ├── 60 RPM
│   └── 10 模型
└── 企业版
    ├── 无限 Token
    ├── 1000 RPM
    └── 无限模型 + 专属资源池
```

#### 3.4.3 支付集成

| 支付方式 | 适用场景 | 集成难度 |
|----------|----------|----------|
| **在线支付** | 小额个人用户 | 中 |
| **企业转账** | 大型企业客户 | 低 |
| **预付费** | 高频用户 | 中 |
| **后付费** | 信用客户 | 高 |

**集成支付网关**:
- 国内：支付宝、微信支付、易支付
- 国际：Stripe、PayPal

#### 3.4.4 账单管理

```
账单周期:
├── 按天（免费用户）
├── 按月（专业版）
└── 按年（企业版，可月结）

账单内容:
├── Token 使用明细（按模型、按时间）
├── API 调用统计
├── 资源占用时长
└── 费用汇总
```

---

### 3.5 模型微调

#### 3.5.1 微调工作流

```
┌────────────┐    ┌────────────┐    ┌────────────┐
│ 数据准备   │ →  │ 训练任务   │ →  │ 模型评估   │
│ • 上传数据 │    │ • LoRA     │    │ • 测试集   │
│ • 数据验证 │    │ • Full Finetune│  │ • 指标对比 │
└────────────┘    └────────────┘    └────────────┘
                          │
                          ▼
                   ┌────────────┐
                   │ 模型发布   │
                   │ • 版本管理 │
                   │ • A/B 测试 │
                   └────────────┘
```

#### 3.5.2 资源高效微调

**DeepSeek-V3 (671B) 微调配置**:

| 配置项 | 值 | 说明 |
|--------|-----|------|
| **GPU** | 70GB | 多卡分布式 |
| **RAM** | 1.3TB | CPU 内存 |
| **算法** | LoRA + CPU Offload | kt-kernel 异构 |
| **吞吐** | ~40 tokens/s | 实测性能 |

#### 3.5.3 微调方法支持

| 方法 | 显存需求 | 训练速度 | 适用场景 |
|------|----------|----------|----------|
| **LoRA** | 低 | 中 | 大多数场景 |
| **Full Fine-tuning** | 高 | 快 | 完全定制 |
| **QLoRA** | 极低 | 慢 | 显存受限 |
| **Adapter** | 低 | 中 | 多任务 |

#### 3.5.4 LLaMA-Factory 集成

```bash
# 微调示例
USE_KT=1 llamafactory-cli train \
  examples/train_lora/deepseek3_lora_sft_kt.yaml

# 参数说明
# --use-kt: 启用 KTransformers 优化
# --kt-method: AMXINT4 / AMXINT8 / LLAMAFILE
# --kt-cpuinfer: CPU 推理线程数
```

---

### 3.6 监控与可观测性

#### 3.6.1 多层级监控

```
┌─────────────────────────────────────────────┐
│  业务层监控                                  │
│  • API 调用量 / 成功率 / 延迟               │
│  • 模型调用量 / Token 消耗                   │
│  • 用户活跃度 / 配额使用                     │
├─────────────────────────────────────────────┤
│  服务层监控                                  │
│  • QPS / TPS / 并发数                       │
│  • 队列深度 / 响应时间                       │
│  • 错误率 / 超时率                           │
├─────────────────────────────────────────────┤
│  基础设施监控                                │
│  • GPU 利用率 / 温度 / 显存                  │
│  • CPU / 内存 / 网络 / 磁盘                  │
│  • 容器状态 / Pod 健康度                     │
└─────────────────────────────────────────────┘
```

#### 3.6.2 告警规则

| 指标 | 阈值 | 级别 | 动作 |
|------|------|------|------|
| GPU 利用率 | > 95% | 警告 | 记录日志 |
| GPU 温度 | > 85°C | 紧急 | 自动降频 |
| API 错误率 | > 5% | 严重 | 发送告警 |
| 响应时间 | > 5s | 警告 | 扩容触发 |
| 队列深度 | > 100 | 警告 | 弹性扩容 |

#### 3.6.3 监控指标导出

```
Prometheus 指标:
├── tokenmachine_api_requests_total
├── tokenmachine_api_latency_seconds
├── tokenmachine_model_tokens_total
├── tokenmachine_gpu_utilization_percent
├── tokenmachine_queue_depth
└── tokenmachine_worker_health_status

Grafana 面板:
├── API 性能仪表盘
├── GPU 资源监控
├── 模型调用统计
└── 成本分析报表
```

---

### 3.7 多租户与权限

#### 3.7.1 租户模型

```
组织 (Organization)
├── 团队 (Team)
│   ├── 用户 (User)
│   │   ├── API Keys
│   │   ├── 模型权限
│   │   └── 配额
│   └── 资源池
└── 计费账户
```

#### 3.7.2 RBAC 权限模型

| 角色 | 权限范围 | 操作权限 |
|------|----------|----------|
| **系统管理员** | 全局 | 全部权限 |
| **组织管理员** | 组织 | 组织内全部权限 |
| **团队负责人** | 团队 | 团队资源管理、成员管理 |
| **开发者** | 团队 | 模型部署、调试、查看监控 |
| **只读用户** | 团队 | 查看监控、报表 |

#### 3.7.3 资源隔离

```
隔离级别:
├── 物理隔离（不同 GPU 池）
├── 逻辑隔离（资源配额）
└── 网络隔离（VPC / Namespace）
```

---

## 4. 技术栈

### 4.1 后端架构

```
语言: Python 3.10+
├── Web 框架: FastAPI
├── 数据库: PostgreSQL / MySQL / SQLite
├── 缓存: Redis
├── 消息队列: Kafka / RabbitMQ
├── 任务调度: Celery / Temporal
├── ORM: SQLModel
└── 指标: Prometheus + Grafana
```

### 4.2 推理引擎集成

```
推理引擎插件系统:
├── vllm_backend.py    (vLLM)
├── sglang_backend.py  (SGLang)
├── chitu_backend.py   (Chitu)
├── kt_kernel.py       (KTransformers)
└── custom_backend.py  (自定义)

基类接口:
class InferenceBackend(ABC):
    @abstractmethod
    def load_model(model_path: str, config: Dict): ...

    @abstractmethod
    def generate(prompt: str, **kwargs) -> Response: ...

    @abstractmethod
    def health_check() -> bool: ...
```

### 4.3 前端技术栈

```
框架: React 18 + TypeScript
├── UI 组件: Ant Design Pro
├── 状态管理: Jotai / Zustand
├── 图表: ECharts / D3.js
├── 代码编辑: Monaco Editor
├── 终端: xterm.js
└── 构建工具: Umi Max
```

### 4.4 部署技术

```
容器化:
├── Docker / Docker Compose
├── Kubernetes (Helm Charts)
└── 镜像仓库: Docker Hub / Harbor

CI/CD:
├── GitHub Actions
├── GitLab CI
└── Jenkins
```

---

## 5. 部署方案

### 5.1 Docker 快速部署

```bash
# All-in-One 快速开始
docker run -d \
  --name tokenmachine \
  -p 80:80 \
  -p 10161:10161 \
  -v tokenmachine-data:/var/lib/tokenmachine \
  tokenmachine/tokenmachine:latest

# 访问
open http://localhost
```

### 5.2 Kubernetes 生产部署

```yaml
# Helm Chart 部署
helm install tokenmachine ./charts/tokenmachine \
  --set gpuPool.nvidia=8 \
  --set gpuPool.ascend=4 \
  --set replicas.server=3 \
  --set database.postgresql.enabled=true \
  --set database.redis.enabled=true
```

### 5.3 高可用部署

```
┌──────────────────────────────────────────────┐
│              负载均衡 (Nginx/HAProxy)          │
└──────────────┬───────────────────────────────┘
               │
       ┌───────┴────────┐
       │                │
┌──────▼──────┐  ┌──────▼──────┐
│  Server 1   │  │  Server 2   │  # 3+ 副本
│  (主节点)   │  │  (从节点)   │
└──────┬──────┘  └──────┬──────┘
       │                │
       └────────┬───────┘
                │
       ┌────────▼─────────┐
       │  共享数据库集群   │
       │  PostgreSQL 集群  │
       └──────────────────┘
```

---

## 6. 实施路线

### Phase 1: MVP（最小可行产品）- 3 天（AI Agent 辅助开发）

**核心功能**（功能不减，AI 加速）:
- ✅ GPU 资源管理（NVIDIA）
- ✅ 模型部署（vLLM 后端）
- ✅ OpenAI 兼容 API
- ✅ 基础监控（Prometheus）
- ✅ API Key 认证

**AI Agent 辅助开发计划**:

#### 📅 第 1 天：基础架构与核心服务

**上午（4小时）**
- 🤖 AI Agent: 生成 FastAPI 项目脚手架
  - 项目结构、配置文件、依赖管理
  - Docker Compose 配置
  - 数据库连接池设置
- 🤖 AI Agent: 创建数据库模型（SQLModel）
  - users, models, deployments, api_keys, usage_logs
  - Alembic 数据库迁移脚本
- 🤖 AI Agent: 实现配置管理系统
  - YAML/环境变量配置
  - 配置验证和热重载

**下午（4小时）**
- 🤖 AI Agent: 实现 GPU 检测与资源管理
  - NVIDIA GPU 检测（nvidia-smi 包装）
  - GPU 分配算法（Spread/Binpack 策略）
  - 资源池管理器
- 🤖 AI Agent: 构建 RESTful API 框架
  - 路由注册、中间件、错误处理
  - 请求验证（Pydantic）
  - API 文档（OpenAPI 3.0）
- 🤖 AI Agent: 实现基础认证系统
  - API Key 生成与验证
  - JWT Token 支持
  - 权限中间件

**第 1 天交付物**:
- ✅ 可运行的项目框架
- ✅ 数据库表结构完整
- ✅ GPU 资源检测和分配
- ✅ 基础 API 和认证系统

---

#### 📅 第 2 天：模型部署与推理引擎

**上午（4小时）**
- 🤖 AI Agent: 集成 vLLM 后端
  - vLLM Python SDK 封装
  - 模型加载器（HuggingFace/ModelScope）
  - 模型进度跟踪和下载管理
- 🤖 AI Agent: 实现模型生命周期管理
  - 模型启动/停止/重启
  - 健康检查和自动恢复
  - 容器化部署（Docker SDK）
- 🤖 AI Agent: 创建 Worker 服务
  - 分布式任务调度
  - GPU 绑定和资源隔离
  - 日志收集和流式输出

**下午（4小时）**
- 🤖 AI Agent: 实现推理服务
  - vLLM 推理接口封装
  - 批处理优化
  - 流式响应支持（SSE）
- 🤖 AI Agent: 构建模型部署 API
  - POST /v1/models/deploy
  - PATCH /v1/models/deployments/{id}
  - DELETE /v1/models/deployments/{id}
  - 部署状态查询
- 🤖 AI Agent: 实现模型版本管理
  - 版本存储和索引
  - 模型指纹校验
  - 快速切换和回滚

**第 2 天交付物**:
- ✅ 完整的模型部署系统
- ✅ vLLM 推理引擎集成
- ✅ 模型生命周期管理
- ✅ 部署 API 和版本控制

---

#### 📅 第 3 天：API 网关、监控与部署

**上午（4小时）**
- 🤖 AI Agent: 实现 OpenAI 兼容 API
  - POST /v1/chat/completions
  - POST /v1/completions
  - GET /v1/models
  - 流式和非流式响应
- 🤖 AI Agent: 构建请求路由系统
  - 模型匹配和转发
  - 负载均衡（Round Robin）
  - 失败重试和熔断
- 🤖 AI Agent: 实现监控指标导出
  - Prometheus metrics endpoint
  - 核心指标（QPS、延迟、GPU 利用率）
  - 自定义业务指标

**下午（4小时）**
- 🤖 AI Agent: 编写测试用例
  - 单元测试（pytest）
  - API 集成测试
  - 端到端测试（E2E）
- 🤖 AI Agent: 配置生产部署
  - Docker 镜像构建优化
  - Docker Compose 编排
  - 健康检查和启动脚本
- 🤖 AI Agent: 编写文档和脚本
  - README（快速开始指南）
  - API 使用示例
  - 部署脚本（deploy.sh）

**第 3 天交付物**:
- ✅ OpenAI 兼容 API
- ✅ Prometheus 监控集成
- ✅ 完整的测试覆盖
- ✅ 生产级 Docker 部署

---

**开发效率提升策略**:

| 传统开发方式 | AI Agent 辅助 | 效率提升 |
|------------|-------------|---------|
| 手写脚手架代码 | AI 生成标准模板 | **10x** |
| 查阅文档和示例 | AI 直接生成实现 | **5x** |
| 调试和测试 | AI 生成测试用例 | **3x** |
| 编写配置和脚本 | AI 自动化生成 | **8x** |
| 代码审查和优化 | AI 实时建议 | **4x** |

**AI Agent 技术栈**:
- **Claude Code** (claude.ai/code) - 代码生成和重构
- **GitHub Copilot** - 代码补全和建议
- **Cursor AI** - 智能代码编辑
- **v0.dev** - UI 组件快速生成（如需前端）

**关键成功因素**:
1. ✅ **明确的代码规范** - AI 生成代码风格一致
2. ✅ **模块化设计** - 每个 Agent 负责独立模块
3. ✅ **持续验证** - 每小时运行测试确保质量
4. ✅ **人类监督** - 开发者审核 AI 生成的关键代码
5. ✅ **增量开发** - 小步快跑，频繁集成

**目标**: 3天内交付可商用的 MVP，验证产品方向，获取早期用户

**风险缓解**:
- 🔄 代码质量：AI 生成代码后立即 Code Review
- 🔄 集成问题：使用标准化接口和契约测试
- 🔄 性能优化：基于 GPUStack 等成熟项目的最佳实践

---

### Phase 2: 增强版 - 3 个月

**新增功能**:
- ➕ 计费系统（Token 计费）
- ➕ 多租户支持
- ➕ SGLang 后端
- ➕ 模型版本管理
- ➕ 灰度发布
- ➕ SSO 登录（OIDC / SAML）

**里程碑**:
- Week 1-4: 计费和多租户
- Week 5-8: 模型管理增强
- Week 9-12: 企业认证集成

**目标**: 建立商业闭环，开始收费

---

### Phase 3: 企业版 - 6 个月

**新增功能**:
- ➕ 国产芯片支持（Chitu 集成）
- ➕ CPU+GPU 异构推理
- ➕ 模型微调（KTransformers 集成）
- ➕ 格式转换网关
- ➕ 高级 RBAC
- ➕ 审计日志
- ➕ 合规功能（等保三级）

**里程碑**:
- Month 1-2: Chitu 集成
- Month 3-4: 模型微调
- Month 5-6: 企业功能完善

**目标**: 服务企业客户，建立品牌

---

### Phase 4: 生态版 - 持续迭代

**新增功能**:
- ➕ 插件市场
- ➕ API 开放平台
- ➕ 移动端 App
- ➕ 第三方集成（Jira、Slack、飞书）
- ➕ 模型市场
- ➕ 开发者社区

**目标**: 构建生态壁垒

---

## 7. 商业模式

### 7.1 收费模式

```
┌─────────────────────────────────────────────┐
│  社区版 (免费)                              │
│  • 最多 4 GPU                               │
│  • 单租户                                   │
│  • 社区支持                                 │
│  • 基础监控                                 │
├─────────────────────────────────────────────┤
│  专业版 ($999 / 月)                         │
│  • 最多 32 GPU                              │
│  • 多租户 (10 租户)                         │
│  • 邮件支持 (48h 响应)                      │
│  • 计费系统                                 │
├─────────────────────────────────────────────┤
│  企业版 ($4,999 / 月)                       │
│  • 无限 GPU                                 │
│  • 无限租户                                 │
│  • 专属支持 + SLA (4h 响应)                │
│  • 定制开发                                 │
│  • 国产芯片支持                             │
│  • 模型微调                                 │
└─────────────────────────────────────────────┘
```

### 7.2 增值服务

| 服务 | 价格 | 说明 |
|------|------|------|
| **部署服务** | $5,000 起 | 上门部署、环境配置 |
| **培训服务** | $3,000 / 天 | 技术培训、最佳实践 |
| **定制开发** | $200 / 小时 | 定制功能开发 |
| **技术支持** | 20% / 年 | 优先技术支持 |

### 7.3 私有化部署

```
企业版私有化部署:
├── 永久授权: $49,999
├── 年度订阅: $9,999 / 年
└── 包含:
    ├── 无限 GPU
    ├── 无限租户
    ├── 源码访问
    ├── 专属支持
    └── 定制化开发
```

---

## 8. 竞争优势

### 8.1 vs 纯开源方案（GPUStack）

| 功能 | GPUStack | 本方案 |
|------|----------|--------|
| GPU 集群管理 | ✅ | ✅ |
| 多推理引擎 | ✅ | ✅ |
| 计费系统 | ❌ | ✅ |
| 多租户 | ⚠️ 基础 | ✅ 企业级 |
| 格式转换 | ❌ | ✅ |
| 模型微调 | ❌ | ✅ |
| 国产芯片 | ⚠️ 部分 | ✅ 广泛支持 |
| 商业支持 | 社区 | ✅ 专属 |

### 8.2 vs SaaS 方案（OpenAI）

| 维度 | OpenAI | 本方案 |
|------|--------|--------|
| 数据隐私 | 云端 | ✅ 私有化 |
| 成本 | 按次计费 | ✅ 固定成本 |
| 定制化 | 有限 | ✅ 完全可控 |
| 国产化 | ❌ | ✅ 支持 |
| 离线部署 | ❌ | ✅ 支持 |

### 8.3 vs 其他开源方案

| 方案 | 优势 | 劣势 |
|------|------|------|
| **LocalAI** | 轻量级 | 功能简单 |
| **Text-Generation-WebUI** | 易用 | 无管理功能 |
| **FastChat** | 多模型支持 | 无计费 |
| **OpenLLMetry** | 监控强 | 无部署 |
| **本方案** | 全功能 | 学习曲线 |

### 8.4 核心竞争力

1. **全栈能力**: 从部署到计费到微调，一站式解决方案
2. **国产化支持**: 完整支持昇腾、沐曦、海光等国产芯片
3. **异构计算**: CPU+GPU 混合推理，降低硬件门槛
4. **企业级**: 多租户、RBAC、审计、合规
5. **开源友好**: Apache 2.0 许可，商用无忧

---

## 9. 风险与挑战

### 9.1 技术风险

| 风险 | 影响 | 应对措施 |
|------|------|----------|
| 国产芯片生态不成熟 | 中 | 多后端支持，降低依赖 |
| 性能优化难度 | 高 | 参考成熟项目，逐步优化 |
| 兼容性问题 | 中 | 充分测试，提供兼容性列表 |

### 9.2 市场风险

| 风险 | 影响 | 应对措施 |
|------|------|----------|
| 竞品价格战 | 高 | 差异化定位，强调本土化 |
| 技术迭代快 | 中 | 保持技术跟进，快速迭代 |
| 客户教育成本 | 中 | 完善文档，降低上手门槛 |

### 9.3 运营风险

| 风险 | 影响 | 应对措施 |
|------|------|----------|
| 支持成本高 | 高 | 自动化运维，知识库建设 |
| 人才需求 | 中 | 培训体系，人才储备 |

---

## 10. 总结

本产品设计方案综合了四个优秀开源项目的优势：

| 来源 | 核心贡献 |
|------|----------|
| **GPUStack** | GPU 集群管理、多推理引擎、OpenAI 兼容 API |
| **New API** | 计费系统、多渠道智能路由、格式转换 |
| **Chitu** | 国产芯片支持、生产级稳定性、异构推理 |
| **KTransformers** | CPU-GPU 异构计算、MoE 优化、模型微调 |

**产品核心价值**：
1. **降本**: 私有化部署，一次投入长期使用
2. **灵活**: 支持多种硬件、多种模型
3. **可控**: 数据不出域，完全自主可控
4. **易用**: 一键部署，开箱即用

**目标市场**：
- 需要私有化部署的企业
- AI 创业公司
- 研究机构
- 对数据隐私有要求的组织

---

## 11. 数据库设计

### 11.1 核心数据模型

```sql
-- 用户表
CREATE TABLE users (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    username VARCHAR(255) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role ENUM('admin', 'user', 'readonly') DEFAULT 'user',
    organization_id BIGINT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_org (organization_id)
);

-- 组织表
CREATE TABLE organizations (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(255) UNIQUE NOT NULL,
    plan ENUM('free', 'professional', 'enterprise') DEFAULT 'free',
    quota_tokens BIGINT DEFAULT 10000,
    quota_models INT DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 模型表
CREATE TABLE models (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(255) NOT NULL,
    version VARCHAR(50) NOT NULL,
    source ENUM('huggingface', 'modelscope', 'local') NOT NULL,
    category ENUM('llm', 'embedding', 'image', 'reranker', 'tts', 'stt') NOT NULL,
    quantization ENUM('fp16', 'int8', 'fp4', 'fp8') DEFAULT 'fp16',
    status ENUM('downloading', 'ready', 'error') DEFAULT 'downloading',
    storage_path VARCHAR(1024),
    UNIQUE KEY uk_model_version (name, version),
    INDEX idx_category (category),
    INDEX idx_status (status)
);

-- 模型部署表
CREATE TABLE model_deployments (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    model_id BIGINT NOT NULL,
    name VARCHAR(255) NOT NULL,
    environment ENUM('dev', 'test', 'staging', 'prod') NOT NULL,
    replicas INT DEFAULT 1,
    gpu_per_replica INT DEFAULT 1,
    backend VARCHAR(50) NOT NULL,
    status ENUM('starting', 'running', 'stopping', 'stopped', 'error') NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (model_id) REFERENCES models(id),
    INDEX idx_env (environment),
    INDEX idx_status (status)
);

-- API Key 表
CREATE TABLE api_keys (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    key_hash VARCHAR(255) UNIQUE NOT NULL,
    user_id BIGINT NOT NULL,
    name VARCHAR(255) NOT NULL,
    scopes JSON NOT NULL,
    quota_tokens BIGINT DEFAULT 0,
    quota_requests BIGINT DEFAULT 0,
    expires_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id),
    INDEX idx_user (user_id)
);

-- 使用记录表
CREATE TABLE usage_logs (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    api_key_id BIGINT NOT NULL,
    model_id BIGINT NOT NULL,
    input_tokens INT DEFAULT 0,
    output_tokens INT DEFAULT 0,
    latency_ms INT,
    status ENUM('success', 'error') NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (api_key_id) REFERENCES api_keys(id),
    FOREIGN KEY (model_id) REFERENCES models(id),
    INDEX idx_api_key (api_key_id),
    INDEX idx_created (created_at)
);

-- 账单表
CREATE TABLE invoices (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    organization_id BIGINT NOT NULL,
    amount DECIMAL(10, 2) NOT NULL,
    currency VARCHAR(3) DEFAULT 'USD',
    status ENUM('pending', 'paid', 'cancelled') DEFAULT 'pending',
    period_start DATE NOT NULL,
    period_end DATE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (organization_id) REFERENCES organizations(id),
    INDEX idx_org (organization_id),
    INDEX idx_status (status)
);
```

### 11.2 数据库索引优化

```sql
-- 高频查询索引
CREATE INDEX idx_api_key_created ON usage_logs(api_key_id, created_at);
CREATE INDEX idx_model_status ON model_deployments(model_id, status);
CREATE INDEX idx_user_org ON users(organization_id, role);

-- 分析型查询优化
CREATE INDEX idx_usage_analytics ON usage_logs(
    created_at, model_id, status
) PARTITION BY RANGE (YEAR(created_at));

-- 全文搜索
CREATE FULLTEXT INDEX ft_model_search ON models(name, version);
```

---

## 12. API 设计

### 12.1 RESTful API 规范

#### 基础规范

```
Base URL: https://api.tokenmachine.com/v1
认证方式: Bearer Token (API Key)
响应格式: JSON
字符编码: UTF-8
```

#### 通用响应格式

```json
{
  "code": 0,
  "message": "success",
  "data": {},
  "request_id": "req_1234567890"
}
```

#### 错误响应格式

```json
{
  "code": 1001,
  "message": "Invalid API key",
  "details": {
    "field": "authorization",
    "reason": "API key expired"
  },
  "request_id": "req_1234567890"
}
```

### 12.2 核心 API 端点

#### 模型管理 API

```http
# 列出所有模型
GET /v1/models
Authorization: Bearer {api_key}

响应:
{
  "code": 0,
  "data": {
    "object": "list",
    "data": [
      {
        "id": "model_123",
        "name": "Qwen2.5-7B-Instruct",
        "version": "v2.0",
        "category": "llm",
        "status": "ready",
        "created_at": "2025-01-12T00:00:00Z"
      }
    ]
  }
}

# 部署模型
POST /v1/models/deploy
Authorization: Bearer {api_key}
Content-Type: application/json

{
  "model_id": "model_123",
  "environment": "production",
  "replicas": 2,
  "gpu_per_replica": 1,
  "backend": "vllm",
  "backend_params": {
    "tensor_parallel_size": 1,
    "max_model_len": 4096
  }
}

# 更新模型部署
PATCH /v1/models/deployments/{deployment_id}
Authorization: Bearer {api_key}
Content-Type: application/json

{
  "replicas": 4,
  "traffic_weight": 100
}

# 停止模型部署
DELETE /v1/models/deployments/{deployment_id}
Authorization: Bearer {api_key}
```

#### OpenAI 兼容 API

```http
# 聊天补全
POST /v1/chat/completions
Authorization: Bearer {api_key}
Content-Type: application/json

{
  "model": "qwen2.5-7b-instruct",
  "messages": [
    {"role": "user", "content": "Hello!"}
  ],
  "temperature": 0.7,
  "max_tokens": 2048,
  "stream": true
}

# 响应 (流式)
data: {"id":"chat_123","choices":[{"delta":{"content":"Hello"}}],"finish_reason":null}
data: {"id":"chat_123","choices":[{"delta":{"content":"! How can I help you?"}}],"finish_reason":"stop"}
data: [DONE]

# 嵌入
POST /v1/embeddings
Authorization: Bearer {api_key}
Content-Type: application/json

{
  "model": "bge-large-en-v1.5",
  "input": "Hello, world!",
  "encoding_format": "float"
}

# Rerank
POST /v1/rerank
Authorization: Bearer {api_key}
Content-Type: application/json

{
  "model": "jina-reranker-v1",
  "query": "机器学习",
  "documents": [
    "机器学习是人工智能的一个分支",
    "今天天气很好"
  ],
  "top_n": 1
}
```

#### 监控 API

```http
# 获取系统状态
GET /v1/monitoring/system
Authorization: Bearer {api_key}

响应:
{
  "code": 0,
  "data": {
    "gpu_total": 8,
    "gpu_used": 5,
    "gpu_utilization": 75.5,
    "model_deployments": {
      "total": 10,
      "running": 8,
      "error": 0
    },
    "api_stats": {
      "qps": 150,
      "latency_p50": 250,
      "latency_p99": 1200
    }
  }
}

# 获取模型指标
GET /v1/monitoring/models/{model_id}?from=2025-01-01&to=2025-01-12
Authorization: Bearer {api_key}

响应:
{
  "code": 0,
  "data": {
    "model_id": "model_123",
    "metrics": {
      "requests_total": 50000,
      "tokens_total": 25000000,
      "avg_latency_ms": 320,
      "error_rate": 0.02
    },
    "time_series": [
      {"timestamp": "2025-01-01T00:00:00Z", "qps": 120, "latency": 300},
      {"timestamp": "2025-01-01T01:00:00Z", "qps": 150, "latency": 320}
    ]
  }
}
```

### 12.3 WebSocket API

```javascript
// 实时日志流
const ws = new WebSocket('wss://api.tokenmachine.com/v1/logs/stream');

ws.onopen = () => {
  ws.send(JSON.stringify({
    action: 'subscribe',
    channels: ['model_deployments', 'system_logs']
  }));
};

ws.onmessage = (event) => {
  const log = JSON.parse(event.data);
  console.log(`[${log.level}] ${log.message}`);
};
```

---

## 13. UI 界面设计

### 13.1 主界面布局

```
┌─────────────────────────────────────────────────────────────┐
│  Logo │ 模型 │ 部署 │ 监控 │ 计费 │ 设置 │ 用户 ▼          │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  📊 仪表盘                                            │   │
│  ├─────────────────────────────────────────────────────┤   │
│  │  • API 调用量 (今日): 125,430                        │   │
│  │  • Token 消耗 (本月): 12.5M / 100M                  │   │
│  │  • GPU 利用率: 78.5%                                 │   │
│  │  • 运行模型: 8 / 10                                  │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  🤖 模型部署                                          │   │
│  ├─────────────────────────────────────────────────────┤   │
│  │  模型 │ 版本 │ 状态 │ 副本 │ QPS │ 延迟 │ 操作      │   │
│  │  Qwen2.5-7B │ v2.0 │ 🟢 │ 2  │ 45 │ 250 │ [编辑]    │   │
│  │  DeepSeek-R1 │ v1.0 │ 🟢 │ 4  │ 12 │ 800 │ [编辑]    │   │
│  │  GLM-4 │ v3.0 │ 🟡 │ 1  │ 23 │ 420 │ [编辑]    │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  📈 实时监控                                          │   │
│  ├─────────────────────────────────────────────────────┤   │
│  │  [GPU 利用率折线图] [API QPS 柱状图]                  │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### 13.2 模型部署向导

```
步骤 1: 选择模型
┌─────────────────────────────────────────────────┐
│  📦 模型仓库                                     │
├─────────────────────────────────────────────────┤
│  搜索: [Qwen            ] [类别▼] [筛选▼]      │
│                                                  │
│  ┌───────────────────────────────────────────┐  │
│  │ Qwen2.5-7B-Instruct                      │  │
│  │ 💬 对话 • 14B 参数 • FP8/INT8            │  │
│  │ [选择模型]                               │  │
│  └───────────────────────────────────────────┘  │
│  ┌───────────────────────────────────────────┐  │
│  │ DeepSeek-R1-Distill-Qwen-32B            │  │
│  │ 💬 对话 • 67B 参数 • FP8                │  │
│  │ [选择模型]                               │  │
│  └───────────────────────────────────────────┘  │
│                                                  │
│                 [上一步]  [下一步 →]            │
└─────────────────────────────────────────────────┘

步骤 2: 配置参数
┌─────────────────────────────────────────────────┐
│  ⚙️ 配置部署参数                                │
├─────────────────────────────────────────────────┤
│  模型: Qwen2.5-7B-Instruct (v2.0)              │
│                                                  │
│  环境名称: [production        ]                 │
│  副本数:   [2        ] 副本                     │
│  GPU/副本: [1        ] GPU                      │
│                                                  │
│  推理引擎:                                         │
│  ○ vLLM (推荐)                                   │
│  ○ SGLang                                         │
│  ○ Chitu (国产芯片)                               │
│                                                  │
│  高级参数 [展开 ▼]:                               │
│    最大上下文: [4096    ] tokens                 │
│    批处理大小: [32      ]                        │
│    量化方式:   [FP8 ▼]                          │
│                                                  │
│                 [← 上一步]  [下一步 →]          │
└─────────────────────────────────────────────────┘

步骤 3: 确认部署
┌─────────────────────────────────────────────────┐
│  ✅ 确认部署                                     │
├─────────────────────────────────────────────────┤
│  部署配置摘要:                                    │
│  • 模型: Qwen2.5-7B-Instruct v2.0                │
│  • 副本: 2                                       │
│  • GPU 总数: 2                                   │
│  • 推理引擎: vLLM                                │
│  • 预计显存: ~14GB                               │
│                                                  │
│  成本估算:                                        │
│  • GPU 时间: ~$50 / 月                          │
│  • 存储: ~20GB                                  │
│                                                  │
│                 [← 上一步]  [开始部署 →]        │
└─────────────────────────────────────────────────┘
```

### 13.3 监控大屏

```
┌─────────────────────────────────────────────────────────────────────┐
│                    📊 TokenMachine 监控中心                         │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐  │
│  │  API 调用量统计   │  │  GPU 资源使用    │  │  模型性能排行    │  │
│  │  [折线图]         │  │  [饼图]          │  │  [柱状图]        │  │
│  │  今日: 125,430   │  │  已用: 78.5%     │  │  1. Qwen2.5-7B  │  │
│  │  本月: 3.2M      │  │  空闲: 21.5%     │  │  2. DeepSeek-R1│  │
│  └──────────────────┘  └──────────────────┘  └──────────────────┘  │
│                                                                      │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │  实时日志流                                                      │ │
│  ├────────────────────────────────────────────────────────────────┤ │
│  │  [2025-01-12 10:23:45] INFO  Model qwen2.5-7b started          │ │
│  │  [2025-01-12 10:23:46] INFO  GPU 0 allocated to worker-1       │ │
│  │  [2025-01-12 10:23:47] WARN  GPU 2 temperature high: 84°C   │ │
│  │  [2025-01-12 10:23:48] ERROR Model deepseek-r1 OOM          │ │
│  │  [暂停] [继续]                                               │ │
│  └────────────────────────────────────────────────────────────────┘ │
│                                                                      │
│  ┌──────────────────────┐  ┌──────────────────────┐                │
│  │  告警中心 (3)         │  │  系统健康度: 95%     │                │
│  │  • GPU 温度警告     │  │                      │                │
│  │  • API 延迟警告     │  │  [查看详情]          │                │
│  │  • 磁盘空间警告     │  │                      │                │
│  └──────────────────────┘  └──────────────────────┘                │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 14. 安全设计

### 14.1 认证与授权

```
认证方式:
├── API Key (推荐用于程序调用)
├── JWT Token (推荐用于 Web UI)
├── OAuth 2.0 / OIDC (企业 SSO)
└── SAML (企业 SSO)

授权模型:
└── RBAC (Role-Based Access Control)
    ├── 角色 (Role)
    ├── 权限 (Permission)
    └── 资源 (Resource)
```

### 14.2 API Key 安全

```python
# API Key 生成算法
import secrets
import hashlib

def generate_api_key(user_id: int) -> str:
    # 生成随机部分
    random_part = secrets.token_urlsafe(32)

    # 生成哈希部分
    key_material = f"{user_id}:{random_part}:{time.time()}"
    hash_part = hashlib.sha256(key_material.encode()).hexdigest()[:8]

    # 组合成最终 Key
    api_key = f"tm_{random_part[:16]}{hash_part}"

    return api_key

# 示例: inf_8a3f2e1b9c4d7f6e5a2b1c3d4e5f6a7
```

### 14.3 数据加密

```
传输加密:
├── HTTPS/TLS 1.3 (强制)
└── WebSocket Secure (WSS)

存储加密:
├── API Key: SHA-256 哈希
├── 密码: Argon2 (内存困难函数)
└── 敏感配置: AES-256-GCM
```

### 14.4 审计日志

```sql
CREATE TABLE audit_logs (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    user_id BIGINT,
    action VARCHAR(255) NOT NULL,
    resource_type VARCHAR(50),
    resource_id BIGINT,
    ip_address VARCHAR(45),
    user_agent TEXT,
    status ENUM('success', 'failure') NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_user (user_id),
    INDEX idx_action (action),
    INDEX idx_created (created_at)
);
```

---

## 15. 性能优化

### 15.1 缓存策略

```
缓存层级:
├── L1: 内存缓存 (Redis)
│   ├── API 响应缓存 (TTL: 60s)
│   ├── 模型元数据缓存 (TTL: 300s)
│   └── 用户配额缓存 (TTL: 60s)
├── L2: CDN 缓存 (静态资源)
│   ├── 前端资源 (JS/CSS)
│   └── 模型文件缓存
└── L3: 数据库查询缓存
    ├── 预编译语句
    └── 连接池
```

### 15.2 数据库优化

```sql
-- 读写分离
主库: 写操作
├── 从库 1: 读操作 (API 请求)
├── 从库 2: 读操作 (分析查询)
└── 从库 3: 读操作 (报表生成)

-- 分区策略
按时间分区: usage_logs (按月)
按哈希分区: api_keys (按用户 ID)

-- 慢查询优化
EXPLAIN ANALYZE <query>;
CREATE INDEX CONCURRENTLY idx_name ON table (columns);
```

### 15.3 GPU 资源优化

```python
# 动态批处理
class DynamicBatchScheduler:
    def __init__(self, max_batch_size=32, max_wait_ms=50):
        self.max_batch_size = max_batch_size
        self.max_wait_ms = max_wait_ms
        self.current_batch = []
        self.last_flush = time.time()

    def add_request(self, request):
        self.current_batch.append(request)

        # 触发条件
        if (len(self.current_batch) >= self.max_batch_size or
            (time.time() - self.last_flush) * 1000 >= self.max_wait_ms):
            self.flush()

    def flush(self):
        if self.current_batch:
            # 批量推理
            results = self.model.generate_batch(self.current_batch)
            self.current_batch.clear()
            self.last_flush = time.time()
            return results
```

---

## 16. 运维手册

### 16.1 日常运维

#### 每日检查清单

- [ ] 检查系统健康状态
- [ ] 查看错误日志
- [ ] 验证 GPU 温度正常
- [ ] 检查磁盘空间
- [ ] 查看告警通知

#### 每周任务

- [ ] 清理过期日志
- [ ] 分析性能趋势
- [ ] 检查备份完整性
- [ ] 更新安全补丁

#### 每月任务

- [ ] 容量规划评估
- [ ] 成本分析报告
- [ ] 灾备演练
- [ ] 性能基线测试

### 16.2 故障排查

```bash
# 服务无法启动
docker logs tokenmachine-server
docker inspect tokenmachine-server

# GPU 不可用
nvidia-smi
lspci | grep -i nvidia

# 模型加载失败
ls -lh /var/lib/tokenmachine/models/
docker exec tokenmachine-worker df -h

# API 响应慢
# 1. 检查队列深度
curl http://localhost:80/v1/monitoring/queue

# 2. 检查 GPU 利用率
nvidia-smi dmon -s u

# 3. 检查数据库连接
psql -h localhost -U tokenmachine -c "SELECT COUNT(*) FROM usage_logs;"
```

### 16.3 备份与恢复

```bash
# 数据库备份
pg_dump -U tokenmachine tokenmachine_db > backup_$(date +%Y%m%d).sql

# 模型文件备份
rsync -avz /var/lib/tokenmachine/models/ /backup/models/

# 配置文件备份
tar -czf config_backup_$(date +%Y%m%d).tar.gz /etc/tokenmachine/

# 恢复流程
# 1. 停止服务
docker-compose down

# 2. 恢复数据库
psql -U tokenmachine tokenmachine_db < backup_20250112.sql

# 3. 恢复模型文件
rsync -avz /backup/models/ /var/lib/tokenmachine/models/

# 4. 恢复配置
tar -xzf config_backup_20250112.tar.gz -C /

# 5. 启动服务
docker-compose up -d
```

---

## 17. 市场推广策略

### 17.1 目标客户

| 客户类型 | 痛点 | 解决方案 | 获客渠道 |
|----------|------|----------|----------|
| **企业 IT 部门** | 数据安全、成本控制 | 私有化部署、计费 | 行业会议、LinkedIn |
| **AI 创业公司** | 快速迭代、降低成本 | 一键部署、多模型支持 | 技术社区、GitHub |
| **研究机构** | 大模型训练、资源有限 | 模型微调、异构计算 | 学术会议、论文 |
| **SaaS 公司** | API 调用成本高 | 固定成本、无限使用 | 广告、内容营销 |

### 17.2 定价策略

```
渗透定价法:
├── 社区版 (免费) - 获取用户
├── 专业版 ($999/月) - 中小企业
└── 企业版 ($4,999/月) - 大客户

价值定价法:
├── 按 GPU 数量定价
├── 按功能模块定价
└── 按支持级别定价

捆绑销售:
├── 部署服务 + 软件许可
├── 培训服务 + 技术支持
└── 私有化 + 云端托管
```

### 17.3 推广渠道

```
线上渠道:
├── GitHub (开源版)
├── 技术博客 / Medium
├── YouTube 教程
├── Twitter / LinkedIn
└── Reddit (r/MachineLearning)

线下渠道:
├── 行业会议 (PyCon, AI Summit)
├── 线下沙龙 / Meetup
├── 企业培训
└── 合作伙伴渠道

合作伙伴:
├── 云服务商 (阿里云、腾讯云)
├── 硬件厂商 (华为、沐曦)
├── 系统集成商
└── 独立软件供应商 (ISV)
```

---

## 附录

### A. 参考资料

- [GPUStack GitHub](https://github.com/gpustack/gpustack)
- [New API GitHub](https://github.com/QuantumNous/new-api)
- [Chitu GitHub](https://github.com/thu-pacman/chitu)
- [KTransformers GitHub](https://github.com/kvcache-ai/ktransformers)
- [vLLM 文档](https://docs.vllm.ai/)
- [SGLang 文档](https://docs.sglang.ai/)

### B. 技术术语表

| 术语 | 解释 |
|------|------|
| **LLM** | Large Language Model，大语言模型 |
| **MoE** | Mixture of Experts，混合专家模型 |
| **LoRA** | Low-Rank Adaptation，高效微调方法 |
| **INT4/INT8** | 4/8 比特整数量化 |
| **FP4/FP8/FP16** | 4/8/16 比特浮点数 |
| **VRAM** | Video RAM，显存 |
| **QPS** | Queries Per Second，每秒查询数 |
| **TPS** | Tokens Per Second，每秒生成 Token 数 |
| **RBAC** | Role-Based Access Control，基于角色的访问控制 |

### C. 版本历史

| 版本 | 日期 | 说明 |
|------|------|------|
| v1.0 | 2025-01-12 | 初始版本 |

---

**文档作者**: Claude (AI Assistant)
**最后更新**: 2025-01-12
**许可证**: 本文档基于 CC BY 4.0 许可
