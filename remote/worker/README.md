# Remote Worker 设计方案 - 修正版

> Worker 是公网节点，Server 在内网，通过 SSH Push 指令

---

## 网络拓扑（实际）

```
┌─────────────────────────────────────────────────────┐
│              TokenMachine Server                     │
│              (内网，无公网访问）                    │
│                                                     │
│  ┌─────────────────────────────────────────┐          │
│  │  SSH Manager                      │          │
│  │  • 连接远程 Worker                │          │
│  │  • 推送任务指令                   │          │
│  │  • 查询状态                       │          │
│  └─────────────────────────────────────────┘          │
└───────────────────────────────────────────────────────────┘
                           ▲ SSH 连接
                           │ ssh -p 39247 root@region-9.autodl.pro
                           │
                           ▼
┌─────────────────────────────────────────────────────┐
│           Remote Worker (公网节点）                │
│        region-9.autodl.pro:39247                    │
│                                                     │
│  ┌─────────────────────────────────────────┐          │
│  │  Agent (被动模式）                   │          │
│  │  • 监听本地端口                   │          │
│  │  • 等待 SSH 隧道连接              │          │
│  │  • 执行接收到的任务                 │          │
│  │  • nvidia-smi 采集 GPU            │          │
│  └─────────────────────────────────────────┘          │
│                                                     │
│  ┌─────────────────────────────────────────┐          │
│  │  NVIDIA V100 GPU                      │          │
│  │  • 32GB HBM2                       │          │
│  │  • PCIe 接口                        │          │
│  └─────────────────────────────────────────┘          │
└───────────────────────────────────────────────────────────┘
```

---

## 核心挑战

| 挑战 | 说明 |
|------|------|
| **Worker 在公网** | Server 无法直接访问 Worker（没有反向连接）|
| **单向 SSH 连接** | Server → Worker 可连，Worker → Server 不可连 |
| **公网 IP 动态** | Worker IP 可能变化 |
| **防火墙限制** | Worker 可能无法开放 HTTP 端口 |

---

## 推荐方案：SSH 隧道 + Push 模式

### 架构设计

```
┌─────────────────────────────────────────────────────┐
│              Server (内网）                           │
│  ┌─────────────────────────────────────────┐          │
│  │  Worker Manager Service            │          │
│  │                                    │          │
│  │  1. 维护 SSH 连接池             │          │
│  │     ssh root@region-9.autodl.pro -p 39247 │          │
│  │                                    │          │
│  │  2. 通过隧道推送任务             │          │
│  │     curl http://localhost:9001/tasks      │          │
│  │     → SSH 转发 → Worker:9001       │          │
│  │                                    │          │
│  │  3. 主动拉取状态                 │          │
│  │     curl http://localhost:9001/health    │          │
│  │     curl http://localhost:9090/metrics   │          │
│  │                                    │          │
│  │  4. 重连断开的隧道               │          │
│  │     autossh 持久化隧道              │          │
│  └─────────────────────────────────────────┘          │
└───────────────────────────────────────────────────────────┘
                           ▲
                           │ SSH 反向隧道
                           │ ssh -N -L 9001:localhost:9001 root@region-9...
                           │ (Server 上监听 :9001，转发到 Worker:9001)
                           ▼
┌─────────────────────────────────────────────────────┐
│           Remote Worker (公网）                      │
│  ┌─────────────────────────────────────────┐          │
│  │  Passive Agent (监听模式）          │          │
│  │                                    │          │
│  │  • 监听 :9001 (任务接收）         │          │
│  │  • 监听 :9090 (Prometheus 指标）     │          │
│  │  • 定期写入状态文件（供 SSH 拉取） │          │
│  │  • 执行任务并记录结果               │          │
│  │                                    │          │
│  │  • nvidia-smi 采集 GPU            │          │
│  │  • 30s 更新一次 GPU 状态文件         │          │
│  └─────────────────────────────────────────┘          │
└───────────────────────────────────────────────────────────┘
```

### 工作流程

#### 1. Worker 首次注册（通过 SSH）
```bash
# Server 端执行：通过 SSH 在 Worker 上运行注册命令
ssh -p 39247 root@region-9.autodl.pro bash -s <<'EOF'
# 注册 Worker
curl -X POST http://server:8000/api/v1/workers/register \
  -d '{
    "token": "TM_REMOTE_xxx",
    "worker_type": "remote",
    "connection_mode": "ssh-tunnel",
    "capabilities": {
      "gpu_count": 1,
      "gpu_model": "NVIDIA V100-32GB"
    }
  }'
EOF

# Worker 返回 Worker ID，Server 保存
```

