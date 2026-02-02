# TokenMachine Ascend Agent

华为昇腾 NPU 设备管理 Agent，支持 Ascend 910/310 等昇腾系列芯片。

## 功能特性

- **NPU 选择工具**: 基于 TUI 的交互式 NPU 选择界面
- **内存占用**: 使用 ACL/CANN API 占用 NPU 内存，防止空闲时算力回收
- **指标导出**: Prometheus 格式的 NPU 指标导出 (npu-smi)
- **任务接收**: 接收并执行模型推理任务
- **心跳机制**: 定期向后台报告 Worker 状态
- **服务管理**: 支持 systemd 服务化部署

## 目录结构

```
ascend-agent/
├── tui.py              # NPU 选择 TUI 界面
├── install.sh          # 安装脚本
├── tm_agent.sh         # 服务管理脚本
├── heartbeat.sh        # 心跳脚本
├── occupier/
│   └── occupy_npu.cpp  # NPU 内存占用程序 (ACL)
├── Exporter/
│   ├── main.go         # Exporter 主程序
│   ├── go.mod
│   └── internal/npu/
│       ├── npu.go      # NPU 监控
│       ├── prometheus.go # Prometheus 指标
│       └── server.go   # HTTP 服务
└── Receiver/
    ├── main.go         # Receiver 主程序
    └── go.mod
```

## 快速开始

### 1. 编译组件

```bash
# 编译 occupy_npu (需要 CANN 环境)
cd ascend-agent/occupier
g++ -O3 -std=c++17 \
    -I${ASCEND_HOME}/ascend-toolkit/latest/include \
    -L${ASCEND_HOME}/ascend-toolkit/latest/lib64 \
    -o occupy_npu occupy_npu.cpp \
    -lacl_op_compiler -lascendcl -lpthread -ldl

# 编译 Exporter
cd ../Exporter
go build -o npu_exporter_main .

# 编译 Receiver
cd ../Receiver
go build -o receiver .
```

### 2. 安装

```bash
cd ascend-agent

# 安装 (需要 root 权限)
sudo ./install.sh install -s http://localhost:8000 -p 9001 -t <worker_token>

# 或指定 NPU 列表
sudo ./install.sh install -s http://localhost:8000 -p 9001 -t <token> --npus "0 1"
```

### 3. 管理服务

```bash
# 启动服务
sudo ./tm_agent.sh start

# 查看状态
sudo ./tm_agent.sh status

# 停止服务
sudo ./tm_agent.sh stop

# 重启服务
sudo ./tm_agent.sh restart

# 选择 NPU
sudo ./tm_agent.sh select
```

## 使用 NPU 选择工具

```bash
# 启动 TUI 界面
python3 tui.py

# 操作说明:
# - ↑↓ 键: 切换选择
# - 空格键: 选中/取消选中
# - 回车键: 确认选择
# - Esc 键: 保存并退出
```

## 监控指标

Exporter 提供以下 Prometheus 指标:

| 指标名 | 类型 | 说明 |
|--------|------|------|
| npu_count | gauge | NPU 设备数量 |
| npu_memory_used_bytes | gauge | 已用内存 (字节) |
| npu_memory_total_bytes | gauge | 总内存 (字节) |
| npu_memory_utilization | gauge | 内存使用率 |
| npu_utilization | gauge | 计算利用率 |
| npu_temperature_celsius | gauge | 温度 (摄氏度) |
| npu_power_watts | gauge | 功耗 (瓦) |
| npu_available | gauge | 可用性状态 |

## API 端点

### Receiver (端口 9001)

| 端点 | 方法 | 说明 |
|------|------|------|
| /health | GET | 健康检查 |
| /api/v1/tasks/list | GET | 列出任务 |
| /api/v1/tasks/start | POST | 启动任务 |
| /api/v1/tasks/stop | POST | 停止任务 |
| /api/v1/npu/status | GET | NPU 状态 |

### Exporter (端口 9090)

| 端点 | 方法 | 说明 |
|------|------|------|
| /health | GET | 健康检查 |
| /metrics | GET | Prometheus 指标 |

## 配置

### 环境变量

```bash
TM_SERVER_URL=      # 后端服务器地址
TM_AGENT_PORT=      # Agent 端口
TM_ASCEND_HOME=     # CANN 安装路径
```

### 配置文件

- `.env`: 环境变量配置
- `.worker_config`: Worker 认证信息

## 依赖

- Python 3.6+
- CANN (昇腾 AI 计算框架)
- Go 1.21+
- curl
- npu-smi

## 故障排查

```bash
# 查看服务日志
journalctl -u tokenmachine-ascend-agent -f

# 查看 NPU 状态
npu-smi list
npu-smi info

# 查看 Exporter 指标
curl http://localhost:9090/metrics

# 查看 Receiver 健康
curl http://localhost:9001/health
```

## 卸载

```bash
cd ascend-agent
sudo ./install.sh uninstall
```
