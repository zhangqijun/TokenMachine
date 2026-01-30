#!/bin/bash

# TokenMachine GPU Agent 简化安装脚本
# 只复制预编译的二进制文件并启动服务

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORK_DIR="/opt/tokenmachine"
LOG_DIR="/var/log/tokenmachine"
RUN_DIR="/var/run/tokenmachine"

# 颜色定义
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
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

# 检查是否以 root 运行
check_root() {
    if [[ $EUID -ne 0 ]]; then
        log_error "此脚本必须以 root 权限运行"
        exit 1
    fi
}

# 检查 GPU 环境
check_gpu() {
    if ! command -v nvidia-smi &> /dev/null; then
        log_error "nvidia-smi 未找到"
        exit 1
    fi

    if ! nvidia-smi &> /dev/null; then
        log_error "NVIDIA 驱动未工作"
        exit 1
    fi

    log_info "GPU 环境检查通过"
    nvidia-smi --query-gpu=index,name --format=csv,noheader,nounits
}

# 创建目录结构
create_directories() {
    log_info "创建目录结构..."
    mkdir -p "$WORK_DIR"
    mkdir -p "$LOG_DIR"
    mkdir -p "$RUN_DIR/occupy_gpu"
    mkdir -p "$RUN_DIR/gpu_exporter"
    log_info "目录创建完成"
}

# 复制二进制文件
copy_binaries() {
    log_info "复制预编译的二进制文件..."

    # 检查源文件是否存在
    if [ ! -f "$SCRIPT_DIR/occupy_gpu" ]; then
        log_error "occupy_gpu 二进制文件不存在"
        exit 1
    fi

    if [ ! -f "$SCRIPT_DIR/Exporter/gpu_exporter_main" ]; then
        log_error "gpu_exporter_main 不存在"
        exit 1
    fi

    if [ ! -f "$SCRIPT_DIR/Receiver/receiver" ]; then
        log_error "receiver 不存在"
        exit 1
    fi

    # 复制文件
    cp "$SCRIPT_DIR/occupy_gpu" "$WORK_DIR/"
    cp -r "$SCRIPT_DIR/Exporter" "$WORK_DIR/"
    cp -r "$SCRIPT_DIR/Receiver" "$WORK_DIR/"
    cp "$SCRIPT_DIR/tm_agent.sh" "$WORK_DIR/"

    # 设置权限
    chmod +x "$WORK_DIR/"*
    chmod +x "$WORK_DIR/Exporter/"*
    chmod +x "$WORK_DIR/Receiver/receiver"

    log_info "二进制文件复制完成"
}

# 创建选中的 GPU 配置
create_gpu_config() {
    log_info "创建 GPU 配置..."
    echo "0" > "$RUN_DIR/selected_gpus"
    echo "1" >> "$RUN_DIR/selected_gpus"
    log_info "已选择 GPU 0 和 1"
}

# 启动服务
start_services() {
    log_info "启动服务..."

    # 启动 GPU 占用
    cd "$WORK_DIR"
    for gpu_id in 0 1; do
        log_info "启动 GPU ${gpu_id} 占用..."
        ./occupy_gpu --gpu "$gpu_id" --log "$RUN_DIR/occupy_${gpu_id}.log" &
        echo $! > "$RUN_DIR/occupy_${gpu_id}.pid"
    done

    # 启动 exporter
    log_info "启动 GPU exporter..."
    cd "$WORK_DIR/Exporter"
    export TM_SELECTED_GPUS="0 1"
    export TM_SELECTED_GPU_COUNT=2
    nohup ./gpu_exporter_main > "$RUN_DIR/exporter.log" 2>&1 &
    echo $! > "$RUN_DIR/exporter.pid"

    # 启动 receiver
    log_info "启动 Receiver..."
    cd "$WORK_DIR/Receiver"
    nohup ./receiver > "$RUN_DIR/receiver.log" 2>&1 &
    echo $! > "$RUN_DIR/receiver.pid"

    sleep 3
    log_info "服务启动完成"
}

# 显示结果
show_results() {
    echo ""
    echo -e "${GREEN}=================================${NC}"
    echo -e "${GREEN}      安装完成！${NC}"
    echo -e "${GREEN}=================================${NC}"
    echo ""

    echo "服务状态:"
    echo "  GPU 占用: $(ps aux | grep occupy_gpu | grep -v grep | wc -l) 个进程"
    echo "  Exporter: $(ps aux | grep gpu_exporter_main | grep -v grep | wc -l) 个进程"
    echo "  Receiver: $(ps aux | grep receiver | grep -v grep | wc -l) 个进程"
    echo ""

    echo "GPU 状态:"
    nvidia-smi --query-gpu=index,memory.used,memory.total --format=csv
    echo ""

    echo "管理命令:"
    echo "  查看状态: $WORK_DIR/tm_agent.sh status"
    echo "  停止服务: $WORK_DIR/tm_agent.sh stop"
    echo "  重启服务: $WORK_DIR/tm_agent.sh restart"
    echo ""

    echo "API 端点:"
    echo "  Receiver: http://localhost:9001"
    echo "  Exporter: http://localhost:9090/metrics"
    echo ""

    echo "日志位置:"
    echo "  GPU 占用: $RUN_DIR/occupy_*.log"
    echo "  Exporter: $RUN_DIR/exporter.log"
    echo "  Receiver: $RUN_DIR/receiver.log"
}

# 主函数
main() {
    log_info "开始 TokenMachine GPU Agent 简化安装"

    check_root
    check_gpu
    create_directories
    copy_binaries
    create_gpu_config
    start_services
    show_results

    log_info "安装完成！"
}

main "$@"