#!/bin/bash

# TokenMachine GPU Agent Control Script
# 只负责运行，不负责编译

set -e

# 配置
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OCCUPY_DIR="$SCRIPT_DIR/occupier"
EXPORTER_DIR="$SCRIPT_DIR/Exporter"
RECEIVER_DIR="$SCRIPT_DIR/Receiver"
VAR_RUN_DIR="/var/run/tokenmachine"
LOG_FILE="/var/log/tokenmachine/agent.log"
CONFIG_FILE="/etc/tokenmachine/config"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 日志函数
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1" | tee -a "$LOG_FILE"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1" | tee -a "$LOG_FILE"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1" | tee -a "$LOG_FILE"
}

# 检查命令是否存在
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# 检查运行环境
check_environment() {
    # 检查 nvidia-smi
    if ! command_exists nvidia-smi; then
        log_error "nvidia-smi not found"
        return 1
    fi

    # 检查驱动
    if ! nvidia-smi >/dev/null 2>&1; then
        log_error "NVIDIA driver not working"
        return 1
    fi

    log_info "Environment check passed"
}

# 获取选中的 GPU 列表
get_selected_gpus() {
    local selected_file="$VAR_RUN_DIR/selected_gpus"
    if [ -f "$selected_file" ]; then
        cat "$selected_file"
        return 0
    else
        log_warn "No GPU selection file found, using default"
        echo "0 1"
        return 1
    fi
}

