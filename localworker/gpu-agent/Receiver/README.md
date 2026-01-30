# TokenMachine GPU Agent Receiver

Receiver 是一个用 Go 编写的轻量级 HTTP 服务器，用于接收来自 TokenMachine 服务器的任务指令并执行。主要负责管理 vLLM 推理容器的生命周期。采用静态编译设计，无需运行时依赖。

## 特性

- ✅ **静态编译** - 无需运行时依赖
- 🚀 **轻量级** - 最小化资源占用
- 🔄 **并发处理** - 支持多任务并发执行
- 📊 **状态管理** - 完整的任务生命周期管理
- 🔧 **易于集成** - 标准 HTTP API 接口
- 🛡️ **错误处理** - 完善的错误处理和重试机制

## 构建和安装

### 静态编译

```bash
# 静态编译（推荐）
cd /path/to/Receiver
./build.sh
```

编译命令详解：
```bash
CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build -a -ldflags '-extldflags "-static"' -o receiver .
```

### 手动编译

```bash
# 确保已安装 Go 1.21+
go version

# 编译
CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build -a -ldflags '-extldflags "-static"' -o receiver .

# 验证静态链接
file receiver
# 应该显示：statically linked
```

## 运行方式

### 启动服务器

```bash
# 默认配置（端口 9001）
./receiver

# 指定端口
./receiver --port 9001

# 绑定特定地址
./receiver --host 192.168.1.100 --port 9001

# 启用调试日志
./receiver --debug

# 使用 JSON 日志格式
./receiver --json --log-file /var/log/tokenmachine/receiver.log
```

### 环境变量配置

```bash
export TM_SERVER_URL=http://your-server:8000    # 后端服务器地址
export TM_AGENT_PORT=9001                       # Receiver 端口
export TM_LOG_LEVEL=info                         # 日志级别
export TM_LOG_JSON=true                          # JSON 日志格式
export TM_MAX_CONCURRENT_TASKS=10                # 最大并发任务数
```

## API 端点

### 1. 健康检查

```
GET /health
```

```bash
curl http://localhost:9001/health
```

响应：
```json
{
  "status": "healthy",
  "timestamp": "2026-01-28T16:49:23Z",
  "version": "1.0.0",
  "tasks_running": 0,
  "tasks_completed": 0
}
```

### 2. 服务状态

```
GET /api/v1/status
```

```bash
curl http://localhost:9001/api/v1/status
```

响应：
```json
{
  "status": "ok",
  "timestamp": "2026-01-28T16:49:23Z",
  "version": "1.0.0",
  "tasks": {
    "running": 0,
    "pending": 0,
    "completed": 0,
    "failed": 0
  },
  "uptime": "1h30m",
  "memory_usage": "15MB"
}
```

### 3. 提交任务

```
POST /api/v1/tasks
Content-Type: application/json
```

```bash
curl -X POST http://localhost:9001/api/v1/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "type": "start_vllm",
    "params": {
      "model_id": "mistralai/Mistral-7B-Instruct-v0.2",
      "gpu_id": 0,
      "port": 8002,
      "memory_fraction": 0.9
    }
  }'
```

响应：
```json
{
  "task_id": "task_12345",
  "status": "pending",
  "message": "Task accepted",
  "created_at": "2026-01-28T16:49:23Z"
}
```

### 4. 查询任务状态

```
GET /api/v1/tasks/{task_id}
```

```bash
curl http://localhost:9001/api/v1/tasks/task_12345
```

响应：
```json
{
  "task_id": "task_12345",
  "type": "start_vllm",
  "status": "running",
  "params": {
    "model_id": "mistralai/Mistral-7B-Instruct-v0.2",
    "gpu_id": 0,
    "port": 8002,
    "memory_fraction": 0.9
  },
  "progress": 50,
  "message": "Starting vLLM container",
  "created_at": "2026-01-28T16:49:23Z",
  "updated_at": "2026-01-28T16:50:23Z",
  "docker_id": "container_abc123",
  "logs": [
    {
      "timestamp": "2026-01-28T16:50:00Z",
      "level": "info",
      "message": "Pulling image..."
    },
    {
      "timestamp": "2026-01-28T16:50:15Z",
      "level": "info",
      "message": "Container started"
    }
  ]
}
```

### 5. 列出所有任务

```
GET /api/v1/tasks/list
```

```bash
curl http://localhost:9001/api/v1/tasks/list
```

响应：
```json
{
  "tasks": [
    {
      "task_id": "task_12345",
      "type": "start_vllm",
      "status": "completed",
      "created_at": "2026-01-28T16:49:23Z",
      "updated_at": "2026-01-28T16:52:23Z",
      "duration": "3m"
    },
    {
      "task_id": "task_12346",
      "type": "stop_vllm",
      "status": "running",
      "created_at": "2026-01-28T16:53:00Z",
      "updated_at": "2026-01-28T16:53:00Z"
    }
  ],
  "total": 2,
  "running": 1,
  "completed": 1,
  "failed": 0
}
```

