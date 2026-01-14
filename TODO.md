# TokenMachine Development Roadmap

> Organized by modules and priorities. This document tracks all development tasks.

## Legend

- **P0**: Critical - Must have for MVP
- **P1**: High - Important for production readiness
- **P2**: Medium - Nice to have
- **P3**: Low - Future enhancements

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

## [P2] Deployment Module

| Task ID | Task | Status | Assignee |
|---------|------|--------|----------|
| DPL-001 | Dockerfile optimization | DONE | |
| DPL-002 | Docker Compose configuration | DONE | |
| DPL-003 | Prometheus configuration | DONE | |
| DPL-004 | Nginx reverse proxy configuration | DONE | |
| DPL-005 | Health check endpoints | TODO | |
| DPL-006 | Graceful shutdown handling | TODO | |
| DPL-007 | Deployment scripts | DONE | |

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
| GPU Management | 0 | 5 | 0% |
| Model Deployment | 0 | 12 | 0% |
| API Gateway | 0 | 8 | 0% |
| Monitoring | 0 | 8 | 0% |
| Database & Auth | 4 | 8 | 50% |
| Admin API | 0 | 5 | 0% |
| Web UI | 0 | 7 | 0% |
| Testing | 3 | 9 | 33% |
| Deployment | 4 | 7 | 57% |
| **TOTAL** | **11** | **83** | **13%** |

### Priority Breakdown

| Priority | Tasks | Completed | Progress |
|----------|-------|-----------|----------|
| P0 | 44 | 4 | 9% |
| P1 | 20 | 7 | 35% |
| P2 | 19 | 0 | 0% |
| P3 | 5 | 0 | 0% |

---

## Next Steps (Current Sprint)

1. **GPU Management** - Implement GPU discovery and monitoring
2. **Model Service** - Complete model download and storage
3. **Worker Pool** - Implement vLLM worker management
4. **Chat API** - Implement OpenAI-compatible chat completions

---

## Notes

- This roadmap is a living document and will be updated as development progresses
- Tasks marked as DONE are already implemented in the current codebase
- Future modules (P2, P3) are planned but not scheduled for current development
