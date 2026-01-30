# TokenMachine GPU Agent

GPU Agent 是 TokenMachine 平台的 NVIDIA GPU 资源管理代理，负责 GPU 资源的占用、监控和任务执行。采用静态编译设计，减少系统依赖，提高部署效率。

## 架构组件

```
gpu-agent/
├── Exporter/          # GPU 监控导出器
├── Receiver/          # 任务接收器
├── occupier/          # GPU 内存占用程序
├── tm_agent.sh        # 主控制脚本
└── install.sh         # 安装脚本
```

### 组件职责

| 组件 | 端口 | 功能 |
|------|------|------|
| Exporter | 9090 | 导出 GPU 监控指标，供 Prometheus 采集 |
| Receiver | 9001 | 接收服务器任务指令，管理推理容器 |
| Occupier | 动态 | 预占用 GPU 内存，防止资源被抢占 |
| tm_agent.sh | - | 统一管理所有组件的生命周期 |

## 快速开始

### 方式一：本地编译部署

```bash
# 1. 编译 Go 组件（静态编译）
cd Exporter
./build.sh

cd ../Receiver
chmod +x build.sh && ./build.sh

# 2. 编译 CUDA 程序
cd ../occupier
nvcc -O3 -o occupy_gpu occupy_gpu.cu
strip occupy_gpu

# 3. 安装到系统
cd ..
./install.sh -s http://your-server:8000 -p 9001
```

### 方式二：预编译二进制部署

```bash
# 直接使用预编译的二进制
./install_simple.sh
```

## 核心功能

### 1. GPU 资源占用

通过 `occupy_gpu` 程序预占用 90% 的 GPU 内存，确保资源不被其他进程抢夺：

```bash
# 启动 GPU 内存占用（默认占用90%内存）
./occupier/occupy_gpu --gpu 0

# 指定内存大小（MB）
./occupier/occupy_gpu --gpu 0 --memory 16384

# 仅监控不占用
./occupier/occupy_gpu --gpu 0 --monitor

# 指定日志文件
./occupier/occupy_gpu --gpu 0 --log /var/log/tokenmachine/occupy_0.log
```

### 2. GPU 监控导出

Exporter 提供标准化的 GPU 监控指标：

```bash
# 启动 Exporter
cd Exporter
./gpu_exporter_main serve --port 9090

# 查看指标
curl http://localhost:9090/metrics

# 查看健康状态
curl http://localhost:9090/health

# 获取 JSON 格式指标
curl http://localhost:9090/json
```

**主要指标**：
```
# HELP gpu_memory_used_bytes GPU 内存使用量
# TYPE gpu_memory_used_bytes gauge
gpu_memory_used_bytes{gpu="0"} 8192000000

# HELP gpu_memory_total_bytes GPU 总内存
# TYPE gpu_memory_total_bytes gauge
gpu_memory_total_bytes{gpu="0"} 16384000000

# HELP gpu_memory_utilization GPU 内存利用率
# TYPE gpu_memory_utilization gauge
gpu_memory_utilization{gpu="0"} 0.5

# HELP gpu_utilization GPU 核心利用率
# TYPE gpu_utilization gauge
gpu_utilization{gpu="0"} 0.75

# HELP gpu_temperature_celsius GPU 温度
# TYPE gpu_temperature_celsius gauge
gpu_temperature_celsius{gpu="0"} 42
```

### 3. 任务管理

Receiver 接收并执行来自服务器的任务：

```bash
# 启动 Receiver
cd Receiver
./receiver

# 健康检查
curl http://localhost:9001/health

# 查看服务状态
curl http://localhost:9001/api/v1/status

# 查看任务列表
curl http://localhost:9001/api/v1/tasks/list
```

**支持的任务**：
- `start_vllm` - 启动 vLLM 推理服务
- `stop_vllm` - 停止 vLLM 推理服务

## 服务管理

### tm_agent.sh 控制脚本

