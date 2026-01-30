# TokenMachine GPU Exporter

GPU Exporter 是一个用 Go 编写的 GPU 监控导出器，用于将 NVIDIA GPU 监控指标导出为 Prometheus 格式。采用静态编译设计，无需运行时依赖。

## 特性

- ✅ **静态编译** - 无需运行时依赖
- 📊 **Prometheus 兼容** - 标准的 Prometheus 指标格式
- 🔧 **丰富指标** - 提供全面的 GPU 监控指标
- 🌐 **多种格式** - 支持 Prometheus、JSON、健康检查等多种输出格式
- 🚀 **高性能** - 轻量级设计，资源占用低
- 🔧 **易于集成** - 可直接集成到现有监控栈

## 构建和安装

### 静态编译

```bash
# 静态编译（推荐）
cd /path/to/Exporter
./build.sh
```

编译命令详解：
```bash
CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build -a -ldflags '-extldflags "-static"' -o gpu_exporter_main .
```

### 手动编译

```bash
# 确保已安装 Go 1.24+
go version

# 编译
CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build -a -ldflags '-extldflags "-static"' -o gpu_exporter_main .

# 验证静态链接
file gpu_exporter_main
# 应该显示：statically linked
```

## 运行方式

### 命令行选项

```bash
./gpu_exporter_main --help
```

```
TokenMachine GPU metrics exporter

Usage:
  gpu_exporter [flags]
  gpu_exporter [command]

Available Commands:
  check            Check GPU availability
  completion       Generate the autocompletion script for the specified shell
  dump             Show metrics once (dry run)
  generate-systemd Generate systemd service file
  help             Help about any command
  serve            Run the GPU exporter HTTP server
  test             Test mode with mock GPU data

Flags:
      --check-gpu             Verify GPU availability on startup
      --debug                 Enable debug logging
  -e, --env strings           Environment variables
  -n, --gpu-count int         Number of mock GPUs (default 1)
  -H, --host string           Bind address (default "0.0.0.0")
      --interactive           Enable interactive mode
      --json                  Enable JSON structured logging
      --log-file string       Log file path
  -p, --port int              Port to listen on (default 9090)
  -s, --service-name string   Service name (default "tokenmachine-gpu-exporter")
  -u, --user string           User to run as (default "root")
  -v, --version               version for gpu_exporter
  -w, --working-dir string    Working directory (default "/opt/tokenmachine")
```

### 启动服务器

```bash
# 默认配置（端口 9090）
./gpu_exporter_main serve

# 指定端口
./gpu_exporter_main serve --port 9090

# 绑定特定地址
./gpu_exporter_main serve --host 192.168.1.100 --port 9090

# 启用调试日志
./gpu_exporter_main serve --debug

# 使用 JSON 日志格式
./gpu_exporter_main serve --json --log-file /var/log/tokenmachine/exporter.log
```

### 生成 systemd 服务文件

```bash
./gpu_exporter_main generate-systemd > /etc/systemd/system/tokenmachine-gpu-exporter.service
```

## API 端点

### 1. Prometheus 指标

```
GET /metrics
```

返回标准的 Prometheus 格式指标：

```bash
curl http://localhost:9090/metrics
```

示例输出：
```
# HELP gpu_count Number of GPUs
# TYPE gpu_count gauge
gpu_count 2

# HELP gpu_memory_used_bytes GPU memory used
# TYPE gpu_memory_used_bytes gauge
gpu_memory_used_bytes{gpu="0"} 8192000000
gpu_memory_used_bytes{gpu="1"} 8192000000

# HELP gpu_memory_total_bytes Total GPU memory
# TYPE gpu_memory_total_bytes gauge
gpu_memory_total_bytes{gpu="0"} 16384000000
gpu_memory_total_bytes{gpu="1"} 16384000000

# HELP gpu_memory_utilization GPU memory utilization
# TYPE gpu_memory_utilization gauge
gpu_memory_utilization{gpu="0"} 0.5
gpu_memory_utilization{gpu="1"} 0.5

# HELP gpu_utilization GPU utilization percentage
# TYPE gpu_utilization gauge
gpu_utilization{gpu="0"} 75.3
gpu_utilization{gpu="1"} 68.2

# HELP gpu_temperature_celsius GPU temperature in Celsius
# TYPE gpu_temperature_celsius gauge
gpu_temperature_celsius{gpu="0"} 42
gpu_temperature_celsius{gpu="1"} 45
```

### 2. 健康检查

```
GET /health
```

```bash
curl http://localhost:9090/health
```

响应：
```json
{
  "status": "healthy",
  "timestamp": "2026-01-28T16:49:23Z",
  "gpu_count": 2,
  "gpu_names": ["NVIDIA A100-SXM4-80GB", "NVIDIA A100-SXM4-80GB"]
}
```