#### 2. Server 建立 SSH 隧道
```python
# backend/services/ssh_tunnel_manager.py

class SSHTunnelManager:
    def establish_tunnel(self, worker: Worker):
        """为远程 Worker 建立 SSH 隧道"""
        tunnel_cmd = [
            "ssh",
            "-N",  # 不执行远程命令，只做端口转发
            "-L", f"{self._get_local_port()}:{worker.ip}:9001",  # 反向隧道
            "-o", "ServerAliveInterval=30",
            "-o", "ServerAliveCountMax=3",
            "-p", str(worker.ssh_port),
            f"{worker.ssh_user}@{worker.hostname}"
        ]

        # 启动隧道进程
        self.tunnel_processes[worker.id] = subprocess.Popen(
            tunnel_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        # 等待隧道建立
        await self._wait_for_tunnel(worker.id)
```

#### 3. Server 通过隧道推送任务
```python
# backend/services/worker_task_service.py

async def push_task_to_remote_worker(self, worker_id: int, task: Task):
    """通过 SSH 隧道推送任务到远程 Worker"""
    
    # 通过本地端口（隧道）访问 Worker
    tunnel_port = self.tunnel_manager.get_tunnel_port(worker_id)
    
    # 推送任务
    response = await httpx.post(
        f"http://localhost:{tunnel_port}/api/tasks",
        json={
            "id": task.id,
            "type": task.type,
            "payload": task.payload
        },
        timeout=30
    )
    
    return response
```

#### 4. Server 主动拉取状态
```python
# backend/services/worker_poller.py

async def poll_remote_worker_status(self, worker: Worker):
    """主动拉取远程 Worker 的状态"""
    
    # 通过隧道访问
    tunnel_port = self.tunnel_manager.get_tunnel_port(worker.id)
    
    # 拉取 GPU 状态
    gpu_response = await httpx.get(
        f"http://localhost:{tunnel_port}/api/gpu-status"
    )
    
    # 拉取 Prometheus 指标
    metrics_response = await httpx.get(
        f"http://localhost:{tunnel_port}/metrics"
    )
    
    # 更新数据库
    self.update_worker_status(worker.id, gpu_response.json())
```

---

## 组件设计

### 1. Server 端新增组件

#### SSH 隧道管理器
```
backend/services/
├── ssh_tunnel_manager.py      # SSH 隧道生命周期管理
├── remote_worker_service.py   # 远程 Worker 任务推送
└── worker_poller.py          # 状态主动轮询
```

#### Worker 表新增字段
```sql
ALTER TABLE workers ADD COLUMN connection_mode VARCHAR(20) DEFAULT 'push';
ALTER TABLE workers ADD COLUMN ssh_user VARCHAR(50) DEFAULT 'root';
ALTER TABLE workers ADD COLUMN ssh_port INT DEFAULT 22;
ALTER TABLE workers ADD COLUMN tunnel_port INT;  -- Server 端本地隧道端口
ALTER TABLE workers ADD COLUMN is_public_node BOOLEAN DEFAULT TRUE;
```

### 2. Remote Worker Agent（被动模式）

#### 文件结构
```
remote/worker/
├── tm_passive_agent.sh     # 主控脚本（Bash）
├── install.sh              # 安装脚本
├── task_handler.sh         # 任务处理器
├── gpu_monitor.sh          # GPU 监控器
└── README.md              # 本文档
```

#### Agent 功能

**功能列表：**
- ✅ 监听 HTTP 端口（9001 任务接收，9090 Prometheus）
- ✅ 接收来自 Server 的任务指令
- ✅ 执行任务（启动/停止 vLLM）
- ✅ 定期更新状态文件（/tmp/worker_status.json）
- ✅ nvidia-smi 采集 GPU 信息
- ✅ 日志记录（/var/log/tokenmachine）

**不主动连接 Server：**
- ❌ 不发送心跳
- ❌ 不主动轮询任务
- ✅ 完全被动，等待 SSH 隧道

---

## API 设计

### Worker 端（Agent 提供）

