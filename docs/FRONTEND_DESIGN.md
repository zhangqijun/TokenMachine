# TokenMachine Web UI 设计文档

## 目录
- [1. 概述](#1-概述)
- [2. 技术栈](#2-技术栈)
- [3. 功能模块设计](#3-功能模块设计)
- [4. 页面结构](#4-页面结构)
- [5. 组件设计](#5-组件设计)
- [6. 状态管理](#6-状态管理)
- [7. API 设计](#7-api-设计)
- [8. 路由设计](#8-路由设计)
- [9. 数据流设计](#9-数据流设计)

---

## 1. 概述

### 1.1 项目简介

TokenMachine Web UI 是 TokenMachine 平台的前端管理界面，用于管理 GPU 集群资源、部署和管理大语言模型。

### 1.2 设计原则

- **用户体验优先**: 简洁直观的界面，减少操作步骤
- **实时响应**: 资源状态和监控数据实时更新
- **可扩展性**: 模块化设计，便于功能扩展
- **类型安全**: 全面使用 TypeScript，保证代码质量

### 1.3 功能范围

| 模块 | 功能 | 说明 |
|------|------|------|
| **仪表盘** | 系统概览 | 资源使用统计、模型运行状态 |
| **模型管理** | 模型部署 | 本地模型管理、部署配置（去除市场对接）|
| **测试场** | 文本生成 | 仅保留文本生成模型测试 |
| **资源管理** | Worker/GPU | GPU 监控、Worker 管理（参考 GPUStack）|
| **集群管理** | 集群配置 | 集群创建、节点管理（参考 GPUStack）|
| **API 密钥** | 密钥管理 | 创建、撤销 API Key |
| **系统设置** | 系统配置 | 用户、权限等设置 |

---

## 2. 技术栈

### 2.1 核心框架

```typescript
{
  "react": "^19.2.0",           // UI 框架
  "react-dom": "^19.2.0",       // DOM 渲染
  "react-router-dom": "^7.12.0", // 路由管理
  "typescript": "~5.9.3",        // 类型系统
  "vite": "^7.2.4"              // 构建工具
}
```

### 2.2 UI 组件库

```typescript
{
  "antd": "^6.2.0",              // 基础组件库
  "@ant-design/icons": "^6.1.0"  // 图标库
}
```

### 2.3 状态管理

```typescript
{
  "zustand": "^5.0.10"  // 轻量级状态管理
}
```

### 2.4 数据可视化

```typescript
{
  "echarts": "^6.0.0",           // 图表库
  "echarts-for-react": "^3.0.5"  // React 集成
}
```

### 2.5 工具库

```typescript
{
  "dayjs": "^1.11.19"  // 日期处理
}
```

---

## 3. 功能模块设计

### 3.1 仪表盘 (Dashboard)

#### 功能描述
展示系统整体状态和关键指标，提供快捷操作入口。

#### 页面布局
```
┌─────────────────────────────────────────────────────────────┐
│                        顶部导航栏                            │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│  │  GPU 总数   │  │  运行模型   │  │  API 调用   │        │
│  │     8       │  │     3       │  │   12.5K     │        │
│  └─────────────┘  └─────────────┘  └─────────────┘        │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────┐  ┌───────────────┐ │
│  │                                     │  │               │ │
│  │          GPU 利用率趋势图            │  │   模型运行    │ │
│  │         (ECharts 折线图)             │  │   状态列表    │ │
│  │                                     │  │               │ │
│  └─────────────────────────────────────┘  └───────────────┘ │
├─────────────────────────────────────────────────────────────┤
│  ┌──────────────────────────────────────────────────────┐  │
│  │                    最近活动日志                        │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

#### 数据指标
- **资源统计**: GPU 总数、可用/使用中、内存使用率
- **模型统计**: 运行中模型数、总模型数
- **API 统计**: 今日调用量、响应时间
- **活动日志**: 最近操作记录

#### 组件设计
```typescript
// src/pages/dashboard/index.tsx
interface DashboardProps {}

interface DashboardStats {
  gpuCount: {
    total: number;
    available: number;
    inUse: number;
  };
  modelCount: {
    running: number;
    total: number;
  };
  apiCalls: {
    today: number;
    avgLatency: number;
  };
}

// 组件：StatCard - 统计卡片
// 组件：GpuUsageChart - GPU 利用率趋势图
// 组件：ModelStatusList - 模型状态列表
// 组件：ActivityLog - 活动日志
```

---

### 3.2 模型管理 (Models)

#### 功能描述
本地模型管理，支持模型上传、部署配置、状态监控。

#### 功能变更
- ❌ **移除**: HuggingFace / ModelScope 市场对接
- ✅ **保留**: 本地模型管理
- ✅ **保留**: 模型部署配置
- ✅ **保留**: 模型状态监控

#### 页面布局
```
┌─────────────────────────────────────────────────────────────┐
│  [模型列表]                              [+ 上传模型]        │
├─────────────────────────────────────────────────────────────┤
│  ┌───────────────────────────────────────────────────────┐ │
│  │  名称           │ 状态     │ 大小    │ 操作           │ │
│  ├───────────────────────────────────────────────────────┤ │
│  │  llama-3-8b     │ 运行中   │ 16 GB   │ 停止 配置 删除 │ │
│  │  qwen2-7b       │ 已停止   │ 14 GB   │ 启动 配置 删除 │ │
│  │  baichuan-13b   │ 加载中   │ 26 GB   │ 配置 删除     │ │
│  └───────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

#### 数据结构
```typescript
interface Model {
  id: string;
  name: string;
  version: string;
  path: string;
  size_gb: number;
  status: 'running' | 'stopped' | 'loading' | 'error';
  backend: 'vllm' | 'sglang';
  created_at: string;
  updated_at: string;
}

interface ModelDeployConfig {
  replicas: number;
  gpu_ids: string[];
  tensor_parallel_size: number;
  max_model_len: number;
  gpu_memory_utilization: number;
}
```

#### 组件设计
```typescript
// src/pages/models/index.tsx
// src/pages/models/components/model-table.tsx
// src/pages/models/components/upload-modal.tsx
// src/pages/models/components/deploy-config-modal.tsx
```

---

### 3.3 测试场 (Playground)

#### 功能描述
仅保留文本生成模型的对话测试功能。

#### 功能变更
- ✅ **保留**: 文本生成对话测试
- ❌ **移除**: Embedding 测试
- ❌ **移除**: Rerank 测试
- ❌ **移除**: 图像生成
- ❌ **移除**: 语音合成
- ❌ **移除**: 视频生成

#### 页面布局
```
┌─────────────────────────────────────────────────────────────┐
│  模型: [llama-3-8b ▼]  参数: [查看配置]                     │
├─────────────────────────────────────┬───────────────────────┤
│                                     │                       │
│  ┌───────────────────────────────┐ │  ┌─────────────────┐ │
│  │                               │ │  │                 │ │
│  │       对话历史区域            │ │  │   当前对话      │ │
│  │                               │ │  │                 │ │
│  │  User: 你好                   │ │  │  Assistant:     │ │
│  │  AI: 你好！有什么可以帮助？   │ │  │  你好！有什么... │ │
│  │                               │ │  │                 │ │
│  └───────────────────────────────┘ │  └─────────────────┘ │
│                                     │                       │
│  ┌───────────────────────────────┐ │  ┌─────────────────┐ │
│  │ [输入消息...]            [发送]│ │  │  停止生成       │ │
│  └───────────────────────────────┘ │  └─────────────────┘ │
└─────────────────────────────────────┴───────────────────────┘
```

#### 数据结构
```typescript
interface ChatMessage {
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: string;
}

interface ChatSession {
  id: string;
  model_id: string;
  messages: ChatMessage[];
  created_at: string;
}

interface GenerationConfig {
  temperature: number;
  top_p: number;
  max_tokens: number;
  stream: boolean;
}
```

#### 组件设计
```typescript
// src/pages/playground/index.tsx
// src/pages/playground/components/chat-box.tsx
// src/pages/playground/components/message-list.tsx
// src/pages/playground/components/config-panel.tsx
```

---

### 3.4 资源管理 (Resources)

#### 功能描述
GPU 和 Worker 资源的实时监控和管理，**参考 GPUStack UI 设计**。

#### 页面布局
```
┌─────────────────────────────────────────────────────────────┐
│  [Workers]  [GPUs]  [模型文件]                               │
├─────────────────────────────────────────────────────────────┤
│  集群: [全部 ▼]  状态: [全部 ▼]  搜索: [..._______________] │
├─────────────────────────────────────────────────────────────┤
│  ┌───────────────────────────────────────────────────────┐ │
│  │ 名称   │ 状态 │ IP地址  │ CPU │ 内存 │ GPU │ 操作    │ │
│  ├───────────────────────────────────────────────────────┤ │
│  │ worker-1│ 运行 │192.168.1.10│ 45%│ 67% │GPU0│ 详情... │ │
│  │         │      │            │    │     │    │         │ │
│  │ worker-2│ 运行 │192.168.1.11│ 23%│ 45% │GPU1│ 详情... │ │
│  └───────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

#### 数据结构
```typescript
interface Worker {
  name: string;
  state: 'running' | 'offline' | 'maintenance';
  ip: string;
  cluster_id: string;
  labels: Record<string, string>;
  status: {
    cpu: {
      total: number;
      allocated: number;
      utilization_rate: number;
    };
    memory: {
      total: number;
      used: number;
      allocated: number;
      utilization_rate: number;
    };
    gpu_devices: GPUDevice[];
    filesystem: FileSystem[];
  };
  last_heartbeat: string;
}

interface GPUDevice {
  uuid: string;
  name: string;
  vendor: 'nvidia' | 'amd' | 'apple';
  index: number;
  core: {
    total: number;
    utilization_rate: number;
  };
  memory: {
    total: number;
    used: number;
    allocated: number;
    utilization_rate: number;
    is_unified_memory: boolean;
  };
  temperature: number;
  state: 'available' | 'in_use' | 'error';
}

interface FileSystem {
    path: string;
    total: number;
    used: number;
    available: number;
}
```

#### 组件设计
```typescript
// src/pages/resources/index.tsx - 资源管理入口
// src/pages/resources/components/workers-tab.tsx - Worker 列表
// src/pages/resources/components/gpus-tab.tsx - GPU 列表
// src/pages/resources/components/worker-detail-drawer.tsx - Worker 详情
// src/pages/resources/components/progress-bar.tsx - 进度条组件
// src/pages/resources/components/status-tag.tsx - 状态标签

// Hooks
// src/pages/resources/hooks/use-worker-columns.tsx - Worker 表格列
// src/pages/resources/hooks/use-gpu-columns.tsx - GPU 表格列
// src/pages/resources/hooks/use-table-fetch.tsx - 通用表格数据获取
```

#### 实时更新
- **GPU 数据**: 轮询更新，间隔 5 秒
- **Worker 数据**: 事件驱动更新 (CREATE, UPDATE, DELETE)
- **进度条**: 实时显示利用率，颜色分级 (绿/黄/红)

---

### 3.5 集群管理 (Cluster Management)

#### 功能描述
集群的创建、配置和管理，**参考 GPUStack UI 设计**。

#### 页面布局
```
┌─────────────────────────────────────────────────────────────┐
│                              [+ 新建集群]                     │
├─────────────────────────────────────────────────────────────┤
│  ┌───────────────────────────────────────────────────────┐ │
│  │ 名称        │ 类型     │ 节点数 │ 状态    │ 操作      │ │
│  ├───────────────────────────────────────────────────────┤ │
│  │ default     │ Docker   │ 2     │ 运行中  │ 详情 删除  │ │
│  │   ├ worker-1│          │       │         │           │ │
│  │   └ worker-2│          │       │         │           │ │
│  ├───────────────────────────────────────────────────────┤ │
│  │ production  │ K8s      │ 4     │ 运行中  │ 详情 删除  │ │
│  │   ├ pool-1  │          │       │         │           │ │
│  │   └ pool-2  │          │       │         │           │ │
│  └───────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

#### 数据结构
```typescript
interface Cluster {
  id: string;
  name: string;
  type: 'docker' | 'kubernetes' | 'digitalocean' | 'aws';
  is_default: boolean;
  status: 'running' | 'stopped' | 'error';
  worker_pools: WorkerPool[];
  created_at: string;
  updated_at: string;
}

interface WorkerPool {
  id: string;
  cluster_id: string;
  name: string;
  worker_count: number;
  min_workers: number;
  max_workers: number;
  status: 'running' | 'scaling' | 'stopped';
  config: WorkerPoolConfig;
}

interface WorkerPoolConfig {
  provider_specific: {
    // Docker 特定配置
    docker?: {
      image: string;
      volumes: string[];
    };
    // K8s 特定配置
    kubernetes?: {
      namespace: string;
      replicas: number;
    };
    // DigitalOcean 特定配置
    digitalocean?: {
      region: string;
      size: string;
      image: string;
    };
  };
}
```

#### 组件设计
```typescript
// src/pages/cluster-management/index.tsx - 集群管理入口
// src/pages/cluster-management/components/cluster-table.tsx - 集群列表
// src/pages/cluster-management/components/cluster-create-modal.tsx - 创建集群
// src/pages/cluster-management/components/cluster-detail-drawer.tsx - 集群详情
// src/pages/cluster-management/components/worker-pool-expand.tsx - 节点池展开行

// 不同提供商的配置组件
// src/pages/cluster-management/components/providers/docker-config.tsx
// src/pages/cluster-management/components/providers/kubernetes-config.tsx
```

#### 新建集群流程
```
┌─────────────────────────────────────────────────────────────┐
│  步骤 1/3: 选择提供商                                        │
├─────────────────────────────────────────────────────────────┤
│  ┌───────┐  ┌───────┐  ┌───────┐  ┌───────┐               │
│  │ Docker│  │  K8s  │  │   DO  │  │  AWS  │               │
│  └───────┘  └───────┘  └───────┘  └───────┘               │
├─────────────────────────────────────────────────────────────┤
│  [上一步]                                    [下一步]       │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│  步骤 2/3: 配置集群                                          │
├─────────────────────────────────────────────────────────────┤
│  集群名称: [________________]                                │
│  凭据:     [选择凭据 ▼]                          [+ 新建]   │
│  [根据提供商显示不同配置项]                                   │
├─────────────────────────────────────────────────────────────┤
│  [上一步]                                    [下一步]       │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│  步骤 3/3: 确认                                              │
├─────────────────────────────────────────────────────────────┤
│  集群名称: my-cluster                                        │
│  类型: Docker                                                │
│  配置: {...摘要...}                                          │
├─────────────────────────────────────────────────────────────┤
│  [上一步]                                    [创建]         │
└─────────────────────────────────────────────────────────────┘
```

---

### 3.6 API 密钥管理 (API Keys)

#### 功能描述
API 密钥的创建、管理和权限控制。

#### 页面布局
```
┌─────────────────────────────────────────────────────────────┐
│                              [+ 创建 API Key]                │
├─────────────────────────────────────────────────────────────┤
│  ┌───────────────────────────────────────────────────────┐ │
│  │ 名称         │ Key 前缀   │ 配额    │ 已用    │ 操作 │ │
│  ├───────────────────────────────────────────────────────┤ │
│  │ Production   │ tm_sk_a1.. │ 10M     │ 1.2M    │ 删除 │ │
│  │ Development  │ tm_sk_b2.. │ 1M      │ 50K     │ 删除 │ │
│  └───────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

#### 数据结构
```typescript
interface APIKey {
  id: string;
  name: string;
  key_prefix: string;  // 仅显示前缀，完整 Key 只在创建时显示
  user_id: string;
  quota_tokens: number;
  tokens_used: number;
  is_active: boolean;
  expires_at: string | null;
  last_used_at: string | null;
  created_at: string;
}

interface CreateAPIKeyRequest {
  name: string;
  user_id: string;
  quota_tokens: number;
  expires_at: string | null;
}
```

---

### 3.7 系统设置 (Settings)

#### 功能描述
用户管理、权限配置、系统设置。

#### 页面布局
```
┌─────────────────────────────────────────────────────────────┐
│  [用户管理]  [权限配置]  [系统设置]                          │
├─────────────────────────────────────────────────────────────┤
│  用户列表                                                   │
│  ┌───────────────────────────────────────────────────────┐ │
│  │ 用户名     │ 邮箱           │ 角色     │ 操作         │ │
│  ├───────────────────────────────────────────────────────┤ │
│  │ admin      │ admin@local    │ 管理员   │ 编辑 删除    │ │
│  │ user1      │ user1@local    │ 普通用户 │ 编辑 删除    │ │
│  └───────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

---

## 4. 页面结构

### 4.1 目录结构

```
web/src/
├── main.tsx                 # 应用入口
├── App.tsx                  # 根组件
├── index.css                # 全局样式
├── assets/                  # 静态资源
│   └── react.svg
├── components/              # 公共组件
│   ├── layout/              # 布局组件
│   │   ├── AppHeader.tsx    # 顶部导航
│   │   ├── AppSidebar.tsx   # 侧边栏
│   │   └── AppLayout.tsx    # 主布局
│   ├── progress-bar/        # 进度条组件
│   ├── status-tag/          # 状态标签
│   └── common/              # 其他公共组件
├── pages/                   # 页面组件
│   ├── dashboard/           # 仪表盘
│   │   ├── index.tsx
│   │   └── components/
│   ├── models/              # 模型管理
│   │   ├── index.tsx
│   │   ├── apis/
│   │   ├── components/
│   │   └── hooks/
│   ├── playground/          # 测试场
│   │   ├── index.tsx
│   │   └── components/
│   ├── resources/           # 资源管理
│   │   ├── index.tsx
│   │   ├── apis/
│   │   ├── components/
│   │   ├── hooks/
│   │   └── config/
│   ├── cluster-management/  # 集群管理
│   │   ├── index.tsx
│   │   ├── apis/
│   │   ├── components/
│   │   └── hooks/
│   ├── api-keys/            # API 密钥
│   │   └── index.tsx
│   └── settings/            # 系统设置
│       └── index.tsx
├── store/                   # 状态管理
│   ├── index.ts
│   ├── userStore.ts
│   ├── clusterStore.ts
│   └── resourceStore.ts
├── services/                # API 服务
│   ├── api.ts               # API 基础配置
│   ├── models.ts
│   ├── resources.ts
│   ├── clusters.ts
│   └── auth.ts
├── types/                   # TypeScript 类型
│   ├── index.d.ts
│   ├── models.ts
│   ├── resources.ts
│   └── clusters.ts
└── utils/                   # 工具函数
    ├── request.ts           # HTTP 请求封装
    ├── format.ts            # 格式化函数
    └── constants.ts         # 常量定义
```

---

## 5. 组件设计

### 5.1 布局组件

#### AppLayout
```typescript
// src/components/layout/AppLayout.tsx
interface AppLayoutProps {
  children: React.ReactNode;
}

export const AppLayout: React.FC<AppLayoutProps> = ({ children }) => {
  return (
    <Layout style={{ minHeight: '100vh' }}>
      <AppHeader />
      <Layout>
        <AppSidebar />
        <Layout.Content style={{ padding: '24px' }}>
          {children}
        </Layout.Content>
      </Layout>
    </Layout>
  );
};
```

#### AppHeader
```typescript
// src/components/layout/AppHeader.tsx
interface MenuItem {
  key: string;
  label: string;
  icon?: React.ReactNode;
  path?: string;
}

export const AppHeader: React.FC = () => {
  const menuItems: MenuItem[] = [
    { key: 'dashboard', label: '仪表盘', path: '/' },
    { key: 'models', label: '模型管理', path: '/models' },
    { key: 'playground', label: '测试场', path: '/playground' },
    { key: 'resources', label: '资源', path: '/resources' },
    { key: 'clusters', label: '集群', path: '/clusters' },
  ];

  return (
    <Layout.Header>
      <div className="logo">TokenMachine</div>
      <Menu mode="horizontal" items={menuItems} />
      <div className="user-info">
        <Dropdown>
          <Avatar />
        </Dropdown>
      </div>
    </Layout.Header>
  );
};
```

### 5.2 通用组件

#### ProgressBar
```typescript
// src/components/progress-bar/index.tsx
interface ProgressBarProps {
  percent: number;
  status?: 'success' | 'exception' | 'normal' | 'active';
  size?: 'small' | 'default' | 'large';
  showInfo?: boolean;
  tooltip?: string;
  strokeColor?: string | string[];
}

export const ProgressBar: React.FC<ProgressBarProps> = ({
  percent,
  tooltip,
  ...props
}) => {
  const getColor = (p: number) => {
    if (p >= 80) return '#ff4d4f';  // 红色
    if (p >= 50) return '#faad14';  // 黄色
    return '#52c41a';               // 绿色
  };

  const content = (
    <Progress
      percent={percent}
      strokeColor={getColor(percent)}
      {...props}
    />
  );

  if (tooltip) {
    return <Tooltip title={tooltip}>{content}</Tooltip>;
  }

  return content;
};
```

#### StatusTag
```typescript
// src/components/status-tag/index.tsx
interface StatusTagProps {
  status: string;
  text?: string;
  progress?: number;
}

export const StatusTag: React.FC<StatusTagProps> = ({
  status,
  text,
  progress
}) => {
  const getStatusConfig = (s: string) => {
    const configs: Record<string, { color: string; icon: React.ReactNode }> = {
      running: { color: 'success', icon: <CheckCircleOutlined /> },
      stopped: { color: 'default', icon: <StopOutlined /> },
      loading: { color: 'processing', icon: <LoadingOutlined /> },
      error: { color: 'error', icon: <CloseCircleOutlined /> },
      available: { color: 'success', icon: null },
      in_use: { color: 'processing', icon: null },
    };
    return configs[s] || { color: 'default', icon: null };
  };

  const config = getStatusConfig(status);

  return (
    <Tag color={config.color} icon={config.icon}>
      {text || status}
      {progress !== undefined && ` (${progress}%)`}
    </Tag>
  );
};
```

### 5.3 资源管理组件 (参考 GPUStack)

#### WorkersTab
```typescript
// src/pages/resources/components/workers-tab.tsx
interface WorkersTabProps {}

export const WorkersTab: React.FC<WorkersTabProps> = () => {
  const { dataSource, loading, queryParams, setQueryParams } = useTableFetch<Worker>({
    fetchAPI: ResourcesAPI.queryWorkersList,
    polling: true,
  });

  const columns = useWorkerColumns();

  return (
    <div className="workers-tab">
      <Table
        columns={columns}
        dataSource={dataSource}
        loading={loading}
        rowKey="name"
        pagination={{
          ...queryParams.pagination,
          onChange: (page, pageSize) =>
            setQueryParams({ pagination: { current: page, pageSize } }),
        }}
      />
    </div>
  );
};
```

#### useWorkerColumns Hook
```typescript
// src/pages/resources/hooks/use-worker-columns.tsx
export const useWorkerColumns = () => {
  const columns: ColumnsType<Worker> = [
    {
      title: '名称',
      dataIndex: 'name',
      key: 'name',
      render: (name, record) => (
        <Space>
          {name}
          {record.labels && Object.keys(record.labels).length > 0 && (
            <Tag color="blue">L</Tag>
          )}
        </Space>
      ),
    },
    {
      title: '状态',
      dataIndex: 'state',
      key: 'state',
      render: (state) => <StatusTag status={state} />,
    },
    {
      title: 'IP 地址',
      dataIndex: 'ip',
      key: 'ip',
      render: (ip) => <Typography.Text code>{ip}</Typography.Text>,
    },
    {
      title: 'CPU',
      key: 'cpu',
      render: (_, record) => (
        <div>
          <ProgressBar
            percent={record.status.cpu.utilization_rate}
            size="small"
          />
          <Typography.Text type="secondary">
            {record.status.cpu.allocated} / {record.status.cpu.total} 核心
          </Typography.Text>
        </div>
      ),
    },
    {
      title: '内存',
      key: 'memory',
      render: (_, record) => (
        <div>
          <ProgressBar
            percent={record.status.memory.utilization_rate}
            size="small"
          />
          <Typography.Text type="secondary">
            {formatBytes(record.status.memory.used)} / {formatBytes(record.status.memory.total)}
          </Typography.Text>
        </div>
      ),
    },
    {
      title: 'GPU',
      key: 'gpu',
      render: (_, record) => (
        <Space direction="vertical" size="small">
          {record.status.gpu_devices.map((gpu) => (
            <div key={gpu.uuid}>
              <Typography.Text>
                GPU {gpu.index} ({gpu.vendor})
              </Typography.Text>
              <ProgressBar
                percent={gpu.core.utilization_rate}
                size="small"
                tooltip={`显存: ${formatBytes(gpu.memory.used)} / ${formatBytes(gpu.memory.total)}`}
              />
            </div>
          ))}
        </Space>
      ),
    },
    {
      title: '操作',
      key: 'actions',
      render: (_, record) => (
        <Space>
          <Button size="small" onClick={() => showWorkerDetail(record)}>
            详情
          </Button>
          <Dropdown
            menu={{
              items: [
                { key: 'maintenance', label: '维护模式' },
                { key: 'labels', label: '编辑标签' },
                { key: 'delete', label: '删除', danger: true },
              ],
            }}
          >
            <Button size="small" icon={<MoreOutlined />} />
          </Dropdown>
        </Space>
      ),
    },
  ];

  return columns;
};
```

---

## 6. 状态管理

### 6.1 Store 结构

```typescript
// src/store/index.ts
import { create } from 'zustand';
import { devtools, persist } from 'zustand/middleware';

// 用户状态
interface UserState {
  user: User | null;
  token: string | null;
  login: (user: User, token: string) => void;
  logout: () => void;
}

export const useUserStore = create<UserState>()(
  devtools(
    persist(
      (set) => ({
        user: null,
        token: null,
        login: (user, token) => set({ user, token }),
        logout: () => set({ user: null, token: null }),
      }),
      { name: 'user-storage' }
    )
  )
);

// 集群状态
interface ClusterState {
  clusters: Cluster[];
  currentCluster: Cluster | null;
  setCurrentCluster: (cluster: Cluster) => void;
}

export const useClusterStore = create<ClusterState>()(
  devtools((set) => ({
    clusters: [],
    currentCluster: null,
    setCurrentCluster: (cluster) => set({ currentCluster: cluster }),
  }))
);

// 资源状态
interface ResourceState {
  workers: Worker[];
  gpus: GPUDevice[];
  updateWorkers: (workers: Worker[]) => void;
  updateGPUs: (gpus: GPUDevice[]) => void;
}

export const useResourceStore = create<ResourceState>()(
  devtools((set) => ({
    workers: [],
    gpus: [],
    updateWorkers: (workers) => set({ workers }),
    updateGPUs: (gpus) => set({ gpus }),
  }))
);
```

---

## 7. API 设计

### 7.1 API 基础配置

```typescript
// src/services/api.ts
import axios, { AxiosInstance, AxiosRequestConfig } from 'axios';
import { useUserStore } from '@/store';

const BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api/v1';

class APIClient {
  private client: AxiosInstance;

  constructor() {
    this.client = axios.create({
      baseURL: BASE_URL,
      timeout: 30000,
      headers: {
        'Content-Type': 'application/json',
      },
    });

    // 请求拦截器
    this.client.interceptors.request.use((config) => {
      const token = useUserStore.getState().token;
      if (token) {
        config.headers.Authorization = `Bearer ${token}`;
      }
      return config;
    });

    // 响应拦截器
    this.client.interceptors.response.use(
      (response) => response.data,
      (error) => {
        if (error.response?.status === 401) {
          useUserStore.getState().logout();
          window.location.href = '/login';
        }
        return Promise.reject(error);
      }
    );
  }

  get<T = any>(url: string, config?: AxiosRequestConfig): Promise<T> {
    return this.client.get(url, config);
  }

  post<T = any>(url: string, data?: any, config?: AxiosRequestConfig): Promise<T> {
    return this.client.post(url, data, config);
  }

  put<T = any>(url: string, data?: any, config?: AxiosRequestConfig): Promise<T> {
    return this.client.put(url, data, config);
  }

  delete<T = any>(url: string, config?: AxiosRequestConfig): Promise<T> {
    return this.client.delete(url, config);
  }
}

export const api = new APIClient();
```

### 7.2 API 服务模块

```typescript
// src/services/models.ts
import { api } from './api';
import type { Model, ModelDeployConfig } from '@/types/models';

export const ModelsAPI = {
  // 获取模型列表
  list: (params?: { page?: number; page_size?: number }) =>
    api.get<{ models: Model[]; total: number }>('/admin/models', { params }),

  // 获取模型详情
  get: (id: string) =>
    api.get<Model>(`/admin/models/${id}`),

  // 上传模型
  upload: (data: { name: string; file: File }) => {
    const formData = new FormData();
    formData.append('name', data.name);
    formData.append('file', data.file);
    return api.post<{ id: string }>('/admin/models/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
  },

  // 部署模型
  deploy: (id: string, config: ModelDeployConfig) =>
    api.post<{ deployment_id: string }>(`/admin/models/${id}/deploy`, config),

  // 停止模型
  stop: (id: string) =>
    api.post(`/admin/models/${id}/stop`),

  // 删除模型
  delete: (id: string) =>
    api.delete(`/admin/models/${id}`),
};

// src/services/resources.ts
export const ResourcesAPI = {
  // 获取 Worker 列表
  queryWorkersList: (params?: { cluster_id?: string; state?: string }) =>
    api.get<{ workers: Worker[]; total: number }>('/admin/workers', { params }),

  // 获取 GPU 列表
  queryGpuDevicesList: (params?: { worker_id?: string }) =>
    api.get<{ gpu_devices: GPUDevice[]; total: number }>('/admin/gpus', { params }),

  // 获取 Worker 详情
  getWorker: (name: string) =>
    api.get<Worker>(`/admin/workers/${name}`),

  // 更新 Worker
  updateWorker: (name: string, data: Partial<Worker>) =>
    api.put(`/admin/workers/${name}`, data),

  // 删除 Worker
  deleteWorker: (name: string) =>
    api.delete(`/admin/workers/${name}`),
};

// src/services/clusters.ts
export const ClustersAPI = {
  // 获取集群列表
  list: () =>
    api.get<Cluster[]>('/admin/clusters'),

  // 创建集群
  create: (data: CreateClusterRequest) =>
    api.post<{ id: string }>('/admin/clusters', data),

  // 获取集群详情
  get: (id: string) =>
    api.get<Cluster>(`/admin/clusters/${id}`),

  // 删除集群
  delete: (id: string) =>
    api.delete(`/admin/clusters/${id}`),

  // 设置默认集群
  setDefault: (id: string) =>
    api.post(`/admin/clusters/${id}/set-default`),
};
```

---

## 8. 路由设计

### 8.1 路由配置

```typescript
// src/App.tsx
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AppLayout } from '@/components/layout/AppLayout';
import { Dashboard } from '@/pages/dashboard';
import { Models } from '@/pages/models';
import { Playground } from '@/pages/playground';
import { Resources } from '@/pages/resources';
import { ClusterManagement } from '@/pages/cluster-management';
import { APIKeys } from '@/pages/api-keys';
import { Settings } from '@/pages/settings';
import { Login } from '@/pages/login';

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/" element={<AppLayout />}>
          <Route index element={<Navigate to="/dashboard" replace />} />
          <Route path="dashboard" element={<Dashboard />} />
          <Route path="models" element={<Models />} />
          <Route path="playground" element={<Playground />} />
          <Route path="resources" element={<Resources />} />
          <Route path="clusters" element={<ClusterManagement />} />
          <Route path="api-keys" element={<APIKeys />} />
          <Route path="settings" element={<Settings />} />
        </Route>
        <Route path="*" element={<Navigate to="/dashboard" replace />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
```

### 8.2 路由权限控制

```typescript
// src/components/ProtectedRoute.tsx
import { Navigate } from 'react-router-dom';
import { useUserStore } from '@/store';

interface ProtectedRouteProps {
  children: React.ReactNode;
}

export const ProtectedRoute: React.FC<ProtectedRouteProps> = ({ children }) => {
  const token = useUserStore((state) => state.token);

  if (!token) {
    return <Navigate to="/login" replace />;
  }

  return <>{children}</>;
};
```

---

## 9. 数据流设计

### 9.1 数据获取流程

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   组件      │────>│   Hook      │────>│   API       │
│  Component  │     │ useTableFetch│    │  Service    │
└─────────────┘     └─────────────┘     └─────────────┘
       ^                   │                    │
       │                   v                    v
       └─────────────┬─────────────┬─────────────┘
                     │             │
                ┌────▼────┐   ┌───▼────┐
                │  Store  │   │  State │
                └─────────┘   └────────┘
```

### 9.2 实时更新流程

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   轮询      │     │  WebSocket  │     │   事件      │
│  Polling    │     │   (可选)    │     │  Events     │
└──────┬──────┘     └──────┬──────┘     └──────┬──────┘
       │                    │                    │
       └────────────────────┼────────────────────┘
                            │
                    ┌───────▼───────┐
                    │  useTableFetch │
                    │     Hook       │
                    └───────┬───────┘
                            │
                    ┌───────▼───────┐
                    │   组件更新     │
                    │  Re-render    │
                    └───────────────┘
```

### 9.3 useTableFetch Hook

```typescript
// src/pages/resources/hooks/use-table-fetch.ts
import { useState, useEffect, useCallback } from 'react';
import { api } from '@/services/api';

interface UseTableFetchOptions<T> {
  fetchAPI: (params: any) => Promise<{ data: T[]; total: number }>;
  polling?: boolean;
  pollingInterval?: number;
  watch?: boolean;
  deleteAPI?: (id: string | number) => Promise<void>;
}

interface UseTableFetchReturn<T> {
  dataSource: T[];
  loading: boolean;
  queryParams: {
    pagination: { current: number; pageSize: number };
    filters: Record<string, (string | number)[] | null>;
  };
  setQueryParams: (params: any) => void;
  reload: () => void;
}

export function useTableFetch<T>({
  fetchAPI,
  polling = false,
  pollingInterval = 5000,
}: UseTableFetchOptions<T>): UseTableFetchReturn<T> {
  const [dataSource, setDataSource] = useState<T[]>([]);
  const [loading, setLoading] = useState(false);
  const [queryParams, setQueryParams] = useState({
    pagination: { current: 1, pageSize: 10 },
    filters: {},
  });

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const { data } = await fetchAPI(queryParams);
      setDataSource(data);
    } catch (error) {
      console.error('Fetch error:', error);
    } finally {
      setLoading(false);
    }
  }, [fetchAPI, queryParams]);

  useEffect(() => {
    fetchData();

    if (polling) {
      const timer = setInterval(fetchData, pollingInterval);
      return () => clearInterval(timer);
    }
  }, [fetchData, polling, pollingInterval]);

  return {
    dataSource,
    loading,
    queryParams,
    setQueryParams,
    reload: fetchData,
  };
}
```

---

## 10. 样式规范

### 10.1 主题配置

```typescript
// src/theme.ts
import { ConfigProvider, theme } from 'antd';

const appTheme = {
  token: {
    colorPrimary: '#1677ff',
    colorSuccess: '#52c41a',
    colorWarning: '#faad14',
    colorError: '#ff4d4f',
    borderRadius: 6,
  },
  components: {
    Layout: {
      headerBg: '#001529',
      siderBg: '#001529',
    },
  },
};

export const AppThemeProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  return (
    <ConfigProvider theme={appTheme}>
      {children}
    </ConfigProvider>
  );
};
```

### 10.2 全局样式

```css
/* src/index.css */
:root {
  --app-header-height: 64px;
  --app-sider-width: 240px;
  --app-padding: 24px;
}

body {
  margin: 0;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
}

.app-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.app-content {
  min-height: calc(100vh - var(--app-header-height));
}

/* 进度条颜色 */
.progress-bar-success {
  background-color: #52c41a;
}
.progress-bar-warning {
  background-color: #faad14;
}
.progress-bar-error {
  background-color: #ff4d4f;
}
```

---

## 附录 A: 类型定义

```typescript
// src/types/index.d.ts
declare global {
  namespace Global {
    type SearchParams = {
      page?: number;
      page_size?: number;
      q?: string;
      sort?: string;
      order?: 'asc' | 'desc';
    };
  }
}

export {};
```

---

## 附录 B: 开发规范

### B.1 命名规范

- **组件**: PascalCase (例: `UserProfile.tsx`)
- **Hook**: camelCase with `use` prefix (例: `useTableFetch.ts`)
- **工具函数**: camelCase (例: `formatBytes.ts`)
- **常量**: UPPER_SNAKE_CASE (例: `API_BASE_URL`)
- **类型/接口**: PascalCase (例: `interface UserModel {}`)

### B.2 文件组织

- 每个页面一个独立目录
- 组件按功能分组
- 公共组件放在 `components/`
- 页面特定组件放在 `pages/[page]/components/`
- Hook 放在对应的 `hooks/` 目录

### B.3 注释规范

```typescript
/**
 * 获取模型列表
 * @param params 查询参数
 * @returns 模型列表和总数
 */
export const getModels = async (params?: SearchParams) => {
  // ...
};
```

---

**文档版本**: v1.0
**最后更新**: 2025-01-14
**作者**: TokenMachine Team
