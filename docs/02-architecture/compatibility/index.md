# 兼容性组件文档索引

## 文档列表

### 1. [README.md](./README.md) - 设计文档
兼容性组件的完整设计文档，包含功能说明、数据来源、数据结构、展示方式和后端对接方式。

**主要内容**:
- 功能说明: 组件概述、核心功能、使用场景
- 数据来源: vLLM usage_stats、SGLang CI/CD、用户上传
- 数据结构设计: 数据库表结构、TypeScript 接口
- 添加新数据: 自动收集、手动上传、批量导入
- 展示方式: 兼容性矩阵页面、检查对话框、可视化图表
- 后端对接方式: API 端点、部署集成、前端集成
- 技术实现: 数据库优化、缓存策略、异步任务
- 安全与隐私: 数据匿名化、风险等级、GDPR 合规

**适合人群**: 架构师、技术负责人、开发者

---

### 2. [API_SPECIFICATION.md](./API_SPECIFICATION.md) - API 规范
兼容性组件的完整 API 规范文档。

**主要内容**:
- 端点列表: 所有 API 端点的详细说明
- 请求/响应格式: JSON Schema 定义
- 错误处理: 错误代码和错误信息
- 速率限制: API 调用频率限制
- 数据模型: TypeScript 接口定义
- 使用示例: Python、JavaScript、cURL 示例

**适合人群**: 前后端开发者、API 集成者

---

### 3. [IMPLEMENTATION_GUIDE.md](./IMPLEMENTATION_GUIDE.md) - 实施指南
兼容性组件的分阶段实施计划和开发指南。

**主要内容**:
- 实施阶段:
  - 阶段 1: 基础设施 (Week 1-2)
  - 阶段 2: 数据收集 (Week 3-4)
  - 阶段 3: 前端集成 (Week 5-6)
  - 阶段 4: 测试与优化 (Week 7-8)
- 部署清单: 前置条件、部署步骤
- 验收标准: 功能、性能、安全、文档
- 监控指标: 关键指标、监控设置

**适合人群**: 项目经理、开发者、测试工程师

---

## 快速导航

### 我想了解...

**兼容性组件的功能**
→ 阅读 [README.md - 1. 功能说明](./README.md#1-功能说明)

**数据从哪里来**
→ 阅读 [README.md - 2. 数据来源](./README.md#2-数据来源)

**如何调用 API**
→ 阅读 [API_SPECIFICATION.md](./API_SPECIFICATION.md)

**如何实施开发**
→ 阅读 [IMPLEMENTATION_GUIDE.md](./IMPLEMENTATION_GUIDE.md)

**数据库表结构**
→ 阅读 [README.md - 3. 数据结构设计](./README.md#3-数据结构设计)

**前端如何集成**
→ 阅读 [README.md - 6. 后端对接方式 - 6.2.2](./README.md#622-前端集成)

### 我正在...

**设计架构**
→ 阅读 [README.md](./README.md)

**开发后端**
→ 阅读 [API_SPECIFICATION.md](./API_SPECIFICATION.md) 和 [IMPLEMENTATION_GUIDE.md - 阶段 1-2](./IMPLEMENTATION_GUIDE.md#阶段-1-基础设施-week-1-2)

**开发前端**
→ 阅读 [README.md - 5. 展示方式](./README.md#5-展示方式) 和 [IMPLEMENTATION_GUIDE.md - 阶段 3](./IMPLEMENTATION_GUIDE.md#阶段-3-前端集成-week-5-6)

**测试**
→ 阅读 [IMPLEMENTATION_GUIDE.md - 阶段 4](./IMPLEMENTATION_GUIDe.md#阶段-4-测试与优化-week-7-8)

**部署**
→ 阅读 [IMPLEMENTATION_GUIDE.md - 部署清单](./IMPLEMENTATION_GUIDE.md#部署清单)

---

## 相关文档

- [产品需求文档](../../PRODUCT_DESIGN.md)
- [后端架构设计](../BACKEND_DESIGN.md)
- [前端架构设计](../FRONTEND_DESIGN.md)
- [测试指南](../../TESTING.md)
- [部署指南](../../DEPLOYMENT.md)

---

## 版本历史

| 版本 | 日期 | 变更说明 |
|------|------|----------|
| v1.0 | 2025-01-21 | 初始版本 |

---

## 贡献指南

如果您对兼容性组件有任何改进建议，请：

1. 提交 Issue 描述问题或建议
2. Fork 仓库并创建分支
3. 提交 Pull Request
4. 等待审核和反馈

---

## 联系方式

- 项目仓库: [TokenMachine GitHub](https://github.com/your-org/TokenMachine)
- 问题反馈: [GitHub Issues](https://github.com/your-org/TokenMachine/issues)
- 邮件: support@tokenmachine.example

---

**文档维护**: TokenMachine Team
**最后更新**: 2025-01-21