### 3. JSON 格式指标

```
GET /json
```

```bash
curl http://localhost:9090/json
```

响应：
```json
{
  "timestamp": "2026-01-28T16:49:23Z",
  "gpu_count": 2,
  "gpus": [
    {
      "index": 0,
      "name": "NVIDIA A100-SXM4-80GB",
      "memory_used": 8192000000,
      "memory_total": 16384000000,
      "memory_utilization": 0.5,
      "utilization": 75.3,
      "temperature": 42,
      "power_usage": 250.0
    },
    {
      "index": 1,
      "name": "NVIDIA A100-SXM4-80GB",
      "memory_used": 8192000000,
      "memory_total": 16384000000,
      "memory_utilization": 0.5,
      "utilization": 68.2,
      "temperature": 45,
      "power_usage": 240.0
    }
  ]
}
```

### 4. 帮助信息

```
GET /
```

```bash
curl http://localhost:9090/
```

## 监控指标

### 核心指标

| 指标名称 | 类型 | 描述 | 标签 |
|----------|------|------|------|
| `gpu_count` | gauge | GPU 总数 | - |
| `gpu_memory_used_bytes` | gauge | GPU 已用内存 | `gpu` |
| `gpu_memory_total_bytes` | gauge | GPU 总内存 | `gpu` |
| `gpu_memory_utilization` | gauge | GPU 内存利用率 | `gpu` |
| `gpu_utilization` | gauge | GPU 核心利用率 | `gpu` |
| `gpu_temperature_celsius` | gauge | GPU 温度 | `gpu` |
| `gpu_power_usage_watts` | gauge | GPU 功耗 | `gpu` |
| `gpu_memory_free_bytes` | gauge | GPU 可用内存 | `gpu` |
| `gpu_memory_busy_bytes` | gauge | GPU 忙碌内存 | `gpu` |

### 计算指标

| 指标名称 | 计算公式 | 说明 |
|----------|----------|------|
| `gpu_memory_utilization` | `memory_used / memory_total` | 内存使用率 |
| `gpu_memory_free_bytes` | `memory_total - memory_used` | 可用内存 |
| `gpu_memory_busy_bytes` | `memory_total - memory_free` | 忙碌内存 |

## 配置

### 环境变量

```bash
export TM_EXPORTER_PORT=9090          # 监听端口
export TM_EXPORTER_HOST=0.0.0.0      # 监听地址
export TM_EXPORTER_LOG_LEVEL=info    # 日志级别
export TM_EXPORTER_LOG_JSON=true     # JSON 格式日志
export TM_EXPORTER_CHECK_GPU=true     # 启动时检查 GPU
```

### 配置文件

Exporter 支持通过环境变量进行配置：

```bash
# 使用环境变量启动
export TM_SELECTED_GPUS="0 1"
export TM_SELECTED_GPU_COUNT=2
./gpu_exporter_main serve --port 9090
```

## 部署

### 作为系统服务运行

1. **生成 systemd 服务文件**：
```bash
./gpu_exporter_main generate-systemd > /etc/systemd/system/tokenmachine-gpu-exporter.service
```

2. **启用并启动服务**：
```bash
sudo systemctl daemon-reload
sudo systemctl enable tokenmachine-gpu-exporter
sudo systemctl start tokenmachine-gpu-exporter
```

3. **查看服务状态**：
```bash
sudo systemctl status tokenmachine-gpu-exporter
sudo journalctl -u tokenmachine-gpu-exporter -f
```

### 作为 Docker 容器运行

```bash
# 构建 Docker 镜像
docker build -t tokenmachine-gpu-exporter .

# 运行容器
docker run -d \
  --name gpu-exporter \
  --restart always \
  -p 9090:9090 \
  -v /var/log/tokenmachine:/var/log/tokenmachine \
  tokenmachine-gpu-exporter
```

### 作为 Kubernetes 部署

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: gpu-exporter
spec:
  replicas: 1
  selector:
    matchLabels:
      app: gpu-exporter
  template:
    metadata:
      labels:
        app: gpu-exporter
    spec:
      containers:
      - name: gpu-exporter
        image: tokenmachine/gpu-exporter:latest
        ports:
        - containerPort: 9090
        resources:
          limits:
            memory: "128Mi"
          requests:
            memory: "64Mi"
        env:
        - name: TM_EXPORTER_PORT
          value: "9090"
```

## 集成示例

### Prometheus 配置

```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'tokenmachine-gpu'
    static_configs:
      - targets: ['localhost:9090']
    scrape_interval: 15s
    metrics_path: /metrics