### 6. 删除任务

```
DELETE /api/v1/tasks/{task_id}
```

```bash
curl -X DELETE http://localhost:9001/api/v1/tasks/task_12346
```

响应：
```json
{
  "message": "Task task_12346 deleted successfully",
  "task_id": "task_12346"
}
```

## 任务类型

### 1. start_vllm

启动 vLLM 推理服务。

**请求参数**：
```json
{
  "type": "start_vllm",
  "params": {
    "model_id": "mistralai/Mistral-7B-Instruct-v0.2",
    "gpu_id": 0,
    "port": 8002,
    "memory_fraction": 0.9,
    "tensor_parallel_size": 1,
    "max_num_batched_tokens": 8192,
    "max_model_len": 4096
  }
}
```

**参数说明**：
- `model_id`: 要加载的模型 ID
- `gpu_id`: 使用的 GPU ID
- `port`: 容器映射的端口
- `memory_fraction`: 使用的 GPU 内存比例
- `tensor_parallel_size`: 张量并行大小
- `max_num_batched_tokens`: 最大批处理 token 数
- `max_model_len`: 最大模型长度

### 2. stop_vllm

停止 vLLM 推理服务。

**请求参数**：
```json
{
  "type": "stop_vllm",
  "params": {
    "container_id": "container_abc123",
    "port": 8002
  }
}
```

**参数说明**：
- `container_id`: 要停止的容器 ID
- `port`: 容器映射的端口（可选）

## 任务状态

| 状态 | 描述 |
|------|------|
| `pending` | 任务已接受，等待执行 |
| `running` | 任务正在执行 |
| `completed` | 任务成功完成 |
| `failed` | 任务执行失败 |
| `cancelled` | 任务被取消 |

## 部署

### 作为系统服务运行

1. **创建 systemd 服务文件**：
```ini
# /etc/systemd/system/tokenmachine-receiver.service
[Unit]
Description=TokenMachine GPU Agent Receiver
After=network.target

[Service]
Type=simple
User=root
Environment="TM_SERVER_URL=http://your-server:8000"
Environment="TM_AGENT_PORT=9001"
WorkingDirectory=/opt/tokenmachine
ExecStart=/opt/tokenmachine/Receiver/receiver
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

2. **启用并启动服务**：
```bash
sudo systemctl daemon-reload
sudo systemctl enable tokenmachine-receiver
sudo systemctl start tokenmachine-receiver
```

3. **查看服务状态**：
```bash
sudo systemctl status tokenmachine-receiver
sudo journalctl -u tokenmachine-receiver -f
```

### Docker 部署

```bash
# 运行容器
docker run -d \
  --name tokenmachine-receiver \
  --restart always \
  --network host \
  -v /var/log/tokenmachine:/var/log/tokenmachine \
  -e TM_SERVER_URL=http://your-server:8000 \
  -e TM_AGENT_PORT=9001 \
  tokenmachine/gpu-receiver:latest
```

### Kubernetes 部署

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: tokenmachine-receiver
spec:
  replicas: 1
  selector:
    matchLabels:
      app: tokenmachine-receiver
  template:
    metadata:
      labels:
        app: tokenmachine-receiver
    spec:
      containers:
      - name: receiver
        image: tokenmachine/gpu-receiver:latest
        ports:
        - containerPort: 9001
        env:
        - name: TM_SERVER_URL
          value: "http://your-server:8000"
        - name: TM_AGENT_PORT
          value: "9001"
        resources:
          limits:
            memory: "64Mi"
          requests:
            memory: "32Mi"
```

## 容器管理

### Docker 操作示例

启动 vLLM 容器：
```bash
docker run -d \
  --name vllm-mistral-7b \
  --gpus all \
  --shm-size 16g \
  -p 8002:8000 \
  -v /var/run/docker.sock:/var/run/docker.sock \
  vllm/vllm-openai:latest \
  --model mistralai/Mistral-7B-Instruct-v0.2 \
  --gpu-memory-utilization 0.9 \
  --port 8000
```

停止 vLLM 容器：
```bash
docker stop vllm-mistral-7b
docker rm vllm-mistral-7b
```

### 并发控制

Receiver 使用信号量机制控制最大并发任务数：

```go
// 默认最大并发数：10
const MaxConcurrentTasks = 10

// 创建信号量
sem := make(chan struct{}, MaxConcurrentTasks)

// 提交任务
sem <- struct{}{} // 获取信号量
defer func() { <-sem }() // 释放信号量
```

## 错误处理

### 常见错误

#### 1. Docker 操作失败

```json
{
  "task_id": "task_12345",
  "status": "failed",
  "error": {
    "code": "DOCKER_PULL_FAILED",
    "message": "Failed to pull image vllm/vllm-openai:latest"
  },
  "logs": [
    {
      "timestamp": "2026-01-28T16:50:00Z",
      "level": "error",
      "message": "Error response from daemon: manifest for vllm/vllm-openai:latest not found"
    }
  ]
}
```