#### 1. 接收任务
```http
POST /api/tasks
```
**Request:**
```json
{
  "id": "task_001",
  "type": "start_vllm",
  "payload": {
    "model_path": "/models/llama-3-8b",
    "port": 8001,
    "gpu_id": 0
  }
}
```
**Response:**
```json
{
  "status": "accepted",
  "task_id": "task_001"
}
```

#### 2. 查询任务状态
```http
GET /api/tasks/{task_id}
```
**Response:**
```json
{
  "id": "task_001",
  "status": "running" | "completed" | "failed",
  "started_at": "2026-01-30T07:00:00Z",
  "result": {...},
  "error": null
}
```

#### 3. GPU 状态（Server 主动拉取）
```http
GET /api/gpu-status
```
**Response:**
```json
{
  "gpu_devices": [
    {
      "index": 0,
      "name": "NVIDIA V100-32GB",
      "memory_used": 8589934592,
      "memory_total": 34359738368,
      "utilization": 45.0,
      "temperature": 65.0,
      "state": "IN_USE"
    }
  ],
  "last_updated": "2026-01-30T07:00:00Z"
}
```

#### 4. Prometheus 指标
```http
GET /metrics
```
**Response:**
```
# HELP gpu_memory_used_bytes GPU 内存使用量
# TYPE gpu_memory_used_bytes gauge
gpu_memory_used_bytes{gpu="0"} 8589934592
```

---

## Server 端实现

### 1. SSH 隧道管理

```python
# backend/services/ssh_tunnel_manager.py

import subprocess
import asyncio
from typing import Dict
from loguru import logger

class SSHTunnelManager:
    """SSH 隧道管理器"""
    
    def __init__(self):
        self.tunnel_processes: Dict[int, subprocess.Popen] = {}
        self.tunnel_ports: Dict[int, int] = {}
        self._base_port = 11000  # 从 11000 开始分配
    
    def _get_next_port(self) -> int:
        """获取下一个可用端口"""
        port = self._base_port
        self._base_port += 1
        return port
    
    async def establish_tunnel(self, worker_id: int, ssh_host: str, 
                            ssh_port: int, ssh_user: str = "root"):
        """建立 SSH 隧道"""
        
        local_port = self._get_next_port()
        
        # SSH 隧道命令：Server 本地端口 → Worker 端口
        cmd = [
            "ssh",
            "-N",  # 不执行远程命令
            "-L", f"{local_port}:localhost:9001",  # 反向转发
            "-o", "ServerAliveInterval=30",  # 保持连接
            "-o", "ServerAliveCountMax=3",  # 3 次超时断开
            "-o", "StrictHostKeyChecking=no",
            "-p", str(ssh_port),
            f"{ssh_user}@{ssh_host}"
        ]
        
        logger.info(f"Establishing SSH tunnel for worker {worker_id}")
        logger.info(f"Command: {' '.join(cmd)}")
        
        # 启动隧道进程
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            stdin=subprocess.DEVNULL
        )
        
        self.tunnel_processes[worker_id] = process
        self.tunnel_ports[worker_id] = local_port
        
        # 保存到数据库
        worker = self.db.query(Worker).filter(Worker.id == worker_id).first()
        if worker:
            worker.tunnel_port = local_port
            self.db.commit()
        
        # 等待隧道就绪（简单检查）
        await asyncio.sleep(2)
        
        logger.info(f"Tunnel established: localhost:{local_port} → worker:9001")
        return local_port
    
    def close_tunnel(self, worker_id: int):
        """关闭 SSH 隧道"""
        if worker_id in self.tunnel_processes:
            process = self.tunnel_processes[worker_id]
            process.terminate()
            process.wait(timeout=5)
            
            del self.tunnel_processes[worker_id]
            del self.tunnel_ports[worker_id]
            
            logger.info(f"Tunnel closed for worker {worker_id}")
    
    def get_tunnel_port(self, worker_id: int) -> int:
        """获取隧道的本地端口"""
        return self.tunnel_ports.get(worker_id)
    
    def check_tunnel_health(self, worker_id: int) -> bool:
        """检查隧道是否健康"""
        local_port = self.tunnel_ports.get(worker_id)
        if not local_port:
            return False
        
        try:
            response = httpx.get(f"http://localhost:{local_port}/api/health", timeout=5)
            return response.status_code == 200
        except:
            return False
```

