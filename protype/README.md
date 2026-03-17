# TokenMachine Prototype

这是 TokenMachine 的**原型演示项目**，展示模型部署和管理界面。

## 🌐 在线演示

访问地址: **https://zhangqijun.github.io/TokenMachine/**

## ✨ 功能特性

- **模型列表展示**：支持DeepSeek、Qwen、GLM、Kimi、MiniMax等系列模型
- **智能部署配置**：可视化参数调整，实时计算显存占用和性能
- **部署可行性分析**：自动评估显存是否足够，推荐最优配置
- **参数说明**：每个参数都有详细提示，平衡易用性和可调整性

## 🚀 本地开发

```bash
# 安装依赖
npm install

# 启动开发服务器
npm run dev

# 访问 http://localhost:1583/models 查看模型列表
```

## 📦 部署配置参数

### 推理引擎选择
- **vLLM** - 高吞吐量优化
- **SGLang** - 结构化生成
- **llama.cpp** - 轻量级推理

### 量化方式
- **INT4** - 4bit量化，最省显存
- **INT8** - 8bit量化，平衡精度
- **FP16** - 半精度浮点，精度最高

### 关键参数
- **GPU显存利用率** (0.5-0.95)：分配给模型的显存比例
- **最大上下文长度** (4K-65K)：支持的token数量
- **张量并行度** (1-8)：多GPU并行数量
- **批处理大小** (1-256)：并发请求数

## 🎯 与主项目的区别

| 特性 | protype (原型) | ui (生产) |
|------|---------------|----------|
| 数据来源 | 静态JSON数据 | 后端API |
| 运行方式 | GitHub Pages静态部署 | 需要完整后端服务 |
| 用途 | 演示、设计确认 | 生产环境 |

## 🛠️ 技术栈

- React 19.2
- TypeScript
- Vite
- Ant Design 6.2
- Zustand

## 📁 项目结构

```
protype/
├── public/data/           # 模型数据JSON
│   ├── model_card.json    # 90个模型信息
│   └── model_logos.json   # 模型Logo映射
├── src/
│   ├── components/        # UI组件
│   └── pages/
│       └── Models.tsx     # 模型列表页面（核心）
└── vite.config.ts        # Vite配置
```