# 启动 GPU 占用
start_gpu_occupation() {
    log_info "Starting GPU occupation"

    local selected_gpus=($(get_selected_gpus))
    local gpu_count=${#selected_gpus[@]}

    if [ $gpu_count -eq 0 ]; then
        log_error "No GPUs selected"
        return 1
    fi

    # 创建日志目录
    sudo mkdir -p "$(dirname "$LOG_FILE")"
    sudo mkdir -p "$VAR_RUN_DIR"

    # 启动每个 GPU 的占用程序
    for gpu_id in "${selected_gpus[@]}"; do
        if [ -f "$OCCUPY_DIR/occupy_gpu" ]; then
            local log_file="$VAR_RUN_DIR/occupy_${gpu_id}.log"

            # 检查是否已经运行
            if pgrep -f "occupy_gpu.*--gpu $gpu_id" > /dev/null; then
                log_warn "GPU $gpu_id occupation already running"
                continue
            fi

            sudo nohup "$OCCUPY_DIR/occupy_gpu" --gpu "$gpu_id" --log "$log_file" > /dev/null 2>&1 &
            local pid=$!
            echo "$pid" > "$VAR_RUN_DIR/occupy_${gpu_id}.pid"
            log_info "GPU $gpu_id occupation started with PID $pid"
        else
            log_error "occupy_gpu binary not found in $OCCUPY_DIR"
            return 1
        fi
    done
}

# 停止 GPU 占用
stop_gpu_occupation() {
    log_info "Stopping GPU occupation"

    # 停止所有 occupy_gpu 进程
    local pids=$(pgrep -f "occupy_gpu" || true)
    if [ -n "$pids" ]; then
        echo "$pids" | xargs -r sudo kill -TERM 2>/dev/null || true
        sleep 2

        # 检查是否还有运行中的进程
        local remaining=$(pgrep -f "occupy_gpu" || true)
        if [ -n "$remaining" ]; then
            echo "$remaining" | xargs -r sudo kill -KILL 2>/dev/null || true
            log_warn "Some GPU occupation processes were forcefully terminated"
        fi
    fi

    # 清理 PID 文件
    rm -f "$VAR_RUN_DIR"/occupy_*.pid
}

# 启动 GPU exporter
start_gpu_exporter() {
    log_info "Starting GPU exporter"

    cd "$EXPORTER_DIR"
    if [ -f "gpu_exporter_main" ]; then
        # 设置选中的 GPU 环境变量
        export TM_SELECTED_GPUS="${gpu_ids[*]}"
        export TM_SELECTED_GPU_COUNT=${#gpu_ids[@]}

        sudo nohup ./gpu_exporter_main > "$VAR_RUN_DIR/exporter.log" 2>&1 &
        local pid=$!
        echo "$pid" > "$VAR_RUN_DIR/exporter.pid"
        log_info "GPU exporter started with PID $pid, monitoring ${#gpu_ids[@]} GPUs"
    else
        log_error "gpu_exporter_main not found"
    fi
}

# 启动 Receiver
start_receiver() {
    log_info "Starting Receiver"

    cd "$RECEIVER_DIR"
    if [ -f "receiver" ]; then
        # 加载环境变量配置
        if [ -f "$WORK_DIR/.env" ]; then
            source "$WORK_DIR/.env"
            log_info "已加载环境变量配置: TM_SERVER_URL=$TM_SERVER_URL"
        fi

        sudo nohup ./receiver > "$VAR_RUN_DIR/receiver.log" 2>&1 &
        local pid=$!
        echo "$pid" > "$VAR_RUN_DIR/receiver.pid"
        log_info "Receiver started with PID $pid"

        # 等待服务启动
        sleep 2

        # 检查服务是否正常运行
        if curl -s "http://localhost:9001/health" > /dev/null; then
            log_info "Receiver health check passed"
        else
            log_warn "Receiver health check failed"
        fi
    else
        log_error "receiver binary not found"
    fi
}

# 停止 GPU exporter
stop_gpu_exporter() {
    log_info "Stopping GPU exporter"

    if [ -f "$VAR_RUN_DIR/exporter.pid" ]; then
        local pid=$(cat "$VAR_RUN_DIR/exporter.pid")
        if ps -p "$pid" > /dev/null 2>&1; then
            log_info "Stopping GPU exporter process $pid"
            sudo kill "$pid" 2>/dev/null || true
            sleep 1
            if ps -p "$pid" > /dev/null 2>&1; then
                sudo kill -9 "$pid" 2>/dev/null || true
            fi
        fi
        rm -f "$VAR_RUN_DIR/exporter.pid"
    fi
}

# 停止 Receiver
stop_receiver() {
    log_info "Stopping Receiver"

    if [ -f "$VAR_RUN_DIR/receiver.pid" ]; then
        local pid=$(cat "$VAR_RUN_DIR/receiver.pid")
        if ps -p "$pid" > /dev/null 2>&1; then
            log_info "Stopping Receiver process $pid"
            sudo kill "$pid" 2>/dev/null || true
            sleep 1
            if ps -p "$pid" > /dev/null 2>&1; then
                sudo kill -9 "$pid" 2>/dev/null || true
            fi
        fi
        rm -f "$VAR_RUN_DIR/receiver.pid"
    fi
}

# 启动服务
start_service() {
    log_info "Starting TokenMachine GPU Agent service"

    # 创建必要目录
    sudo mkdir -p "$VAR_RUN_DIR"
    sudo mkdir -p "$(dirname "$LOG_FILE")"

    # 显示 GPU 选择界面（如果还没有选择过）
    local selected_gpus_file="$VAR_RUN_DIR/selected_gpus"
    if [ ! -f "$selected_gpus_file" ] && [ ! -f "$CONFIG_FILE" ]; then
        log_info "第一次运行，请选择要管理的 GPU"
        show_gpu_selection
    fi

    # 显示选中的 GPU
    if [ -f "$selected_gpus_file" ]; then
        local selected=($(cat "$selected_gpus_file"))
        log_info "已选中的 GPU: ${selected[*]}"
    fi

    # 启动 GPU 占用程序
    start_gpu_occupation

    # 启动 GPU exporter
    start_gpu_exporter

    # 启动 Receiver
    start_receiver

    # 启动 Heartbeat
    if [ -f "$WORK_DIR/heartbeat.sh" ] && [ -f "$WORK_DIR/.worker_config" ]; then
        log_info "Starting Heartbeat..."
        cd "$WORK_DIR"
        nohup ./heartbeat.sh > "$VAR_RUN_DIR/heartbeat.log" 2>&1 &
        echo $! > "$VAR_RUN_DIR/heartbeat.pid"
        log_info "Heartbeat started with PID $(cat $VAR_RUN_DIR/heartbeat.pid)"
    else
        log_warn "Heartbeat script or worker config not found, skipping"
    fi

    log_info "All services started"
}

# 停止 Heartbeat
stop_heartbeat() {
    if [ -f "$VAR_RUN_DIR/heartbeat.pid" ]; then
        local pid=$(cat "$VAR_RUN_DIR/heartbeat.pid")
        if ps -p "$pid" > /dev/null 2>&1; then
            log_info "Stopping heartbeat (PID: $pid)..."
            kill "$pid"
            rm -f "$VAR_RUN_DIR/heartbeat.pid"
            log_info "Heartbeat stopped"
        else
            log_warn "Heartbeat process not running"
            rm -f "$VAR_RUN_DIR/heartbeat.pid"
        fi
    else
        log_info "Heartbeat PID file not found"
    fi

    # 强制杀死所有heartbeat进程（备用）
    pkill -f "heartbeat.sh" || true
}

# 停止服务
stop_service() {
    log_info "Stopping TokenMachine GPU Agent service"

    stop_heartbeat
    stop_receiver
    stop_gpu_exporter
    stop_gpu_occupation

    log_info "All services stopped"
}

# 显示服务状态
show_status() {
    echo "=================================================="
    echo "TokenMachine GPU Agent Status"
    echo "=================================================="

    local gpu_count=0
    local gpu_occupation_count=0
    local exporter_count=0
    local receiver_count=0
    local heartbeat_count=0

    # 统计 GPU 占用进程
    gpu_occupation_count=$(pgrep -f "occupy_gpu" | wc -l)
    if [ "$gpu_occupation_count" -gt 0 ]; then
        echo -e "${GREEN}GPU 占用: $gpu_occupation_count 个进程${NC}"
    else
        echo -e "${RED}GPU 占用: 0 个进程${NC}"
    fi

    # 统计 Exporter 进程
    exporter_count=$(pgrep -f "gpu_exporter_main" | wc -l)
    if [ "$exporter_count" -gt 0 ]; then
        echo -e "${GREEN}Exporter: $exporter_count 个进程${NC}"
    else
        echo -e "${RED}Exporter: 0 个进程${NC}"
    fi

    # 统计 Receiver 进程
    receiver_count=$(pgrep -f "receiver" | wc -l)
    if [ "$receiver_count" -gt 0 ]; then
        echo -e "${GREEN}Receiver: $receiver_count 个进程${NC}"
    else
        echo -e "${RED}Receiver: 0 个进程${NC}"
    fi

    # 统计 Heartbeat 进程
    heartbeat_count=$(pgrep -f "heartbeat.sh" | wc -l)
    if [ "$heartbeat_count" -gt 0 ]; then
        echo -e "${GREEN}Heartbeat: $heartbeat_count 个进程${NC}"
    else
        echo -e "${RED}Heartbeat: 0 个进程${NC}"
    fi

    # 检查端口占用
    echo ""
    echo "端口占用情况:"
    if netstat -tlnp 2>/dev/null | grep -q ":9001"; then
        echo -e "${GREEN}Receiver: 端口 9001 正在使用${NC}"
    else
        echo -e "${RED}Receiver: 端口 9001 未使用${NC}"
    fi

    if netstat -tlnp 2>/dev/null | grep -q ":9090"; then
        echo -e "${GREEN}Exporter: 端口 9090 正在使用${NC}"
    else
        echo -e "${RED}Exporter: 端口 9090 未使用${NC}"
    fi

    # 显示最近的日志
    echo ""
    echo "最近日志 (最后5行):"
    if [ -f "$LOG_FILE" ]; then
        tail -n 5 "$LOG_FILE"
    else
        echo "日志文件不存在"
    fi
}

# 交互式 GPU 选择界面
show_gpu_selection() {
    echo "=================================================="
    echo "TokenMachine GPU Agent"
    echo "=================================================="
    echo "请选择要管理的 GPU（使用空格键选择，上下键切换）："

    # 获取 GPU 列表
    local gpu_list=()
    local gpu_index=0
    while IFS= read -r line; do
        if [[ $line =~ ^[0-9]+ ]]; then
            local name=$(echo "$line" | awk -F', ' '{print $2}')
            gpu_list[$gpu_index]="$name"
            gpu_index=$((gpu_index + 1))
        fi
    done < <(nvidia-smi --query-gpu=index,name --format=csv,noheader 2>/dev/null || true)

    if [ ${#gpu_list[@]} -eq 0 ]; then
        log_error "未找到可用的 GPU"
        exit 1
    fi

    # 显示 GPU 列表
    local selected=()
    local gpu_count=${#gpu_list[@]}
    local cursor=0

    # 读取选中的 GPU
    if [ -f "$VAR_RUN_DIR/selected_gpus" ]; then
        selected=($(cat "$VAR_RUN_DIR/selected_gpus"))
    fi

    # 如果没有选中，默认选择所有
    if [ ${#selected[@]} -eq 0 ]; then
        for ((i=0; i<gpu_count; i++)); do
            selected[i]=1
        done
    fi

    # 简单的选择显示（实际实现可以使用更复杂的 TUI 库）
    for ((i=0; i<gpu_count; i++)); do
        if [ ${selected[i]} -eq 1 ]; then
            echo "■ [$i] ${gpu_list[i]} [已选择]"
        else
            echo "□ [$i] ${gpu_list[i]} [未选择]"
        fi
    done

    echo ""
    echo "操作："
    echo "空格: 切换选择 (当前GPU: $cursor)"
    echo "回车: 确认选择"
    echo "q:   退出程序"
    echo -n ">"

    while true; do
        read -r -n1 key
        case "$key" in
            ' ')
                selected[$cursor]=$((1 - selected[$cursor]))
                # 重新显示
                clear
                echo "=================================================="
                echo "TokenMachine GPU Agent"
                echo "=================================================="
                echo "请选择要管理的 GPU（使用空格键选择，上下键切换）："
                for ((i=0; i<gpu_count; i++)); do
                    if [ ${selected[i]} -eq 1 ]; then
                        echo "■ [$i] ${gpu_list[i]} [已选择]"
                    else
                        echo "□ [$i] ${gpu_list[i]} [未选择]"
                    fi
                done
                echo ""
                echo "操作："
                echo "空格: 切换选择 (当前GPU: $cursor)"
                echo "回车: 确认选择"
                echo "q:   退出程序"
                echo -n ">"
                ;;
            $'\r') # Enter
                break
                ;;
            'q')
                log_info "User chose to quit"
                exit 0
                ;;
        esac
    done

    # 保存选择
    echo "${selected[@]}" | tr ' ' '\n' > "$VAR_RUN_DIR/selected_gpus"
    log_info "GPU selection saved"
}

# 主函数
main() {
    case "${1:-}" in
        start)
            check_environment
            start_service
            ;;
        stop)
            stop_service
            ;;
        restart)
            stop_service
            sleep 2
            check_environment
            start_service
            ;;
        status)
            show_status
            ;;
        select)
            show_gpu_selection
            ;;
        *)
            echo "Usage: $0 {start|stop|restart|status|select}"
            echo "  start    - Start the service"
            echo "  stop     - Stop the service"
            echo "  restart  - Restart the service"
            echo "  status   - Show service status"
            echo "  select   - Select GPUs to manage"
            exit 1
            ;;
    esac
}

# 运行主函数
main "$@"