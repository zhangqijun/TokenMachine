#!/bin/bash

# TokenMachine Ascend Agent 心跳脚本
# 向后端发送心跳信号，报告 Worker 状态

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_FILE="$SCRIPT_DIR/.worker_config"
LOG_FILE="${XDG_RUNTIME_DIR:-/var/run}/tokenmachine-ascend/heartbeat.log"
HEARTBEAT_INTERVAL=30  # 心跳间隔（秒）

# 颜色定义
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [INFO] $1" >> "$LOG_FILE"
}

log_error() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [ERROR] $1" >> "$LOG_FILE"
}

log_warn() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [WARN] $1" >> "$LOG_FILE"
}

# 读取配置
load_config() {
    if [ ! -f "$CONFIG_FILE" ]; then
        log_error "配置文件不存在: $CONFIG_FILE"
        exit 1
    fi

    source "$CONFIG_FILE"

    if [ -z "$WORKER_ID" ]; then
        log_error "WORKER_ID 未配置"
        exit 1
    fi

    if [ -z "$WORKER_SECRET" ]; then
        log_error "WORKER_SECRET 未配置"
        exit 1
    fi

    # 从环境变量读取服务器地址
    if [ -z "$TM_SERVER_URL" ]; then
        if [ -f "$SCRIPT_DIR/.env" ]; then
            source "$SCRIPT_DIR/.env"
        fi
    fi

    if [ -z "$TM_SERVER_URL" ]; then
        log_error "TM_SERVER_URL 未配置"
        exit 1
    fi
}

# 收集 NPU 状态信息
collect_npu_status() {
    local npu_status="["
    local first=true

    # 获取选中的 NPU 列表
    local selected_npus_file="${XDG_RUNTIME_DIR:-/var/run}/tokenmachine-ascend/selected_npus"
    if [ -f "$selected_npus_file" ]; then
        local npus=($(cat "$selected_npus_file"))
    else
        # 默认使用所有检测到的 NPU
        local npus=($(npu-smi list 2>/dev/null | grep -oP '^\d+' | sort -n))
    fi

    for npu_id in "${npus[@]}"; do
        if [ "$first" = true ]; then
            first=false
        else
            npu_status="$npu_status, "
        fi

        # 获取 NPU 信息
        local npu_info=$(npu-smi info -i $npu_id 2>/dev/null)
        local util=$(echo "$npu_info" | grep "AIC" | awk '{print $2}' | head -1)
        local memory=$(echo "$npu_info" | grep "HBM" | awk '{print $2}' | head -1)

        # 解析内存使用率
        local mem_used=$(echo "$memory" | grep -oP '\d+' | head -1)
        local mem_total=$(echo "$memory" | grep -oP '\d+\s*GB' | head -1 | grep -oP '\d+')
        if [ -z "$mem_total" ]; then
            mem_total=32  # 默认 32GB
        fi

        npu_status="$npu_status{\"npu_id\": $npu_id, \"utilization\": \"$util\", \"memory_used\": \"$mem_used\", \"memory_total\": \"${mem_total}GB\"}"
    done

    npu_status="$npu_status]"
    echo "$npu_status"
}

# 收集系统状态
collect_system_status() {
    # CPU 使用率
    local cpu_usage=$(top -bn1 | grep "Cpu(s)" | awk '{print $2}' | cut -d'%' -f1)

    # 内存使用率
    local mem_usage=$(free | grep Mem | awk '{printf "%.0f", $3/$2 * 100.0}')

    # 磁盘使用率
    local disk_usage=$(df / | tail -1 | awk '{print $5}' | cut -d'%' -f1)

    echo "{\"cpu_usage\": $cpu_usage, \"memory_usage\": $mem_usage, \"disk_usage\": $disk_usage}"
}

# 发送心跳
send_heartbeat() {
    local npu_status=$(collect_npu_status)
    local system_status=$(collect_system_status)

    # 获取服务状态
    local exporter_status="stopped"
    local receiver_status="stopped"
    local occupy_status="stopped"

    if pgrep -f "npu_exporter_main" > /dev/null; then
        exporter_status="running"
    fi

    if pgrep -f "receiver" > /dev/null; then
        receiver_status="running"
    fi

    if pgrep -f "occupy_npu" > /dev/null; then
        occupy_status="running"
    fi

    # 构建心跳数据
    local heartbeat_data=$(cat << EOF
{
    "worker_id": $WORKER_ID,
    "status": "running",
    "services": {
        "exporter": "$exporter_status",
        "receiver": "$receiver_status",
        "occupy": "$occupy_status"
    },
    "npu_status": $npu_status,
    "system_status": $system_status
}
EOF
)

    log_info "发送心跳数据: $heartbeat_data"

    # 发送心跳到后端
    local response=$(curl -s -X POST "${TM_SERVER_URL}/api/v1/workers/heartbeat" \
        -H "Content-Type: application/json" \
        -H "Authorization: Bearer ${WORKER_SECRET}" \
        -d "$heartbeat_data")

    local http_code=$(curl -s -o /dev/null -w "%{http_code}" -X POST "${TM_SERVER_URL}/api/v1/workers/heartbeat" \
        -H "Content-Type: application/json" \
        -H "Authorization: Bearer ${WORKER_SECRET}" \
        -d "$heartbeat_data")

    if [ "$http_code" -eq 200 ]; then
        log_info "心跳发送成功"
        echo "心跳发送成功" >> "$LOG_FILE"
        return 0
    else
        log_warn "心跳发送失败，HTTP 状态码: $http_code，响应: $response"
        return 1
    fi
}

# 主循环
main() {
    log_info "心跳守护进程启动"

    # 确保日志目录存在
    mkdir -p "$(dirname "$LOG_FILE")"

    # 加载配置
    load_config

    log_info "配置加载完成，Worker ID: $WORKER_ID"
    log_info "服务器地址: $TM_SERVER_URL"
    log_info "心跳间隔: $HEARTBEAT_INTERVAL 秒"

    # 初始心跳
    send_heartbeat

    # 定时心跳循环
    while true; do
        sleep $HEARTBEAT_INTERVAL

        # 检查配置文件是否存在
        if [ ! -f "$CONFIG_FILE" ]; then
            log_error "配置文件不存在，退出"
            exit 1
        fi

        # 重新加载配置（支持热更新）
        source "$CONFIG_FILE"

        # 发送心跳
        send_heartbeat
    done
}

# 处理信号
trap 'log_info "收到退出信号，正在停止..."; exit 0' TERM INT

# 运行主函数
main "$@"
