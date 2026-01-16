# Backend Design - 详细设计方案

## 目录
- [1. 核心功能范围](#1-核心功能范围)
- [2. 系统架构设计](#2-系统架构设计)
- [3. Server-Worker 分离架构](#3-server-worker-分离架构)
- [4. 数据库设计](#4-数据库设计)
- [5. API 设计](#5-api-设计)
- [6. 核心功能模块](#6-核心功能模块)
- [7. 部署架构](#7-部署架构)
- [8. 技术选型](#8-技术选型)
- [9. 开发计划](#9-开发计划)

---

## 1. 核心功能范围

### 1.1 核心功能清单

| 模块 | 功能 | 优先级 | 说明 |
|------|------|--------|------|
| **GPU管理** | GPU 资源发现 | P0 | 自动检测可用 GPU |
| | GPU 状态监控 | P0 | 利用率、温度、显存 |
| | GPU 资源分配 | P0 | 模型部署时自动分配 |
| **集群管理** | 集群 CRUD | P0 | 创建、查询、更新、删除集群 |
| | Worker 池管理 | P0 | 动态扩缩容 Worker 池 |
| | 多集群支持 | P0 | 生产、测试、开发环境隔离 |
| **Worker管理** | Worker 注册 | P0 | 自动注册和心跳 |
| | Worker 状态监控 | P0 | CPU、内存、GPU、文件系统 |
| | Worker 调度 | P0 | Spread/Binpack 策略 |
| | 标签选择器 | P1 | 基于 labels 的调度 |
| **模型部署** | 模型仓库集成 | P0 | HuggingFace/ModelScope/本地 |
| | 模型下载 | P0 | 支持断点续传 |
| | 模型版本管理 | P0 | 版本记录和回滚 |
| | 量化变体 | P1 | FP16/INT8/FP4/FP8 |
| | 灰度发布 | P1 | 流量分配 |
| | vLLM 后端集成 | P0 | 默认推理引擎 |
| | 部署状态管理 | P0 | starting/running/stopped/error |
| | 副本管理 | P0 | 单机多副本 |
| **API 网关** | OpenAI Chat API | P0 | /v1/chat/completions |
| | OpenAI Models API | P0 | /v1/models |
| | OpenAI Embeddings API | P1 | /v1/embeddings |
| | 格式转换 | P1 | OpenAI ↔ Claude ↔ Gemini |
| | 智能路由 | P1 | 多渠道支持 |
| | 流式输出 | P0 | SSE 支持 |
| | API Key 认证 | P0 | Bearer Token |
| **计费系统** | Token 计费 | P0 | 输入/输出分别计价 |
| | 配额管理 | P0 | 免费版/专业版/企业版 |
| | 账单生成 | P0 | 按周期生成账单 |
| | 使用记录 | P0 | 详细的调用记录 |
| **多租户** | 组织管理 | P0 | 多组织隔离 |
| | RBAC 权限 | P0 | 角色和权限控制 |
| | 资源配额 | P0 | 按组织分配资源 |
| **监控** | Prometheus 指标 | P0 | GPU/模型/API 指标 |
| | Grafana 面板 | P1 | 基础可视化 |
| | 统计 API | P0 | Dashboard 数据聚合 |
| | 日志记录 | P0 | 结构化日志 |
| | 审计日志 | P1 | 操作审计 |
| **Web UI 支持** | 仪表盘 | P0 | 系统概览和统计 |
| | 模型管理界面 | P0 | 部署/停止模型 |
| | 集群管理界面 | P0 | 集群和 Worker 管理 |
| | 监控面板 | P1 | 实时指标 |
| | API Key 管理 | P0 | 创建/撤销 API Key |
| | 计费管理 | P1 | 账单和使用记录 |

### 1.2 功能边界（不包含）

- ❌ SGLang 后端 (P2)
- ❌ 国产芯片支持 (P2) - Chitu 集成
- ❌ 模型微调 (P2)
- ❌ SSO 登录 (P2)

### 1.3 未来增强功能 (P2)

- ➕ SGLang 后端
- ➕ Chitu 后端（国产芯片）
- ➕ 模型微调（LoRA、Full Fine-tuning）
- ➕ SSO 登录（OIDC / SAML）
- ➕ 支付集成（在线支付）
- ➕ 高级 RBAC

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
│  │  • 认证      │  │  • 集群管理  │  │  • Exporter  │       │
│  │  • 路由      │  │  • Worker管理│  │              │       │
│  │  • 格式转换  │  │  • 模型管理  │  │              │       │
│  │  • 智能路由  │  │  • 调度器    │  │              │       │
│  └──────────────┘  └──────────────┘  └──────────────┘       │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       │
│  │  计费系统    │  │  多租户      │  │  审计日志    │       │
│  │  • Token计费 │  │  • RBAC      │  │  • 操作记录  │       │
│  │  • 配额管理  │  │  • 组织隔离  │  │              │       │
│  │  • 账单生成  │  │              │  │              │       │
│  └──────────────┘  └──────────────┘  └──────────────┘       │
└────────────────────────────┬────────────────────────────────┘
                             │
         ┌───────────────────┼───────────────────┐
         │                   │                   │
┌────────▼────────┐  ┌──────▼──────┐  ┌────────▼────────┐
│   PostgreSQL     │  │    Redis    │  │  Workers        │
│   (数据存储)     │  │   (缓存)    │  │  (推理引擎)     │
│                  │  │             │  │                 │
│  • organizations │  │  • 模型元   │  │  Worker 1       │
│  • users         │  │  • API Key  │  │  Worker 2       │
│  • clusters      │  │  • 配额     │  │  Worker N       │
│  • workers       │  │  • 队列     │  │                 │
│  • models        │  │             │  │  GPU 0, 1...   │
│  • deployments   │  │             │  │                 │
│  • api_keys      │  │             │  │                 │
│  • usage_logs    │  │             │  │                 │
│  • invoices      │  │             │  │                 │
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
│   │       ├── models.py    # 模型管理
│   │       ├── deployments.py # 部署管理
│   │       ├── clusters.py  # 集群管理
│   │       ├── workers.py   # Worker 管理
│   │       ├── api_keys.py  # API Key 管理
│   │       ├── billing.py   # 计费管理
│   │       ├── monitoring.py # 监控统计
│   │       └── users.py     # 用户管理
│   ├── deps.py              # 依赖注入
│   └── middleware.py        # 中间件（认证、限流、RBAC）
├── core/
│   ├── config.py            # 配置管理
│   ├── security.py          # 安全相关
│   ├── gpu.py               # GPU 管理核心
│   ├── rbac.py              # 权限控制
│   └── quota.py             # 配额管理
├── models/
│   ├── database.py          # SQLAlchemy 模型
│   └── schemas.py           # Pydantic 模式
├── services/
│   ├── model_service.py     # 模型服务
│   ├── deployment_service.py # 部署服务
│   ├── gpu_service.py       # GPU 服务
│   ├── cluster_service.py   # 集群服务
│   ├── worker_service.py    # Worker 服务
│   ├── billing_service.py   # 计费服务
│   ├── quota_service.py     # 配额服务
│   └── stats_service.py     # 统计服务
├── gateway/
│   ├── format_converter.py  # 格式转换
│   ├── router.py            # 智能路由
│   └── channels.py          # 渠道管理
├── controllers/            # Server-Worker 通信控制器
│   ├── worker_controller.py
│   ├── instance_controller.py
│   ├── cluster_controller.py
│   └── scheduler.py         # 调度器
├── monitoring/
│   ├── metrics.py           # Prometheus 指标
│   └── exporter.py          # 指标导出器
├── utils/
│   ├── logger.py            # 日志工具
│   └── validators.py        # 验证工具
└── main.py                  # 应用入口
```

#### 2.2.2 Worker 节点

**设计要点**:
- 每个 Worker 独立进程
- 使用 `subprocess.Popen` 管理
- 通过 HTTP/REST 通信
- 自动注册和心跳
- 健康检查和自动重启

---

## 3. Server-Worker 分离架构

### 3.1 架构概述

TokenMachine 采用 Server-Worker 分离架构，将控制平面和数据平面解耦，实现更好的可扩展性和容错性。

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
│  │ • 路由       │  │ • 调度策略   │  │ • Cluster    │          │
│  │ • 认证       │  │ • 资源分配   │  │ • Worker     │          │
│  │ • 限流       │  │ • 负载均衡   │  │ • Instance   │          │
│  │ • 格式转换   │  │ • 标签选择   │  │ • Model      │          │
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
│  │ • 状态上报   │  │ • 副本管理   │  │              │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
│                                                                   │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │                  GPU Resources                           │    │
│  │  GPU 0 │ GPU 1 │ GPU 2 │ GPU 3 │ ...                    │    │
│  └─────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
```

### 3.2 核心概念

| 概念 | 说明 | 示例 |
|------|------|------|
| **Server** | 控制平面，负责任务调度、资源管理、状态维护 | API Server、Scheduler |
| **Worker** | 数据平面，负责模型加载、推理执行、资源上报 | 推理节点 |
| **Cluster** | 逻辑集群，一组 Worker 的集合 | 生产集群、测试集群 |
| **WorkerPool** | Worker 池，用于弹性伸缩的一组 Worker | GPU 池、NPU 池 |
| **Model** | 模型定义，包含模型元数据 | Qwen2.5-7B-Instruct |
| **ModelInstance** | 模型实例，模型在 Worker 上的运行实例 | worker-1 上的 Qwen 实例 |
| **Organization** | 组织，多租户隔离单位 | 企业 A、企业 B |

### 3.3 Server 组件

#### 3.3.1 目录结构

```
backend/server/
├── __init__.py
├── server.py              # Server 主类
├── api/                   # Server API
│   ├── __init__.py
│   ├── workers.py         # Worker 管理 API
│   └── instances.py       # Instance 管理 API
├── controllers/           # 控制器
│   ├── __init__.py
│   ├── worker_controller.py
│   ├── instance_controller.py
│   ├── cluster_controller.py
│   └── model_controller.py
└── client/                # Worker 客户端
    ├── __init__.py
    └── client.py          # HTTP 客户端
```

#### 3.3.2 Server 主类

`backend/server/server.py` - Server 控制平面

**主要功能**:
- 初始化并管理控制器 (WorkerController, ClusterController, ModelInstanceController)
- 启动后台任务（健康检查、状态同步）
- 提供 API 服务

**关键方法**:
```python
async def start()                          # 启动 Server
async def stop()                           # 停止 Server
async def serve(host, port)                # 启动 API 服务
```

#### 3.3.3 控制器

| 控制器 | 文件 | 职责 |
|--------|------|------|
| **ClusterController** | `cluster_controller.py` | 集群 CRUD、Worker 池管理 |
| **WorkerController** | `worker_controller.py` | Worker 节点的 CRUD、状态管理、健康检查 |
| **ModelInstanceController** | `instance_controller.py` | 模型实例管理、健康检查 |
| **ModelController** | `model_controller.py` | 模型定义管理 |
| **Scheduler** | `scheduler.py` | 调度策略、资源分配 |

### 3.4 Worker 组件

#### 3.4.1 目录结构

```
backend/worker/
├── __init__.py
├── worker.py              # Worker 主类
├── config.py              # Worker 配置
├── api/                   # Worker API
│   ├── __init__.py
│   ├── health.py          # 健康检查
│   ├── logs.py            # 日志流
│   ├── status.py          # 状态上报
│   └── proxy.py           # 推理代理
├── serve_manager.py       # 模型服务管理
├── backends/              # 推理后端
│   ├── __init__.py
│   ├── base.py            # 后端抽象
│   ├── vllm_backend.py    # vLLM
│   └── sglang_backend.py  # SGLang (预留)
├── collector.py           # 指标采集
└── exporter.py            # 指标导出
```

#### 3.4.2 Worker 主类

`backend/worker/worker.py` - Worker 数据平面

**主要功能**:
- 向 Server 注册
- 启动模型实例管理
- 定时发送心跳
- 指标采集和上报

**关键方法**:
```python
async def register()                        # 向 Server 注册
async def start()                          # 启动 Worker
async def stop()                           # 停止 Worker
async def _heartbeat_loop()                # 心跳循环
async def _status_report_loop()            # 状态上报循环
```

#### 3.4.3 ServeManager

`backend/worker/serve_manager.py` - 模型服务管理器

**主要功能**:
- 监听分配给 Worker 的模型实例
- 启动/停止推理后端
- 健康检查和状态同步

#### 3.4.4 推理后端

`backend/worker/backends/` - 推理引擎实现

| 后端 | 文件 | 状态 |
|------|------|------|
| **vLLM** | `vllm_backend.py` | ✅ 已实现 |
| **SGLang** | `sglang_backend.py` | 🔧 占位符 |
| **Chitu** | `chitu_backend.py` | 📋 计划中（国产芯片） |

### 3.5 通信协议

| 协议 | 用途 | 说明 |
|------|------|------|
| **HTTP/REST** | 管理 API | Server-Worker 之间的管理通信 |
| **WebSocket** | 日志流 | Worker 日志实时推送到 Server |
| **HTTP** | 推理请求 | 兼容 OpenAI API |

### 3.6 Worker 生命周期

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
                     ▲                │ 错误/超时
                     │                └────────────────┘
```

### 3.7 API 端点

#### 3.7.1 Worker 管理 API

| 方法 | 路径 | 描述 |
|------|------|------|
| POST | `/api/v1/workers/register` | Worker 注册 |
| POST | `/api/v1/workers/{id}/heartbeat` | 心跳上报 |
| POST | `/api/v1/workers/{id}/status` | 状态上报 |
| GET | `/api/v1/workers` | 列出 Workers |
| GET | `/api/v1/workers/{id}` | 获取 Worker 详情 |
| POST | `/api/v1/workers/{id}/drain` | 排空 Worker |
| DELETE | `/api/v1/workers/{id}` | 删除 Worker |

#### 3.7.2 ModelInstance 管理 API

| 方法 | 路径 | 描述 |
|------|------|------|
| POST | `/api/v1/instances` | 创建实例 |
| GET | `/api/v1/instances` | 列出实例 |
| GET | `/api/v1/instances/{id}` | 获取实例详情 |
| PATCH | `/api/v1/instances/{id}/status` | 更新实例状态 |
| DELETE | `/api/v1/instances/{id}` | 删除实例 |

---

## 4. 数据库设计

### 4.1 ER 图

```
┌─────────────┐       ┌─────────────┐       ┌─────────────┐
│Organizations│───────│   Users     │───────│  ApiKeys    │
├─────────────┤ 1   N ├─────────────┤ 1   N ├─────────────┤
│ id (PK)     │       │ id (PK)     │       │ id (PK)     │
│ name        │       │ username    │       │ key_hash     │
│ plan        │       │ email       │       │ key_prefix   │
│ quota_...   │       │ password    │       │ quota_tokens │
│ created_at  │       │ org_id(FK)  │       │ tokens_used  │
└─────────────┘       │ role        │       │ created_at   │
                      └─────────────┘       └─────────────┘
                            │                      │
                            │                      │
                       ┌────▼────┐            ┌───▼───────┐
                       │UsageLogs│            │Invoices   │
                       ├────────┤            ├───────────┤
                       │ api_key │            │ amount     │
                       │ tokens  │            │ status     │
                       └─────────┘            └───────────┘

┌─────────────┐       ┌─────────────┐       ┌─────────────┐
│  Clusters   │───────│WorkerPools  │───────│  Workers    │
├─────────────┤ 1   N ├─────────────┤ 1   N ├─────────────┤
│ id (PK)     │       │ id (PK)     │       │ id (PK)     │
│ name        │       │ cluster_id  │       │ name        │
│ type        │       │ min_workers │       │ cluster_id  │
│ is_default  │       │ max_workers │       │ pool_id     │
└─────────────┘       │ config      │       │ state       │
                      └─────────────┘       │ ip          │
                            │                │ labels      │
                            │                │ status      │
                       ┌────▼────┐            └─────────────┘
                       │ModelInst│                  │
                       ├────────┤                  │
                       │ worker  │           ┌──────▼──────┐
                       │ model   │           │GPU Devices  │
                       │ status  │           ├─────────────┤
                       └─────────┘           │ uuid        │
                             │                │ name        │
┌─────────────┐             │                │ utilization │
│   Models    │─────────────┘                │ temperature │
├─────────────┤                              └─────────────┘
│ id (PK)     │
│ name        │
│ version     │
│ source      │
│ category    │
│ quantiz...  │
│ status      │
└─────────────┘
```

### 4.2 表结构定义

#### 4.2.1 多租户相关表

```sql
-- 组织表（多租户支持）
CREATE TABLE organizations (
    id BIGSERIAL PRIMARY KEY,
    name VARCHAR(255) UNIQUE NOT NULL,
    plan VARCHAR(50) DEFAULT 'free',  -- free, professional, enterprise
    quota_tokens BIGINT DEFAULT 10000,  -- 每月 token 配额
    quota_models INT DEFAULT 1,          -- 可部署模型数
    quota_gpus INT DEFAULT 1,            -- 可使用 GPU 数
    max_workers INT DEFAULT 2,           -- 最大 Worker 数
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 用户表（扩展）
CREATE TABLE users (
    id BIGSERIAL PRIMARY KEY,
    username VARCHAR(255) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    organization_id BIGINT REFERENCES organizations(id),
    role VARCHAR(50) DEFAULT 'user',  -- admin, user, readonly
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (organization_id, username)
);
```

#### 4.2.2 集群和 Worker 表

```sql
-- 集群表
CREATE TABLE clusters (
    id BIGSERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    type VARCHAR(50) NOT NULL,  -- docker, kubernetes, digitalocean, aws
    is_default BOOLEAN DEFAULT FALSE,
    status VARCHAR(50) DEFAULT 'running',  -- running, stopped, error
    config JSONB,  -- provider-specific config
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (name)
);

-- Worker 池表
CREATE TABLE worker_pools (
    id BIGSERIAL PRIMARY KEY,
    cluster_id BIGINT NOT NULL REFERENCES clusters(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    min_workers INT DEFAULT 1,
    max_workers INT DEFAULT 10,
    status VARCHAR(50) DEFAULT 'running',  -- running, scaling, stopped
    config JSONB,  -- docker, k8s, cloud-specific config
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Worker 表
CREATE TABLE workers (
    id BIGSERIAL PRIMARY KEY,
    name VARCHAR(255) UNIQUE NOT NULL,
    cluster_id BIGINT NOT NULL REFERENCES clusters(id) ON DELETE CASCADE,
    pool_id BIGINT REFERENCES worker_pools(id) ON DELETE SET NULL,
    state VARCHAR(50) DEFAULT 'running',  -- running, offline, maintenance
    ip VARCHAR(45),
    port INT DEFAULT 8080,
    labels JSONB,  -- {"gpu": "nvidia", "zone": "us-west-1"}
    status JSONB,  -- {cpu: {...}, memory: {...}, gpu_devices: [...]}
    last_heartbeat TIMESTAMP,
    last_status_update TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### 4.2.3 模型和部署表

```sql
-- 模型表（扩展）
CREATE TABLE models (
    id BIGSERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    version VARCHAR(50) NOT NULL,
    source VARCHAR(50) NOT NULL,  -- huggingface, modelscope, local
    category VARCHAR(50) NOT NULL, -- llm, embedding, reranker
    quantization VARCHAR(10) DEFAULT 'fp16',  -- fp16, int8, fp4, fp8
    path VARCHAR(1024),
    size_gb DECIMAL(10, 2),
    status VARCHAR(50) DEFAULT 'downloading',  -- downloading, ready, error
    download_progress INT DEFAULT 0,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (name, version, quantization)
);

-- 模型部署表（扩展）
CREATE TABLE deployments (
    id BIGSERIAL PRIMARY KEY,
    model_id BIGINT NOT NULL REFERENCES models(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    environment VARCHAR(50) DEFAULT 'production',  -- dev, test, staging, prod
    status VARCHAR(50) DEFAULT 'starting',  -- starting, running, stopped, error
    replicas INT DEFAULT 1,
    traffic_weight INT DEFAULT 100,  -- 灰度发布流量权重
    backend VARCHAR(50) DEFAULT 'vllm',
    config JSONB,  -- 后端配置参数
    health_status JSONB,  -- 每个副本的健康状态
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 模型实例表（新增）
CREATE TABLE model_instances (
    id BIGSERIAL PRIMARY KEY,
    deployment_id BIGINT NOT NULL REFERENCES deployments(id) ON DELETE CASCADE,
    worker_id BIGINT NOT NULL REFERENCES workers(id) ON DELETE CASCADE,
    model_id BIGINT NOT NULL REFERENCES models(id),
    status VARCHAR(50) DEFAULT 'starting',  -- starting, running, stopped, error
    endpoint VARCHAR(255),  -- http://worker-1:8001
    config JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### 4.2.4 GPU 设备表

```sql
-- GPU 设备表（来自 Worker 上报）
CREATE TABLE gpu_devices (
    id BIGSERIAL PRIMARY KEY,
    worker_id BIGINT NOT NULL REFERENCES workers(id) ON DELETE CASCADE,
    uuid VARCHAR(255) NOT NULL,
    name VARCHAR(255) NOT NULL,
    vendor VARCHAR(50),  -- nvidia, amd, apple, ascend, muxi
    index INT NOT NULL,
    core_total INT,
    core_utilization_rate DECIMAL(5, 2),
    memory_total BIGINT,
    memory_used BIGINT,
    memory_allocated BIGINT,
    memory_utilization_rate DECIMAL(5, 2),
    temperature DECIMAL(5, 2),
    state VARCHAR(50) DEFAULT 'available',  -- available, in_use, error
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (worker_id, uuid)
);
```

#### 4.2.5 计费相关表

```sql
-- API Key 表（扩展）
CREATE TABLE api_keys (
    id BIGSERIAL PRIMARY KEY,
    key_hash VARCHAR(255) UNIQUE NOT NULL,
    key_prefix VARCHAR(10) NOT NULL,  -- 用于显示
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    organization_id BIGINT NOT NULL REFERENCES organizations(id),
    name VARCHAR(255) NOT NULL,
    quota_tokens BIGINT DEFAULT 10000000,  -- 10M tokens
    tokens_used BIGINT DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    expires_at TIMESTAMP,
    last_used_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 使用日志表（保持不变）
CREATE TABLE usage_logs (
    id BIGSERIAL PRIMARY KEY,
    api_key_id BIGINT NOT NULL REFERENCES api_keys(id),
    deployment_id BIGINT NOT NULL REFERENCES deployments(id),
    model_id BIGINT NOT NULL REFERENCES models(id),
    input_tokens INT DEFAULT 0,
    output_tokens INT DEFAULT 0,
    total_tokens INT GENERATED ALWAYS AS (input_tokens + output_tokens) STORED,
    latency_ms INT,
    status VARCHAR(50) DEFAULT 'success',  -- success, error
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 账单表（新增）
CREATE TABLE invoices (
    id BIGSERIAL PRIMARY KEY,
    organization_id BIGINT NOT NULL REFERENCES organizations(id),
    amount DECIMAL(10, 2) NOT NULL,
    currency VARCHAR(3) DEFAULT 'USD',
    status VARCHAR(50) DEFAULT 'pending',  -- pending, paid, cancelled
    period_start DATE NOT NULL,
    period_end DATE NOT NULL,
    tokens_used BIGINT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### 4.2.6 审计日志表

```sql
-- 审计日志表（新增）
CREATE TABLE audit_logs (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES users(id),
    organization_id BIGINT REFERENCES organizations(id),
    action VARCHAR(255) NOT NULL,  -- create, update, delete, deploy, stop
    resource_type VARCHAR(50),  -- model, deployment, cluster, worker, api_key
    resource_id BIGINT,
    resource_name VARCHAR(255),
    ip_address VARCHAR(45),
    user_agent TEXT,
    status VARCHAR(50) DEFAULT 'success',  -- success, failure
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### 4.2.7 索引

```sql
-- 组织和用户索引
CREATE INDEX idx_users_org ON users(organization_id);
CREATE INDEX idx_users_role ON users(role);

-- 集群和 Worker 索引
CREATE INDEX idx_clusters_type ON clusters(type);
CREATE INDEX idx_clusters_status ON clusters(status);
CREATE INDEX idx_worker_pools_cluster ON worker_pools(cluster_id);
CREATE INDEX idx_workers_cluster ON workers(cluster_id);
CREATE INDEX idx_workers_pool ON workers(pool_id);
CREATE INDEX idx_workers_state ON workers(state);

-- 模型和部署索引
CREATE INDEX idx_models_category ON models(category);
CREATE INDEX idx_models_status ON models(status);
CREATE INDEX idx_deployments_status ON deployments(status);
CREATE INDEX idx_deployments_model ON deployments(model_id);
CREATE INDEX idx_deployments_env ON deployments(environment);
CREATE INDEX idx_model_instances_deployment ON model_instances(deployment_id);
CREATE INDEX idx_model_instances_worker ON model_instances(worker_id);

-- GPU 设备索引
CREATE INDEX idx_gpu_devices_worker ON gpu_devices(worker_id);
CREATE INDEX idx_gpu_devices_state ON gpu_devices(state);

-- 计费索引
CREATE INDEX idx_api_keys_org ON api_keys(organization_id);
CREATE INDEX idx_api_keys_user ON api_keys(user_id);
CREATE INDEX idx_api_keys_active ON api_keys(is_active);
CREATE INDEX idx_usage_logs_api_key ON usage_logs(api_key_id);
CREATE INDEX idx_usage_logs_created ON usage_logs(created_at);
CREATE INDEX idx_usage_logs_deployment ON usage_logs(deployment_id);
CREATE INDEX idx_invoices_org ON invoices(organization_id);
CREATE INDEX idx_invoices_status ON invoices(status);

-- 审计日志索引
CREATE INDEX idx_audit_logs_user ON audit_logs(user_id);
CREATE INDEX idx_audit_logs_org ON audit_logs(organization_id);
CREATE INDEX idx_audit_logs_action ON audit_logs(action);
CREATE INDEX idx_audit_logs_resource ON audit_logs(resource_type, resource_id);
CREATE INDEX idx_audit_logs_created ON audit_logs(created_at);
```

---

## 5. API 设计

### 5.1 OpenAI 兼容 API

#### 5.1.1 Chat Completions

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

#### 5.1.2 Models

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

#### 5.1.3 Embeddings (可选)

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

### 5.2 管理 API

#### 5.2.1 模型管理

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
      "category": "llm",
      "quantization": "fp16",
      "status": "ready",
      "size_gb": 16.5
    }
  ]
}

# 获取模型详情
GET /api/v1/admin/models/{model_id}

# 删除模型
DELETE /api/v1/admin/models/{model_id}
```

#### 5.2.2 部署管理

```http
# 创建部署
POST /api/v1/admin/deployments
Authorization: Bearer {admin_token}
Content-Type: application/json

{
  "model_id": 1,
  "name": "llama-3-8b-prod",
  "environment": "production",
  "replicas": 2,
  "traffic_weight": 100,
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
    "http://worker-1:8001",
    "http://worker-2:8002"
  ]
}

# 列出部署
GET /api/v1/admin/deployments

# 获取部署详情
GET /api/v1/admin/deployments/{deployment_id}

# 停止部署
DELETE /api/v1/admin/deployments/{deployment_id}

# 更新部署配置
PATCH /api/v1/admin/deployments/{deployment_id}
Content-Type: application/json

{
  "replicas": 4,
  "traffic_weight": 50
}
```

#### 5.2.3 集群管理

```http
# 创建集群
POST /api/v1/admin/clusters
Authorization: Bearer {admin_token}
Content-Type: application/json

{
  "name": "production",
  "type": "kubernetes",
  "is_default": false,
  "config": {
    "namespace": "tokenmachine",
    "replicas": 3
  }
}

# 列出集群
GET /api/v1/admin/clusters

Response:
{
  "clusters": [
    {
      "id": 1,
      "name": "production",
      "type": "kubernetes",
      "is_default": true,
      "status": "running",
      "worker_pools": [
        {
          "id": 1,
          "name": "gpu-pool-1",
          "min_workers": 2,
          "max_workers": 10,
          "status": "running"
        }
      ],
      "created_at": "2025-01-12T00:00:00Z"
    }
  ]
}

# 获取集群详情
GET /api/v1/admin/clusters/{cluster_id}

# 更新集群
PUT /api/v1/admin/clusters/{cluster_id}

# 删除集群
DELETE /api/v1/admin/clusters/{cluster_id}

# 设置默认集群
POST /api/v1/admin/clusters/{cluster_id}/set-default

# 创建 Worker 池
POST /api/v1/admin/clusters/{cluster_id}/pools
Content-Type: application/json

{
  "name": "gpu-pool-2",
  "min_workers": 1,
  "max_workers": 5,
  "config": {
    "docker": {
      "image": "tokenmachine/worker:latest"
    }
  }
}
```

#### 5.2.4 Worker 管理

```http
# Worker 注册（由 Worker 自动调用）
POST /api/v1/workers/register
Content-Type: application/json

{
  "name": "worker-1",
  "cluster_id": 1,
  "pool_id": 1,
  "ip": "192.168.1.10",
  "port": 8080,
  "labels": {
    "gpu": "nvidia",
    "zone": "us-west-1"
  }
}

# 心跳上报（由 Worker 定时调用）
POST /api/v1/workers/{worker_id}/heartbeat

# 状态上报（由 Worker 定时调用）
POST /api/v1/workers/{worker_id}/status
Content-Type: application/json

{
  "cpu": {
    "total": 64,
    "allocated": 32,
    "utilization_rate": 45.5
  },
  "memory": {
    "total": 256000,
    "used": 128000,
    "allocated": 192000,
    "utilization_rate": 50.0
  },
  "gpu_devices": [
    {
      "uuid": "GPU-0",
      "name": "NVIDIA RTX 3090",
      "vendor": "nvidia",
      "index": 0,
      "core_total": 10752,
      "core_utilization_rate": 65.5,
      "memory_total": 25769803264,
      "memory_used": 12884901888,
      "memory_allocated": 10737418240,
      "memory_utilization_rate": 50.0,
      "temperature": 75.0,
      "state": "available"
    }
  ],
  "filesystem": [
    {
      "path": "/var/lib/backend",
      "total": 1000000000000,
      "used": 500000000000,
      "available": 500000000000
    }
  ]
}

# 列出 Workers（管理接口）
GET /api/v1/admin/workers?cluster_id={cluster_id}&state={state}

Response:
{
  "workers": [
    {
      "id": 1,
      "name": "worker-1",
      "cluster_id": 1,
      "pool_id": 1,
      "state": "running",
      "ip": "192.168.1.10",
      "labels": {"gpu": "nvidia"},
      "status": {
        "cpu": {"total": 64, "utilization_rate": 45.5},
        "memory": {"total": 256000, "utilization_rate": 50.0},
        "gpu_devices": [...],
        "filesystem": [...]
      },
      "last_heartbeat": "2025-01-12T10:30:00Z"
    }
  ]
}

# 获取 Worker 详情
GET /api/v1/admin/workers/{worker_id}

# 更新 Worker
PUT /api/v1/admin/workers/{worker_id}
Content-Type: application/json

{
  "state": "maintenance",
  "labels": {"gpu": "nvidia", "zone": "us-west-1", "maintenance": "true"}
}

# 删除 Worker
DELETE /api/v1/admin/workers/{worker_id}

# 排空 Worker（停止所有实例）
POST /api/v1/admin/workers/{worker_id}/drain
```

#### 5.2.5 GPU 设备管理

```http
# 获取所有 GPU 设备
GET /api/v1/admin/gpus

Response:
{
  "gpu_devices": [
    {
      "id": 1,
      "worker_id": 1,
      "worker_name": "worker-1",
      "uuid": "GPU-0",
      "name": "NVIDIA RTX 3090",
      "vendor": "nvidia",
      "index": 0,
      "core_utilization_rate": 65.5,
      "memory_utilization_rate": 50.0,
      "temperature": 75.0,
      "state": "available"
    }
  ]
}

# 获取指定 Worker 的 GPU
GET /api/v1/admin/workers/{worker_id}/gpus
```

#### 5.2.6 API Key 管理

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
  "organization_id": 1,
  "quota_tokens": 100000000,
  "tokens_used": 0
}

# 列出 API Keys
GET /api/v1/admin/api-keys

# 获取 API Key 详情
GET /api/v1/admin/api-keys/{key_id}

# 撤销 API Key
DELETE /api/v1/admin/api-keys/{key_id}
```

#### 5.2.7 计费管理

```http
# 获取组织使用统计
GET /api/v1/admin/billing/usage?organization_id={org_id}&from={date}&to={date}

Response:
{
  "organization_id": 1,
  "period_start": "2025-01-01",
  "period_end": "2025-01-31",
  "total_tokens": 12500000,
  "total_cost": 125.00,
  "by_model": [
    {"model_id": 1, "model_name": "llama-3-8b", "tokens": 10000000, "cost": 100.00}
  ],
  "by_day": [
    {"date": "2025-01-01", "tokens": 500000, "cost": 5.00}
  ]
}

# 生成账单
POST /api/v1/admin/billing/invoices
Content-Type: application/json

{
  "organization_id": 1,
  "period_start": "2025-01-01",
  "period_end": "2025-01-31"
}

# 列出账单
GET /api/v1/admin/billing/invoices?organization_id={org_id}

Response:
{
  "invoices": [
    {
      "id": 1,
      "organization_id": 1,
      "amount": 125.00,
      "currency": "USD",
      "status": "pending",
      "period_start": "2025-01-01",
      "period_end": "2025-01-31",
      "tokens_used": 12500000,
      "created_at": "2025-02-01T00:00:00Z"
    }
  ]
}

# 获取账单详情
GET /api/v1/admin/billing/invoices/{invoice_id}

# 更新账单状态
PATCH /api/v1/admin/billing/invoices/{invoice_id}
Content-Type: application/json

{
  "status": "paid"
}
```

#### 5.2.8 用户和组织管理

```http
# 创建组织
POST /api/v1/admin/organizations
Content-Type: application/json

{
  "name": "Acme Corp",
  "plan": "professional",
  "quota_tokens": 1000000,
  "quota_models": 10,
  "quota_gpus": 8
}

# 列出组织
GET /api/v1/admin/organizations

# 获取组织详情
GET /api/v1/admin/organizations/{org_id}

# 更新组织
PUT /api/v1/admin/organizations/{org_id}

# 创建用户
POST /api/v1/admin/users
Content-Type: application/json

{
  "username": "john",
  "email": "john@acme.com",
  "password": "secure_password",
  "organization_id": 1,
  "role": "user"
}

# 列出用户
GET /api/v1/admin/users?organization_id={org_id}

# 更新用户
PUT /api/v1/admin/users/{user_id}

# 删除用户
DELETE /api/v1/admin/users/{user_id}
```

#### 5.2.9 监控统计

```http
# 获取 Dashboard 统计数据
GET /api/v1/admin/monitoring/stats

Response:
{
  "gpu_count": {
    "total": 8,
    "available": 3,
    "in_use": 5
  },
  "model_count": {
    "running": 3,
    "total": 10
  },
  "deployment_count": {
    "running": 3,
    "total": 5
  },
  "worker_count": {
    "running": 5,
    "total": 6
  },
  "api_calls": {
    "today": 125430,
    "avg_latency_ms": 320
  },
  "token_usage": {
    "today": 1250000,
    "this_month": 12500000
  }
}

# 获取系统健康状态
GET /api/v1/admin/monitoring/health

Response:
{
  "status": "healthy",
  "components": {
    "database": "healthy",
    "redis": "healthy",
    "workers": {
      "total": 6,
      "healthy": 5,
      "unhealthy": 1
    }
  }
}
```

---

## 6. 核心功能模块

### 6.1 集群服务模块

```python
# services/cluster_service.py
from typing import List, Optional
from sqlalchemy.orm import Session
from models.database import Cluster, WorkerPool, Worker
import asyncio

class ClusterService:
    """集群服务"""

    def __init__(self, db: Session):
        self.db = db

    def create_cluster(
        self,
        name: str,
        cluster_type: str,
        config: dict,
        is_default: bool = False
    ) -> Cluster:
        """创建集群"""
        # 如果设置为默认，取消其他集群的默认状态
        if is_default:
            self.db.query(Cluster).filter(
                Cluster.is_default == True
            ).update({"is_default": False})

        cluster = Cluster(
            name=name,
            type=cluster_type,
            config=config,
            is_default=is_default,
            status="running"
        )
        self.db.add(cluster)
        self.db.commit()
        self.db.refresh(cluster)

        return cluster

    def get_cluster(self, cluster_id: int) -> Optional[Cluster]:
        """获取集群"""
        return self.db.query(Cluster).filter(
            Cluster.id == cluster_id
        ).first()

    def list_clusters(self) -> List[Cluster]:
        """列出所有集群"""
        return self.db.query(Cluster).all()

    def update_cluster(
        self,
        cluster_id: int,
        **kwargs
    ) -> Optional[Cluster]:
        """更新集群"""
        cluster = self.get_cluster(cluster_id)
        if not cluster:
            return None

        for key, value in kwargs.items():
            if hasattr(cluster, key):
                setattr(cluster, key, value)

        self.db.commit()
        self.db.refresh(cluster)
        return cluster

    def delete_cluster(self, cluster_id: int) -> bool:
        """删除集群"""
        cluster = self.get_cluster(cluster_id)
        if not cluster:
            return False

        # 检查是否有 Worker 在运行
        worker_count = self.db.query(Worker).filter(
            Worker.cluster_id == cluster_id,
            Worker.state == "running"
        ).count()

        if worker_count > 0:
            raise ValueError(f"Cannot delete cluster with {worker_count} running workers")

        self.db.delete(cluster)
        self.db.commit()
        return True

    def set_default_cluster(self, cluster_id: int) -> Optional[Cluster]:
        """设置默认集群"""
        # 取消其他默认状态
        self.db.query(Cluster).filter(
            Cluster.is_default == True
        ).update({"is_default": False})

        # 设置新的默认
        cluster = self.get_cluster(cluster_id)
        if cluster:
            cluster.is_default = True
            self.db.commit()
            self.db.refresh(cluster)

        return cluster

    def create_worker_pool(
        self,
        cluster_id: int,
        name: str,
        min_workers: int,
        max_workers: int,
        config: dict
    ) -> WorkerPool:
        """创建 Worker 池"""
        pool = WorkerPool(
            cluster_id=cluster_id,
            name=name,
            min_workers=min_workers,
            max_workers=max_workers,
            config=config,
            status="running"
        )
        self.db.add(pool)
        self.db.commit()
        self.db.refresh(pool)

        return pool
```

### 6.2 Worker 服务模块

```python
# services/worker_service.py
from typing import List, Optional, Dict
from sqlalchemy.orm import Session
from models.database import Worker, Cluster, GPUDevice
from datetime import datetime, timedelta

class WorkerService:
    """Worker 服务"""

    def __init__(self, db: Session):
        self.db = db

    def register_worker(
        self,
        name: str,
        cluster_id: int,
        pool_id: Optional[int],
        ip: str,
        port: int,
        labels: dict
    ) -> Worker:
        """注册 Worker"""
        # 检查 Worker 名称是否已存在
        existing = self.db.query(Worker).filter(
            Worker.name == name
        ).first()

        if existing:
            # 更新现有 Worker
            existing.cluster_id = cluster_id
            existing.pool_id = pool_id
            existing.ip = ip
            existing.port = port
            existing.labels = labels
            existing.state = "running"
            existing.last_heartbeat = datetime.utcnow()
            self.db.commit()
            self.db.refresh(existing)
            return existing

        # 创建新 Worker
        worker = Worker(
            name=name,
            cluster_id=cluster_id,
            pool_id=pool_id,
            ip=ip,
            port=port,
            labels=labels,
            state="running",
            last_heartbeat=datetime.utcnow()
        )
        self.db.add(worker)
        self.db.commit()
        self.db.refresh(worker)

        return worker

    def heartbeat(self, worker_id: int) -> bool:
        """更新 Worker 心跳"""
        worker = self.db.query(Worker).filter(
            Worker.id == worker_id
        ).first()

        if not worker:
            return False

        worker.last_heartbeat = datetime.utcnow()
        self.db.commit()
        return True

    def update_status(
        self,
        worker_id: int,
        status: dict
    ) -> bool:
        """更新 Worker 状态"""
        worker = self.db.query(Worker).filter(
            Worker.id == worker_id
        ).first()

        if not worker:
            return False

        worker.status = status
        worker.last_status_update = datetime.utcnow()
        self.db.commit()

        # 更新 GPU 设备信息
        if "gpu_devices" in status:
            self._update_gpu_devices(worker_id, status["gpu_devices"])

        return True

    def _update_gpu_devices(
        self,
        worker_id: int,
        gpu_devices: List[dict]
    ):
        """更新 GPU 设备信息"""
        for gpu_data in gpu_devices:
            uuid = gpu_data["uuid"]

            # 查找或创建 GPU 设备记录
            gpu = self.db.query(GPUDevice).filter(
                GPUDevice.worker_id == worker_id,
                GPUDevice.uuid == uuid
            ).first()

            if not gpu:
                gpu = GPUDevice(
                    worker_id=worker_id,
                    uuid=uuid
                )
                self.db.add(gpu)

            # 更新 GPU 信息
            for key, value in gpu_data.items():
                if hasattr(gpu, key):
                    setattr(gpu, key, value)

            gpu.updated_at = datetime.utcnow()

        self.db.commit()

    def list_workers(
        self,
        cluster_id: Optional[int] = None,
        state: Optional[str] = None
    ) -> List[Worker]:
        """列出 Workers"""
        query = self.db.query(Worker)

        if cluster_id:
            query = query.filter(Worker.cluster_id == cluster_id)

        if state:
            query = query.filter(Worker.state == state)

        return query.all()

    def get_worker(self, worker_id: int) -> Optional[Worker]:
        """获取 Worker 详情"""
        return self.db.query(Worker).filter(
            Worker.id == worker_id
        ).first()

    def update_worker(
        self,
        worker_id: int,
        **kwargs
    ) -> Optional[Worker]:
        """更新 Worker"""
        worker = self.get_worker(worker_id)
        if not worker:
            return None

        for key, value in kwargs.items():
            if hasattr(worker, key):
                setattr(worker, key, value)

        self.db.commit()
        self.db.refresh(worker)
        return worker

    def delete_worker(self, worker_id: int) -> bool:
        """删除 Worker"""
        worker = self.get_worker(worker_id)
        if not worker:
            return False

        # 检查是否有运行中的模型实例
        from models.database import ModelInstance
        instance_count = self.db.query(ModelInstance).filter(
            ModelInstance.worker_id == worker_id,
            ModelInstance.status.in_(["starting", "running"])
        ).count()

        if instance_count > 0:
            raise ValueError(f"Cannot delete worker with {instance_count} running instances")

        self.db.delete(worker)
        self.db.commit()
        return True

    def drain_worker(self, worker_id: int) -> bool:
        """排空 Worker（停止所有实例）"""
        # TODO: 实现排空逻辑
        # 1. 将 Worker 状态设置为 draining
        # 2. 停止该 Worker 上的所有模型实例
        # 3. 等待所有实例停止完成
        # 4. 将 Worker 状态设置为 drained
        pass

    def check_offline_workers(self, timeout_seconds: int = 60) -> List[Worker]:
        """检查离线 Workers"""
        timeout_threshold = datetime.utcnow() - timedelta(seconds=timeout_seconds)

        offline_workers = self.db.query(Worker).filter(
            Worker.state == "running",
            Worker.last_heartbeat < timeout_threshold
        ).all()

        # 标记为离线
        for worker in offline_workers:
            worker.state = "offline"

        self.db.commit()
        return offline_workers
```

### 6.3 GPU 管理模块

```python
# core/gpu.py
import pynvml
from typing import List, Dict
import psutil

class GPUManager:
    """GPU 资源管理器"""

    def __init__(self):
        try:
            pynvml.nvmlInit()
            self.num_gpus = pynvml.nvmlDeviceGetCount()
            self.available = True
        except:
            self.available = False
            self.num_gpus = 0

    def get_gpu_info(self, gpu_id: int) -> Dict:
        """获取单个 GPU 信息"""
        if not self.available:
            return {}

        handle = pynvml.nvmlDeviceGetHandleByIndex(gpu_id)

        # 基本信息
        name = pynvml.nvmlDeviceGetName(handle)

        # 显存信息
        mem_info = pynvml.nvmlDeviceGetMemoryInfo(handle)

        # 利用率
        utilization = pynvml.nvmlDeviceGetUtilizationRates(handle)

        # 温度
        try:
            temperature = pynvml.nvmlDeviceGetTemperature(
                handle, pynvml.NVML_TEMPERATURE_GPU
            )
        except:
            temperature = 0

        return {
            "uuid": pynvml.nvmlDeviceGetUUID(handle).decode('utf-8'),
            "name": name.decode('utf-8'),
            "vendor": "nvidia",
            "index": gpu_id,
            "memory_total": mem_info.total,
            "memory_used": mem_info.used,
            "memory_free": mem_info.free,
            "core_utilization_rate": float(utilization.gpu),
            "memory_utilization_rate": float(mem_info.used / mem_info.total * 100),
            "temperature": float(temperature),
            "state": "available"  # 需要结合实际使用情况判断
        }

    def get_all_gpus(self) -> List[Dict]:
        """获取所有 GPU 信息"""
        if not self.available:
            return []

        return [self.get_gpu_info(i) for i in range(self.num_gpus)]

    def get_worker_status(self) -> Dict:
        """获取 Worker 状态（CPU、内存、GPU、文件系统）"""
        status = {
            "cpu": {
                "total": psutil.cpu_count(logical=True),
                "allocated": 0,  # TODO: 从模型实例计算
                "utilization_rate": psutil.cpu_percent(interval=1)
            },
            "memory": {
                "total": psutil.virtual_memory().total,
                "used": psutil.virtual_memory().used,
                "allocated": 0,  # TODO: 从模型实例计算
                "utilization_rate": psutil.virtual_memory().percent
            },
            "gpu_devices": self.get_all_gpus(),
            "filesystem": [
                {
                    "path": "/",
                    "total": psutil.disk_usage('/').total,
                    "used": psutil.disk_usage('/').used,
                    "available": psutil.disk_usage('/').free
                }
            ]
        }
        return status

    def __del__(self):
        if self.available:
            try:
                pynvml.nvmlShutdown()
            except:
                pass
```

### 6.4 计费服务模块

```python
# services/billing_service.py
from typing import List, Optional
from sqlalchemy.orm import Session
from models.database import APIKey, UsageLog, Invoice, Organization
from datetime import datetime, date, timedelta
from decimal import Decimal

PRICING = {
    "input_token": 0.001,  # 每 1K tokens 价格
    "output_token": 0.002  # 每 1K tokens 价格
}

class BillingService:
    """计费服务"""

    def __init__(self, db: Session):
        self.db = db

    def record_usage(
        self,
        api_key_id: int,
        deployment_id: int,
        model_id: int,
        input_tokens: int,
        output_tokens: int,
        latency_ms: int,
        status: str
    ) -> UsageLog:
        """记录使用日志"""
        log = UsageLog(
            api_key_id=api_key_id,
            deployment_id=deployment_id,
            model_id=model_id,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            latency_ms=latency_ms,
            status=status
        )
        self.db.add(log)

        # 更新 API Key 的已用额度
        api_key = self.db.query(APIKey).filter(
            APIKey.id == api_key_id
        ).first()
        if api_key:
            api_key.tokens_used += (input_tokens + output_tokens)
            api_key.last_used_at = datetime.utcnow()

        self.db.commit()
        self.db.refresh(log)
        return log

    def calculate_cost(self, input_tokens: int, output_tokens: int) -> Decimal:
        """计算费用"""
        input_cost = (input_tokens / 1000) * PRICING["input_token"]
        output_cost = (output_tokens / 1000) * PRICING["output_token"]
        return Decimal(str(input_cost + output_cost))

    def get_usage_stats(
        self,
        organization_id: int,
        start_date: date,
        end_date: date
    ) -> dict:
        """获取使用统计"""
        logs = self.db.query(UsageLog).join(APIKey).filter(
            APIKey.organization_id == organization_id,
            UsageLog.created_at >= start_date,
            UsageLog.created_at <= end_date + timedelta(days=1)
        ).all()

        total_tokens = sum(log.input_tokens + log.output_tokens for log in logs)
        total_cost = sum(
            self.calculate_cost(log.input_tokens, log.output_tokens)
            for log in logs
        )

        # 按模型统计
        by_model = {}
        for log in logs:
            model_id = log.model_id
            if model_id not in by_model:
                by_model[model_id] = {
                    "model_id": model_id,
                    "tokens": 0,
                    "cost": Decimal("0")
                }
            by_model[model_id]["tokens"] += (log.input_tokens + log.output_tokens)
            by_model[model_id]["cost"] += self.calculate_cost(
                log.input_tokens, log.output_tokens
            )

        # 按日期统计
        by_day = {}
        for log in logs:
            log_date = log.created_at.date()
            if log_date not in by_day:
                by_day[log_date] = {
                    "date": log_date.isoformat(),
                    "tokens": 0,
                    "cost": Decimal("0")
                }
            by_day[log_date]["tokens"] += (log.input_tokens + log.output_tokens)
            by_day[log_date]["cost"] += self.calculate_cost(
                log.input_tokens, log.output_tokens
            )

        return {
            "organization_id": organization_id,
            "period_start": start_date.isoformat(),
            "period_end": end_date.isoformat(),
            "total_tokens": total_tokens,
            "total_cost": float(total_cost),
            "by_model": list(by_model.values()),
            "by_day": sorted(by_day.values(), key=lambda x: x["date"])
        }

    def create_invoice(
        self,
        organization_id: int,
        period_start: date,
        period_end: date
    ) -> Invoice:
        """创建账单"""
        # 检查是否已存在
        existing = self.db.query(Invoice).filter(
            Invoice.organization_id == organization_id,
            Invoice.period_start == period_start,
            Invoice.period_end == period_end
        ).first()

        if existing:
            return existing

        # 计算费用
        stats = self.get_usage_stats(organization_id, period_start, period_end)

        invoice = Invoice(
            organization_id=organization_id,
            amount=Decimal(str(stats["total_cost"])),
            currency="USD",
            status="pending",
            period_start=period_start,
            period_end=period_end,
            tokens_used=stats["total_tokens"]
        )
        self.db.add(invoice)
        self.db.commit()
        self.db.refresh(invoice)

        return invoice

    def list_invoices(
        self,
        organization_id: Optional[int] = None
    ) -> List[Invoice]:
        """列出账单"""
        query = self.db.query(Invoice)

        if organization_id:
            query = query.filter(Invoice.organization_id == organization_id)

        return query.order_by(Invoice.created_at.desc()).all()
```

### 6.5 统计服务模块

```python
# services/stats_service.py
from typing import Dict
from sqlalchemy.orm import Session
from models.database import Worker, Model, Deployment, ModelInstance, GPUDevice, UsageLog, Cluster
from datetime import datetime, date, timedelta

class StatsService:
    """统计服务"""

    def __init__(self, db: Session):
        self.db = db

    def get_dashboard_stats(self) -> Dict:
        """获取 Dashboard 统计数据"""
        today = date.today()
        today_start = datetime.combine(today, datetime.min.time())

        # GPU 统计
        gpu_total = self.db.query(GPUDevice).count()
        gpu_available = self.db.query(GPUDevice).filter(
            GPUDevice.state == "available"
        ).count()
        gpu_in_use = gpu_total - gpu_available

        # 模型统计
        model_total = self.db.query(Model).count()
        model_running = self.db.query(Deployment).filter(
            Deployment.status == "running"
        ).count()

        # 部署统计
        deployment_total = self.db.query(Deployment).count()
        deployment_running = self.db.query(Deployment).filter(
            Deployment.status == "running"
        ).count()

        # Worker 统计
        worker_total = self.db.query(Worker).count()
        worker_running = self.db.query(Worker).filter(
            Worker.state == "running"
        ).count()

        # API 调用统计
        api_calls_today = self.db.query(UsageLog).filter(
            UsageLog.created_at >= today_start
        ).count()

        avg_latency = self.db.query(
            func.avg(UsageLog.latency_ms)
        ).filter(
            UsageLog.created_at >= today_start,
            UsageLog.status == "success"
        ).scalar() or 0

        # Token 使用统计
        token_today = self.db.query(
            func.sum(UsageLog.input_tokens + UsageLog.output_tokens)
        ).filter(
            UsageLog.created_at >= today_start
        ).scalar() or 0

        month_start = today.replace(day=1)
        token_month = self.db.query(
            func.sum(UsageLog.input_tokens + UsageLog.output_tokens)
        ).filter(
            UsageLog.created_at >= month_start
        ).scalar() or 0

        return {
            "gpu_count": {
                "total": gpu_total,
                "available": gpu_available,
                "in_use": gpu_in_use
            },
            "model_count": {
                "running": model_running,
                "total": model_total
            },
            "deployment_count": {
                "running": deployment_running,
                "total": deployment_total
            },
            "worker_count": {
                "running": worker_running,
                "total": worker_total
            },
            "api_calls": {
                "today": api_calls_today,
                "avg_latency_ms": float(avg_latency)
            },
            "token_usage": {
                "today": token_today,
                "this_month": token_month
            }
        }

    def get_system_health(self) -> Dict:
        """获取系统健康状态"""
        # 检查 Worker 健康状态
        timeout_threshold = datetime.utcnow() - timedelta(seconds=60)
        worker_total = self.db.query(Worker).count()
        worker_healthy = self.db.query(Worker).filter(
            Worker.last_heartbeat >= timeout_threshold
        ).count()

        return {
            "status": "healthy" if worker_healthy == worker_total else "degraded",
            "components": {
                "database": "healthy",  # TODO: 实际检查
                "redis": "healthy",     # TODO: 实际检查
                "workers": {
                    "total": worker_total,
                    "healthy": worker_healthy,
                    "unhealthy": worker_total - worker_healthy
                }
            }
        }
```

### 6.6 配额管理模块

```python
# core/quota.py
from typing import Dict, Tuple
from sqlalchemy.orm import Session
from models.database import Organization, APIKey
from fastapi import HTTPException

class QuotaManager:
    """配额管理器"""

    def __init__(self, db: Session):
        self.db = db

    def check_api_key_quota(self, api_key_id: int) -> Tuple[bool, str]:
        """检查 API Key 配额"""
        api_key = self.db.query(APIKey).filter(
            APIKey.id == api_key_id
        ).first()

        if not api_key:
            return False, "API key not found"

        if not api_key.is_active:
            return False, "API key is inactive"

        # 检查过期时间
        if api_key.expires_at and api_key.expires_at < datetime.utcnow():
            return False, "API key has expired"

        # 检查 token 配额
        if api_key.tokens_used >= api_key.quota_tokens:
            return False, "Token quota exceeded"

        # 检查组织配额
        org = self.db.query(Organization).filter(
            Organization.id == api_key.organization_id
        ).first()

        if not org:
            return False, "Organization not found"

        # 计算组织总使用量
        total_used = self.db.query(
            func.sum(APIKey.tokens_used)
        ).filter(
            APIKey.organization_id == org.id
        ).scalar() or 0

        if total_used >= org.quota_tokens:
            return False, "Organization token quota exceeded"

        return True, "OK"

    def get_quota_info(self, organization_id: int) -> Dict:
        """获取配额信息"""
        org = self.db.query(Organization).filter(
            Organization.id == organization_id
        ).first()

        if not org:
            raise HTTPException(status_code=404, detail="Organization not found")

        # 计算总使用量
        total_used = self.db.query(
            func.sum(APIKey.tokens_used)
        ).filter(
            APIKey.organization_id == organization_id
        ).scalar() or 0

        return {
            "plan": org.plan,
            "quota_tokens": org.quota_tokens,
            "tokens_used": int(total_used),
            "tokens_remaining": max(0, org.quota_tokens - int(total_used)),
            "usage_percentage": min(100, int(total_used / org.quota_tokens * 100)) if org.quota_tokens > 0 else 0,
            "quota_models": org.quota_models,
            "quota_gpus": org.quota_gpus,
            "max_workers": org.max_workers
        }
```

---

## 7. 部署架构

### 7.1 Docker Compose 部署

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

  # FastAPI Server
  api:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: tokenmachine-api
    environment:
      DATABASE_URL: postgresql://tokenmachine:${POSTGRES_PASSWORD}@postgres:5432/tokenmachine
      REDIS_URL: redis://redis:6379/0
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

---

## 8. 技术选型

### 8.1 后端技术栈

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

### 8.2 推理引擎

| 引擎 | 版本 | 用途 | 备注 |
|------|------|------|------|
| **vLLM** | 0.3.0 | 默认推理引擎 | PagedAttention、OpenAI API 兼容 |
| **(预留)** | - | SGLang | P2 支持 |
| **(预留)** | - | Chitu | P2 支持（国产芯片） |

---

## 9. 开发计划

### 9.1 迭代计划（16 周）

#### Week 1-2: 基础架构
- [x] 项目初始化（代码结构、依赖配置）
- [ ] 数据库设计和迁移（新增表）
- [ ] 配置管理系统
- [ ] 日志系统
- [ ] API 认证中间件
- [ ] RBAC 权限控制

#### Week 3-4: 集群和 Worker 管理
- [ ] 集群 CRUD API
- [ ] Worker 池管理
- [ ] Worker 注册和心跳
- [ ] Worker 状态上报
- [ ] GPU 设备信息采集
- [ ] Worker 健康检查

#### Week 5-6: 模型管理
- [ ] 模型下载功能
- [ ] 模型存储管理
- [ ] 模型版本管理
- [ ] 量化变体支持
- [ ] 模型状态管理

#### Week 7-8: 部署管理
- [ ] vLLM Worker 封装
- [ ] 部署创建/停止
- [ ] 灰度发布支持
- [ ] Worker 健康检查
- [ ] 部署状态监控

#### Week 9-10: 计费和配额
- [ ] Token 计费逻辑
- [ ] 配额管理
- [ ] 账单生成
- [ ] 使用统计 API
- [ ] 配额检查中间件

#### Week 11: API 网关
- [ ] OpenAI Chat API 实现
- [ ] OpenAI Models API 实现
- [ ] 流式输出支持
- [ ] 格式转换引擎（可选）
- [ ] 智能路由（可选）

#### Week 12-13: 监控和前端支持
- [ ] Prometheus 指标收集
- [ ] Dashboard 统计 API
- [ ] Grafana 面板配置
- [ ] 结构化日志
- [ ] 审计日志

#### Week 14: 多租户支持
- [ ] 组织管理 API
- [ ] 用户管理 API
- [ ] 资源隔离
- [ ] RBAC 完善

#### Week 15-16: 测试和优化
- [ ] 单元测试
- [ ] 集成测试
- [ ] 性能测试
- [ ] 文档完善

### 9.2 里程碑

| 周次 | 里程碑 | 交付物 |
|------|--------|--------|
| Week 2 | 基础架构完成 | 数据库、配置、日志系统 |
| Week 4 | 集群管理完成 | 集群、Worker、GPU 管理功能 |
| Week 6 | 模型管理完成 | 模型下载、版本管理 |
| Week 8 | 部署管理完成 | vLLM 集成、灰度发布 |
| Week 10 | 计费系统完成 | Token 计费、配额、账单 |
| Week 11 | API 网关完成 | OpenAI API 兼容 |
| Week 13 | 监控完成 | Prometheus + Dashboard API |
| Week 14 | 多租户完成 | 组织隔离、RBAC |
| Week 16 | MVP 发布 | 可用的完整产品 |

---

**文档版本**: v2.0
**最后更新**: 2025-01-16
**作者**: TokenMachine Team
