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
docker-compose up -d

# 等待服务就绪
docker-compose logs -f api
```

### 部署第一个模型

```bash
# 1. 下载模型 (通过 Web UI: http://localhost:3000)
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
| [产品设计](docs/PRODUCT_DESIGN.md) | 完整的产品功能设计和商业模式 |
| [MVP 设计](docs/PHASE1_MVP_DESIGN.md) | Phase 1 详细技术设计文档 |
| [框架对比](docs/INFERENCE_FRAMEWORKS_COMPARISON.md) | 推理引擎技术对比分析 |

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

### 部署
- Docker / Docker Compose
- Kubernetes (Helm Charts)

---

## 功能路线图

### Phase 1: MVP (当前)
- [x] GPU 资源管理
- [x] vLLM 模型部署
- [x] OpenAI 兼容 API
- [x] 基础监控
- [x] API Key 认证

### Phase 2: 增强版
- [ ] 计费系统
- [ ] 多租户支持
- [ ] SGLang 后端
- [ ] 模型版本管理
- [ ] SSO 登录

### Phase 3: 企业版
- [ ] 国产芯片支持
- [ ] CPU+GPU 异构推理
- [ ] 模型微调
- [ ] 高级 RBAC
- [ ] 审计日志

---

## 贡献

欢迎贡献代码、报告问题或提出新功能建议！

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/amazing-feature`)
3. 提交更改 (`git commit -m 'Add amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 提交 Pull Request

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

**Links**: [文档](docs/) | [演示](https://demo.tokenmachine.com) | [社区](https://github.com/your-org/tokenmachine/discussions)
