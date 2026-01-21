# TokenMachine GPU Agent

纯 Shell 实现的 GPU Worker 管理代理程序，用于 TokenMachine 平台的 GPU 资源管理。

## 特性

- **超轻量**：Agent 总体积 < 50KB（对比 Python 方案 ~50MB）
- **纯 Shell**：无 Python 依赖，仅需 bash + curl + nvidia-smi
- **快速启动**：< 0.5 秒启动时间
- **自动占卡**：启动即占用 95% 显存
- **实时心跳**：30 秒心跳，90 秒超时检测
- **跨机器**：支持一个 Worker 跨多台物理机器的 GPU

## 文件说明

```
agent/
├── occupy_gpu.cu      # CUDA C++ 占卡程序（需编译）
├── tm_agent.sh        # Agent 主脚本（纯 Bash）
├── install.sh         # 一键安装脚本
└── README.md          # 本文档
```

## 快速开始

### 1. 编译 occupy_gpu

```bash
cd agent
nvcc -O3 -o occupy_gpu occupy_gpu.cu
strip occupy_gpu  # 去除符号，减小体积
```

### 2. 一键安装 Agent

```bash
# 单张卡
export TM_TOKEN="tm_worker_abc123xyz789"
export TM_GPU_IDS="0"
./install.sh

# 多张卡
export TM_TOKEN="tm_worker_abc123xyz789"
export TM_GPU_IDS="0,1,2,3"
./install.sh
```

### 3. 手动运行

```bash
# 设置环境变量
export TM_TOKEN="tm_worker_abc123xyz789"
export TM_GPU_ID="0"

# 运行 Agent
./tm_agent.sh
```

## 环境变量

| 变量 | 必填 | 说明 | 默认值 |
|------|------|------|--------|
| `TM_TOKEN` | 是 | Worker 注册 Token | - |
| `TM_GPU_ID` | 是 | GPU ID（单张卡） | - |
| `TM_GPU_IDS` | 是 | GPU ID 列表（多张卡，逗号分隔） | - |
| `TM_SERVER_URL` | 否 | Server API 地址 | https://api.tokenmachine.io |
| `TM_AGENT_PORT` | 否 | Agent 端口 | 9000 + GPU_ID |
| `TM_HEARTBEAT_INTERVAL` | 否 | 心跳间隔（秒） | 30 |

## 工作流程

```
1. 占卡
   └─ occupy_gpu 占用 95% 显存

2. 注册
   └─ 使用 Token 注册 GPU 到 Worker

3. 心跳
   └─ 每 30 秒上报一次 GPU 状态
```

## 部署架构

```
Worker-01 (worker-gpu-pool)
├── 机器1 (192.168.1.101)
│   ├── GPU-2 (port: 9002)
│   ├── GPU-3 (port: 9003)
│   └── GPU-4 (port: 9004)
└── 机器2 (192.168.1.102)
    ├── GPU-6 (port: 9006)
    └── GPU-7 (port: 9007)
```

## 日志文件

- Agent 日志：`/var/log/tokenmachine/agent_<GPU_ID>.log`
- 占卡日志：`/var/run/tokenmachine/occupy_<GPU_ID>.log`

## 常见问题

### 1. 如何查看 Agent 状态？

```bash
# 查看 systemd 服务状态
sudo systemctl status tm-agent@0

# 查看 Agent 日志
sudo tail -f /var/log/tokenmachine/agent_0.log

# 查看进程
ps aux | grep tm_agent
```

### 2. GPU 已被占用怎么办？

```bash
# 查看哪些进程在使用 GPU
nvidia-smi

# 停止占用 GPU 的进程
kill -9 <PID>

# 然后重新启动 Agent
sudo systemctl restart tm-agent@0
```

### 3. 如何重启 Agent？

```bash
# systemd 模式
sudo systemctl restart tm-agent@0

# 手动模式（先停止）
pkill -f "tm_agent.sh.*0"
TM_TOKEN="..." TM_GPU_ID="0" ./tm_agent.sh
```

### 4. 如何卸载 Agent？

```bash
# 停止所有 Agent
sudo systemctl stop tm-agent@*
sudo systemctl disable tm-agent@*

# 删除服务文件
sudo rm -f /etc/systemd/system/tm-agent@*.service
sudo systemctl daemon-reload

# 删除安装文件
sudo rm -rf /opt/tokenmachine
```

## 系统要求

- **操作系统**：Linux (支持 nvidia-smi)
- **NVIDIA 驱动**：>= 470.x
- **CUDA**：>= 11.0（用于编译 occupy_gpu.cu）
- **工具**：bash, curl, nvidia-smi

## 开发

### 编译 occupy_gpu.cu

```bash
# 基础编译
nvcc -O3 -o occupy_gpu occupy_gpu.cu

# 优化编译（减小体积）
nvcc -O3 -o occupy_gpu occupy_gpu.cu
strip occupy_gpu

# 验证
./occupy_gpu 0 0.95
```

### 测试 tm_agent.sh

```bash
# 1. 设置测试环境变量
export TM_TOKEN="test_token_abc123"
export TM_GPU_ID="0"
export TM_SERVER_URL="http://localhost:8000"

# 2. 启动 Agent（调试模式）
bash -x tm_agent.sh

# 3. 查看日志
tail -f /var/log/tokenmachine/agent_0.log
```

## 性能指标

| 指标 | 数值 |
|------|------|
| Agent 体积 | < 50KB |
| Agent 启动时间 | < 0.5秒 |
| 单卡注册时间 | < 5秒 |
| 100 卡注册时间 | < 30秒 |
| 内存占用（每 GPU） | < 5MB |
| 心跳响应时间 | < 1秒 |

## 架构文档

详细架构设计请参考：
- [后端架构设计](../../docs/02-architecture/backend/GPU_WORKER_SHELL_ARCHITECTURE.md)

## 许可证

MIT License
