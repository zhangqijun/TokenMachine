# TokenMachine Development Roadmap

> Organized by modules and priorities. This document tracks all development tasks.

## 新增设计文档参考

基于 GPUStack 架构分析，新增以下设计文档：
- [SERVER_WORKER_ARCHITECTURE.md](./docs/SERVER_WORKER_ARCHITECTURE.md) - Server-Worker 分离架构
- [SCHEDULING_FRAMEWORK.md](./docs/SCHEDULING_FRAMEWORK.md) - 调度策略框架
- [INFERENCE_BACKEND_PLUGIN.md](./docs/INFERENCE_BACKEND_PLUGIN.md) - 推理后端插件系统
- [MODEL_INSTANCE_MANAGEMENT.md](./docs/MODEL_INSTANCE_MANAGEMENT.md) - 模型实例管理
- [MULTI_CLUSTER_MANAGEMENT.md](./docs/MULTI_CLUSTER_MANAGEMENT.md) - 多集群管理

---

## Legend

- **P0**: Critical - Must have for MVP
- **P1**: High - Important for production readiness
- **P2**: Medium - Nice to have
- **P3**: Low - Future enhancements

---

## [P0] Server-Worker 架构模块 (新增)

基于 GPUStack 架构，实现 Server-Worker 分离架构。

| Task ID | Task | Status | Assignee |
|---------|------|--------|----------|
| SW-001 | 创建 `backend/server/` 目录结构 | TODO | |
| SW-002 | 实现 Server 主类 (`server/server.py`) | TODO | |
| SW-003 | 实现 WorkerController | TODO | |
| SW-004 | 实现 ModelInstanceController | TODO | |
| SW-005 | 实现 ClusterController | TODO | |
| SW-006 | 创建 `backend/worker/` 目录结构 | TODO | |
| SW-007 | 实现 Worker 主类 (`worker/worker.py`) | TODO | |
| SW-008 | 实现 ServeManager (`worker/serve_manager.py`) | TODO | |
| SW-009 | 实现状态采集器 (`worker/collector.py`) | TODO | |
| SW-010 | 实现指标导出器 (`worker/exporter.py`) | TODO | |
| SW-011 | 实现 Worker 注册 API | TODO | |
| SW-012 | 实现心跳 API | TODO | |
| SW-013 | 实现状态上报 API | TODO | |
| SW-014 | 实现健康检查循环 | TODO | |
| SW-015 | 数据库 Schema 更新 (clusters, workers, model_instances) | TODO | |

### Files
- `backend/server/server.py` - Server 主类
- `backend/server/controllers/` - 控制器
- `backend/server/api/workers.py` - Worker 管理 API
- `backend/worker/worker.py` - Worker 主类
- `backend/worker/serve_manager.py` - 模型服务管理
- `backend/worker/api/` - Worker API

---

## [P0] 调度策略框架模块 (新增)

可插拔的调度策略框架，支持过滤器、选择器、评分器。

| Task ID | Task | Status | Assignee |
|---------|------|--------|----------|
| SCH-001 | 创建 `backend/scheduler/` 目录 | TODO | |
| SCH-002 | 实现基础抽象 (`policies/base.py`) | TODO | |
| SCH-003 | 实现调度器主类 (`scheduler/scheduler.py`) | TODO | |
| SCH-004 | 实现 StatusFilter | TODO | |
| SCH-005 | 实现 ClusterFilter | TODO | |
| SCH-006 | 实现 GPUFilter | TODO | |
| SCH-007 | 实现 LabelFilter | TODO | |
| SCH-008 | 实现 BackendFilter | TODO | |
| SCH-009 | 实现 WorkerFilterChain | TODO | |
| SCH-010 | 实现 BaseCandidateSelector | TODO | |
| SCH-011 | 实现 VLLMSelector | TODO | |
| SCH-012 | 实现 SGLangSelector | TODO | |
| SCH-013 | 实现 PlacementScorer | TODO | |
| SCH-014 | 实现配置管理系统 | TODO | |

### Files
- `backend/scheduler/scheduler.py` - 主调度器
- `backend/scheduler/policies/base.py` - 策略抽象
- `backend/scheduler/policies/worker_filters/` - 过滤器
- `backend/scheduler/policies/candidate_selectors/` - 选择器
- `backend/scheduler/policies/scorers/` - 评分器

---

## [P0] 推理后端插件系统 (新增)

可插拔的推理引擎架构，支持多种后端。

| Task ID | Task | Status | Assignee |
|---------|------|--------|----------|
| BE-001 | 创建 `backend/worker/backends/` 目录 | TODO | |
| BE-002 | 实现 InferenceBackend 抽象 | TODO | |
| BE-003 | 实现后端配置管理 | TODO | |
| BE-004 | 实现后端注册表 | TODO | |
| BE-005 | 实现 VLLMBackend | TODO | |
| BE-006 | 实现 SGLangBackend | TODO | |
| BE-007 | 实现 TensorRTBackend (可选) | TODO | |
| BE-008 | 实现 ChituBackend (可选) | TODO | |
| BE-009 | 实现 InferenceBackendManager | TODO | |
| BE-010 | 实现配置同步 | TODO | |

