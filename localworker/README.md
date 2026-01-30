# TokenMachine Worker Agent

TokenMachine Worker 是一个异构计算资源管理代理程序，用于管理 GPU、NPU、AI 芯片等硬件资源。支持静态编译部署，减少系统依赖，提高部署效率。

## 支持的硬件平台

| 平台 | 状态 | 组件 | 功能 |
|------|------|------|------|
| NVIDIA GPU | ✅ 完整实现 | Exporter, Receiver, Occupier | GPU 资源占用和监控 |
| 华为昇腾 NPU | 🚧 开发中 | Ascend Exporter | NPU 资源监控 |
| AMD AI 芯片 | 🚧 开发中 | AMD Exporter | AI 芯片资源监控 |
| Intel AI 加速器 | 🚧 开发中 | Intel Exporter | AI 加速器资源监控 |

## 项目结构

```
worker/
├── gpu-agent/                    # NVIDIA GPU Agent (主要实现)
│   ├── tm_agent.sh              # 主控制脚本
│   ├── install.sh               # 完整安装脚本（含 CUDA 编译）
│   ├── install_simple.sh        # 简化安装脚本（预编译二进制）
│   ├── heartbeat.sh             # 心跳守护进程
│   ├── test_90_percent.sh       # 90% 内存占用测试
│   ├── test_compile_only.sh     # 编译测试脚本
│   ├── tui.py                   # GPU 选择 TUI 界面
│   ├── Exporter/                # GPU 监控导出器 (Go)
│   │   ├── main.go              # CLI 入口点
│   │   ├── server.go            # HTTP 服务器
│   │   ├── gpu_info.go          | GPU 信息收集
│   │   ├── prometheus.go        | Prometheus 指标格式
│   │   ├── build.sh             # 静态编译脚本
│   │   ├── go.mod               | Go 模块定义
│   │   └── gpu_exporter_main    | 编译后的二进制
│   ├── Receiver/                | 任务接收器 (Go)
│   │   ├── main.go              | HTTP 服务器实现
│   │   ├── go.mod               | Go 模块定义
│   │   └── receiver             | 编译后的二进制
│   ├── occupier/                | GPU 内存占用程序 (CUDA)
│   │   ├── occupy_gpu.cu        | CUDA 源代码
│   │   └── occupy_gpu           | 编译后的二进制
│   └── README.md                | GPU Agent 文档
├── Ascend-agent/                 # 华为昇腾 NPU Agent
│   └── README.md                | Ascend Agent 文档
├── Amd-agent/                    # AMD AI 芯片 Agent
│   └── README.md                | AMD Agent 文档
└── Intel-agent/                  # Intel AI 加速器 Agent
    └── README.md                | Intel Agent 文档
```

## 架构概览

### 核心组件

1. **Exporter** - GPU 资源监控导出器
   - 端口：9090
   - 提供Prometheus格式的GPU指标
   - 支持健康检查和JSON格式

2. **Receiver** - 任务接收器
   - 端口：9001
   - 接收来自服务器的任务指令
   - 执行 vLLM 容器管理

3. **Occupier** - GPU内存占用程序
   - 预占用90%的GPU内存
   - 防止其他进程抢占GPU资源
   - 支持监控和日志

4. **tm_agent.sh** - 主控制脚本
   - 统一管理所有组件
   - 提供启动、停止、重启功能
   - 支持GPU选择和配置

## 快速部署

### 标准部署流程

```bash
# 1. 本地编译
cd /home/ht706/Documents/TokenMachine/worker/gpu-agent/Exporter
./build.sh

cd ../Receiver
./build.sh

# 2. 部署整个worker目录到目标机器
cd /home/ht706/Documents/TokenMachine/worker
scp -r worker ht706@192.168.247.76:/home/ht706/

# 3. SSH到目标机器运行安装
ssh ht706@192.168.247.76
cd /home/ht706/worker/gpu-agent
sudo ./install.sh -s http://your-server:8000 -p 9001
```

### 部署说明

**步骤1：本地编译**
- Exporter 和 Receiver 必须在本地编译为静态链接
- build.sh 会自动验证二进制是否为静态链接
- 验证通过后才能部署

**步骤2：部署**
- 使用 `scp -r worker` 复制整个worker目录
- 包含所有预编译二进制和源代码

**步骤3：安装**
- install.sh 会自动：
  - 检查预编译二进制（Exporter、Receiver）
  - 编译 occupy_gpu（CUDA程序，在目标机器编译）
  - 创建目录结构
  - 复制文件到 /opt/tokenmachine
  - 启动所有服务

