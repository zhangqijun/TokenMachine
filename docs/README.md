# TokenMachine 设计文档

## 文档目录

### 01. 设计 (01-design/)
产品定位、功能规划和路线图

| 文档 | 描述 |
|------|------|
| **[PRODUCT_DESIGN.md](./01-design/PRODUCT_DESIGN.md)** | 产品定位、核心功能、功能优先级 |

---

### 02. 技术架构 (02-architecture/)
系统架构、模块设计和技术选型

#### 后端架构 (backend/)

| 文档 | 描述 |
|------|------|
| **[BACKEND_DESIGN.md](./02-architecture/backend/BACKEND_DESIGN.md)** | 后端架构设计、数据库设计、API 接口、核心功能模块 |
| **[SERVER_WORKER_ARCHITECTURE.md](./02-architecture/backend/SERVER_WORKER_ARCHITECTURE.md)** | Server-Worker 分离架构设计 |
| **[SCHEDULING_FRAMEWORK.md](./02-architecture/backend/SCHEDULING_FRAMEWORK.md)** | 调度策略框架设计（过滤器、选择器、评分器） |
| **[INFERENCE_BACKEND_PLUGIN.md](./02-architecture/backend/INFERENCE_BACKEND_PLUGIN.md)** | 推理后端插件系统（vLLM、SGLang、Chitu 等） |
| **[MODEL_INSTANCE_MANAGEMENT.md](./02-architecture/backend/MODEL_INSTANCE_MANAGEMENT.md)** | 模型实例管理（多副本、灰度发布、A/B 测试） |
| **[MULTI_CLUSTER_MANAGEMENT.md](./02-architecture/backend/MULTI_CLUSTER_MANAGEMENT.md)** | 多集群管理（跨地域、跨环境） |
| **[INFERENCE_FRAMEWORKS_COMPARISON.md](./02-architecture/backend/INFERENCE_FRAMEWORKS_COMPARISON.md)** | 推理框架对比（vLLM、SGLang、TensorRT-LLM、Chitu、KTransformers） |

#### 前端架构 (frontend/)

| 文档 | 描述 |
|------|------|
| **[FRONTEND_DESIGN.md](./02-architecture/frontend/FRONTEND_DESIGN.md)** | 前端技术栈、页面结构、组件设计、状态管理、API 设计 |

---

### 03. 开发环境与部署 (03-development/)
开发环境搭建、部署配置和运维

| 文档 | 描述 |
|------|------|
| **[DEVELOPMENT_SETUP.md](./03-development/DEVELOPMENT_SETUP.md)** | 开发环境搭建指南 |
| **[DEPLOYMENT.md](./03-development/DEPLOYMENT.md)** | 生产部署指南（Docker、Kubernetes） |

---

### 04. 测试与发布 (04-testing/)
测试策略、测试用例和发布流程

| 文档 | 描述 |
|------|------|
| **[TESTING.md](./04-testing/TESTING.md)** | 测试策略和指南 |
| **[TEST_CASES.md](./04-testing/TEST_CASES.md)** | 测试用例集 |

---

## 技术栈总览

### 前端
| 类别 | 技术 | 版本 |
|------|------|------|
| 框架 | React | 19.2.0 |
| 语言 | TypeScript | 5.9.3 |
| 构建工具 | Vite | 7.2.4 |
| UI 组件库 | Ant Design | 6.2.0 |
| 状态管理 | Zustand | 5.0.10 |
| 路由 | React Router | 7.12.0 |
| 图表 | ECharts | 6.0.0 |

### 后端
| 类别 | 技术 | 版本 |
|------|------|------|
| Web 框架 | FastAPI | 0.109.0 |
| ASGI 服务器 | Uvicorn | 0.27.0 |
| ORM | SQLAlchemy | 2.0.25 |
| 数据库 | PostgreSQL | 15 |
| 缓存 | Redis | 7 |
| 推理引擎 | vLLM | 0.3.0 |

---

## 快速导航

| 我想了解... | 查看文档 |
|-------------|----------|
| 产品功能和规划 | [PRODUCT_DESIGN.md](./01-design/PRODUCT_DESIGN.md) |
| 后端架构设计 | [BACKEND_DESIGN.md](./02-architecture/backend/BACKEND_DESIGN.md) |
| 前端架构设计 | [FRONTEND_DESIGN.md](./02-architecture/frontend/FRONTEND_DESIGN.md) |
| Server-Worker 架构 | [SERVER_WORKER_ARCHITECTURE.md](./02-architecture/backend/SERVER_WORKER_ARCHITECTURE.md) |
| 调度策略框架 | [SCHEDULING_FRAMEWORK.md](./02-architecture/backend/SCHEDULING_FRAMEWORK.md) |
| 推理后端插件 | [INFERENCE_BACKEND_PLUGIN.md](./02-architecture/backend/INFERENCE_BACKEND_PLUGIN.md) |
| 推理框架对比 | [INFERENCE_FRAMEWORKS_COMPARISON.md](./02-architecture/backend/INFERENCE_FRAMEWORKS_COMPARISON.md) |
| 开发环境搭建 | [DEVELOPMENT_SETUP.md](./03-development/DEVELOPMENT_SETUP.md) |
| 部署指南 | [DEPLOYMENT.md](./03-development/DEPLOYMENT.md) |
| 测试指南 | [TESTING.md](./04-testing/TESTING.md) |

---

## 设计原则

1. **用户体验优先**: 简洁直观的界面，减少操作步骤
2. **实时响应**: 资源状态和监控数据实时更新
3. **OpenAI 兼容**: 无缝替换 OpenAI API，支持零代码迁移
4. **可扩展性**: 模块化设计，便于功能扩展
5. **类型安全**: 全面使用 TypeScript/Python 类型注解

---

**文档版本**: v2.0
**最后更新**: 2025-01-16