### Files
- `backend/worker/backends/base.py` - 后端抽象
- `backend/worker/backends/vllm_backend.py` - vLLM 后端
- `backend/worker/backends/sglang_backend.py` - SGLang 后端

---

## [P0] 模型实例管理模块 (新增)

Model 与 ModelInstance 分离，支持多副本、灰度发布。

| Task ID | Task | Status | Assignee |
|---------|------|--------|----------|
| MI-001 | 更新数据库 Schema (model_instances 表) | TODO | |
| MI-002 | 实现 ModelInstanceController | TODO | |
| MI-003 | 实现健康检查循环 | TODO | |
| MI-004 | 实现扩缩容逻辑 | TODO | |
| MI-005 | 实现 CanaryController (灰度发布) | TODO | |
| MI-006 | 实现流量权重路由 | TODO | |
| MI-007 | 实现 ABTest 模型 (可选) | TODO | |
| MI-008 | 实现 A/B 路由 (可选) | TODO | |

### Files
- `backend/controllers/instance_controller.py`
- `backend/controllers/canary_controller.py`

---

## [P0] 多集群管理模块 (新增)

跨地域、跨环境的 GPU 集群管理。

| Task ID | Task | Status | Assignee |
|---------|------|--------|----------|
| CL-001 | 创建 `backend/cluster/` 目录 | TODO | |
| CL-002 | 实现 BaseClusterProvider | TODO | |
| CL-003 | 实现 Cluster 数据模型 | TODO | |
| CL-004 | 实现 ClusterController | TODO | |
| CL-005 | 实现 DockerClusterProvider | TODO | |
| CL-006 | 实现 KubernetesClusterProvider | TODO | |
| CL-007 | 实现集群健康检查循环 | TODO | |
| CL-008 | 实现集群管理 API | TODO | |
| CL-009 | 实现 MultiClusterFilter | TODO | |
| CL-010 | 实现配额管理 | TODO | |

### Files
- `backend/cluster/base.py`
- `backend/cluster/docker_cluster.py`
- `backend/cluster/kubernetes_cluster.py`
- `backend/controllers/cluster_controller.py`
- `backend/api/v1/clusters.py`

---

## [P0] GPU Management Module

| Task ID | Task | Status | Assignee |
|---------|------|--------|----------|
| GPU-001 | GPU resource discovery (NVIDIA) | TODO | |
| GPU-002 | GPU status monitoring (utilization, temperature, VRAM) | TODO | |
| GPU-003 | GPU resource allocation algorithm | TODO | |
| GPU-004 | GPU health checking | TODO | |
| GPU-005 | GPU metrics export to Prometheus | TODO | |

### Files
- `backend/core/gpu.py` - GPU manager implementation
- `backend/services/gpu_service.py` - GPU business logic

---

## [P0] Model Deployment Module

| Task ID | Task | Status | Assignee |
|---------|------|--------|----------|
| MDL-001 | Model repository integration (HuggingFace/ModelScope) | TODO | |
| MDL-002 | Model download with progress tracking | TODO | |
| MDL-003 | Model download resume support | TODO | |
| MDL-004 | Model storage management | TODO | |
| MDL-005 | Model version management (basic) | TODO | |
| MDL-006 | vLLM backend integration | TODO | |
| MDL-007 | Worker process management (start/stop/restart) | TODO | |
| MDL-008 | Worker health checking | TODO | |
| MDL-009 | Deployment status management (starting/running/stopped/error) | TODO | |
| MDL-010 | Multi-replica support (single machine) | TODO | |
| MDL-011 | GPU binding to workers | TODO | |
| MDL-012 | Model fingerprint verification | TODO | |

### Files
- `backend/services/model_service.py` - Model lifecycle management
- `backend/services/deployment_service.py` - Deployment orchestration
- `backend/workers/vllm_worker.py` - vLLM worker wrapper
- `backend/workers/worker_pool.py` - Worker pool management

---

## [P0] API Gateway Module

| Task ID | Task | Status | Assignee |
|---------|------|--------|----------|
| API-001 | OpenAI Chat Completions API (`/v1/chat/completions`) | TODO | |
| API-002 | OpenAI Models API (`/v1/models`) | TODO | |
| API-003 | Streaming response support (SSE) | TODO | |
| API-004 | API Key authentication (Bearer Token) | TODO | |
| API-005 | Request routing to workers | TODO | |
| API-006 | Round-robin load balancing | TODO | |
| API-007 | Request/response format conversion | TODO | |
| API-008 | Error handling and retry logic | TODO | |