```bash
# 启动所有服务
./tm_agent.sh start

# 停止所有服务
./tm_agent.sh stop

# 重启所有服务
./tm_agent.sh restart

# 查看服务状态
./tm_agent.sh status

# 编译所有组件（Go 程序）
./tm_agent.sh compile

# 交互式 GPU 选择
./tm_agent.sh select
```

### systemd 服务管理

```bash
# 启用服务
sudo systemctl enable tokenmachine-gpu-agent

# 启动服务
sudo systemctl start tokenmachine-gpu-agent

# 查看状态
sudo systemctl status tokenmachine-gpu-agent

# 查看日志
sudo journalctl -u tokenmachine-gpu-agent -f
```

## 配置

### 环境变量

```bash
export TM_SERVER_URL=http://your-server:8000    # 后端 API 地址
export TM_AGENT_PORT=9001                       # Receiver 端口
export TM_SELECTED_GPUS="0 1"                    # 选择的 GPU 列表
export TM_SELECTED_GPU_COUNT=2                   # GPU 数量
```

### GPU 选择

运行 `./tm_agent.sh select` 会显示交互式界面：

```
==================================================
TokenMachine GPU Agent
==================================================
请选择要管理的 GPU（使用空格键选择，上下键切换）：
■ [0] NVIDIA A100-SXM4-80GB (80GB) [可用]
■ [1] NVIDIA A100-SXM4-80GB (80GB) [可用]
□ [2] NVIDIA H100-SXM5-80GB (80GB) [可用]
□ [3] NVIDIA H100-SXM5-80GB (80GB) [可用]

操作：
↑/↓ : 上下移动
空格: 切换选择
回车: 确认选择
q:   退出程序
>
```

选择结果保存在 `~/.tokenmachine/selected_gpus.txt`。

## 监控和日志

### 日志位置

```
/var/log/tokenmachine/agent.log      # 主日志
/var/run/tokenmachine/exporter.log    # Exporter 日志
/var/run/tokenmachine/receiver.log   # Receiver 日志
/var/run/tokenmachine/occupy_*.log  # Occupier 日志（每个 GPU 一个）
```

### 监控命令

```bash
# 检查所有服务状态
./tm_agent.sh status

# 查看 GPU 状态
nvidia-smi --query-gpu=index,name,memory.used,memory.total --format=csv

# 查看 Exporter 指标
curl -s http://localhost:9090/metrics | grep gpu

# 测试 Receiver 连接
curl http://localhost:9001/health
```

## 故障排查

### 常见问题

#### 1. 二进制文件不是静态链接

```bash
# 检查二进制类型
file Exporter/gpu_exporter_main
file Receiver/receiver

# 应该显示：statically linked
```

#### 2. GLIBC 版本兼容性问题（已解决）

**现象**（已解决）：
- Receiver 启动失败，错误信息：
  ```
  ./receiver: /lib/x86_64-linux-gnu/libc.so.6: version 'GLIBC_2.34' not found
  ./receiver: /lib/x86_64-linux-gnu/libc.so.6: version 'GLIBC_2.32' not found
  ```
- Exporter 无法启动

**原因**：
- Ubuntu 20.04 系统的 GLIBC 版本为 2.31
- 现代 Go 1.21+ 编译的二进制需要 GLIBC 2.32+

**解决方案**（已实现）：
使用 Go 1.20 重新编译静态二进制文件

**关键修改**：
```bash
# 在 build.sh 中指定 Go 1.20
export GOTOOLCHAIN=go1.20

# 静态编译命令
CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build -a -ldflags '-extldflags "-static"' -o binary .
```

**验证**：
```bash
# 检查静态链接
file gpu_exporter_main  # 应显示：statically linked
file receiver          # 应显示：statically linked

# 检查无动态依赖
ldd gpu_exporter_main  # 应显示：not a dynamic executable
```

#### 2. GPU 内存占用失败