### 2. 远程 Worker 任务推送

```python
# backend/services/remote_worker_service.py

import httpx
import asyncio
from loguru import logger

class RemoteWorkerService:
    """远程 Worker 任务推送服务"""
    
    def __init__(self, tunnel_manager: SSHTunnelManager):
        self.tunnel_manager = tunnel_manager
        self.http_client = httpx.AsyncClient(timeout=30)
    
    async def push_task(self, worker_id: int, task_data: dict):
        """推送任务到远程 Worker"""
        
        # 获取隧道端口
        tunnel_port = self.tunnel_manager.get_tunnel_port(worker_id)
        if not tunnel_port:
            raise ValueError(f"No tunnel for worker {worker_id}")
        
        # 通过隧道推送任务
        url = f"http://localhost:{tunnel_port}/api/tasks"
        
        try:
            response = await self.http_client.post(url, json=task_data)
            logger.info(f"Task pushed to worker {worker_id}: {task_data['id']}")
            return response.json()
        except httpx.ConnectError:
            logger.error(f"Failed to connect to worker {worker_id} via tunnel")
            # 尝试重连隧道
            await self._reconnect_tunnel(worker_id)
            raise
        except Exception as e:
            logger.error(f"Error pushing task to worker {worker_id}: {e}")
            raise
    
    async def poll_gpu_status(self, worker_id: int):
        """主动拉取 GPU 状态"""
        
        tunnel_port = self.tunnel_manager.get_tunnel_port(worker_id)
        if not tunnel_port:
            return None
        
        url = f"http://localhost:{tunnel_port}/api/gpu-status"
        
        try:
            response = await self.http_client.get(url)
            return response.json()
        except Exception as e:
            logger.warning(f"Failed to poll GPU status for worker {worker_id}: {e}")
            return None
    
    async def _reconnect_tunnel(self, worker_id: int):
        """重连隧道"""
        # 获取 Worker 信息
        worker = self.db.query(Worker).filter(Worker.id == worker_id).first()
        
        if worker:
            # 关闭旧隧道
            self.tunnel_manager.close_tunnel(worker_id)
            
            # 建立新隧道
            await self.tunnel_manager.establish_tunnel(
                worker_id,
                worker.hostname,
                worker.ssh_port,
                worker.ssh_user
            )
```

---

## 部署流程

### 1. Worker 端部署（通过 SSH）

```bash
# 从 Server 端执行，通过 SSH 在 Worker 上安装
ssh -p 39247 root@region-9.autodl.pro bash -s <<'ENDSSH'

# 下载安装脚本
curl -sfL https://raw.githubusercontent.com/your-repo/main/remote/worker/install.sh -o /tmp/install.sh

# 执行安装
bash /tmp/install.sh -n remote-v100-01 -s http://192.168.1.100:8000

# 安装完成后返回
echo "Worker installed successfully"

ENDSSH
```

### 2. Agent 自动启动

```bash
# install.sh 会创建 systemd 服务
# Worker 重启后自动启动

# 检查状态
ssh -p 39247 root@region-9.autodl.pro "systemctl status tm-passive-agent"
```

### 3. Server 端连接

```python
# Server 启动时建立所有隧道
# backend/main.py

@app.on_event("startup")
async def startup_event():
    """启动时建立所有隧道"""
    workers = db.query(Worker).filter(
        Worker.connection_mode == "ssh-tunnel"
    ).all()
    
    for worker in workers:
        try:
            await ssh_tunnel_manager.establish_tunnel(
                worker.id,
                worker.hostname,
                worker.ssh_port,
                worker.ssh_user
            )
        except Exception as e:
            logger.error(f"Failed to establish tunnel for worker {worker.id}: {e}")
```

---

## 对比总结

| 方案 | 适用场景 | 实时性 | 稳定性 | 复杂度 |
|------|--------|--------|--------|--------|
| **SSH 隧道 + Push** | 公网 Worker，内网 Server | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ |
| Pull 轮询 | Worker 能连 Server | ⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ |

**本场景推荐：SSH 隧道 + Push**

---

## 关键优势

✅ **完全解决单向连接问题**
✅ **Worker 无需主动连接**
✅ **Server 可以完全控制远程节点**
✅ **支持多 Worker 并行管理**
✅ **隧道自动重连机制**
✅ **超轻量 Agent（纯 Bash）**
