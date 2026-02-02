#!/bin/bash

# TokenMachine AMD Agent 服务控制脚本
# 管理 AMD GPU Agent 的启动、停止、重启和状态查询

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

# 颜色定义
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() {
    echo -e "${GREEN}[INFO]${NC} $*"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $*" >&2
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $*"
}

log_section() {
    echo ""
    echo -e "${BLUE}=================================${NC}"
    echo -e "${BLUE}      $1${NC}"
    echo -e "${BLUE}=================================${NC}"
    echo ""
}

# 创建必要的目录
create_dirs() {
    mkdir -p "$RUN_DIR"
    mkdir -p "$LOG_DIR"
    mkdir -p "$RUN_DIR/occupy_gpu"
    mkdir -p "$RUN_DIR/amd_exporter"
}

# 加载配置
load_config() {
    if [ -f "$WORK_DIR/.env" ]; then
        source "$WORK_DIR/.env"
    fi

    if [ -f "$WORK_DIR/.worker_config" ]; then
        source "$WORK_DIR/.worker_config"
    fi

    # 设置默认值
    AGENT_PORT=${TM_AGENT_PORT:-9001}
    MOCK_MODE=${TM_MOCK_MODE:-0}
}

# 检查服务是否运行
is_running() {
    local pid_file=$1
    if [ -f "$pid_file" ]; then
        local pid=$(cat "$pid_file" 2>/dev/null)
        if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
            return 0
        fi
    fi
    return 1
}

# 获取进程 PID
get_pid() {
    local pid_file=$1
    if [ -f "$pid_file" ]; then
        cat "$pid_file" 2>/dev/null
    fi
}

# 启动所有服务
start() {
    log_section "启动 AMD Agent 服务"

    load_config
    create_dirs

    local exporter_port=$((AGENT_PORT + 91))
    local started=0
    local failed=0

    # 1. 启动 GPU 占用进程
    log_info "启动 GPU 占用进程..."
    if [ -f "$RUN_DIR/selected_gpus" ]; then
        while IFS= read -r gpu_id; do
            if [ -n "$gpu_id" ]; then
                local pid_file="$RUN_DIR/occupy_${gpu_id}.pid"
                if is_running "$pid_file"; then
                    log_warn "GPU ${gpu_id} 占用进程已在运行 (PID: $(get_pid $pid_file))"
                else
                    cd "$WORK_DIR/occupier"
                    if [[ $MOCK_MODE -eq 1 ]]; then
                        ./occupy_gpu --gpu "$gpu_id" --percent 90 --mock > "$RUN_DIR/occupy_${gpu_id}.log" 2>&1 &
                    else
                        ./occupy_gpu --gpu "$gpu_id" --percent 90 > "$RUN_DIR/occupy_${gpu_id}.log" 2>&1 &
                    fi
                    echo $! > "$pid_file"
                    sleep 1
                    if is_running "$pid_file"; then
                        log_info "  ✓ GPU ${gpu_id} 占用进程已启动 (PID: $(get_pid $pid_file))"
                        ((started++))
                    else
                        log_error "  ✗ GPU ${gpu_id} 占用进程启动失败"
                        ((failed++))
                    fi
                fi
            fi
        done < "$RUN_DIR/selected_gpus"
    else
        # 默认启动 GPU 0
        cd "$WORK_DIR/occupier"
        if [[ $MOCK_MODE -eq 1 ]]; then
            ./occupy_gpu --gpu 0 --percent 90 --mock > "$RUN_DIR/occupy_0.log" 2>&1 &
        else
            ./occupy_gpu --gpu 0 --percent 90 > "$RUN_DIR/occupy_0.log" 2>&1 &
        fi
        echo $! > "$RUN_DIR/occupy_0.pid"
        sleep 1
        if is_running "$RUN_DIR/occupy_0.pid"; then
            log_info "  ✓ GPU 0 占用进程已启动"
            ((started++))
        else
            log_error "  ✗ GPU 0 占用进程启动失败"
            ((failed++))
        fi
    fi

    # 2. 启动 Exporter
    log_info "启动 AMD Exporter (端口: $exporter_port)..."
    cd "$WORK_DIR/Exporter"
    export TM_MOCK_MODE=$MOCK_MODE

    if is_running "$RUN_DIR/exporter.pid"; then
        log_warn "Exporter 已在运行 (PID: $(get_pid $RUN_DIR/exporter.pid))"
    else
        if [[ $MOCK_MODE -eq 1 ]]; then
            nohup ./amd_exporter_main --port $exporter_port --mock > "$RUN_DIR/exporter.log" 2>&1 &
        else
            nohup ./amd_exporter_main --port $exporter_port > "$RUN_DIR/exporter.log" 2>&1 &
        fi
        echo $! > "$RUN_DIR/exporter.pid"
        sleep 2
        if is_running "$RUN_DIR/exporter.pid"; then
            log_info "  ✓ Exporter 已启动 (PID: $(get_pid $RUN_DIR/exporter.pid))"
            ((started++))
        else
            log_error "  ✗ Exporter 启动失败"
            ((failed++))
        fi
    fi

    # 3. 启动 Receiver
    log_info "启动 Receiver (端口: $AGENT_PORT)..."
    cd "$WORK_DIR/Receiver"
    export TM_RECEIVER_PORT=$AGENT_PORT
    export TM_WORK_DIR="$WORK_DIR"
    export TM_RECEIVER_LOG="$RUN_DIR/receiver.log"

    if is_running "$RUN_DIR/receiver.pid"; then
        log_warn "Receiver 已在运行 (PID: $(get_pid $RUN_DIR/receiver.pid))"
    else
        nohup ./receiver > "$RUN_DIR/receiver.log" 2>&1 &
        echo $! > "$RUN_DIR/receiver.pid"
        sleep 2
        if is_running "$RUN_DIR/receiver.pid"; then
            log_info "  ✓ Receiver 已启动 (PID: $(get_pid $RUN_DIR/receiver.pid))"
            ((started++))
        else
            log_error "  ✗ Receiver 启动失败"
            ((failed++))
        fi
    fi

    # 4. 启动心跳
    log_info "启动心跳守护进程..."
    cd "$WORK_DIR"
    export TM_MOCK_MODE=$MOCK_MODE

    if is_running "$RUN_DIR/heartbeat.pid"; then
        log_warn "心跳已在运行 (PID: $(get_pid $RUN_DIR/heartbeat.pid))"
    else
        nohup ./heartbeat.sh > "$RUN_DIR/heartbeat.log" 2>&1 &
        echo $! > "$RUN_DIR/heartbeat.pid"
        sleep 1
        if is_running "$RUN_DIR/heartbeat.pid"; then
            log_info "  ✓ 心跳已启动 (PID: $(get_pid $RUN_DIR/heartbeat.pid))"
            ((started++))
        else
            log_error "  ✗ 心跳启动失败"
            ((failed++))
        fi
    fi

    echo ""
    log_info "启动完成: $started 成功, $failed 失败"

    return $failed
}

