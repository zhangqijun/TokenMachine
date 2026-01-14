# TokenMachine 开发计划与前后依赖关系

> 本文档基于所有设计文档,梳理模块间的依赖关系,制定合理的开发顺序和测试节点

---

## 目录

- [1. 模块依赖关系图](#1-模块依赖关系图)
- [2. 并行开发策略](#2-并行开发策略)
- [3. 分阶段开发计划](#3-分阶段开发计划)
- [4. 测试节点定义](#4-测试节点定义)
- [5. 里程碑交付](#5-里程碑交付)

---

## 1. 模块依赖关系图

### 1.1 整体架构分层

```
┌─────────────────────────────────────────────────────────────────┐
│                        表现层 (Frontend)                        │
│  Dashboard │ Models │ Playground │ Resources │ Clusters        │
└────────────────────────────┬────────────────────────────────────┘
                             │ API 调用
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                        API 网关层                               │
│  OpenAI API │ Admin API │ Worker API │ Internal API          │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                        业务逻辑层                               │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐      │
│  │Scheduler │  │Controllers│ │   Server │  │  Worker  │      │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘      │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                        核心服务层                               │
│  ┌──────────────────┐  ┌──────────────────┐                   │
│  │ InferenceBackend │  │ ServeManager     │                   │
│  │    Manager       │  │                  │                   │
│  └──────────────────┘  └──────────────────┘                   │
│  ┌──────────────────┐  ┌──────────────────┐                   │
│  │  WorkerController│  │InstanceController│                   │
│  └──────────────────┘  └──────────────────┘                   │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                        数据层                                   │
│  PostgreSQL │ Redis │ Prometheus │ File System                │
└─────────────────────────────────────────────────────────────────┘
```

### 1.2 后端模块依赖矩阵

| 模块 | 依赖的前置模块 | 被依赖的模块 | 说明 |
|------|---------------|-------------|------|
| **数据库Schema** | - | 所有模块 | 基础,必须最先完成 |
| **核心配置** | 数据库Schema | 所有模块 | 配置管理 |
| **Server架构** | 数据库Schema, 核心配置 | 调度框架, 集群管理 | 控制平面基础 |
| **Worker架构** | 数据库Schema, 核心配置 | 推理后端 | 数据平面基础 |
| **推理后端插件** | Worker架构 | 调度框架 | 推理执行层 |
| **调度框架** | Server架构, 推理后端 | 模型实例管理 | 资源调度 |
| **模型实例管理** | Server, 调度框架 | - | 模型生命周期 |
| **多集群管理** | Server架构 | - | 跨集群部署 |
| **API网关** | Server, 调度框架 | 前端 | 对外接口 |
| **监控模块** | Server, Worker | - | 可观测性 |

### 1.3 前端模块依赖矩阵

| 模块 | 依赖的前置模块 | 被依赖的模块 | 说明 |
|------|---------------|-------------|------|
| **基础布局** | - | 所有页面 | AppLayout, Header, Sidebar |
| **API服务层** | - | 所有页面 | axios封装, API定义 |
| **状态管理** | - | 所有页面 | Zustand stores |
| **通用组件** | 基础布局 | 所有页面 | ProgressBar, StatusTag |
| **仪表盘** | API服务, 状态管理 | - | 首页 |
| **模型管理** | API服务, 通用组件 | - | 模型部署 |
| **测试场** | API服务 | - | 对话测试 |
| **资源管理** | API服务, 通用组件 | - | Worker/GPU监控 |
| **集群管理** | API服务, 通用组件 | - | 集群配置 |

### 1.4 前后端依赖关系

```
后端进度                     前端进度
│                            │
│ ◌────────┐                 │ ◌────────┐
│ │  DB     │─────────────┬──▶│ API层    │ (基于OpenAPI Spec)
│ │ Schema  │             │  │         │
│ └────────┘             │  └────────┘
│                        │
│ ◌────────┐             │  ◌────────┐
│ │ Server  │─────────────┼──▶│ 资源管理 │ (Worker/GPU数据)
│ │ Worker  │             │  │         │
│ └────────┘             │  └────────┘
│                        │
│ ◌────────┐             │  ◌────────┐
│ │ 调度    │─────────────┼──▶│ 模型管理 │ (部署/停止)
│ │ 框架    │             │  │         │
│ └────────┘             │  └────────┘
│                        │
│ ◌────────┐             │  ◌────────┐
│ │ 推理    │─────────────┼──▶│ 测试场   │ (对话测试)
│ │ 后端    │             │  │         │
│ └────────┘             │  └────────┘
│                        │
│ ◌────────┐             │  ◌────────┐
│ │ API     │─────────────┴──▶│ 所有页面 │ (完整功能)
│ │ Gateway │                │         │
│ └────────┘                └────────┘
```

**关键点:**
- 前端可使用Mock数据先行开发,不阻塞后端
- 后端API优先级: 数据库 → Server/Worker → 调度 → API网关
- 前后端并行开发,通过OpenAPI Spec对齐接口

---

## 2. 并行开发策略

### 2.1 可并行开发的模块组

#### 组A: 基础设施 (可并行)
```
┌─────────────────────────────────────────────┐
│ 后端: 数据库Schema + 核心配置               │
│ 前端: 基础布局 + 通用组件 + 状态管理        │
│ 后端: 监控模块(独立)                       │
└─────────────────────────────────────────────┘
```

#### 组B: 核心架构 (可并行)
```
┌─────────────────────────────────────────────┐
│ 后端: Server架构                            │
│ 后端: Worker架构                            │
│ 前端: API服务层(基于Schema Mock)           │
└─────────────────────────────────────────────┘
```

#### 组C: 业务功能 (需组B完成)
```
┌─────────────────────────────────────────────┐
│ 后端: 推理后端插件                          │
│ 后端: 调度框架                              │
│ 前端: 资源管理页面                          │
└─────────────────────────────────────────────┘
```

#### 组D: 完整功能 (需组C完成)
```
┌─────────────────────────────────────────────┐
│ 后端: 模型实例管理                          │
│ 后端: 多集群管理                            │
│ 后端: API网关                               │
│ 前端: 模型管理 + 测试场 + 集群管理         │
└─────────────────────────────────────────────┘
```

### 2.2 前端Mock策略

前端可在后端API完成前使用Mock数据并行开发:

```typescript
// ui/src/services/mock.ts
export const mockWorkers = [
  {
    id: 1,
    name: "worker-gpu-01",
    status: "running",
    ip: "192.168.1.100",
    gpu_count: 4,
    // ...
  }
];

// 开发时切换
const USE_MOCK = import.meta.env.VITE_USE_MOCK === 'true';

export const getWorkers = USE_MOCK
  ? () => Promise.resolve(mockWorkers)
  : () => ResourcesAPI.queryWorkersList();
```

### 2.3 团队分工建议

| 团队 | 负责模块 | 可并行时间点 |
|------|---------|-------------|
| **后端A组** | 数据库, Server架构 | Day 1 |
| **后端B组** | Worker架构, 推理后端 | Day 1 (需数据库) |
| **后端C组** | 调度框架 | Day 7 (需Server/Worker) |
| **前端A组** | 基础布局, 通用组件 | Day 1 |
| **前端B组** | 资源管理, 集群管理 | Day 7 (需API Spec) |
| **前端C组** | 模型管理, 测试场 | Day 14 (需更多API) |

---

## 3. 分阶段开发计划

### Phase 0: 准备阶段 (Week 0)

**目标**: 项目初始化,开发环境搭建

| 任务 | 负责人 | 交付物 | 前置依赖 |
|------|-------|--------|---------|
| 项目仓库初始化 | DevOps | Git仓库, 目录结构 | - |
| 开发环境搭建 | DevOps | Docker Compose, K8s集群 | - |
| 依赖选型确认 | 架构师 | 技术栈文档 | - |
| 数据库设计评审 | 后端A | Schema设计文档 | - |

**测试节点**:
- [ ] Docker Compose 一键启动成功
- [ ] 数据库连接测试通过

---

### Phase 1: 基础设施 (Week 1-2)

**目标**: 数据库, 核心配置, 基础UI框架

#### 后端任务

| 任务ID | 任务 | 优先级 | 工期 | 依赖 |
|--------|------|--------|------|------|
| DB-001 | 数据库Schema设计 | P0 | 2天 | - |
| DB-002 | SQLAlchemy模型实现 | P0 | 2天 | DB-001 |
| DB-003 | Alembic迁移脚本 | P0 | 1天 | DB-002 |
| CFG-001 | 核心配置系统 | P0 | 2天 | DB-002 |
| LOG-001 | 结构化日志(Loguru) | P0 | 1天 | - |

#### 前端任务

| 任务ID | 任务 | 优先级 | 工期 | 依赖 |
|--------|------|--------|------|------|
| UI-001 | 基础布局组件 | P0 | 2天 | - |
| UI-002 | 通用组件(ProgressBar, StatusTag) | P0 | 2天 | - |
| UI-003 | 状态管理(Zustand) | P0 | 1天 | - |
| UI-004 | API服务层(含Mock) | P0 | 2天 | DB-001 |
| UI-005 | 路由配置 | P0 | 1天 | UI-001 |

**测试节点**:
- [ ] 数据库迁移测试
- [ ] 配置加载测试
- [ ] 前端基础组件单元测试
- [ ] 前端路由测试

---

### Phase 2: Server-Worker架构 (Week 3-4)

**目标**: 控制平面和数据平面分离

#### 后端任务

| 任务ID | 任务 | 优先级 | 工期 | 依赖 |
|--------|------|--------|------|------|
| SW-001 | Server主类实现 | P0 | 3天 | CFG-001 |
| SW-002 | Worker主类实现 | P0 | 3天 | CFG-001 |
| SW-003 | Worker注册API | P0 | 2天 | SW-001 |
| SW-004 | 心跳机制 | P0 | 2天 | SW-002 |
| SW-005 | 状态上报API | P0 | 2天 | SW-002 |
| SW-006 | WorkerController | P0 | 2天 | SW-003 |
| SW-007 | 健康检查循环 | P0 | 2天 | SW-006 |

#### 前端任务

| 任务ID | 任务 | 优先级 | 工期 | 依赖 |
|--------|------|--------|------|------|
| UI-006 | 资源管理页面框架 | P0 | 2天 | UI-002 |
| UI-007 | Worker列表组件 | P0 | 3天 | UI-006 |
| UI-008 | Worker详情Drawer | P0 | 2天 | UI-007 |
| UI-009 | 实时更新(useTableFetch) | P0 | 2天 | UI-004 |

**测试节点**:
- [ ] Server-Worker注册测试
- [ ] 心跳机制测试
- [ ] Worker状态同步测试
- [ ] 前端Worker列表渲染测试
- [ ] 前端实时更新测试

---

### Phase 3: 推理后端与调度 (Week 5-7)

**目标**: 推理执行和资源调度

#### 后端任务

| 任务ID | 任务 | 优先级 | 工期 | 依赖 |
|--------|------|--------|------|------|
| BE-001 | InferenceBackend抽象 | P0 | 2天 | - |
| BE-002 | VLLMBackend实现 | P0 | 3天 | BE-001 |
| BE-003 | SGLangBackend实现 | P1 | 2天 | BE-002 |
| BE-004 | InferenceBackendManager | P0 | 2天 | BE-002 |
| SCH-001 | 调度基础抽象 | P0 | 2天 | SW-006 |
| SCH-002 | WorkerFilterChain | P0 | 2天 | SCH-001 |
| SCH-003 | StatusFilter | P0 | 1天 | SCH-002 |
| SCH-004 | GPUFilter | P0 | 2天 | SCH-002 |
| SCH-005 | VLLMSelector | P0 | 2天 | SCH-002 |
| SCH-006 | PlacementScorer | P0 | 2天 | SCH-002 |
| SCH-007 | Scheduler主类 | P0 | 3天 | SCH-006 |

#### 前端任务

| 任务ID | 任务 | 优先级 | 工期 | 依赖 |
|--------|------|--------|------|------|
| UI-010 | GPU列表组件 | P0 | 2天 | UI-007 |
| UI-011 | 模型管理页面框架 | P0 | 2天 | UI-002 |
| UI-012 | 模型列表组件 | P0 | 3天 | UI-011 |
| UI-013 | 模型上传Modal | P0 | 2天 | UI-012 |
| UI-014 | 部署配置Modal | P0 | 3天 | UI-012 |

**测试节点**:
- [ ] vLLM后端启动测试
- [ ] 模型实例创建测试
- [ ] 调度器端到端测试
- [ ] 前端模型列表测试
- [ ] 前端部署配置表单测试

---

### Phase 4: 完整功能 (Week 8-10)

**目标**: 模型实例管理, 多集群, API网关

#### 后端任务

| 任务ID | 任务 | 优先级 | 工期 | 依赖 |
|--------|------|--------|------|------|
| MI-001 | ModelInstanceController | P0 | 3天 | SCH-007 |
| MI-002 | 实例健康检查循环 | P0 | 2天 | MI-001 |
| MI-003 | 实例扩缩容逻辑 | P1 | 2天 | MI-002 |
| CL-001 | ClusterController | P0 | 2天 | SW-001 |
| CL-002 | DockerClusterProvider | P0 | 2天 | CL-001 |
| CL-003 | KubernetesClusterProvider | P1 | 3天 | CL-001 |
| API-001 | OpenAI Chat API | P0 | 3天 | MI-001 |
| API-002 | OpenAI Models API | P0 | 1天 | API-001 |
| API-003 | 流式输出(SSE) | P0 | 2天 | API-001 |
| API-004 | 请求路由 | P0 | 2天 | API-001 |

#### 前端任务

| 任务ID | 任务 | 优先级 | 工期 | 依赖 |
|--------|------|--------|------|------|
| UI-015 | 测试场页面 | P0 | 3天 | API-001 |
| UI-016 | 对话组件 | P0 | 2天 | UI-015 |
| UI-017 | 流式输出处理 | P0 | 2天 | UI-016 |
| UI-018 | 集群管理页面 | P0 | 2天 | UI-002 |
| UI-019 | 集群创建Modal | P0 | 3天 | UI-018 |
| UI-020 | 仪表盘页面 | P1 | 3天 | UI-004 |

**测试节点**:
- [ ] 模型实例生命周期测试
- [ ] 集群创建测试
- [ ] OpenAI API兼容性测试
- [ ] 流式输出测试
- [ ] 前端对话功能测试

---

### Phase 5: 监控与优化 (Week 11-12)

**目标**: 可观测性, 性能优化, 文档

#### 后端任务

| 任务ID | 任务 | 优先级 | 工期 | 依赖 |
|--------|------|--------|------|------|
| MON-001 | Prometheus指标采集 | P0 | 2天 | - |
| MON-002 | GPU指标导出 | P0 | 2天 | MON-001 |
| MON-003 | API指标导出 | P0 | 1天 | MON-001 |
| MON-004 | Grafana仪表盘配置 | P0 | 2天 | MON-002 |
| PERF-001 | 数据库查询优化 | P1 | 2天 | MI-001 |
| PERF-002 | API响应缓存 | P1 | 2天 | API-001 |

#### 前端任务

| 任务ID | 任务 | 优先级 | 工期 | 依赖 |
|--------|------|--------|------|------|
| UI-021 | 监控仪表盘页面 | P1 | 3天 | MON-004 |
| UI-022 | 图表组件(ECharts) | P1 | 2天 | UI-021 |
| UI-023 | 前端性能优化 | P1 | 2天 | - |
| UI-024 | 错误边界处理 | P0 | 1天 | - |

#### 测试与文档

| 任务ID | 任务 | 优先级 | 工期 | 依赖 |
|--------|------|--------|------|------|
| TST-001 | 单元测试补充 | P0 | 3天 | - |
| TST-002 | 集成测试补充 | P0 | 3天 | Phase 4完成 |
| TST-003 | 性能压力测试 | P1 | 2天 | Phase 4完成 |
| DOC-001 | API文档生成 | P0 | 1天 | API-001 |
| DOC-002 | 部署文档编写 | P0 | 2天 | CL-002 |
| DOC-003 | 用户手册编写 | P1 | 3天 | - |

**测试节点**:
- [ ] 单元测试覆盖率 > 80%
- [ ] 集成测试通过率 100%
- [ ] 性能基准测试达标
- [ ] 文档完整性检查

---

## 4. 测试节点定义

### 4.1 测试金字塔

```
                    /\
                   /  \
                  / E2E \          ← 端到端测试 (10%)
                 /──────\
                /        \
               / 集成测试  \       ← 集成测试 (30%)
              /────────────\
             /              \
            /   单元测试     \    ← 单元测试 (60%)
           /────────────────\
```

### 4.2 各阶段测试要求

#### Phase 1 测试要求

**后端:**
- [ ] 数据库Schema迁移测试
- [ ] 配置加载测试
- [ ] 日志输出测试
- [ ] 单元测试覆盖率 > 70%

**前端:**
- [ ] 布局组件快照测试
- [ ] 通用组件单元测试
- [ ] 路由测试
- [ ] 单元测试覆盖率 > 70%

#### Phase 2 测试要求

**后端:**
- [ ] Server-Worker通信测试
- [ ] 注册/心跳集成测试
- [ ] 健康检查测试
- [ ] 单元测试覆盖率 > 75%

**前端:**
- [ ] Worker列表组件测试
- [ ] API Mock测试
- [ ] 实时更新Hook测试
- [ ] 单元测试覆盖率 > 75%

#### Phase 3 测试要求

**后端:**
- [ ] vLLM后端集成测试
- [ ] 调度器单元测试
- [ ] 过滤器链测试
- [ ] 单元测试覆盖率 > 80%

**前端:**
- [ ] 模型列表测试
- [ ] 表单验证测试
- [ ] 组件交互测试
- [ ] 单元测试覆盖率 > 80%

#### Phase 4 测试要求

**后端:**
- [ ] 模型实例E2E测试
- [ ] OpenAI API兼容性测试
- [ ] 集群管理集成测试
- [ ] 集成测试覆盖率 > 70%

**前端:**
- [ ] 对话功能E2E测试
- [ ] 集群创建流程测试
- [ ] 页面集成测试
- [ ] E2E测试覆盖率 > 60%

#### Phase 5 测试要求

**后端:**
- [ ] 完整集成测试套件
- [ ] 性能压力测试
- [ ] 单元测试覆盖率 > 85%
- [ ] 集成测试覆盖率 > 75%

**前端:**
- [ ] 完整E2E测试套件
- [ ] 性能测试(Lighthouse)
- [ ] 单元测试覆盖率 > 85%
- [ ] E2E测试覆盖率 > 70%

### 4.3 测试自动化

```yaml
# .github/workflows/test.yml
name: Test Pipeline

on: [push, pull_request]

jobs:
  backend-unit:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Run unit tests
        run: |
          cd backend
          pytest tests/unit/ --cov=backend --cov-report=xml

  backend-integration:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:15
      redis:
        image: redis:7
    steps:
      - name: Run integration tests
        run: pytest tests/integration/

  frontend-test:
    runs-on: ubuntu-latest
    steps:
      - name: Install dependencies
        run: cd ui && npm install
      - name: Run tests
        run: cd ui && npm run test:coverage

  e2e-test:
    runs-on: ubuntu-latest
    needs: [backend-unit, backend-integration, frontend-test]
    steps:
      - name: Run E2E tests
        run: npm run test:e2e
```

---

## 5. 里程碑交付

### Milestone 1: 基础架构完成 (Week 2)

**交付物:**
- [x] 数据库Schema设计完成
- [x] 核心配置系统完成
- [x] 前端基础框架完成
- [x] 基础测试通过

**演示场景:**
```bash
# 1. 启动项目
docker-compose up -d

# 2. 运行测试
pytest tests/unit/
npm test

# 3. 访问前端
open http://localhost:3000
# → 显示基础布局, 可导航各页面(Mock数据)
```

---

### Milestone 2: Server-Worker架构完成 (Week 4)

**交付物:**
- [x] Server主类完成
- [x] Worker主类完成
- [x] 注册/心跳机制完成
- [x] 前端资源管理页面完成

**演示场景:**
```bash
# 1. 启动Server
python -m backend.server.server --mode server

# 2. 启动Worker
python -m backend.worker.worker --mode worker

# 3. 查看Worker状态
curl http://localhost:8000/api/v1/workers
# → 返回已注册的Worker列表

# 4. 访问前端资源页面
open http://localhost:3000/resources
# → 显示Worker列表, 实时更新状态
```

---

### Milestone 3: 推理与调度完成 (Week 7)

**交付物:**
- [x] vLLM后端完成
- [x] 调度框架完成
- [x] 前端模型管理页面完成

**演示场景:**
```bash
# 1. 创建调度请求
curl -X POST http://localhost:8000/api/v1/schedule \
  -H "Content-Type: application/json" \
  -d '{
    "model_id": 1,
    "replicas": 2,
    "backend": "vllm"
  }'
# → 返回调度成功的Worker分配

# 2. 查看模型实例
curl http://localhost:8000/api/v1/instances
# → 返回运行中的模型实例

# 3. 访问前端模型页面
open http://localhost:3000/models
# → 显示模型列表, 可部署/停止模型
```

---

### Milestone 4: 完整功能完成 (Week 10)

**交付物:**
- [x] 模型实例管理完成
- [x] 多集群管理完成
- [x] OpenAI API完成
- [x] 前端所有页面完成

**演示场景:**
```bash
# 1. 创建集群
curl -X POST http://localhost:8000/api/v1/clusters \
  -H "Content-Type: application/json" \
  -d '{"name": "production", "type": "docker"}'

# 2. 部署模型
curl -X POST http://localhost:8000/api/v1/models/deploy \
  -H "Content-Type: application/json" \
  -d '{
    "model_id": 1,
    "replicas": 2,
    "cluster_id": 1
  }'

# 3. 调用OpenAI API
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "qwen2.5-7b",
    "messages": [{"role": "user", "content": "Hello!"}]
  }'
# → 返回模型响应

# 4. 访问前端测试场
open http://localhost:3000/playground
# → 可进行对话测试
```

---

### Milestone 5: MVP发布 (Week 12)

**交付物:**
- [x] 监控系统完成
- [x] 所有测试通过
- [x] 文档完善
- [x] 部署脚本完成

**演示场景:**
```bash
# 1. 一键部署
./scripts/deploy.sh production

# 2. 访问Grafana监控
open http://localhost:3001
# → 显示GPU利用率, API调用量等指标

# 3. 运行完整测试套件
./scripts/test.sh
# → 所有测试通过

# 4. 查看文档
open docs/README.md
# → 完整的使用和部署文档
```

---

## 6. 风险与应对

### 6.1 技术风险

| 风险 | 影响 | 应对措施 | 责任人 |
|------|------|----------|--------|
| vLLM兼容性问题 | 高 | 提前测试,准备降级方案 | 后端B组 |
| GPU资源不足 | 中 | 使用Mock测试,小规模验证 | DevOps |
| 前后端接口不一致 | 中 | OpenAPI Spec强制对齐 | 架构师 |
| 性能不达标 | 高 | 预留1周性能优化时间 | 全员 |

### 6.2 进度风险

| 风险 | 影响 | 应对措施 | 责任人 |
|------|------|----------|--------|
| 任务延期 | 中 | 20%缓冲时间,每周Review | 项目经理 |
| 依赖阻塞 | 高 | 并行开发,Mock先行 | 架构师 |
| 人员变动 | 高 | 知识共享,代码Review | 团队Lead |

---

## 7. 关键成功指标

### 7.1 质量指标

| 指标 | 目标值 | 测量方式 |
|------|--------|----------|
| 单元测试覆盖率 | > 85% | pytest --cov |
| 集成测试覆盖率 | > 75% | pytest tests/integration/ |
| E2E测试覆盖率 | > 70% | npm run test:e2e |
| API响应时间 | < 500ms (P50) | Prometheus metrics |
| GPU利用率 | > 80% | Grafana dashboard |

### 7.2 进度指标

| 指标 | 目标值 | 测量方式 |
|------|--------|----------|
| 按时交付率 | > 90% | Milestone达成情况 |
| Bug修复时间 | < 2天 | Issue tracking |
| Code Review响应 | < 4小时 | PR tracking |

---

## 8. 附录

### 8.1 开发环境要求

```bash
# 后端
Python 3.10+
PostgreSQL 15
Redis 7
NVIDIA GPU (可选)

# 前端
Node.js 18+
npm 9+

# 工具
Docker 24+
Docker Compose v2
Git 2.40+
```

### 8.2 推荐工具

| 类别 | 工具 | 用途 |
|------|------|------|
| IDE | VSCode, PyCharm | 开发 |
| API测试 | Postman, Insomnia | API调试 |
| 数据库 | DBeaver, pgAdmin | 数据库管理 |
| 监控 | Grafana, Prometheus | 性能监控 |
| 日志 | Loki, Grafana | 日志查询 |

---

**文档版本**: v1.0
**最后更新**: 2025-01-14
**维护者**: TokenMachine Team
