#!/bin/bash
# ===================================================================
# 任务处理器 - 执行来自 Server 的任务
# ===================================================================

TASK_FILE_DIR="/tmp/tokenmachine/tasks"
LOG_FILE="/var/log/tokenmachine/passive-agent.log"

# 确保任务目录存在
mkdir -p "$TASK_FILE_DIR"

# 打印日志
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [TASK] $1" | tee -a "$LOG_FILE"
}

# 启动 vLLM 任务
start_vllm() {
    local task_id="$1"
    local model_path="$2"
    local port="$3"
    local gpu_id="$4"
    
    log "Starting vLLM task: $task_id"
    log "  Model: $model_path"
    log "  Port: $port"
    log "  GPU: $gpu_id"
    
    # 这里实现实际的 vLLM 启动逻辑
    # 示例：使用 Docker 启动
    # docker run -d --gpus device=$gpu_id -p $port:$port --name vllm-$task_id ...
    
    # 记录任务状态
    local task_file="$TASK_FILE_DIR/${task_id}.json"
    cat > "$task_file" <<EOF
{
  "id": "$task_id",
  "type": "start_vllm",
  "status": "completed",
  "started_at": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
  "completed_at": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
  "result": {
    "port": $port,
    "gpu_id": "$gpu_id"
  },
  "error": null
}
EOF
    
    log "vLLM task completed: $task_id"
}

# 停止 vLLM 任务
stop_vllm() {
    local task_id="$1"
    local port="$2"
    
    log "Stopping vLLM task: $task_id"
    log "  Port: $port"
    
    # 实现 vLLM 停止逻辑
    # docker stop vllm-$task_id
    
    # 更新任务状态
    local task_file="$TASK_FILE_DIR/${task_id}.json"
    if [[ -f "$task_file" ]]; then
        cat > "$task_file" <<EOF
{
  "id": "$task_id",
  "type": "stop_vllm",
  "status": "completed",
  "started_at": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
  "completed_at": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
  "result": {
    "stopped": true
  },
  "error": null
}
EOF
    fi
    
    log "vLLM stop task completed: $task_id"
}

# 占用 GPU 内存
occupy_gpu() {
    local gpu_id="$1"
    local memory_mb="$2"
    
    log "Occupying GPU: $gpu_id with ${memory_mb}MB"
    
    # 这里可以调用 occupy_gpu 程序
    # /opt/tokenmachine/passive_worker/occupy_gpu --gpu $gpu_id --memory $memory_mb &
}

# 释放 GPU 内存
release_gpu() {
    local gpu_id="$1"
    
    log "Releasing GPU: $gpu_id"
    
    # 杀死 occupy_gpu 进程
    # pkill -f "occupy_gpu.*--gpu $gpu_id"
}

# 主处理函数
if [[ $# -eq 0 ]]; then
    log "Usage: $0 <task_type> <task_id> [args...]"
    log "Task types:"
    log "  start_vllm <task_id> <model_path> <port> <gpu_id>"
    log "  stop_vllm <task_id> <port>"
    log "  occupy_gpu <gpu_id> <memory_mb>"
    log "  release_gpu <gpu_id>"
    exit 1
fi

TASK_TYPE="$1"
TASK_ID="$2"

case "$TASK_TYPE" in
    start_vllm)
        start_vllm "$TASK_ID" "$3" "$4" "$5"
        ;;
    
    stop_vllm)
        stop_vllm "$TASK_ID" "$3"
        ;;
    
    occupy_gpu)
        occupy_gpu "$TASK_ID" "$3"
        ;;
    
    release_gpu)
        release_gpu "$TASK_ID"
        ;;
    
    *)
        log "Unknown task type: $TASK_TYPE"
        exit 1
        ;;
esac