**完全自动化，无需手工操作！**

## 组件详细说明

### Exporter 组件

**功能**：导出GPU监控指标，供Prometheus采集

**API端点**：
- `GET /metrics` - Prometheus格式指标
- `GET /health` - 健康检查
- `GET /json` - JSON格式指标
- `GET /` - 帮助信息

**主要指标**：
- `gpu_memory_used_bytes` - GPU内存使用量
- `gpu_memory_total_bytes` - GPU总内存
- `gpu_memory_utilization` - 内存利用率
- `gpu_utilization` - GPU利用率
- `gpu_temperature_celsius` - GPU温度

### Receiver 组件

**功能**：接收并执行任务，管理推理容器

**API端点**：
- `POST /api/v1/tasks` - 提交任务
- `GET /api/v1/tasks/{id}` - 查询任务状态
- `GET /api/v1/tasks/list` - 列出所有任务
- `DELETE /api/v1/tasks/{id}` - 删除任务
- `GET /api/v1/status` - 服务状态
- `GET /health` - 健康检查

**支持的任务类型**：
- `start_vllm` - 启动vLLM推理服务
- `stop_vllm` - 停止vLLM推理服务

### Occupier 组件

**功能**：预占用GPU内存，防止资源被其他进程抢夺

**参数选项**：
- `--gpu N` - 指定GPU编号（默认0）
- `--memory MB` - 指定内存大小
- `--log FILE` - 日志文件路径
- `--monitor` - 仅监控不占用
- `--help` - 显示帮助

**默认行为**：
- 占用90%的GPU内存
- 在指定GPU上运行
- 持续运行直到收到终止信号

### tm_agent.sh 控制脚本

**功能**：统一管理所有组件的服务生命周期

**命令**：
```bash
./tm_agent.sh start    # 启动所有服务
./tm_agent.sh stop     # 停止所有服务
./tm_agent.sh restart  # 重启所有服务
./tm_agent.sh status   # 查看服务状态
./tm_agent.sh compile  # 编译所有组件
./tm_agent.sh select   # 交互式GPU选择
```

## 系统要求

### 基础依赖
- Linux系统（x86_64）
- root权限（用于系统服务）
- Docker（用于运行vLLM容器）

### GPU 相关依赖
- NVIDIA驱动（包含nvidia-smi）
- CUDA Toolkit（编译时需要，运行时不需要）
- GPU内存（建议至少8GB）

### 网络要求
- 能够访问后端API服务器
- 端口9090和9001可用

## 配置说明

### 环境变量

| 变量 | 必需 | 默认值 | 说明 |
|------|------|--------|------|
| TM_SERVER_URL | 是 | - | 后端API地址 |
| TM_AGENT_PORT | 是 | 9001 | Receiver端口 |
| TM_SELECTED_GPUS | 否 | "0 1" | 选择的GPU列表 |
| TM_SELECTED_GPU_COUNT | 否 | 2 | GPU数量 |

### 配置文件

**GPU选择配置**：`~/.tokenmachine/selected_gpus.txt`
```
0
1
```

## 监控和维护

### 服务检查

```bash
# 查看所有服务状态
./tm_agent.sh status

# 检查GPU状态
nvidia-smi --query-gpu=index,name,memory.used,memory.total --format=csv

# 检查Exporter指标
curl http://localhost:9090/metrics

# 检查Receiver状态
curl http://localhost:9001/health
```

### 日志查看

```bash
# 组件日志位置
/var/log/tokenmachine/agent.log      # 主日志
/var/run/tokenmachine/exporter.log    # Exporter日志
/var/run/tokenmachine/receiver.log   # Receiver日志
/var/run/tokenmachine/occupy_*.log  # Occupier日志（每个GPU一个）
```

### 故障排查

```bash
# 1. 检查二进制是否为静态链接
file /opt/tokenmachine/Exporter/gpu_exporter_main
file /opt/tokenmachine/Receiver/receiver

# 应该显示：statically linked

# 2. 验证GPU状态
nvidia-smi

# 3. 测试CUDA编译（如果需要）
cd /opt/tokenmachine
nvcc -O3 -o occupy_gpu occupier/occupy_gpu.cu

# 4. 重启服务
./tm_agent.sh restart

# 5. 查看详细日志
tail -f /var/log/tokenmachine/agent.log
```

### 已知问题

#### Ubuntu 20.04 GLIBC 兼容性问题（已解决）