# 停止所有服务
stop() {
    log_section "停止 AMD Agent 服务"

    local stopped=0
    local not_running=0

    # 1. 停止心跳
    log_info "停止心跳..."
    if is_running "$RUN_DIR/heartbeat.pid"; then
        kill $(get_pid "$RUN_DIR/heartbeat.pid") 2>/dev/null || true
        rm -f "$RUN_DIR/heartbeat.pid"
        log_info "  ✓ 心跳已停止"
        ((stopped++))
    else
        log_warn "  心跳未运行"
        ((not_running++))
    fi

    # 2. 停止 Receiver
    log_info "停止 Receiver..."
    if is_running "$RUN_DIR/receiver.pid"; then
        kill $(get_pid "$RUN_DIR/receiver.pid") 2>/dev/null || true
        rm -f "$RUN_DIR/receiver.pid"
        log_info "  ✓ Receiver 已停止"
        ((stopped++))
    else
        log_warn "  Receiver 未运行"
        ((not_running++))
    fi

    # 3. 停止 Exporter
    log_info "停止 Exporter..."
    if is_running "$RUN_DIR/exporter.pid"; then
        kill $(get_pid "$RUN_DIR/exporter.pid") 2>/dev/null || true
        rm -f "$RUN_DIR/exporter.pid"
        log_info "  ✓ Exporter 已停止"
        ((stopped++))
    else
        log_warn "  Exporter 未运行"
        ((not_running++))
    fi

    # 4. 停止 GPU 占用进程
    log_info "停止 GPU 占用进程..."
    for pid_file in "$RUN_DIR"/occupy_*.pid; do
        if [ -f "$pid_file" ] && is_running "$pid_file"; then
            kill $(get_pid "$pid_file") 2>/dev/null || true
            rm -f "$pid_file"
            ((stopped++))
        fi
    done
    # 强制清理残留进程
    pkill -f "occupy_gpu.*amd" 2>/dev/null || true
    log_info "  ✓ GPU 占用进程已停止 ($stopped 个)"

    # 清理 PID 文件
    rm -f "$RUN_DIR"/occupy_*.pid 2>/dev/null || true

    echo ""
    log_info "停止完成: $stopped 停止, $not_running 未运行"

    return 0
}

