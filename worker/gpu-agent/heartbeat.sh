#!/bin/bash

# TokenMachine GPU Agent - Heartbeat Daemon
# 定期向Backend发送心跳，保持Worker在线状态

set -e

# 自动检测用户目录模式（非 root 用户自动使用用户目录）
if [[ $EUID -ne 0 ]]; then
    WORK_DIR="${HOME}/.local/tokenmachine"
else
    WORK_DIR="/opt/tokenmachine"
fi

WORKER_CONFIG="$WORK_DIR/.worker_config"
HEARTBEAT_INTERVAL=30  # 心跳间隔（秒）

# 颜色
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

log_info() {
    echo -e "${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')] [INFO]${NC} $*"
}

log_error() {
    echo -e "${RED}[$(date '+%Y-%m-%d %H:%M:%S')] [ERROR]${NC} $*" >&2
}

log_warn() {
    echo -e "${YELLOW}[$(date '+%Y-%m-%d %H:%M:%S')] [WARN]${NC} $*"
}

# 加载Worker配置
load_worker_config() {
    if [ ! -f "$WORKER_CONFIG" ]; then
        log_error "Worker配置文件不存在: $WORKER_CONFIG"
        exit 1
    fi

    source "$WORKER_CONFIG"

    if [ -z "$WORKER_ID" ] || [ -z "$WORKER_SECRET" ]; then
        log_error "Worker配置不完整"
        exit 1
    fi

    log_info "Worker配置加载成功: ID=$WORKER_ID"
}

# 发送心跳
send_heartbeat() {
    local response
    response=$(curl -s -X POST "${SERVER_URL}/api/v1/workers/${WORKER_ID}/heartbeat" \
        -H "Content-Type: application/json" \
        -H "Authorization: Bearer ${WORKER_SECRET}" \
        -d '{"status": "online"}' 2>&1)

    local curl_exit_code=$?

    if [ $curl_exit_code -eq 0 ]; then
        log_info "心跳发送成功"
    else
        log_error "心跳发送失败 (curl退出码: $curl_exit_code): $response"
    fi
}

# 心跳主循环
heartbeat_loop() {
    log_info "心跳守护进程启动"
    log_info "心跳间隔: ${HEARTBEAT_INTERVAL}秒"
    log_info "Worker ID: $WORKER_ID"

    while true; do
        send_heartbeat

        # 等待下一次心跳
        sleep $HEARTBEAT_INTERVAL
    done
}

# 主函数
main() {
    log_info "TokenMachine GPU Agent - Heartbeat Daemon"
    echo "========================================="

    # 加载配置
    load_worker_config

    # 启动心跳循环
    heartbeat_loop
}

# 运行主函数
main "$@"