#### 2. GPU 资源不足

```json
{
  "task_id": "task_12346",
  "status": "failed",
  "error": {
    "code": "GPU_INSUFFICIENT",
    "message": "GPU 0 memory utilization is too high (95%)"
  }
}
```

#### 3. 端口冲突

```json
{
  "task_id": "task_12347",
  "status": "failed",
  "error": {
    "code": "PORT_CONFLICT",
    "message": "Port 8002 is already in use"
  }
}
```

#### 4. GLIBC 版本不兼容

**错误信息**：
```bash
./receiver: /lib/x86_64-linux-gnu/libc.so.6: version 'GLIBC_2.34' not found
./receiver: /lib/x86_64-linux-gnu/libc.so.6: version 'GLIBC_2.32' not found
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
/usr/local/go/bin/go build -o receiver .
```

### 错误重试机制

对于临时性错误，Receiver 会自动重试：

- **Docker 拉取失败**：重试 3 次，间隔 30 秒
- **端口冲突**：自动选择可用端口，重试 5 次
- **GPU 资源不足**：等待 60 秒后重试

## 监控和日志

### 日志格式

```json
{
  "timestamp": "2026-01-28T16:49:23Z",
  "level": "info",
  "message": "Task accepted",
  "task_id": "task_12345",
  "type": "start_vllm",
  "gpu_id": 0
}
```

### 关键监控指标

| 指标 | 说明 |
|------|------|
| `tasks_total` | 总任务数 |
| `tasks_completed` | 成功完成任务数 |
| `tasks_failed` | 失败任务数 |
| `tasks_pending` | 等待中任务数 |
| `tasks_running` | 运行中任务数 |
| `avg_task_duration` | 平均任务执行时间 |
| `docker_operations_total` | Docker 操作总数 |

### 监控命令

```bash
# 查看实时任务
curl http://localhost:9001/api/v1/tasks/list | jq '.tasks[] | "\(.task_id): \(.status) - \(.type)"'

# 查看服务状态
curl http://localhost:9001/api/v1/status

# 检查健康状态
curl http://localhost:9001/health
```

## 开发指南

### 本地开发

```bash
# 克隆仓库
git clone <repository>
cd Receiver

# 安装依赖
go mod tidy

# 运行测试
go test ./...

# 编译开发版本
go build -o receiver .

# 测试运行
./receiver --debug --port 9001
```

### 添加新任务类型

1. **定义任务结构**：
```go
type StartVLLMTask struct {
    ModelID          string  `json:"model_id"`
    GPUID           int     `json:"gpu_id"`
    Port            int     `json:"port"`
    MemoryFraction  float64 `json:"memory_fraction"`
}
```

2. **实现任务处理器**：
```go
func (t *StartVLLMTask) Execute(ctx context.Context, logger *log.Logger) error {
    // 实现 vLLM 容器启动逻辑
    cmd := exec.CommandContext(ctx, "docker", "run", "-d", ...)
    return cmd.Run()
}
```

3. **注册任务处理器**：
```go
taskRegistry.Register("start_vllm", func(params json.RawMessage) (Task, error) {
    var task StartVLLMTask
    err := json.Unmarshal(params, &task)
    return &task, err
})
```

### 性能优化

1. **连接池管理**：
```go
// 创建 Docker 客户端池
dockerPool := sync.Pool{
    New: func() interface{} {
        return docker.NewClient()
    },
}
```

2. **任务队列优化**：
```go
// 使用带优先级的任务队列
priorityQueue := NewPriorityQueue()

// 提交任务
priorityQueue.Submit(&task, priority)
```

## 安全考虑

1. **容器安全**：
- 使用非特权用户运行容器
- 限制容器资源使用
- 定期更新基础镜像

2. **API 安全**：
- 实现认证和授权
- 限制 API 访问源 IP
- 记录所有 API 操作日志

3. **网络安全**：
- 使用 HTTPS 通信
- 配置防火墙规则
- 定期更新依赖包

## 故障排查

### 常见问题

#### 1. Docker 服务未运行

```bash
# 检查 Docker 服务
sudo systemctl status docker

# 启动 Docker 服务
sudo systemctl start docker
```

#### 2. 端口被占用

```bash
# 查看端口占用
netstat -tlnp | grep 9001

# 停占用进程
sudo kill -9 <PID>
```

#### 3. 权限问题

```bash
# 检查 Docker 权限
docker ps

# 如果权限不足，将用户加入 docker 组
sudo usermod -aG docker $USER
```

### 调试技巧

```bash
# 启用详细日志
./receiver --debug

# 查看 Docker 日志
docker logs <container_id>

# 查看任务详情
curl http://localhost:9001/api/v1/tasks/{task_id} | jq
```

## 版本信息

- **版本**: 1.0.0
- **Go 版本**: 1.21
- **Docker 版本**: 20.10+
- **支持平台**: Linux x86_64

## 许可证

MIT License