**问题表现**：
- Exporter 和 Receiver 无法启动，提示 GLIBC 版本不兼容
- 错误信息：`./receiver: /lib/x86_64-linux-gnu/libc.so.6: version 'GLIBC_2.34' not found`

**原因**：
- Ubuntu 20.04 使用 GLIBC 2.31
- 现代 Go 1.21+ 编译的二进制需要 GLIBC 2.32+

**解决方案**：

**已解决**：使用 Go 1.20 重新编译静态二进制文件

**关键修改**：
1. **Go 版本**：在 `build.sh` 中使用 `GOTOOLCHAIN=go1.20`
2. **go.mod**：将 `go 1.24.0` 和 `go 1.21` 改为 `go 1.20`
3. **静态编译**：使用 `CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build -a -ldflags '-extldflags "-static"'`

**编译命令**：
```bash
# Exporter
export GOTOOLCHAIN=go1.20
CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build -a -ldflags '-extldflags "-static"' -o gpu_exporter_main .

# Receiver
export GOTOOLCHAIN=go1.20
CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build -a -ldflags '-extldflags "-static"' -o receiver .
```

验证：
```bash
# 检查是否为静态链接
file gpu_exporter_main
file receiver

# 应该显示：statically linked

# 检查无动态依赖
ldd gpu_exporter_main  # 应该显示：not a dynamic executable
```

## 测试工具

### Pytest 自动化测试套件

完整的 pytest 测试套件，覆盖编译、部署、安装、服务等所有环节。

**快速开始**：
```bash
# 安装测试依赖
cd /home/ht706/Documents/TokenMachine/worker/tests
pip install -r requirements.txt

# 配置测试环境
cp .env.test.example .env.test
# 编辑 .env.test 填入你的配置

# 运行所有测试
cd ..
pytest

# 或使用 Makefile
make test
```

**测试覆盖**：
- ✅ 本地编译验证（静态链接检查）
- ✅ 部署验证（文件完整性）
- ✅ 完整安装流程
- ✅ 服务状态检查（进程、端口）
- ✅ API 端点测试（/health、/metrics）
- ✅ 配置文件验证
- ✅ 心跳功能测试
- ✅ GPU 内存占用验证
- ✅ systemd 服务管理
- ✅ GPU 过滤功能
- ✅ 端到端注册（需要 Backend）

**详细文档**：见 [tests/README.md](tests/README.md)

**使用示例**：
```bash
# 只运行编译测试
make test-compile

# 只运行快速测试（跳过慢速测试）
make test-fast

# 生成覆盖率报告
make test-coverage

# 运行特定测试类
pytest tests/test_gpu_agent.py::TestServiceStatus -v

# 并行运行测试（更快）
pytest -n auto
```

### 90% 内存占用测试

```bash
# 在 Bulbasaur 上运行
cd /opt/tokenmachine
./test_90_percent.sh
```

该脚本会：
1. 检查主机名为 Bulbasaur
2. 测试每个GPU的90%内存占用
3. 验证内存占用准确性

### 编译测试

```bash
# 测试 CUDA 编译功能
cd /opt/tokenmachine
./test_compile_only.sh
```

## 开发指南

### 本地开发

```bash
# 1. 编译 Go 组件
cd Exporter
CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build -a -ldflags '-extldflags "-static"' -o gpu_exporter_main .

cd ../Receiver
CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build -a -ldflags '-extldflags "-static"' -o receiver .

# 2. 编译 CUDA 程序
cd ../occupier
nvcc -O3 -o occupy_gpu occupy_gpu.cu

# 3. 测试运行
cd ..
export TM_SELECTED_GPUS="0 1"
export TM_SELECTED_GPU_COUNT=2

# 启动 Exporter
./Exporter/gpu_exporter_main serve --port 9090 &

# 启动 Receiver
./Receiver/receiver &

# 启动 Occupier
./occupier --gpu 0 --log /tmp/occupy_0.log &
./occupier --gpu 1 --log /tmp/occupy_1.log &
```

### 静态编译要点

使用以下参数进行静态编译：
```bash
CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build -a -ldflags '-extldflags "-static"' -o binary .
```

关键参数：
- `CGO_ENABLED=0`: 禁用CGO依赖
- `GOOS=linux GOARCH=amd64`: 目标平台
- `-a`: 强制重新编译所有包
- `-ldflags '-extldflags "-static"'`: 链接静态库

## 许可证

TokenMachine Worker Agent - 遵循 MIT 许可证