### Files
- `backend/api/v1/chat.py` - Chat completions endpoint
- `backend/api/v1/models.py` - Models endpoint
- `backend/api/deps.py` - Dependency injection
- `backend/api/middleware.py` - Authentication middleware

---

## [P0] Monitoring Module

| Task ID | Task | Status | Assignee |
|---------|------|--------|----------|
| MON-001 | Prometheus metrics collection | TODO | |
| MON-002 | GPU metrics (utilization, memory, temperature) | TODO | |
| MON-003 | Model metrics (tokens, requests, latency) | TODO | |
| MON-004 | API metrics (QPS, error rate, latency) | TODO | |
| MON-005 | System metrics (CPU, memory, disk) | TODO | |
| MON-006 | `/metrics` endpoint | TODO | |
| MON-007 | Structured logging (Loguru) | TODO | |
| MON-008 | Grafana dashboard configuration | TODO | |

### Files
- `backend/monitoring/metrics.py` - Prometheus metrics definitions
- `backend/monitoring/exporter.py` - Metrics endpoint

---

## [P0] Database & Auth Module

| Task ID | Task | Status | Assignee |
|---------|------|--------|----------|
| DB-001 | Database schema design (PostgreSQL) | TODO | |
| DB-002 | SQLAlchemy models implementation | DONE | |
| DB-003 | Alembic migration setup | DONE | |
| DB-004 | User model and management | DONE | |
| DB-005 | API Key model and management | DONE | |
| DB-006 | API Key generation (hash + prefix) | DONE | |
| DB-007 | API Key authentication middleware | TODO | |
| DB-008 | Usage logging | DONE | |

### Files
- `backend/models/database.py` - SQLAlchemy models
- `backend/core/database.py` - Database session management
- `migrations/versions/` - Alembic migration scripts

---

## [P1] Admin API Module

| Task ID | Task | Status | Assignee |
|---------|------|--------|----------|
| ADM-001 | Model management API (create/list/delete) | TODO | |
| ADM-002 | Deployment management API (create/stop/list) | TODO | |
| ADM-003 | GPU status API | TODO | |
| ADM-004 | API Key management API (create/list/revoke) | TODO | |
| ADM-005 | User management API | TODO | |

### Files
- `backend/api/v1/admin.py` - Admin endpoints

---

## [P1] Web UI Module

| Task ID | Task | Status | Assignee |
|---------|------|--------|----------|
| UI-001 | Dashboard page (overview) | TODO | |
| UI-002 | Model management page | TODO | |
| UI-003 | Deployment management page | TODO | |
| UI-004 | GPU status page | TODO | |
| UI-005 | API Key management page | TODO | |
| UI-006 | Monitoring dashboard | TODO | |
| UI-007 | API documentation integration | DONE | |

### Files
- `ui/src/pages/` - Page components
- `ui/src/components/` - Reusable components

---

## [P1] Testing Module

| Task ID | Task | Status | Assignee |
|---------|------|--------|----------|
| TST-001 | Unit tests for GPU service | TODO | |
| TST-002 | Unit tests for model service | TODO | |
| TST-003 | Unit tests for deployment service | TODO | |
| TST-004 | Unit tests for security (API Key, JWT) | DONE | |
| TST-005 | Integration tests for chat API | DONE | |
| TST-006 | Integration tests for models API | DONE | |
| TST-007 | Integration tests for admin API | DONE | |
| TST-008 | E2E tests for model deployment workflow | TODO | |
| TST-009 | Load testing | TODO | |

### Files
- `tests/unit/` - Unit tests
- `tests/integration/` - Integration tests
- `pytest.ini` - Test configuration

---

## [P1] Deployment Module

| Task ID | Task | Status | Assignee |
|---------|------|--------|----------|
| DPL-001 | Dockerfile optimization | DONE | |
| DPL-002 | Docker Compose configuration | DONE | |
| DPL-003 | Prometheus configuration | DONE | |
| DPL-004 | Nginx reverse proxy configuration | DONE | |
| DPL-005 | Health check endpoints | TODO | |
| DPL-006 | Graceful shutdown handling | TODO | |
| DPL-007 | Deployment scripts | DONE |

### Files
- `infra/docker/Dockerfile` - Backend container
- `infra/docker/docker-compose.yml` - Service orchestration
- `infra/nginx/nginx.conf` - Reverse proxy
- `scripts/deploy.sh` - Deployment script

---

## [P2] Billing Module (Future)

| Task ID | Task | Status | Assignee |
|---------|------|--------|----------|
| BIL-001 | Token-based billing calculation | TODO | |
| BIL-002 | Quota management | TODO | |
| BIL-003 | Invoice generation | TODO | |
| BIL-004 | Payment gateway integration | TODO | |
| BIL-005 | Usage analytics dashboard | TODO | |