```

### Grafana 仪表板

使用以下查询创建 Grafana 仪表板：

1. **GPU 内存使用率**：
```
avg(gpu_memory_utilization) by (gpu)
```

2. **GPU 温度**：
```
avg(gpu_temperature_celsius) by (gpu)
```

3. **GPU 利用率**：
```
avg(gpu_utilization) by (gpu)
```

### AlertManager 告警

```yaml
groups:
- name: gpu_alerts
  rules:
  - alert: HighGPUUtilization
    expr: gpu_utilization > 90
    for: 5m
    labels:
      severity: warning
    annotations:
      summary: "GPU utilization is high"
      description: "GPU {{ $labels.gpu }} utilization is {{ $value }}%"

  - alert: HighGPUMemoryUsage
    expr: gpu_memory_utilization > 0.95
    for: 2m
    labels:
      severity: critical
    annotations:
      summary: "GPU memory usage is critical"
      description: "GPU {{ $labels.gpu }} memory utilization is {{ $value }}"
```

## 开发指南

### 本地开发

```bash
# 克隆仓库
git clone <repository>
cd Exporter

# 安装依赖
go mod tidy

# 运行测试
go test ./...

# 编译开发版本
go build -o gpu_exporter_main .

# 测试运行
./gpu_exporter_main serve --port 9090 --debug
```

### 修改指标

1. **添加新指标**：
```go
// 在 metrics.go 中添加新指标
var NewMetric = prometheus.NewGaugeVec(
    prometheus.GaugeOpts{
        Name: "new_metric",
        Help: "New metric description",
    },
    []string{"gpu"},
)
```

2. **更新指标收集**：
```go
// 在 collectMetrics() 中更新
NewMetric.WithLabelValues(strconv.Itoa(i)).Set(newValue)
```

### 性能优化

1. **减少 nvidia-smi 调用频率**：
```go
// 使用缓存机制
type GPUInfo struct {
    lastUpdate time.Time
    cachedData *GPUStats
}

func (g *GPUInfo) Get() (*GPUStats, error) {
    // 实现5秒缓存
}
```

2. **并发收集 GPU 信息**：
```go
var wg sync.WaitGroup

for i := 0; i < gpuCount; i++ {
    wg.Add(1)
    go func(idx int) {
        defer wg.Done()
        metrics[idx] = collectGPU(idx)
    }(i)
}
wg.Wait()
```

## 故障排查

### 常见问题

#### 1. nvidia-smi 命令未找到

```bash
# 检查 NVIDIA 驱动
nvidia-smi --version

# 如果未安装，安装 NVIDIA 驱动
sudo apt install nvidia-driver-535
```

#### 2. 端口占用

```bash
# 检查端口占用
netstat -tlnp | grep 9090

# 如果端口被占用，更改端口
./gpu_exporter_main serve --port 9091
```

#### 3. 权限问题

```bash
# 确保 exporter 有权限访问 GPU
sudo ./gpu_exporter_main serve

# 或者将用户加入 video 组
sudo usermod -a -G video $USER
```

#### 4. GLIBC 版本不兼容

**错误信息**：
```bash
./gpu_exporter_main: /lib/x86_64-linux-gnu/libc.so.6: version 'GLIBC_2.34' not found
./gpu_exporter_main: /lib/x86_64-linux-gnu/libc.so.6: version 'GLIBC_2.32' not found
```

**解决方案**：
1. **升级系统**到 Ubuntu 22.04+
2. **使用兼容的 Go 版本**（Go 1.20）重新编译
3. **使用 Docker 容器**运行

```bash
# 检查系统 GLIBC 版本
ldd --version

# 使用 Go 1.20 重新编译
GOVERSION=1.20
wget https://go.dev/dl/go${GOVERSION}.linux-amd64.tar.gz
sudo tar -C /usr/local -xzf go${GOVERSION}.linux-amd64.tar.gz
cd Exporter
/usr/local/go/bin/go build -a -ldflags '-extldflags "-static"' -o gpu_exporter_main .
```

### 调试模式

```bash
# 启用调试日志
./gpu_exporter_main serve --debug

# 使用 JSON 日志
./gpu_exporter_main serve --json --log-file /var/log/exporter.log

# 检查 GPU 状态
./gpu_exporter_main check
```

### 日志分析

```bash
# 查看 GPU 详细信息
curl http://localhost:9090/metrics | grep gpu

# 查看内存使用
curl http://localhost:9090/metrics | grep memory

# 查看温度信息
curl http://localhost:9090/metrics | grep temperature
```

## 版本信息

- **版本**: 0.1.0
- **Go 版本**: 1.24
- **CUDA 版本**: 11.x+
- **支持平台**: Linux x86_64

## 许可证

MIT License