# GPU Worker 架构设计（纯 Shell 方案）

> 基于纯 Shell + curl + nvidia-smi 的轻量级 GPU Worker 管理架构

---

## 目录

- [1. 架构概述](#1-架构概述)
- [2. 核心概念](#2-核心概念)
- [3. Agent 设计](#3-agent-设计)
- [4. 数据库设计](#4-数据库设计)
- [5. API 设计](#5-api-设计)
- [6. 心跳机制](#6-心跳机制)
- [7. 注册流程](#7-注册流程)
- [8. 状态管理](#8-状态管理)
- [9. 占卡机制](#9-占卡机制)
- [10. 后端代码结构](#10-后端代码结构)
- [11. 部署方案](#11-部署方案)
- [12. 实施计划](#12-实施计划)

---

## 1. 架构概述

### 1.1 设计原则

| 原则 | 说明 |
|------|------|
| **以卡为单位** | Worker 是逻辑概念，由多张卡组成（可跨机器） |
| **超轻量 Agent** | 纯 Shell 实现，无 Python 依赖，< 50KB |
| **快速注册** | 并行注册，100 卡 < 30 秒完成 |
| **自动占卡** | Agent 启动即占用 95% 显存 |
| **实时心跳** | 30 秒心跳，90 秒超时检测 |
| **动态扩容** | 支持用同一 Token 追加新卡 |

### 1.2 整体架构

```
┌─────────────────────────────────────────────────────────────────┐
│                        前端层                                   │
│  Web UI (React) │ CLI │ OpenAI API                             │
└────────────────────────────┬────────────────────────────────────┘
                             │ HTTPS
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                     Server (控制平面)                           │
├─────────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │  Worker API  │  │   GPU API    │  │Health Check  │          │
│  │              │  │              │  │              │          │
│  │ • 创建Worker │  │ • GPU注册    │  │ • 心跳接收   │          │
│  │ • 查询状态   │  │ • 状态更新   │  │ • 超时检测   │          │
│  │ • 删除Worker │  │ • 告警检查   │  │ • 状态同步   │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
│                                                                   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │ PostgreSQL   │  │    Redis     │  │  Prometheus  │          │
│  │              │  │              │  │              │          │
│  │ • workers    │  │ • 状态缓存   │  │ • 监控指标   │          │
│  │ • gpu_devices│  │ • Pub/Sub    │  │ • 告警规则   │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
└────────────────────────────┬────────────────────────────────────┘
                             │ HTTPS (心跳/注册)
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                  GPU Agent (每张卡一个)                         │
├─────────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │ occupy_gpu   │  │ tm_agent.sh  │  │ nvidia-smi   │          │
│  │ (CUDA C++)   │  │ (Bash)       │  │ (Driver)     │          │
│  │              │  │              │  │              │          │
│  │ • 占用显存   │  │ • 注册GPU    │  │ • 采集状态   │          │
│  │ • 保持运行   │  │ • 发送心跳   │  │ • 温度监控   │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
│                                                                   │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │                  GPU 硬件                               │    │
│  │  GPU-0 │ GPU-1 │ GPU-2 │ GPU-3 │ ...                   │    │
│  └─────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
```

### 1.3 Worker 与 GPU 的关系

**传统方案（错误）：**
```
1台物理机器 = 1个Worker
├── 机器1 (Worker-1)
│   ├── GPU-0
│   ├── GPU-1
│   └── GPU-2
```

**本方案（正确）：**
```
1个Worker = 多张卡的集合（可跨机器）

Worker-01 (worker-gpu-pool)
├── 机器1: GPU-2, GPU-3, GPU-4
├── 机器2: GPU-6, GPU-7, GPU-8
└── 机器3: GPU-0, GPU-1
```

---

## 2. 核心概念

### 2.1 概念定义

| 概念 | 说明 | 示例 |
|------|------|------|
| **Worker** | 逻辑概念，是一张或多张 GPU 卡的集合 | `worker-gpu-pool-01` |
| **GPU 卡** | 物理实体，通过 Token 注册到 Worker | `uuid: GPU-xxx` |
| **Agent** | 每张卡上运行的轻量级进程 | `tm_agent.sh (PID: 1234)` |
| **Token** | Worker 的注册凭证，可复用 | `tm_worker_abc123xyz789` |
| **集群** | Worker 的逻辑分组 | `production-cluster` |

### 2.2 设计优势

```
┌─────────────────────────────────────────────────────────────┐
│  优势1: 超轻量                                              │
│  ───────────────────────────────────────────────────────── │
│  • Agent 体积: < 50KB (对比 Python 方案 ~50MB)             │
│  • 启动时间: < 0.5秒 (对比 Python 方案 ~2-3秒)              │
│  • 内存占用: < 5MB (对比 Python 方案 ~50MB)                │
│  • 依赖: bash + curl + nvidia-smi (系统自带)               │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│  优势2: 灵活扩展                                            │
│  ───────────────────────────────────────────────────────── │
│  • 一台机器的卡可以拆分到多个 Worker                         │
│  • 跨机器的卡可以组成一个 Worker                             │
│  • 支持动态添加/删除 GPU                                    │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│  优势3: 快速部署                                            │
│  ───────────────────────────────────────────────────────── │
│  • 一键安装: curl | bash                                    │
│  • 并行注册: 100 卡 < 30 秒                                 │
│  • 自动占卡: 启动即占 95% 显存                              │
└─────────────────────────────────────────────────────────────┘
```

---

## 3. Agent 设计

### 3.1 Agent 组成

```
TokenMachine Agent (纯 Shell)
├── occupy_gpu          # CUDA C++ 编译的二进制 (5KB)
│   ├── 占用 95% 显存
│   ├── 保持运行（防止显存回收）
│   └── 支持 SIGTERM 优雅退出
│
└── tm_agent.sh         # Bash 脚本 (10KB)
    ├── GPU 信息采集（nvidia-smi）
    ├── 注册到 Server
    ├── 心跳发送（每 30 秒）
    ├── 状态监控
    └── 日志记录
```

### 3.2 occupy_gpu.cu

```cpp
// CUDA C++ 实现的占卡程序
#include <cuda_runtime.h>
#include <signal.h>
#include <unistd.h>

void* g_gpu_ptr = nullptr;

void cleanup(int signum) {
    if (g_gpu_ptr) {
        cudaFree(g_gpu_ptr);
    }
    exit(0);
}

int main(int argc, char** argv) {
    int gpu_id = atoi(argv[1]);
    float occupy_ratio = argc > 2 ? atof(argv[2]) : 0.95f;

    signal(SIGTERM, cleanup);
    signal(SIGINT, cleanup);

    cudaSetDevice(gpu_id);

    size_t free_mem, total_mem;
    cudaMemGetInfo(&free_mem, &total_mem);

    size_t occupy_size = (size_t)(total_mem * occupy_ratio);
    cudaMalloc(&g_gpu_ptr, occupy_size);
    cudaMemset(g_gpu_ptr, 0, occupy_size);

    printf("OCCUPIED:%d\n", gpu_id);
    fflush(stdout);

    // 保持运行，定期刷新
    while (true) {
        sleep(30);
        cudaMemset(g_gpu_ptr, 0, 1024);  // 防止被系统回收
    }

    return 0;
}
```

**编译：**
```bash
nvcc -O3 -o occupy_gpu occupy_gpu.cu
strip occupy_gpu  # 去除符号，体积 < 5KB
```

### 3.3 tm_agent.sh 核心逻辑

```bash
#!/bin/bash
# tm_agent.sh - TokenMachine GPU Agent

# ============================================================================
# 配置
# ============================================================================
TM_TOKEN="${TM_TOKEN:?Missing TM_TOKEN}"
TM_GPU_ID="${TM_GPU_ID:?Missing TM_GPU_ID}"
TM_SERVER_URL="${TM_SERVER_URL:-https://api.tokenmachine.io}"
TM_AGENT_PORT="${TM_AGENT_PORT:-$((9000 + TM_GPU_ID))}"
TM_HEARTBEAT_INTERVAL="${TM_HEARTBEAT_INTERVAL:-30}"

# 工作目录
TM_WORK_DIR="/var/run/tokenmachine"
OCCUPY_BIN="./occupy_gpu"

# ============================================================================
# 核心功能
# ============================================================================

# 1. 获取 GPU 信息（nvidia-smi）
get_gpu_info() {
    nvidia-smi -i "$TM_GPU_ID" \
        --query-gpu=name,uuid,memory.total,pci.bus_id \
        --format=csv,noheader,nounits
}

# 2. 启动占卡进程
start_occupy() {
    "$OCCUPY_BIN" "$TM_GPU_ID" 0.95 > "$TM_WORK_DIR/occupy_${TM_GPU_ID}.log" 2>&1 &
    local pid=$!
    echo "$pid" > "$TM_WORK_DIR/occupy_${TM_GPU_ID}.pid"
    sleep 2
}

# 3. 注册到 Server
register_gpu() {
    local gpu_info=$(get_gpu_info)
    # 解析 CSV，构造 JSON
    # POST /api/v1/workers/register-gpu
}

# 4. 发送心跳
send_heartbeat() {
    local status=$(nvidia-smi -i "$TM_GPU_ID" \
        --query-gpu=utilization.gpu,memory.used,temperature.gpu \
        --format=csv,noheader,nounits)

    # 构造 JSON，POST 到 /api/v1/gpus/heartbeat
}

# 5. 心跳循环
heartbeat_loop() {
    while true; do
        sleep "$TM_HEARTBEAT_INTERVAL"
        send_heartbeat
    done
}

# 主流程
main() {
    start_occupy
    register_gpu
    heartbeat_loop
}

main "$@"
```

### 3.4 一键安装脚本

```bash
#!/bin/bash
# install.sh

set -e

TM_TOKEN="${TM_TOKEN:?Missing TM_TOKEN}"
TM_GPU_IDS="${TM_GPU_IDS:?Missing TM_GPU_IDS}"
TM_VERSION="v1.0.0"
DOWNLOAD_BASE="https://releases.tokenmachine.io/agent/$TM_VERSION"

# 下载
mkdir -p /tmp/tokenmachine
cd /tmp/tokenmachine

curl -sSL -o occupy_gpu "$DOWNLOAD_BASE/occupy_gpu"
curl -sSL -o tm_agent.sh "$DOWNLOAD_BASE/tm_agent.sh"
chmod +x occupy_gpu tm_agent.sh

# 安装
sudo mkdir -p /opt/tokenmachine
sudo cp occupy_gpu tm_agent.sh /opt/tokenmachine/

# 启动
IFS=',' read -ra GPU_ID_ARRAY <<< "$TM_GPU_IDS"
for gpu_id in "${GPU_ID_ARRAY[@]}"; do
    TM_TOKEN="$TM_TOKEN" TM_GPU_ID="$gpu_id" \
        nohup /opt/tokenmachine/tm_agent.sh \
        > /var/log/tm_agent_${gpu_id}.log 2>&1 &
done

echo "Installation completed!"
```

### 3.5 使用方式

```bash
# 方式1: 一键安装（推荐）
export TM_TOKEN="tm_worker_abc123xyz789"
export TM_GPU_IDS="0,1,2,3"
curl -sfL https://get.tokenmachine.io | bash -

# 方式2: 手动运行
wget https://releases.tokenmachine.io/agent/v1.0.0/occupy_gpu
wget https://releases.tokenmachine.io/agent/v1.0.0/tm_agent.sh
chmod +x occupy_gpu tm_agent.sh

export TM_TOKEN="tm_worker_abc123xyz789"
export TM_GPU_ID="0"
./tm_agent.sh
```

---

## 4. 数据库设计

### 4.1 ER 图

```
┌─────────────┐       1:N       ┌─────────────┐
│  Workers    │──────────────>│ GPU_Devices │
├─────────────┤                ├─────────────┤
│ id (PK)     │                │ id (PK)     │
│ name        │                │ worker_id(FK)│
│ cluster_id  │                │ uuid        │
│ status      │                │ name        │
│ token_hash  │                │ ip          │ ← 物理机器IP
│ labels(JSON)│                │ port        │ ← Agent端口
│ gpu_count   │                │ index       │
│ ...         │                │ memory_total│
└─────────────┘                │ state       │
                                 │ updated_at  │ ← 心跳时间
                                 └─────────────┘
```

### 4.2 workers 表

```sql
CREATE TABLE workers (
    id SERIAL PRIMARY KEY,
    cluster_id INTEGER REFERENCES clusters(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    status VARCHAR(50) DEFAULT 'registering',

    -- 注册凭证
    token_hash VARCHAR(255) UNIQUE NOT NULL,

    -- 配置
    labels JSON,              -- {"gpu-type": "a100", "zone": "prod"}
    expected_gpu_count INTEGER DEFAULT 0,

    -- 统计
    gpu_count INTEGER DEFAULT 0,

    -- 心跳
    last_heartbeat_at TIMESTAMP,

    -- 时间戳
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),

    -- 唯一约束
    UNIQUE (cluster_id, name)
);

CREATE INDEX idx_workers_status ON workers(status);
CREATE INDEX idx_workers_cluster ON workers(cluster_id);
CREATE INDEX idx_workers_token ON workers(token_hash);
```

### 4.3 gpu_devices 表

```sql
CREATE TABLE gpu_devices (
    id BIGSERIAL PRIMARY KEY,
    worker_id INTEGER REFERENCES workers(id) ON DELETE CASCADE,

    -- GPU 标识
    uuid VARCHAR(255) NOT NULL,
    name VARCHAR(255) NOT NULL,
    vendor VARCHAR(50),
    index INTEGER NOT NULL,

    -- 位置信息
    ip VARCHAR(45) NOT NULL,      -- 物理机器IP
    port INTEGER NOT NULL,         -- Agent端口
    hostname VARCHAR(255),
    pci_bus VARCHAR(100),

    -- 硬件信息
    core_total INTEGER,
    memory_total BIGINT NOT NULL,

    -- 实时状态（心跳更新）
    memory_used BIGINT DEFAULT 0,
    memory_allocated BIGINT DEFAULT 0,
    memory_utilization_rate DECIMAL(5,2) DEFAULT 0.0,
    core_utilization_rate DECIMAL(5,2) DEFAULT 0.0,
    temperature DECIMAL(5,2),

    -- 状态
    state VARCHAR(50) DEFAULT 'available',

    -- 扩展信息
    status_json JSON,

    -- 时间戳
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),

    -- 唯一约束
    UNIQUE (worker_id, uuid)
);

CREATE INDEX idx_gpu_worker ON gpu_devices(worker_id);
CREATE INDEX idx_gpu_uuid ON gpu_devices(uuid);
CREATE INDEX idx_gpu_state ON gpu_devices(state);
CREATE INDEX idx_gpu_updated ON gpu_devices(updated_at);
```

### 4.4 数据模型

```python
# backend/models/database.py

class WorkerStatus(str, Enum):
    """Worker 状态"""
    CREATING = "creating"
    REGISTERING = "registering"
    READY = "ready"
    DEGRADED = "degraded"
    OFFLINE = "offline"
    MAINTENANCE = "maintenance"


class Worker(Base):
    """Worker 模型"""
    __tablename__ = "workers"

    id = Column(Integer, primary_key=True)
    cluster_id = Column(Integer, ForeignKey("clusters.id"))
    name = Column(String(255), nullable=False)
    status = Column(SQLEnum(WorkerStatus), default=WorkerStatus.REGISTERING)

    # 注册凭证
    token_hash = Column(String(255), unique=True, nullable=False)

    # 配置
    labels = Column(JSON)
    expected_gpu_count = Column(Integer, default=0)

    # 统计
    gpu_count = Column(Integer, default=0)

    # 心跳
    last_heartbeat_at = Column(TIMESTAMP)

    created_at = Column(TIMESTAMP, default=func.now())
    updated_at = Column(TIMESTAMP, default=func.now(), onupdate=func.now())

    # 关系
    gpus = relationship("GPUDevice", back_populates="worker")


class GPUDeviceState(str, Enum):
    """GPU 状态"""
    AVAILABLE = "available"
    IN_USE = "in_use"
    ERROR = "error"


class GPUDevice(Base):
    """GPU 设备模型"""
    __tablename__ = "gpu_devices"

    id = Column(BigInteger, primary_key=True)
    worker_id = Column(Integer, ForeignKey("workers.id"))

    # 标识
    uuid = Column(String(255), nullable=False)
    name = Column(String(255), nullable=False)
    vendor = Column(String(50))
    index = Column(Integer, nullable=False)

    # 位置
    ip = Column(String(45), nullable=False)
    port = Column(Integer, nullable=False)
    hostname = Column(String(255))
    pci_bus = Column(String(100))

    # 硬件
    core_total = Column(Integer)
    memory_total = Column(BigInteger, nullable=False)

    # 实时状态
    memory_used = Column(BigInteger, default=0)
    memory_allocated = Column(BigInteger, default=0)
    memory_utilization_rate = Column(DECIMAL(5,2), default=0.0)
    core_utilization_rate = Column(DECIMAL(5,2), default=0.0)
    temperature = Column(DECIMAL(5,2))

    state = Column(SQLEnum(GPUDeviceState), default=GPUDeviceState.AVAILABLE)

    status_json = Column(JSON)

    created_at = Column(TIMESTAMP, default=func.now())
    updated_at = Column(TIMESTAMP, default=func.now(), onupdate=func.now())

    # 关系
    worker = relationship("Worker", back_populates="gpus")
```

---

## 5. API 设计

### 5.1 Worker 管理 API

#### 5.1.1 创建 Worker

```http
POST /api/v1/workers
Authorization: Bearer {admin_token}
Content-Type: application/json

{
  "name": "worker-gpu-pool-01",
  "cluster_id": 1,
  "labels": {
    "gpu-type": "a100",
    "zone": "prod"
  },
  "expected_gpu_count": 6
}

Response:
{
  "id": 5,
  "name": "worker-gpu-pool-01",
  "status": "registering",
  "register_token": "tm_worker_abc123xyz789",
  "install_command": "TM_TOKEN=tm_worker_abc123xyz789 TM_GPU_ID=0 curl -sfL https://get.tokenmachine.io | bash -",
  "expected_gpu_count": 6,
  "current_gpu_count": 0,
  "created_at": "2025-01-21T10:30:00Z"
}
```

#### 5.1.2 查询 Worker 列表

```http
GET /api/v1/workers
Authorization: Bearer {admin_token}

Response:
{
  "items": [
    {
      "id": 5,
      "name": "worker-gpu-pool-01",
      "status": "ready",
      "gpu_count": 6,
      "gpus": [
        {
          "id": 123,
          "uuid": "GPU-xxx",
          "name": "NVIDIA A100-SXM4-80GB",
          "ip": "192.168.1.101",
          "index": 2,
          "state": "in_use"
        }
      ]
    }
  ]
}
```

#### 5.1.3 查询 Worker 详情

```http
GET /api/v1/workers/{worker_id}
Authorization: Bearer {admin_token}

Response:
{
  "id": 5,
  "name": "worker-gpu-pool-01",
  "cluster_id": 1,
  "status": "ready",
  "gpu_count": 6,
  "expected_gpu_count": 6,
  "labels": {...},
  "gpus": [...],
  "last_heartbeat_at": "2025-01-21T10:35:00Z",
  "created_at": "2025-01-21T10:30:00Z"
}
```

#### 5.1.4 获取添加 GPU 的 Token

```http
POST /api/v1/workers/{worker_id}/add-gpu
Authorization: Bearer {admin_token}

Response:
{
  "register_token": "tm_worker_abc123xyz789",
  "install_command": "TM_TOKEN=tm_worker_abc123xyz789 TM_GPU_ID=3 curl -sfL https://get.tokenmachine.io | bash -",
  "message": "Use this token to add more GPUs to worker"
}
```

#### 5.1.5 删除 Worker

```http
DELETE /api/v1/workers/{worker_id}
Authorization: Bearer {admin_token}

Response:
{
  "success": true,
  "message": "Worker deleted successfully"
}
```

### 5.2 GPU 注册 API

#### 5.2.1 GPU 注册（由 Agent 调用）

```http
POST /api/v1/workers/register-gpu
Authorization: Bearer {register_token}
Content-Type: application/json

{
  "gpu_uuid": "GPU-12345678-1234-1234-1234-123456789abc",
  "gpu_index": 2,
  "ip": "192.168.1.101",
  "port": 9002,
  "memory_total": 85899345920,
  "memory_allocated": 81604278624,
  "memory_utilization_rate": 0.0,
  "temperature": 35.0,
  "agent_pid": 12345,
  "vllm_pid": null,
  "timestamp": "2025-01-21T10:31:00Z",
  "state": "in_use",
  "extra": {
    "name": "NVIDIA A100-SXM4-80GB",
    "hostname": "gpu-server-01",
    "pci_bus": "0000:07:00.0"
  }
}

Response:
{
  "success": true,
  "gpu_device_id": 123,
  "worker_id": 5,
  "worker_name": "worker-gpu-pool-01",
  "current_gpu_count": 1,
  "expected_gpu_count": 6,
  "worker_status": "registering"
}
```

### 5.3 心跳 API

#### 5.3.1 单 GPU 心跳

```http
POST /api/v1/gpus/heartbeat
Authorization: Bearer {register_token}
Content-Type: application/json

{
  "gpu_uuid": "GPU-xxx",
  "gpu_index": 2,
  "ip": "192.168.1.101",
  "port": 9002,
  "memory_total": 85899345920,
  "memory_used": 42949672960,
  "memory_allocated": 81604278624,
  "memory_utilization_rate": 0.5,
  "core_utilization_rate": 0.85,
  "temperature": 65.0,
  "agent_pid": 12345,
  "vllm_pid": null,
  "timestamp": "2025-01-21T10:35:00Z",
  "state": "in_use",
  "extra": null
}

Response:
{
  "success": true,
  "message": "Heartbeat received"
}
```

#### 5.3.2 批量心跳（优化）

```http
POST /api/v1/gpus/heartbeat/batch
Authorization: Bearer {register_token}
Content-Type: application/json

{
  "heartbeats": [
    { "gpu_uuid": "GPU-xxx", ... },
    { "gpu_uuid": "GPU-yyy", ... },
    { "gpu_uuid": "GPU-zzz", ... }
  ]
}

Response:
{
  "success": true,
  "updated_count": 3
}
```

---

## 6. 心跳机制

### 6.1 心跳流程

```
时间轴（每30秒一个周期）

0s   Agent 采集 GPU 状态
     ├─ nvidia-smi --query-gpu=utilization.gpu
     ├─ nvidia-smi --query-gpu=memory.used
     └─ nvidia-smi --query-gpu=temperature.gpu
     ↓
1s   构造 JSON（Shell 脚本）
     ↓
2s   curl POST 到 /api/v1/gpus/heartbeat
     ↓
3s   Server 接收并更新数据库
     ├─ UPDATE gpu_devices SET
     │   memory_used = ...,
     │   temperature = ...,
     │   updated_at = NOW()
     └─ 写入 Redis 缓存
     ↓
4s   Server 检查告警规则
     ├─ 温度 > 85°C → 告警
     ├─ 显存泄漏 → 告警
     └─ 其他异常 → 记录日志
     ↓
5s   响应 Agent (success)
     ↓
30s  下一轮心跳...
```

### 6.2 心跳超时检测

```python
# backend/tasks/health_check.py

class GPUHealthChecker:
    """GPU 健康检查器"""

    def __init__(self, heartbeat_timeout: int = 90):
        self.heartbeat_timeout = heartbeat_timeout

    async def check_all_gpus(self):
        """检查所有 GPU 健康状态"""
        db: Session = next(get_db())

        # 获取所有在用 GPU
        gpus = db.query(GPUDevice).filter(
            GPUDevice.state == GPUDeviceState.IN_USE
        ).all()

        offline_gpus = []
        offline_workers = set()

        for gpu in gpus:
            # 检查最后更新时间
            if gpu.updated_at:
                elapsed = datetime.now() - gpu.updated_at

                if elapsed.total_seconds() > self.heartbeat_timeout:
                    # 标记为 ERROR
                    gpu.state = GPUDeviceState.ERROR
                    offline_gpus.append(gpu)
                    offline_workers.add(gpu.worker_id)

        if offline_gpus:
            db.commit()

            # 更新 Worker 状态
            for worker_id in offline_workers:
                self._handle_worker_degraded(db, worker_id)
```

### 6.3 心跳优化

| 优化点 | 方案 | 效果 |
|--------|------|------|
| **批量心跳** | 一台机器的多张卡批量发送 | 减少 80% HTTP 请求 |
| **UPSERT** | 使用 PostgreSQL ON CONFLICT | 减少 50% 查询 |
| **Redis 缓存** | 实时状态写入 Redis | 查询速度提升 10x |
| **连接复用** | HTTP Keep-Alive | 减少 TCP 握手开销 |

---

## 7. 注册流程

### 7.1 Worker 注册时序图

```
┌─────────┐      ┌──────────┐      ┌─────────┐      ┌──────────┐
│  前端   │      │  Server  │      │  Agent  │      │  GPU硬件 │
└────┬────┘      └─────┬────┘      └────┬────┘      └─────┬────┘
     │                 │                │                 │
     │ 1. 创建Worker   │                │                 │
     │────────────────>│                │                 │
     │                 │                │                 │
     │ 2. 返回Token    │                │                 │
     │<────────────────│                │                 │
     │                 │                │                 │
     │ 3. 显示安装命令 │                │                 │
     │──────────────────│                │                 │
     │                 │                │                 │
     │ 4. 启动Agent    │                │                 │
     │────────────────────────────────>│                 │
     │                 │                │                 │
     │                 │                │ 5. 占卡         │
     │                 │                │────────────────>│
     │                 │                │                 │
     │                 │                │ 6. 采集GPU信息   │
     │                 │                │<────────────────>│
     │                 │                │                 │
     │                 │ 7. 注册GPU     │                 │
     │                 │<───────────────│                 │
     │                 │                │                 │
     │                 │ 8. 返回成功    │                 │
     │                 │───────────────>│                 │
     │                 │                │                 │
     │ 9. 开始心跳     │                │                 │
     │                 │<───────────────│                 │
     │                 │───────────────>│                 │
     │                 │                │                 │
     │ 10. 轮询查询状态 │                │                 │
     │────────────────>│                │                 │
     │<────────────────│                │                 │
     │                 │                │                 │
     │ 11. 状态: ready │                │                 │
     │<────────────────│                │                 │
```

### 7.2 并行注册示例

```bash
# 机器1：并行启动 3 张卡的 Agent
export TM_TOKEN="tm_worker_abc123xyz789"

for gpu_id in 2 3 4; do
  TM_GPU_ID=$gpu_id TM_AGENT_PORT=$((9000 + $gpu_id)) \
    nohup /opt/tokenmachine/tm_agent.sh &
done

# 机器2：并行启动 3 张卡的 Agent
for gpu_id in 6 7 8; do
  TM_GPU_ID=$gpu_id TM_AGENT_PORT=$((9000 + $gpu_id)) \
    nohup /opt/tokenmachine/tm_agent.sh &
done

# 总耗时：~10 秒（6 张卡）
```

---

## 8. 状态管理

### 8.1 Worker 状态转换

```
┌───────────┐
│ CREATING  │  ← 创建 Worker 记录
└─────┬─────┘
      │
      ▼
┌───────────┐
│REGISTERING│  ← 等待 GPU 注册 (gpu_count = 0)
└─────┬─────┘
      │
      │ GPU 陆续注册
      ▼
┌───────────┐
│REGISTERING│  ← 部分 GPU 已注册 (gpu_count = 3/6)
└─────┬─────┘
      │
      │ 达到 expected_gpu_count
      ▼
┌───────────┐
│   READY   │  ← 所有 GPU 就绪 (gpu_count = 6/6)
└─────┬─────┘
      │
      │ 某 GPU 掉线
      ▼
┌───────────┐
│ DEGRADED  │  ← 部分 GPU 离线 (1 张卡掉线)
└─────┬─────┘
      │
      │ 所有 GPU 离线
      ▼
┌───────────┐
│  OFFLINE  │
└───────────┘
```

### 8.2 GPU 状态转换

```
┌───────────┐
│AVAILABLE  │  ← 初始状态
└─────┬─────┘
      │
      │ Agent 注册成功
      ▼
┌───────────┐
│  IN_USE   │  ← 占卡成功，心跳正常
└─────┬─────┘
      │
      │ 心跳超时
      ▼
┌───────────┐
│   ERROR   │  ← 离线
└───────────┘
```

### 8.3 状态同步

```python
# backend/services/worker_sync.py

class WorkerSyncService:
    """Worker 状态同步服务"""

    async def sync_gpu_registered(self, gpu_id: int):
        """GPU 注册后同步 Worker 状态"""
        gpu = db.query(GPUDevice).get(gpu_id)
        worker = gpu.worker

        # 更新 GPU 计数
        worker.gpu_count += 1

        # 检查是否达到预期数量
        if worker.expected_gpu_count > 0:
            if worker.gpu_count >= worker.expected_gpu_count:
                worker.status = WorkerStatus.READY

        # 发布事件
        await redis.publish(f"worker:{worker.id}", {
            "type": "gpu_registered",
            "gpu_id": gpu_id,
            "current_count": worker.gpu_count
        })

        db.commit()

    async def sync_gpu_offline(self, gpu_id: int):
        """GPU 离线后同步 Worker 状态"""
        gpu = db.query(GPUDevice).get(gpu_id)
        worker = gpu.worker

        # 统计离线 GPU 数量
        offline_count = db.query(GPUDevice).filter(
            GPUDevice.worker_id == worker.id,
            GPUDevice.state == GPUDeviceState.ERROR
        ).count()

        total_count = worker.gpu_count

        # 更新 Worker 状态
        if offline_count == total_count:
            worker.status = WorkerStatus.OFFLINE
        elif worker.status == WorkerStatus.READY:
            worker.status = WorkerStatus.DEGRADED

        db.commit()
```

---

## 9. 占卡机制

### 9.1 占卡原理

```
GPU 显存布局（80GB A100）

┌─────────────────────────────────────────┐
│         Total: 80 GB                    │
├─────────────────────────────────────────┤
│                                         │
│  ┌───────────────────────────────────┐ │
│  │  occupy_gpu 占用: 76 GB (95%)     │ │
│  │  • CUDA cudaMalloc               │ │
│  │  • cudaMemset 填充 0             │ │
│  │  • 定期刷新防止回收               │ │
│  └───────────────────────────────────┘ │
│                                         │
│  ┌──────────────┐  ┌─────────────────┐ │
│  │  系统预留:   │  │  可用: ~4 GB    │ │
│  │  ~200 MB     │  │  (给其他进程)   │ │
│  └──────────────┘  └─────────────────┘ │
│                                         │
└─────────────────────────────────────────┘

效果：
✓ 防止其他程序占用此 GPU
✓ 确保 vLLM 启动时有足够显存
✓ 可随时释放（SIGTERM）
```

### 9.2 占卡代码（occupy_gpu.cu）

```cpp
#include <cuda_runtime.h>
#include <signal.h>
#include <unistd.h>
#include <iostream>

void* g_gpu_ptr = nullptr;
int g_gpu_id = 0;

void cleanup(int signum) {
    std::cout << "Cleaning up GPU " << g_gpu_id << std::endl;
    if (g_gpu_ptr) {
        cudaFree(g_gpu_ptr);
        std::cout << "GPU memory freed" << std::endl;
    }
    exit(0);
}

int main(int argc, char** argv) {
    if (argc < 2) {
        std::cerr << "Usage: " << argv[0] << " <gpu_id> [occupy_ratio=0.95]" << std::endl;
        return 1;
    }

    g_gpu_id = atoi(argv[1]);
    float occupy_ratio = argc > 2 ? atof(argv[2]) : 0.95f;

    // 设置信号处理
    signal(SIGTERM, cleanup);
    signal(SIGINT, cleanup);

    // 设置 GPU
    cudaSetDevice(g_gpu_id);

    // 获取显存信息
    size_t free_mem, total_mem;
    cudaMemGetInfo(&free_mem, &total_mem);

    // 计算占用大小（留 5% 给系统）
    size_t occupy_size = (size_t)(total_mem * occupy_ratio);

    std::cout << "GPU " << g_gpu_id << ": "
              << "Total: " << total_mem / 1024.0 / 1024.0 / 1024.0 << " GB, "
              << "Occupy: " << occupy_size / 1024.0 / 1024.0 / 1024.0 << " GB ("
              << (occupy_ratio * 100) << "%)" << std::endl;

    // 分配显存
    cudaError_t err = cudaMalloc(&g_gpu_ptr, occupy_size);
    if (err != cudaSuccess) {
        std::cerr << "cudaMalloc failed: " << cudaGetErrorString(err) << std::endl;
        return 1;
    }

    // 用 0 填充（确保物理分配）
    cudaMemset(g_gpu_ptr, 0, occupy_size);

    std::cout << "GPU " << g_gpu_id << " occupied successfully, PID: " << getpid() << std::endl;

    // 保持运行，定期刷新（防止被系统回收）
    int counter = 0;
    while (true) {
        sleep(30);

        // 定期刷新显存
        cudaMemset(g_gpu_ptr, counter++ % 256, 1024);
    }

    return 0;
}
```

### 9.3 编译和打包

```bash
# 编译
nvcc -O3 -o occupy_gpu occupy_gpu.cu

# 去除符号（减小体积）
strip occupy_gpu

# 打包
tar czf tokenmachine-agent-v1.0.0.tar.gz \
  occupy_gpu \
  tm_agent.sh \
  install.sh \
  README.md

# 发布到 CDN
curl -X POST https://releases.tokenmachine.io/upload \
  --data-binary @tokenmachine-agent-v1.0.0.tar.gz
```

---

## 10. 后端代码结构

### 10.1 目录结构

```
backend/
├── api/
│   ├── v1/
│   │   ├── workers.py         # Worker API
│   │   ├── gpus.py            # GPU API
│   │   └── clusters.py        # Cluster API
│   └── deps.py                # 依赖注入
│
├── core/
│   ├── config.py              # 配置管理
│   ├── database.py            # 数据库连接
│   └── security.py            # Token 管理
│
├── models/
│   ├── database.py            # SQLAlchemy 模型
│   └── schemas.py             # Pydantic 模型
│
├── services/
│   ├── worker_service.py      # Worker 服务
│   ├── gpu_service.py         # GPU 服务
│   └── health_check.py        # 健康检查
│
├── tasks/
│   ├── heartbeat_monitor.py   # 心跳监控
│   └── alert_manager.py       # 告警管理
│
└── main.py                    # 应用入口
```

### 10.2 核心 API 实现

#### Worker 创建 API

```python
# backend/api/v1/workers.py

@router.post("/workers")
async def create_worker(
    request: WorkerCreateRequest,
    db: Session = Depends(get_db),
    admin_user: User = Depends(require_admin)
):
    """创建 Worker"""

    # 1. 生成 Token
    register_token = generate_worker_token()
    token_hash = hash_token(register_token)

    # 2. 创建 Worker 记录
    worker = Worker(
        name=request.name,
        cluster_id=request.cluster_id,
        status=WorkerStatus.REGISTERING,
        token_hash=token_hash,
        labels=request.labels,
        expected_gpu_count=request.expected_gpu_count,
        gpu_count=0
    )
    db.add(worker)
    db.commit()
    db.refresh(worker)

    # 3. 构造安装命令
    install_command = (
        f"TM_TOKEN={register_token} "
        f"TM_GPU_ID=<GPU_ID> "
        f"curl -sfL https://get.tokenmachine.io | bash -"
    )

    return {
        "id": worker.id,
        "name": worker.name,
        "status": worker.status,
        "register_token": register_token,  # 仅返回一次
        "install_command": install_command,
        "expected_gpu_count": worker.expected_gpu_count,
        "current_gpu_count": 0,
        "created_at": worker.created_at
    }
```

#### GPU 注册 API

```python
# backend/api/v1/gpus.py

@router.post("/workers/register-gpu")
async def register_gpu(
    request: GPURegisterRequest,
    db: Session = Depends(get_db)
):
    """GPU 注册（由 Agent 调用）"""

    # 1. 验证 Token
    worker = db.query(Worker).filter(
        Worker.token_hash == hash_token(request.token)
    ).first()

    if not worker:
        raise HTTPException(401, "Invalid token")

    # 2. 检查 GPU 是否已注册（通过 UUID 去重）
    existing_gpu = db.query(GPUDevice).filter(
        GPUDevice.worker_id == worker.id,
        GPUDevice.uuid == request.gpu.uuid
    ).first()

    if existing_gpu:
        return {"success": True, "message": "GPU already registered"}

    # 3. 创建 GPU 记录
    gpu_device = GPUDevice(
        worker_id=worker.id,
        uuid=request.gpu.uuid,
        name=request.gpu.extra.get("name", ""),
        vendor=request.gpu.extra.get("vendor", "nvidia"),
        index=request.gpu.gpu_index,
        ip=request.gpu.ip,
        port=request.gpu.port,
        hostname=request.gpu.extra.get("hostname", ""),
        pci_bus=request.gpu.extra.get("pci_bus", ""),
        core_total=request.gpu.extra.get("core_total", 0),
        memory_total=request.gpu.memory_total,
        memory_allocated=request.gpu.memory_allocated,
        memory_utilization_rate=request.gpu.memory_utilization_rate,
        temperature=request.gpu.temperature,
        state=GPUDeviceState.IN_USE,
        status_json={
            "agent_pid": request.gpu.agent_pid,
            "vllm_pid": request.gpu.vllm_pid,
            "registered_at": datetime.now().isoformat()
        }
    )

    db.add(gpu_device)

    # 4. 更新 Worker 状态
    worker.gpu_count += 1

    if worker.expected_gpu_count > 0:
        if worker.gpu_count >= worker.expected_gpu_count:
            worker.status = WorkerStatus.READY

    worker.last_heartbeat_at = datetime.now()

    db.commit()
    db.refresh(gpu_device)

    # 5. 发布事件
    await redis.publish(f"worker:{worker.id}", {
        "type": "gpu_registered",
        "gpu_id": gpu_device.id,
        "current_count": worker.gpu_count
    })

    return {
        "success": True,
        "gpu_device_id": gpu_device.id,
        "worker_id": worker.id,
        "worker_name": worker.name,
        "current_gpu_count": worker.gpu_count,
        "expected_gpu_count": worker.expected_gpu_count,
        "worker_status": worker.status
    }
```

#### 心跳 API

```python
@router.post("/gpus/heartbeat")
async def gpu_heartbeat(
    request: GPUHeartbeatRequest,
    db: Session = Depends(get_db)
):
    """单 GPU 心跳"""

    # 1. 查找 GPU
    gpu = db.query(GPUDevice).filter(
        GPUDevice.uuid == request.gpu_uuid
    ).first()

    if not gpu:
        raise HTTPException(404, "GPU not found")

    # 2. 更新状态
    gpu.memory_used = request.memory_used
    gpu.memory_utilization_rate = request.memory_utilization_rate
    gpu.core_utilization_rate = request.core_utilization_rate
    gpu.temperature = request.temperature
    gpu.updated_at = datetime.now()

    # 3. 更新扩展信息
    status_json = gpu.status_json or {}
    status_json.update({
        "agent_pid": request.agent_pid,
        "vllm_pid": request.vllm_pid,
        "ip": request.ip,
        "port": request.port,
        "last_heartbeat": request.timestamp
    })
    gpu.status_json = status_json

    db.commit()

    # 4. 检查告警
    await check_gpu_alerts(gpu)

    return {"success": True, "message": "Heartbeat received"}
```

---

## 11. 部署方案

### 11.1 Agent 部署方式

#### 方式1：一键安装（推荐）

```bash
# 单张卡
export TM_TOKEN="tm_worker_abc123xyz789"
export TM_GPU_IDS="0"
curl -sfL https://get.tokenmachine.io | bash -

# 多张卡（并行启动）
export TM_TOKEN="tm_worker_abc123xyz789"
export TM_GPU_IDS="0,1,2,3"
curl -sfL https://get.tokenmachine.io | bash -
```

#### 方式2：Systemd 服务

```bash
# 安装后自动创建 systemd 服务
sudo systemctl start tm-agent@0
sudo systemctl status tm-agent@0
sudo systemctl enable tm-agent@0  # 开机自启
```

#### 方式3：Docker（可选）

```dockerfile
FROM nvidia/cuda:12.1.0-runtime-ubuntu22.04

RUN apt-get update && apt-get install -y curl

COPY occupy_gpu /opt/tokenmachine/
COPY tm_agent.sh /opt/tokenmachine/

ENV TM_TOKEN=""
ENV TM_GPU_ID="0"

CMD ["/opt/tokenmachine/tm_agent.sh"]
```

```bash
docker run -d \
  --gpus device=0 \
  -e TM_TOKEN="tm_worker_abc123xyz789" \
  -e TM_GPU_ID="0" \
  tokenmachine/agent:latest
```

### 11.2 Server 部署

```yaml
# docker-compose.yml
version: '3.8'

services:
  postgres:
    image: postgres:15
    environment:
      POSTGRES_DB: tokenmachine
      POSTGRES_USER: tokenmachine
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7
    volumes:
      - redis_data:/data

  api:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      DATABASE_URL: postgresql://tokenmachine:${POSTGRES_PASSWORD}@postgres:5432/tokenmachine
      REDIS_URL: redis://redis:6379/0
    depends_on:
      - postgres
      - redis
    command: uvicorn main:app --host 0.0.0.0 --port 8000

volumes:
  postgres_data:
  redis_data:
```

---

## 12. 实施计划

### Phase 1: 基础架构（1 周）

- [ ] 创建数据库迁移（workers, gpu_devices 表）
- [ ] 实现 Token 生成和验证
- [ ] 实现 Worker CRUD API
- [ ] 编写单元测试

### Phase 2: Agent 开发（1 周）

- [ ] 实现 occupy_gpu.cu
- [ ] 实现 tm_agent.sh
- [ ] 实现 install.sh
- [ ] 本地测试（单卡、多卡）

### Phase 3: 注册和心跳（1 周）

- [ ] 实现 GPU 注册 API
- [ ] 实现心跳 API（单卡、批量）
- [ ] 实现心跳超时检测
- [ ] 集成测试

### Phase 4: 状态管理（1 周）

- [ ] 实现 Worker 状态转换
- [ ] 实现 GPU 状态同步
- [ ] 实现告警规则
- [ ] 端到端测试

### Phase 5: 前端集成（1 周）

- [ ] 前端添加 Worker 页面
- [ ] 实时状态显示（SSE）
- [ ] GPU 分布可视化
- [ ] UI 测试

### Phase 6: 部署和优化（1 周）

- [ ] 打包 Agent 发布
- [ ] CDN 上传安装脚本
- [ ] 性能优化（批量心跳、缓存）
- [ ] 文档完善

---

## 附录

### A. 环境变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `TM_TOKEN` | Worker 注册 Token | 必填 |
| `TM_GPU_ID` | GPU ID（单张卡） | 必填 |
| `TM_GPU_IDS` | GPU ID 列表（多张卡，逗号分隔） | 必填 |
| `TM_SERVER_URL` | Server API 地址 | https://api.tokenmachine.io |
| `TM_AGENT_PORT` | Agent 端口 | 9000 + GPU_ID |
| `TM_HEARTBEAT_INTERVAL` | 心跳间隔（秒） | 30 |

### B. 性能指标

| 指标 | 目标值 |
|------|--------|
| Agent 体积 | < 50KB |
| Agent 启动时间 | < 0.5秒 |
| 单卡注册时间 | < 5秒 |
| 100 卡注册时间 | < 30秒 |
| 心跳响应时间 | < 1秒 |
| 内存占用（每 GPU） | < 5MB |

### C. 故障排查

```bash
# 查看 Agent 日志
tail -f /var/log/tm_agent_0.log

# 检查占卡进程
ps aux | grep occupy_gpu

# 检查 GPU 状态
nvidia-smi

# 测试 API 连通性
curl -X POST https://api.tokenmachine.io/api/v1/gpus/heartbeat \
  -H "Authorization: Bearer $TM_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"test": true}'

# 查看 systemd 服务状态
sudo systemctl status tm-agent@0
```

---

**文档版本**: v1.0
**最后更新**: 2025-01-21
**作者**: TokenMachine Team