# 重启所有服务
restart() {
    log_section "重启 AMD Agent 服务"

    stop
    sleep 2
    start
}

# 查看状态
status() {
    log_section "AMD Agent 服务状态"

    load_config

    echo "工作目录: $WORK_DIR"
    echo "Agent 端口: $AGENT_PORT"
    echo "模拟模式: $([[ $MOCK_MODE -eq 1 ]] && echo '是' || echo '否')"
    echo ""

    local running=0
    local total=0

    # GPU 占用进程
    echo "GPU 占用进程:"
    for pid_file in "$RUN_DIR"/occupy_*.pid 2>/dev/null; do
        if [ -f "$pid_file" ]; then
            ((total++))
            local pid=$(get_pid "$pid_file")
            if is_running "$pid_file"; then
                echo -e "  ✓ GPU ${pid_file##*/occupy_}.pid: 运行中 (PID: $pid)"
                ((running++))
            else
                echo -e "  ✗ GPU ${pid_file##*/occupy_}.pid: 未运行 (PID文件存在但进程不存在)"
            fi
        fi
    done
    if [ $total -eq 0 ]; then
        echo "  无 GPU 占用进程"
    fi
    echo ""

    # Exporter
    echo "AMD Exporter (端口: $((AGENT_PORT + 91))):"
    if is_running "$RUN_DIR/exporter.pid"; then
        echo -e "  ✓ 运行中 (PID: $(get_pid "$RUN_DIR/exporter.pid"))"
        ((running++))
    else
        echo -e "  ✗ 未运行"
    fi
    ((total++))
    echo ""

    # Receiver
    echo "Receiver (端口: $AGENT_PORT):"
    if is_running "$RUN_DIR/receiver.pid"; then
        echo -e "  ✓ 运行中 (PID: $(get_pid "$RUN_DIR/receiver.pid"))"
        ((running++))
    else
        echo -e "  ✗ 未运行"
    fi
    ((total++))
    echo ""

    # Heartbeat
    echo "心跳守护进程:"
    if is_running "$RUN_DIR/heartbeat.pid"; then
        echo -e "  ✓ 运行中 (PID: $(get_pid "$RUN_DIR/heartbeat.pid"))"
        ((running++))
    else
        echo -e "  ✗ 未运行"
    fi
    ((total++))
    echo ""

    echo "================================"
    echo "总进程数: $total"
    echo "运行中: $running"
    echo "已停止: $((total - running))"
    echo "================================"

    if [ $running -eq $total ]; then
        return 0
    else
        return 1
    fi
}

# 查看日志
logs() {
    local service=${1:-all}
    local follow=${2:-0}

    log_section "$service 日志"

    case $service in
        exporter)
            tail -f "$RUN_DIR/exporter.log"
            ;;
        receiver)
            tail -f "$RUN_DIR/receiver.log"
            ;;
        heartbeat)
            tail -f "$RUN_DIR/heartbeat.log"
            ;;
        occupy)
            tail -f "$RUN_DIR/occupy_*.log"
            ;;
        all)
            tail -f "$RUN_DIR"/*.log
            ;;
        *)
            echo "未知服务: $service"
            echo "可用服务: exporter, receiver, heartbeat, occupy, all"
            exit 1
            ;;
    esac
}

# 显示帮助
help() {
    echo "TokenMachine AMD Agent 服务控制脚本"
    echo "====================================="
    echo ""
    echo "用法: $0 <命令> [参数]"
    echo ""
    echo "命令:"
    echo "  start           启动所有服务"
    echo "  stop            停止所有服务"
    echo "  restart         重启所有服务"
    echo "  status          查看服务状态"
    echo "  logs [服务]     查看日志 (exporter|receiver|heartbeat|occupy|all)"
    echo "  help            显示此帮助信息"
    echo ""
    echo "示例:"
    echo "  $0 start           # 启动所有服务"
    echo "  $0 stop            # 停止所有服务"
    echo "  $0 status          # 查看状态"
    echo "  $0 logs receiver   # 查看 Receiver 日志"
}

# 主逻辑
case "${1:-help}" in
    start)
        start
        ;;
    stop)
        stop
        ;;
    restart)
        restart
        ;;
    status)
        status
        ;;
    logs)
        logs "${2:-all}"
        ;;
    help|--help|-h)
        help
        ;;
    *)
        log_error "未知命令: $1"
        help
        exit 1
        ;;
esac
