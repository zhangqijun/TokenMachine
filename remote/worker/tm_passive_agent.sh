#!/bin/bash
# ===================================================================
# TokenMachine Passive Worker Agent
# 完全被动模式，等待 Server 通过 SSH 隧道连接和推送任务
# ===================================================================

set -e

INSTALL_DIR="/opt/tokenmachine/passive_worker"
CONFIG_FILE="$INSTALL_DIR/.config"
STATUS_FILE="/tmp/tokenmachine/worker_status.json"
PID_FILE="$INSTALL_DIR/.agent.pid"
LOG_FILE="/var/log/tokenmachine/passive-agent.log"

# 加载配置
if [[ -f "$CONFIG_FILE" ]]; then
    source "$CONFIG_FILE"
else
    echo "Error: Config file not found: $CONFIG_FILE"
    exit 1
fi

# 创建状态文件目录
mkdir -p $(dirname "$STATUS_FILE")

# 打印日志
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# 停止 Agent
stop_agent() {
    log "Stopping agent..."
    
    # 杀死任务处理器
    if [[ -f "$INSTALL_DIR/.task_handler.pid" ]]; then
        kill $(cat "$INSTALL_DIR/.task_handler.pid") 2>/dev/null || true
        rm "$INSTALL_DIR/.task_handler.pid"
    fi
    
    # 停止 GPU 监控
    if [[ -f "$INSTALL_DIR/.gpu_monitor.pid" ]]; then
        kill $(cat "$INSTALL_DIR/.gpu_monitor.pid") 2>/dev/null || true
        rm "$INSTALL_DIR/.gpu_monitor.pid"
    fi
    
    # 删除 PID 文件
    rm -f "$PID_FILE"
    
    log "Agent stopped"
    exit 0
}

# 启动 Agent
start_agent() {
    log "Starting passive worker agent..."
    log "  Worker Name: $WORKER_NAME"
    log "  Worker ID: ${WORKER_ID:-'Not assigned'}"
    log "  Task Port: $TASK_PORT"
    log "  Metrics Port: $METRICS_PORT"
    
    # 保存 PID
    echo $$ > "$PID_FILE"
    
    # 启动 GPU 监控器（后台）
    log "Starting GPU monitor..."
    $INSTALL_DIR/gpu_monitor.sh &
    echo $! > "$INSTALL_DIR/.gpu_monitor.pid"
    
    # 启动简单的 HTTP 服务器（用于接收任务）
    log "Starting HTTP server on port $TASK_PORT..."
    
    # 使用 Python 快速启动 HTTP 服务器
    cat <<'PYSCRIPT' > "$INSTALL_DIR/task_server.py"
#!/usr/bin/env python3
import json
import os
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import parse_qs
import subprocess

CONFIG_FILE = "$CONFIG_FILE"
STATUS_FILE = "$STATUS_FILE"

# 读取配置
with open(CONFIG_FILE) as f:
    config = dict(line.strip().split('=', 1) for line in f if '=' in line)
    
TASK_PORT = int(config.get('TASK_PORT', 9001))

class TaskHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/api/tasks':
            # 返回任务列表
            response = {
                "tasks": [],
                "last_updated": os.path.getmtime(STATUS_FILE)
            }
            self.send_json(200, response)
        
        elif self.path == '/api/gpu-status':
            # 返回 GPU 状态
            try:
                with open(STATUS_FILE) as f:
                    gpu_data = json.load(f)
                self.send_json(200, gpu_data)
            except:
                self.send_json(200, {"gpu_devices": []})
        
        elif self.path == '/health':
            self.send_json(200, {"status": "healthy", "worker": config.get('WORKER_NAME', 'unknown')})
        
        elif self.path == '/metrics':
            # Prometheus 指标
            try:
                with open(STATUS_FILE) as f:
                    gpu_data = json.load(f)
                
                response = "# HELP tm_worker_status Worker status\n"
                response += "# TYPE tm_worker_status gauge\ntm_worker_status 1\n\n"
                
                for gpu in gpu_data.get('gpu_devices', []):
                    response += f"# HELP gpu_memory_used_bytes GPU memory used\n"
                    response += f"# TYPE gpu_memory_used_bytes gauge\n"
                    response += f"gpu_memory_used_bytes{{gpu=\"{gpu['index']}\"}} {gpu['memory_used']}\n"
                    response += f"# HELP gpu_utilization GPU utilization percent\n"
                    response += f"# TYPE gpu_utilization gauge\n"
                    response += f"gpu_utilization{{gpu=\"{gpu['index']}\"}} {gpu['utilization']}\n"
                
                self.send_response(200, 'text/plain; version=0.0.4; charset=utf-8', response.encode())
            except:
                self.send_response(200, 'text/plain; charset=utf-8', b'# No metrics available')
        
        else:
            self.send_json(404, {"error": "Not found"})
    
    def do_POST(self):
        if self.path == '/api/tasks':
            # 接收新任务
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)
            
            try:
                task_data = json.loads(post_data.decode())
                
                # 执行任务
                result = execute_task(task_data)
                
                self.send_json(200, {"status": "accepted", "task_id": task_data.get('id'), "result": result})
            except Exception as e:
                self.send_json(500, {"error": str(e)})
        else:
            self.send_json(404, {"error": "Not found"})
    
    def send_json(self, status, data):
        self.send_response(status, 'application/json', json.dumps(data).encode())
    
    def send_response(self, status, content_type, content):
        self.send_response(status, content_type, content)
        
        if 'Content-Length' not in self.headers:
            self.end_headers()
        self.wfile.write(content)

