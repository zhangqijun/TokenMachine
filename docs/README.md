# TokenMachine 设计文档

## 文档目录

### 1. 产品设计
**[PRODUCT_DESIGN.md](./PRODUCT_DESIGN.md)**
- 产品定位与目标用户
- 核心功能与商业模式
- 竞品分析与差异化
- 产品路线图

### 2. 前端设计
**[FRONTEND_DESIGN.md](./FRONTEND_DESIGN.md)**
- 技术栈选型 (React 19 + TypeScript 5.9 + Vite 7 + Ant Design 6)
- 功能模块设计
- 页面结构与路由设计
- 组件设计规范
- 状态管理 (Zustand)
- API 设计
- 数据流与实时更新

### 3. 后端设计
**[BACKEND_DESIGN.md](./BACKEND_DESIGN.md)**
- 系统架构设计
- 数据库设计
- API 接口设计 (OpenAI 兼容 API + 管理 API)
- 核心功能模块 (GPU 管理、模型管理、部署管理)
- 监控与可观测性
- 部署架构 (Docker Compose)
- 技术选型
- 开发计划

### 4. 推理框架对比
**[INFERENCE_FRAMEWORKS_COMPARISON.md](./INFERENCE_FRAMEWORKS_COMPARISON.md)**
- vLLM 技术分析
- SGLang 技术分析
- 框架对比与选型建议

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
| 产品功能和商业模式 | [PRODUCT_DESIGN.md](./PRODUCT_DESIGN.md) |
| 前端页面和组件设计 | [FRONTEND_DESIGN.md](./FRONTEND_DESIGN.md) |
| 后端 API 和数据库设计 | [BACKEND_DESIGN.md](./BACKEND_DESIGN.md) |
| 推理框架技术对比 | [INFERENCE_FRAMEWORKS_COMPARISON.md](./INFERENCE_FRAMEWORKS_COMPARISON.md) |

---

## 设计原则

1. **用户体验优先**: 简洁直观的界面，减少操作步骤
2. **实时响应**: 资源状态和监控数据实时更新
3. **OpenAI 兼容**: 无缝替换 OpenAI API，支持零代码迁移
4. **可扩展性**: 模块化设计，便于功能扩展
5. **类型安全**: 全面使用 TypeScript/Python 类型注解

---

**文档版本**: v1.0
**最后更新**: 2025-01-14
