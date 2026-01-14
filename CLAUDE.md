# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

TokenMachine is an enterprise-grade AI model deployment and management platform. It provides OpenAI-compatible APIs, GPU cluster scheduling, model versioning, and multi-inference engine support (vLLM, SGLang, Chitu).

**Tech Stack:**
- Backend: FastAPI + Python 3.10+, PostgreSQL 15, Redis 7, SQLAlchemy 2.0
- Frontend: React 19.2 + TypeScript + Vite + Ant Design 6.2 + Zustand
- Inference: vLLM, SGLang, Chitu
- Monitoring: Prometheus + Grafana

**Architecture Pattern:** Clean architecture with separation between API layer, services, workers, and monitoring.

## Common Commands

### Backend Development

```bash
# Run development server
uvicorn backend.main:app --reload

# Install test dependencies
pip install -r tests/requirements.txt

# Run all backend tests
pytest

# Run specific test categories
pytest -m unit          # Unit tests only
pytest -m integration  # Integration tests only
pytest tests/unit/test_security.py  # Specific file

# Run with coverage
pytest --cov=backend --cov-report=html

# Database migrations
alembic revision --autogenerate -m "message"
alembic upgrade head
alembic downgrade -1
```

### Frontend Development

```bash
cd ui

# Install dependencies
npm install

# Development server
npm run dev

# Build for production
npm run build

# Run tests
npm test              # Watch mode
npm run test:run      # Run once
npm run test:coverage # With coverage
```

### Docker Development

```bash
cd infra/docker

# Start all services
docker compose up -d

# View logs
docker compose logs -f [service]

# Stop all services
docker compose down
```

## Codebase Structure

```
TokenMachine/
├── backend/              # Python backend (FastAPI)
│   ├── core/            # Core utilities (config, database, gpu, security)
│   ├── api/             # API endpoints (v1/chat.py, v1/models.py, v1/admin.py)
│   ├── models/          # SQLAlchemy database models
│   ├── services/        # Business logic (model_service, deployment_service, gpu_service)
│   ├── workers/         # Background worker pool (vllm_worker, worker_pool)
│   └── monitoring/      # Prometheus metrics
│
├── ui/                  # React frontend
│   └── src/
│       ├── components/  # Reusable UI components
│       ├── pages/       # Page components
│       ├── store/       # Zustand state management
│       └── api/         # API client
│
├── infra/               # Infrastructure
│   ├── docker/          # Docker files (Dockerfile, docker-compose.yml)
│   ├── prometheus/      # Prometheus config
│   └── nginx/           # nginx config
│
├── migrations/          # Database migrations (Alembic)
├── scripts/             # Deployment and utility scripts
├── tests/               # Test suite
│   ├── unit/           # Backend unit tests
│   ├── integration/    # Backend integration tests
│   └── conftest.py     # Shared pytest fixtures
│
└── docs/               # Documentation
    ├── PRODUCT_DESIGN.md  # Product requirements
    ├── BACKEND_DESIGN.md  # Backend architecture
    ├── FRONTEND_DESIGN.md # Frontend design
    ├── TESTING.md         # Testing guide
    └── DEPLOYMENT.md      # Deployment instructions
```

## Architecture Notes

### Backend Service Layer

The backend uses a service-oriented architecture:

- **API Layer** (`api/v1/`): FastAPI endpoints with dependency injection via `api/deps.py`
- **Services Layer** (`services/`): Business logic for models, deployments, GPU management
- **Workers** (`workers/`): Background processing for model inference with worker pool pattern
- **GPU Manager** (`core/gpu.py`): Manages GPU allocation across heterogeneous hardware (NVIDIA, 昇腾, 沐曦, 海光)

### OpenAI-Compatible API

The chat API (`api/v1/chat.py`) implements OpenAI-compatible endpoints. Key patterns:
- Format conversion between internal models and OpenAI request/response formats
- JWT-based authentication via API keys
- Request routing to appropriate inference engines

### Database Models

SQLAlchemy models (`models/database.py`) include:
- User, Model, Deployment, GPU, APIKey, UsageLog
- Async database session management via `core/database.py`

### Frontend State Management

Uses Zustand for state management with stores in `ui/src/store/index.ts`. Components use Ant Design for UI consistency.

### Testing Infrastructure

- **Pytest fixtures** in `tests/conftest.py`: `db_session`, `test_user`, `test_api_key`, `test_model`, `test_deployment`, `mock_gpu_manager`, `mock_worker_pool`
- **Test markers**: `unit`, `integration`, `slow`, `gpu`, `auth`
- Unit tests use in-memory SQLite; integration tests use PostgreSQL
- Frontend tests use Vitest with jsdom environment

## Configuration

### Environment Variables (.env.example)

Key configuration areas:
- Database: PostgreSQL connection string
- Redis: Cache connection
- API: Host/port, CORS, security settings
- GPU: Memory utilization (`GPU_MEMORY_UTILIZATION`), max model length (`MAX_MODEL_LENGTH`)
- Storage: Model storage path, log paths
- vLLM: Inference engine parameters

### Docker Compose Services

Services defined in `infra/docker/docker-compose.yml`:
- `postgres` (port 5432)
- `redis` (port 6379)
- `api` (ports 8000, 9090) - FastAPI backend
- `web` (ports 8080, 8443) - React frontend with nginx
- `prometheus` (port 9091) - Metrics
- `grafana` (port 3001) - Dashboards

Note: Non-standard ports for public access (8080/8443 instead of 80/443)

## Inference Engine Integration

The platform supports multiple inference engines via the worker pool:
- **vLLM**: PagedAttention for high-throughput inference
- **SGLang**: Structured generation optimization
- **Chitu**: Chinese domestic chip support (华为昇腾, 沐曦, 海光)

Worker abstraction in `workers/worker_pool.py` allows pluggable inference backends.

## Important Notes

1. **Project Structure**: Backend code is in `backend/` (not `tokenmachine/` or `inferx/`). Frontend is in `ui/` (not `web/` or `frontend/`).

2. **API Authentication**: All API endpoints use JWT token authentication via API keys. API keys have prefixes and are stored hashed in the database.

3. **GPU Scheduling**: The GPU manager handles heterogeneous hardware. When working with GPU-related code, ensure abstraction supports multiple GPU vendors.

4. **Database Migrations**: Always create migrations for schema changes using Alembic. Do not modify database models directly without migrations.

5. **Test Coverage Goals**: Unit tests >90%, Integration tests >70%, Component tests >60%

6. **Mock External Services**: In tests, always mock GPU manager (`mock_gpu_manager`) and worker pool (`mock_worker_pool`) fixtures.

7. **Frontend Path Aliases**: Use `@/` prefix for imports from `ui/src/` (configured in `vite.config.ts`).

8. **Docker Context**: When running docker compose, navigate to `infra/docker/` first.
