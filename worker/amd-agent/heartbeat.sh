#!/bin/bash

# TokenMachine AMD Agent 心跳守护进程
# 定期向后端服务器发送心跳信号

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# 自动检测工作目录
if [[ $EUID -ne 0 ]]; then
    WORK_DIR="${HOME}/.local/tokenmachine_amd"
else
    WORK_DIR="/opt/tokenmachine-amd"
fi

RUN_DIR="${WORK_DIR}/run"
LOG_DIR="${WORK_DIR}/logs"
LOG_FILE="$LOG_DIR/heartbeat.log"
PID_FILE="$RUN_DIR/heartbeat.pid"

# 加载配置
load_config() {
    if [ -f "$WORK_DIR/.env" ]; then
        source "$WORK_DIR/.env"
    fi

    if [ -f "$WORK_DIR/.worker_config" ]; then
        source "$WORK_DIR/.worker_config"
    fi

    # 设置默认值
    SERVER_URL=${TM_SERVER_URL:-"http://localhost:8000"}
    WORKER_ID=${WORKER_ID:-""}
    WORKER_SECRET=${WORKER_SECRET:-""}
    HEARTBEAT_INTERVAL=${HEARTBEAT_INTERVAL:-30}
    MOCK_MODE=${TM_MOCK_MODE:-0}

    # Agent 端口
    AGENT_PORT=${TM_AGENT_PORT:-9001}
    EXPORTER_PORT=$((AGENT_PORT + 91))
}

# 颜色定义
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [INFO] $*" | tee -a "$LOG_FILE"
}

log_error() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [ERROR] $*" | tee -a "$LOG_FILE" >&2
}

log_warn() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [WARN] $*" | tee -a "$LOG_FILE"
}

# 创建必要的目录
create_dirs() {
    mkdir -p "$RUN_DIR"
    mkdir -p "$LOG_DIR"
}

# 保存 PID
save_pid() {
    echo $$ > "$PID_FILE"
}

# 删除 PID 文件
remove_pid() {
    rm -f "$PID_FILE"
}

# 发送心跳
send_heartbeat() {
    local timestamp=$(date +%s)
    local status="running"

    # 构建心跳数据
    local heartbeat_data="{
        \"worker_id\": $WORKER_ID,
        \"status\": \"$status\",
        \"timestamp\": $timestamp,
        \"agent_type\": \"amd\",
        \"mock_mode\": $MOCK_MODE
    }"

    # 发送心跳到后端
    local response=$(curl -s -w "\n%{http_code}" \
        -X POST "${SERVER_URL}/workers/heartbeat" \
        -H "Content-Type: application/json" \
        -H "Authorization: Bearer ${WORKER_SECRET}" \
        -d "$heartbeat_data" 2>&1)

    # 分离 HTTP 状态码和响应体
    local http_code=$(echo "$response" | tail -n 1)
    local response_body=$(echo "$response" | sed '$d')

    if [ "$http_code" = "200" ]; then
        log_info "心跳发送成功 (HTTP $http_code)"
        return 0
    else
        log_warn "心跳发送失败 (HTTP $http_code): $response_body"
        return 1
    fi
}

# 收集 AMD GPU 指标
collect_metrics() {
    local metrics="{}"

    if [[ $MOCK_MODE -eq 1 ]]; then
        # 模拟模式：返回模拟指标
        metrics='{
            "gpu_count": 1,
            "gpu_memory_used_mb": 12288,
            "gpu_memory_total_mb": 16384,
            "gpu_temperature_celsius": 75,
            "gpu_utilization_percent": 45
        }'
    else
        # 真实模式：从 rocm-smi 收集指标
        local gpu_count=$(rocm-smi --list | grep -c "GPU" 2>/dev/null || echo "0")
        local memory_used=$(rocm-smi --showmeminfo vram --parse 2>/dev/null | grep "Used" | awk '{print $2}' || echo "0")
        local memory_total=$(rocm-smi --showmeminfo vram --parse 2>/dev/null | grep "Total" | awk '{print $2}' || echo "0")
        local temperature=$(rocm-smi --showtemp --parse 2>/dev/null | grep "Temperature" | awk '{print $2}' || echo "0")
        local utilization=$(rocm-smi --showuse --parse 2>/dev/null | grep "GPU use" | awk '{print $3}' || echo "0")

        metrics="{\"gpu_count\":$gpu_count,\"gpu_memory_used_mb\":$memory_used,\"gpu_memory_total_mb\":$memory_total,\"gpu_temperature_celsius\":$temperature,\"gpu_utilization_percent\":$utilization}"
    fi

    echo "$metrics"
}