---

## [P2] Multi-Tenant Module (Future)

| Task ID | Task | Status | Assignee |
|---------|------|--------|----------|
| MTN-001 | Organization model | TODO | |
| MTN-002 | Team management | TODO | |
| MTN-003 | Resource pool isolation | TODO | |
| MTN-004 | Per-tenant quotas | TODO | |
| MTN-005 | RBAC implementation | TODO | |

---

## [P2] Advanced Inference Module (Future)

| Task ID | Task | Status | Assignee |
|---------|------|--------|----------|
| INF-001 | SGLang backend support | TODO | |
| INF-002 | Chitu backend support (domestic chips) | TODO | |
| INF-003 | Format conversion (OpenAI/Claude/Gemini) | TODO | |
| INF-004 | Smart routing based on model/cost | TODO | |
| INF-005 | External API channel support | TODO | |

---

## [P2] Model Fine-tuning Module (Future)

| Task ID | Task | Status | Assignee |
|---------|------|--------|----------|
| FT-001 | LoRA training integration | TODO | |
| FT-002 | KTransformers integration (CPU+GPU) | TODO | |
| FT-003 | Training job management | TODO | |
| FT-004 | Model evaluation | TODO | |
| FT-005 | A/B testing for model versions | TODO | |

---

## [P2] Enterprise Features Module (Future)

| Task ID | Task | Status | Assignee |
|---------|------|--------|----------|
| ENT-001 | SSO login (OIDC/SAML) | TODO | |
| ENT-002 | Audit logging | TODO | |
| ENT-003 | Advanced RBAC | TODO | |
| ENT-004 | Compliance features (等级保护) | TODO | |
| ENT-005 | Data encryption at rest | TODO | |

---

## [P3] Ecosystem Module (Future)

| Task ID | Task | Status | Assignee |
|---------|------|--------|----------|
| ECO-001 | Plugin marketplace | TODO | |
| ECO-002 | Model marketplace | TODO | |
| ECO-003 | API开放平台 | TODO | |
| ECO-004 | SDK development | TODO | |
| ECO-005 | Third-party integrations (Jira, Slack, Feishu) | TODO | |

---

## Progress Tracking

### Overall Progress

| Module | Completed | Total | Progress |
|--------|-----------|-------|----------|
| Server-Worker 架构 | 0 | 15 | 0% |
| 调度策略框架 | 0 | 14 | 0% |
| 推理后端插件 | 0 | 10 | 0% |
| 模型实例管理 | 0 | 8 | 0% |
| 多集群管理 | 0 | 10 | 0% |
| GPU Management | 0 | 5 | 0% |
| Model Deployment | 0 | 12 | 0% |
| API Gateway | 0 | 8 | 0% |
| Monitoring | 0 | 8 | 0% |
| Database & Auth | 4 | 8 | 50% |
| Admin API | 0 | 5 | 0% |
| Web UI | 1 | 7 | 14% |
| Testing | 3 | 9 | 33% |
| Deployment | 4 | 7 | 57% |
| Billing | 0 | 5 | 0% |
| Multi-Tenant | 0 | 5 | 0% |
| Advanced Inference | 0 | 5 | 0% |
| Fine-tuning | 0 | 5 | 0% |
| Enterprise | 0 | 5 | 0% |
| Ecosystem | 0 | 5 | 0% |
| **TOTAL** | **12** | **156** | **8%** |

### Priority Breakdown

| Priority | Tasks | Completed | Progress |
|----------|-------|-----------|----------|
| P0 | 92 | 4 | 4% |
| P1 | 20 | 8 | 40% |
| P2 | 35 | 0 | 0% |
| P3 | 5 | 0 | 0% |

---

## Next Steps (Current Sprint)

### 新架构实施优先级

1. **Phase 1: 数据模型更新** - 添加 Cluster、Worker、ModelInstance 表
2. **Phase 2: Server-Worker 基础** - 实现基本的 Server 和 Worker 类
3. **Phase 3: 调度框架** - 实现基础的调度策略
4. **Phase 4: 后端插件** - 实现 vLLM 后端插件
5. **Phase 5: 集成测试** - 端到端测试

### 当前 Sprint 任务

1. **数据库 Schema** - 更新数据库模型
2. **Server 框架** - 实现 Server 主类和控制器
3. **Worker 框架** - 实现 Worker 主类和 ServeManager
4. **注册/心跳** - 实现 Worker 注册和心跳机制

---

## Notes

- 本文档基于 GPUStack 架构分析进行了更新
- 新增了 5 个核心架构模块的设计文档
- 所有新增任务都是基于 GPUStack 的成熟实践
- 技术栈可能需要调整（详见各设计文档）

---

**文档版本**: v2.0
**最后更新**: 2025-01-14
**基于**: GPUStack 架构分析
