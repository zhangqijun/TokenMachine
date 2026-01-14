# TokenMachine

> 一站式 AI 模型部署、调度与管理平台

[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10%2B-brightgreen.svg)](https://www.python.org/)

---

## 简介

TokenMachine 是一个开源的企业级 AI 模型部署与管理平台，支持多种推理引擎、多种硬件架构，提供 OpenAI 兼容的 API，帮助企业快速构建私有化的大模型服务能力。

### 核心特性

- **多推理引擎支持** - 集成 vLLM、SGLang、Chitu 等主流推理引擎
- **GPU 集群调度** - 智能资源分配，支持 NVIDIA、昇腾、沐曦、海光等异构硬件
- **OpenAI 兼容 API** - 无缝替换 OpenAI API，支持零代码迁移
- **模型版本管理** - Git-like 版本控制，支持灰度发布和一键回滚
- **计费与配额** - 内置 Token 计费系统，支持多租户资源隔离
- **模型微调** - 集成 LoRA 训练，支持 CPU+GPU 异构微调超大模型
- **监控与可观测性** - Prometheus + Grafana 监控，完整的企业级指标

---

## 快速开始

### 前置要求

- Docker & Docker Compose
- NVIDIA GPU (或华为昇腾 NPU)
- 16GB+ 内存

### 一键部署

```bash
# 克隆仓库
git clone https://github.com/your-org/tokenmachine.git
cd tokenmachine

# 启动服务
cd infra/docker && docker-compose up -d

# 等待服务就绪
docker-compose logs -f api
```

### 部署第一个模型

```bash
# 1. 下载模型 (通过 Web UI: http://localhost:8080)
# 或使用 API:

# 2. 创建 API Key
API_KEY=$(curl -X POST http://localhost:8000/api/v1/admin/api-keys \
  -H "Content-Type: application/json" \
  -d '{"name": "My Key", "user_id": 1}' | jq -r '.key')

# 3. 调用模型 (OpenAI 兼容)
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "qwen2.5-7b-instruct",
    "messages": [{"role": "user", "content": "Hello!"}]
  }'
```

---

## 项目结构

```
TokenMachine/
├── backend/              # Python 后端 (FastAPI)
│   ├── api/             # API 端点
│   ├── core/            # 核心模块 (config, database, gpu, security)
│   ├── models/          # 数据库模型
│   ├── services/        # 业务逻辑
│   ├── workers/         # 推理工作进程
│   └── monitoring/      # 监控指标
│
├── ui/                   # React 前端
│   └── src/
│       ├── components/   # UI 组件
│       ├── pages/        # 页面
│       └── store/        # 状态管理
│
├── infra/                # 基础设施
│   ├── docker/          # Docker 配置
│   ├── prometheus/      # Prometheus 配置
│   └── nginx/           # nginx 配置
│
├── migrations/           # 数据库迁移
├── scripts/              # 部署脚本
├── tests/                # 测试套件
└── docs/                 # 文档
```

---

## 系统架构

```
┌─────────────────────────────────────────────────────────────────┐
│                        客户端层                                  │
│  Web UI │ CLI │ SDK │ OpenAI API                                │
└────────────────────────────┬────────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────────┐
│                     统一 API 网关层                              │
│  • 格式转换 • 智能路由 • 认证鉴权 • 限流熔断                      │
└────────────────────────────┬────────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────────┐
│                      核心功能层                                  │
│  模型部署 │ GPU 调度 │ 计费系统 │ 模型微调                        │
└────────────────────────────┬────────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────────┐
│                     推理引擎层                                   │
│  vLLM │ SGLang │ Chitu │ kt-kernel                              │
└────────────────────────────┬────────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────────┐
│                      硬件资源层                                  │
│  NVIDIA GPU │ 昇腾 NPU │ 沐曦 GPU │ 海光 GPU │ CPU               │
└─────────────────────────────────────────────────────────────────┘
```

---

## 文档

| 文档 | 说明 |
|------|------|
| [开发路线图](TODO.md) | 按模块和优先级组织的任务清单 |
| [产品设计](docs/PRODUCT_DESIGN.md) | 完整的产品功能设计和商业模式 |
| [后端设计](docs/BACKEND_DESIGN.md) | 后端架构详细设计 |
| [前端设计](docs/FRONTEND_DESIGN.md) | 前端设计规范 |
| [部署指南](docs/DEPLOYMENT.md) | 生产环境部署说明 |
| [测试指南](docs/TESTING.md) | 测试基础设施和使用 |

---

## 技术栈

### 后端
- **Web 框架**: FastAPI 0.109+
- **数据库**: PostgreSQL 15 / Redis 7
- **ORM**: SQLAlchemy 2.0
- **监控**: Prometheus + Grafana

### 推理引擎
- **vLLM** - PagedAttention 高性能推理
- **SGLang** - 结构化生成优化
- **Chitu** - 国产芯片支持
- **kt-kernel** - CPU+GPU 异构计算

### 前端
- **框架**: React 19 + TypeScript
- **UI**: Ant Design 6
- **构建**: Vite
- **状态**: Zustand

### 部署
- Docker / Docker Compose
- Kubernetes (Helm Charts)

---

## 开发

### 后端开发

```bash
# 运行开发服务器
uvicorn backend.main:app --reload

# 运行测试
pytest

# 运行特定测试
pytest tests/unit/test_security.py

# 数据库迁移
alembic revision --autogenerate -m "message"
alembic upgrade head
```

### 前端开发

```bash
cd ui

# 安装依赖
npm install

# 开发服务器
npm run dev

# 构建
npm run build

# 测试
npm test
```

---

## 功能路线图

### P0 - 核心功能（当前开发中）
- [x] 数据库设计
- [x] API Key 认证
- [x] 基础测试框架
- [ ] GPU 资源管理
- [ ] 模型部署（vLLM）
- [ ] OpenAI 兼容 API
- [ ] 基础监控

### P1 - 增强功能
- [ ] Admin API
- [ ] Web UI
- [ ] 完整测试覆盖
- [ ] 部署自动化

### P2 - 企业功能
- [ ] 计费系统
- [ ] 多租户支持
- [ ] SGLang 后端
- [ ] 模型版本管理增强
- [ ] SSO 登录

### P3 - 高级功能
- [ ] 国产芯片支持
- [ ] CPU+GPU 异构推理
- [ ] 模型微调
- [ ] 高级 RBAC
- [ ] 审计日志

**详细任务列表请查看 [TODO.md](TODO.md)**

---

## 贡献

欢迎贡献代码、报告问题或提出新功能建议！

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/amazing-feature`)
3. 提交更改 (`git commit -m 'Add amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 提交 Pull Request

---

## 许可证

本项目采用 Apache License 2.0 许可证 - 详见 [LICENSE](LICENSE) 文件。

---

## 致谢

本项目从以下优秀开源项目中汲取灵感：

- [GPUStack](https://github.com/gpustack/gpustack) - GPU 集群管理
- [New API](https://github.com/QuantumNous/new-api) - 计费与格式转换
- [Chitu](https://github.com/thu-pacman/chitu) - 国产芯片支持
- [KTransformers](https://github.com/kvcache-ai/ktransformers) - 异构计算优化

---

**Links**: [文档](docs/) | [任务列表](TODO.md) | [演示](https://demo.tokenmachine.com) | [社区](https://github.com/your-org/tokenmachine/discussions)