# 发送指标到后端
send_metrics() {
    local metrics=$(collect_metrics)
    local timestamp=$(date +%s)

    # 发送指标数据
    local response=$(curl -s -w "\n%{http_code}" \
        -X POST "${SERVER_URL}/workers/metrics" \
        -H "Content-Type: application/json" \
        -H "Authorization: Bearer ${WORKER_SECRET}" \
        -d "{
            \"worker_id\": $WORKER_ID,
            \"timestamp\": $timestamp,
            \"metrics\": $metrics
        }" 2>&1)

    local http_code=$(echo "$response" | tail -n 1)
    local response_body=$(echo "$response" | sed '$d')

    if [ "$http_code" = "200" ]; then
        log_info "指标发送成功"
        return 0
    else
        log_warn "指标发送失败 (HTTP $http_code): $response_body"
        return 1
    fi
}

# 检查服务健康状态
check_health() {
    local healthy=1

    # 检查 Exporter
    if curl -s "http://localhost:${EXPORTER_PORT}/health" | grep -q "healthy"; then
        log_info "Exporter 健康检查通过"
    else
        log_warn "Exporter 健康检查失败"
        healthy=0
    fi

    # 检查 Receiver
    if curl -s "http://localhost:${AGENT_PORT}/health" | grep -q "ok"; then
        log_info "Receiver 健康检查通过"
    else
        log_warn "Receiver 健康检查失败"
        healthy=0
    fi

    return $healthy
}

# 主循环
main_loop() {
    log_info "AMD Agent 心跳守护进程启动"
    log_info "Worker ID: ${WORKER_ID:-未配置}"
    log_info "Server URL: $SERVER_URL"
    log_info "心跳间隔: ${HEARTBEAT_INTERVAL}秒"
    log_info "模拟模式: $MOCK_MODE"
    log_info "Exporter 端口: $EXPORTER_PORT"
    log_info "Receiver 端口: $AGENT_PORT"

    local consecutive_failures=0
    local max_failures=5

    while true; do
        # 检查是否应该停止
        if [ -f "$RUN_DIR/stop_heartbeat" ]; then
            log_info "收到停止信号，退出心跳守护进程"
            break
        fi

        # 发送心跳
        if send_heartbeat; then
            consecutive_failures=0
        else
            ((consecutive_failures++))
            if [ $consecutive_failures -ge $max_failures ]; then
                log_error "连续 $max_failures 次心跳失败，请检查网络和服务器状态"
                consecutive_failures=0
            fi
        fi

        # 每 5 个心跳周期发送一次指标
        if [ $((SECONDS % (HEARTBEAT_INTERVAL * 5))) -eq 0 ]; then
            send_metrics || true
        fi

        # 每 10 个心跳周期进行一次健康检查
        if [ $((SECONDS % (HEARTBEAT_INTERVAL * 10))) -eq 0 ]; then
            check_health || log_warn "部分服务健康检查失败"
        fi

        # 等待下一个心跳周期
        sleep $HEARTBEAT_INTERVAL
    done
}

# 清理
cleanup() {
    log_info "正在停止心跳守护进程..."
    remove_pid
    log_info "心跳守护进程已停止"
    exit 0
}

# 信号处理
trap cleanup SIGTERM SIGINT SIGHUP

# 主程序
main() {
    load_config
    create_dirs
    save_pid

    # 检查必要配置
    if [ -z "$WORKER_ID" ]; then
        log_error "未配置 Worker ID，无法发送心跳"
        log_error "请先运行 install.sh 注册 Worker"
        exit 1
    fi

    # 运行主循环
    main_loop
}

# 运行主程序
main "$@"