def execute_task(task_data):
    task_id = task_data.get('id')
    task_type = task_data.get('type')
    payload = task_data.get('payload', {})
    
    # 记录任务到文件
    task_file = f"$STATUS_FILE.task_{task_id}.json"
    with open(task_file, 'w') as f:
        json.dump({
            "id": task_id,
            "type": task_type,
            "payload": payload,
            "status": "running",
            "started_at": None
        }, f)
    
    # 执行任务（这里可以扩展不同的任务类型）
    if task_type == 'start_vllm':
        result = start_vllm(payload)
    elif task_type == 'stop_vllm':
        result = stop_vllm(payload)
    else:
        result = {"error": "Unknown task type"}
    
    return result

def start_vllm(payload):
    # 这里实现启动 vLLM 的逻辑
    return {"status": "success", "port": payload.get('port')}

def stop_vllm(payload):
    # 这里实现停止 vLLM 的逻辑
    return {"status": "success"}

if __name__ == '__main__':
    server = HTTPServer(('0.0.0.0', TASK_PORT), TaskHandler)
    print(f"Server listening on port {TASK_PORT}")
    server.serve_forever()
PYSCRIPT
    
    # 启动 Python 服务器
    python3 "$INSTALL_DIR/task_server.py" > "$LOG_FILE.server" 2>&1 &
    SERVER_PID=$!
    echo $SERVER_PID > "$INSTALL_DIR/.task_server.pid"
    
    log "Agent started successfully"
    log "  HTTP server listening on port $TASK_PORT"
    log "  Prometheus metrics on port $METRICS_PORT (via file)"
    
    # 主循环（保持运行）
    while true; do
        # 检查 PID 文件是否存在（用于优雅停止）
        if [[ ! -f "$PID_FILE" ]]; then
            log "PID file removed, stopping..."
            break
        fi
        
        sleep 5
    done
    
    # 清理
    if [[ -f "$INSTALL_DIR/.task_server.pid" ]]; then
        kill $(cat "$INSTALL_DIR/.task_server.pid") 2>/dev/null || true
        rm "$INSTALL_DIR/.task_server.pid"
    fi
    
    log "Agent stopped"
}

# 主程序
case "$1" in
    start)
        # 检查是否已在运行
        if [[ -f "$PID_FILE" ]]; then
            if ps -p $(cat "$PID_FILE") > /dev/null 2>&1; then
                echo "Agent is already running (PID: $(cat "$PID_FILE}))"
                exit 1
            else
                # 清理旧的 PID 文件
                rm -f "$PID_FILE"
            fi
        fi
        start_agent
        ;;
    
    stop)
        if [[ -f "$PID_FILE" ]]; then
            kill $(cat "$PID_FILE") 2>/dev/null && echo "Agent stopped"
            rm -f "$PID_FILE"
        else
            echo "Agent is not running"
        fi
        ;;
    
    restart)
        $0 stop
        sleep 2
        $0 start
        ;;
    
    status)
        if [[ -f "$PID_FILE" ]]; then
            if ps -p $(cat "$PID_FILE") > /dev/null 2>&1; then
                echo "Status: RUNNING (PID: $(cat "$PID_FILE}))"
                echo "  Task Port: $TASK_PORT"
                echo "  Status File: $STATUS_FILE"
            else
                echo "Status: DEAD (PID file exists but process not running)"
            fi
        else
            echo "Status: NOT RUNNING"
        fi
        ;;
    
    *)
        echo "Usage: $0 {start|stop|restart|status}"
        exit 1
        ;;
esac