```bash
# 检查 occupy_gpu 进程
ps aux | grep occupy_gpu

# 查看 occupy_gpu 日志
tail -f /var/run/tokenmachine/occupy_0.log

# 检查 GPU 状态
nvidia-smi --query-gpu=index,memory.used,memory.total --format=csv
```

#### 3. Exporter 无法启动

```bash
# 检查端口占用
netstat -tlnp | grep 9090

# 查看 Exporter 日志
tail -f /var/run/tokenmachine/exporter.log

# 测试Exporter
curl http://localhost:9090/health
```

#### 4. Receiver 无法接收任务

```bash
# 检查 Receiver 日志
tail -f /var/run/tokenmachine/receiver.log

# 测试 Receiver 健康状态
curl http://localhost:9001/health

# 检查任务提交
curl -X POST http://localhost:9001/api/v1/tasks \
  -H "Content-Type: application/json" \
  -d '{"type":"test","params":{}}'
```

#### 5. 服务启动失败

```bash
# 查看 systemd 日志
sudo journalctl -u tokenmachine-gpu-agent -n 100

# 检查环境变量
sudo systemctl status tokenmachine-gpu-agent

# 重启服务
sudo systemctl restart tokenmachine-gpu-agent
```

### 测试工具

#### 90% 内存占用测试

```bash
# 运行测试脚本
./test_90_percent.sh
```

该脚本会：
1. 检查主机名为 Bulbasaur
2. 测试每个 GPU 的 90% 内存占用
3. 验证内存占用准确性

#### CUDA 编译测试

```bash
# 测试 CUDA 编译功能
./test_compile_only.sh
```

## 开发指南

### 本地开发环境设置

```bash
# 1. 安装 Go 1.21+
sudo apt install golang-go

# 2. 安装 CUDA Toolkit
sudo apt install cuda-toolkit-12-3

# 3. 设置环境变量
export PATH=/usr/local/cuda/bin:$PATH
export LD_LIBRARY_PATH=/usr/local/cuda/lib64:$LD_LIBRARY_PATH

# 4. 验证安装
go version
nvcc --version
```

### 修改和重新编译

```bash
# 修改 Exporter
cd Exporter
vim main.go
./build.sh

# 修改 Receiver
cd ../Receiver
vim main.go
chmod +x build.sh && ./build.sh

# 修改 CUDA 程序
cd ../occupier
vim occupy_gpu.cu
nvcc -O3 -o occupy_gpu occupy_gpu.cu
strip occupy_gpu
```

### 静态编译要点

使用以下命令进行静态编译：

```bash
# Exporter
CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build -a -ldflags '-extldflags "-static"' -o gpu_exporter_main .

# Receiver
CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build -a -ldflags '-extldflags "-static"' -o receiver .
```

关键参数说明：
- `CGO_ENABLED=0`: 禁用 CGO，避免 C 库依赖
- `GOOS=linux GOARCH=amd64`: 指定目标平台
- `-a`: 强制重新编译所有包
- `-ldflags '-extldflags "-static"'`: 链接静态库

## 部署建议

### 生产环境

1. **使用静态编译版本**：减少系统依赖，提高兼容性
2. **配置监控**：确保 Prometheus 能够采集 GPU 指标
3. **设置告警**：对 GPU 异常使用率设置告警
4. **定期更新**：及时更新 Agent 版本

### 安全考虑

1. **最小权限原则**：Agent 以 root 运行，但确保 Docker 容器使用非特权用户
2. **网络安全**：只开放必要的端口（9001, 9090）
3. **日志保护**：确保日志文件不被未授权访问

### 性能优化

1. **GPU 选择**：根据任务需求选择合适的 GPU
2. **内存管理**：合理设置内存占用比例（默认90%）
3. **并发控制**：通过 Receiver 的信号量限制并发任务数

## 版本历史

- **v1.0.0**: 初始版本，支持基本的 GPU 占用和监控
- **v1.1.0**: 添加任务接收功能，支持 vLLM 容器管理
- **v1.2.0**: 支持静态编译，减少系统依赖

## 许可证

MIT License