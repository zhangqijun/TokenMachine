#!/bin/bash

# TokenMachine AMD Agent 安装脚本
# 支持 AMD ROCm 平台的 GPU Agent

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# 自动检测用户目录模式（非 root 用户自动使用用户目录）
if [[ $EUID -ne 0 ]]; then
    USER_HOME="${HOME:-/tmp}"
    WORK_DIR="${USER_HOME}/.local/tokenmachine_amd"
    LOG_DIR="${USER_HOME}/.local/logs/tokenmachine_amd"
    RUN_DIR="${USER_HOME}/.local/run/tokenmachine_amd"
    echo "[INFO] 用户目录模式: $WORK_DIR"
else
    WORK_DIR="/opt/tokenmachine-amd"
    LOG_DIR="/var/log/tokenmachine-amd"
    RUN_DIR="/var/run/tokenmachine-amd"
fi

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

# 初始化变量
TOKEN=""
SERVER_URL=""
AGENT_PORT=""
WORKER_ID=""
WORKER_SECRET=""
DETECTED_IPS=()
REACHABLE_IP=""
SELECTED_GPUS=""  # 选中的GPU列表（空=自动检测）
GPU_COUNT=0       # 实际GPU数量
MOCK_MODE=0       # 模拟模式（无真实AMD硬件时使用）

# Prometheus 服务发现配置
PROMETHEUS_SD_DIR="/etc/prometheus/workers"  # Prometheus SD 文件目录

# 检查是否以 root 运行
check_root() {
    if [[ $EUID -ne 0 ]]; then
        log_warn "非 root 用户运行，将使用用户目录模式"
    fi
}

# 检查系统依赖
check_dependencies() {
    log_info "检查系统依赖..."

    local required_commands=("rocm-smi" "git" "curl" "systemctl")

    for cmd in "${required_commands[@]}"; do
        if ! command -v "$cmd" &> /dev/null; then
            # rocm-smi 不存在时，可能是在模拟模式
            if [[ "$cmd" == "rocm-smi" ]]; then
                log_warn "rocm-smi 未找到，将使用模拟模式"
                MOCK_MODE=1
                continue
            fi
            log_error "缺少必要的命令: $cmd"
            exit 1
        fi
    done

    log_info "所有依赖检查通过"
}

# 检查 ROCm 环境
check_rocm() {
    if [[ $MOCK_MODE -eq 1 ]]; then
        log_info "模拟模式: 跳过 ROCm 检查"
        GPU_COUNT=1
        SELECTED_GPUS="0"
        return 0
    fi

    if ! rocm-smi &> /dev/null; then
        log_warn "rocm-smi 未工作，检查是否在模拟模式..."
        MOCK_MODE=1
        GPU_COUNT=1
        SELECTED_GPUS="0"
        return 0
    fi

    # 检测实际GPU数量
    GPU_COUNT=$(rocm-smi --list | grep -c "GPU")
    if [[ $GPU_COUNT -eq 0 ]]; then
        log_warn "未检测到 AMD GPU，进入模拟模式"
        MOCK_MODE=1
        GPU_COUNT=1
        SELECTED_GPUS="0"
        return 0
    fi

    log_info "检测到 $GPU_COUNT 个 AMD GPU"

    # 如果没有指定GPU，自动选择第一个
    if [ -z "$SELECTED_GPUS" ]; then
        SELECTED_GPUS="0"
        log_info "自动选择GPU: $SELECTED_GPUS"
    else
        log_info "使用指定的GPU: $SELECTED_GPUS"
    fi

    log_info "ROCm 环境检查通过"
    rocm-smi --showproductname
}

# 获取所有可用的IP地址
get_local_ips() {
    log_info "检测本地IP地址..."

    local ips=()

    # 方法1: 使用ip命令（推荐）
    if command -v ip &> /dev/null; then
        while IFS= read -r line; do
            local ip=$(echo "$line" | awk '{print $1}')
            if [[ ! "$ip" =~ ^127\. ]] && [[ ! "$ip" =~ ^169\.254\. ]]; then
                ips+=("$ip")
            fi
        done < <(ip -4 addr show | grep -oP '(?<=inet\s)\d+(\.\d+){3}' | sort -u)
    elif command -v hostname &> /dev/null; then
        while IFS= read -r ip; do
            if [[ ! "$ip" =~ ^127\. ]] && [[ ! "$ip" =~ ^169\.254\. ]]; then
                ips+=("$ip")
            fi
        done < <(hostname -I 2>/dev/null || echo "")
    fi

    if [ ${#ips[@]} -eq 0 ]; then
        log_warn "未检测到可用的IP地址，使用默认值"
        ips=("127.0.0.1")
    fi

    log_info "检测到 ${#ips[@]} 个IP地址:"
    for ip in "${ips[@]}"; do
        log_info "  - $ip"
    done

    DETECTED_IPS=("${ips[@]}")
}

# 创建目录结构
create_directories() {
    log_info "创建目录结构..."
    mkdir -p "$WORK_DIR"
    mkdir -p "$LOG_DIR"
    mkdir -p "$RUN_DIR/occupy_gpu"
    mkdir -p "$RUN_DIR/amd_exporter"
    log_info "目录创建完成"
}

# 检查预编译的二进制文件
check_precompiled_binaries() {
    log_info "检查预编译的二进制文件..."

    # 检查 Exporter 是否存在
    if [ ! -f "$SCRIPT_DIR/Exporter/amd_exporter_main" ]; then
        log_error "预编译的 amd_exporter_main 不存在"
        log_error "请先在本地运行: cd Exporter && ./build.sh"
        exit 1
    fi
    log_info "✓ 预编译的 amd_exporter_main 存在"

    # 检查 Receiver 是否存在
    if [ ! -f "$SCRIPT_DIR/Receiver/receiver" ]; then
        log_error "预编译的 receiver 不存在"
        log_error "请先在本地运行: cd Receiver && ./build.sh"
        exit 1
    fi
    log_info "✓ 预编译的 receiver 存在"

    # 检查 occupy_gpu 源文件
    if [ ! -f "$SCRIPT_DIR/occupier/occupy_gpu.hip" ]; then
        log_error "occupy_gpu.hip 源文件不存在"
        exit 1
    fi
    log_info "✓ occupy_gpu.hip 源文件存在"

    # 验证预编译二进制是静态链接
    log_info "验证预编译二进制..."

    if command -v file > /dev/null; then
        if ! file "$SCRIPT_DIR/Exporter/amd_exporter_main" | grep -q "statically linked"; then
            log_warn "⚠ amd_exporter_main 可能不是静态链接"
        else
            log_info "✓ amd_exporter_main 是静态链接"
        fi

        if ! file "$SCRIPT_DIR/Receiver/receiver" | grep -q "statically linked"; then
            log_warn "⚠ receiver 可能不是静态链接"
        else
            log_info "✓ receiver 是静态链接"
        fi
    fi

    log_info "所有预编译文件检查通过"
}

# 编译 occupy_gpu（HIP 程序）
compile_occupy_gpu() {
    if [[ $MOCK_MODE -eq 1 ]]; then
        log_info "模拟模式: 跳过 HIP 编译"
        return 0
    fi

    log_info "编译 occupy_gpu（HIP 程序）..."

    cd "$SCRIPT_DIR"

    # 检查 HIP 路径
    export HIP_PATH="/opt/rocm/hip"
    if [ ! -f "$HIP_PATH/bin/hipcc" ]; then
        if [ -f "/opt/rocm-*/hip/bin/hipcc" ]; then
            HIP_PATH=$(ls -d /opt/rocm-* | tail -1)/hip
        else
            log_error "找不到 HIP Toolkit 安装"
            log_error "请安装 ROCm HIP Toolkit"
            exit 1
        fi
    fi

    export PATH="$HIP_PATH/bin:$PATH"
    log_info "使用 HIP 路径: $HIP_PATH"

    # 检查 hipcc 是否可用
    if ! command -v hipcc &> /dev/null; then
        log_error "hipcc 不可用，请检查 ROCm HIP 安装"
        exit 1
    fi

    # 编译 occupy_gpu
    if [ ! -f "occupier/occupy_gpu.hip" ]; then
        log_error "找不到 occupy_gpu.hip 源文件"
        exit 1
    fi

    log_info "编译 occupy_gpu.hip..."
    if ! hipcc -O3 -o occupy_gpu occupier/occupy_gpu.hip 2>&1; then
        log_error "编译 occupy_gpu.hip 失败"
        exit 1
    fi

    # 优化二进制文件
    if command -v strip &> /dev/null; then
        strip occupy_gpu
        log_info "已优化 occupy_gpu 二进制"
    fi

    chmod +x occupy_gpu
    log_info "✓ occupy_gpu 编译完成"
}

# 更新 Prometheus 服务发现文件
update_prometheus_sd() {
    local worker_ip=$1
    local worker_id=$2
    local worker_name=$3
    local exporter_port="${AGENT_PORT}91"  # Exporter 端口 = Agent 端口 + 91 (AMD 使用 91 避免冲突)

    log_info "更新 Prometheus 服务发现文件..."

    if [[ $EUID -ne 0 ]]; then
        log_warn "非 root 用户模式，跳过 Prometheus SD 文件创建"
        return 0
    fi

    mkdir -p "$PROMETHEUS_SD_DIR"

    local sd_file="${PROMETHEUS_SD_DIR}/amd-worker-${worker_id}.json"
    cat > "$sd_file" << EOF
[
  {
    "targets": ["${worker_ip}:${exporter_port}"],
    "labels": {
      "worker_id": "${worker_id}",
      "worker_name": "${worker_name}",
      "instance": "${worker_name}",
      "gpu_vendor": "amd"
    }
  }
]
EOF

    log_info "✓ Prometheus SD 文件已创建: $sd_file"

    if command -v curl &> /dev/null; then
        if curl -s "localhost:9090/-/reload" &>/dev/null; then
            log_info "✓ Prometheus 配置已重载"
        else
            log_info "  (Prometheus 自动重载将在 1 分钟内生效)"
        fi fi
}

# 移除 Prometheus 服务发现文件
remove_prometheus_sd() {
    local worker_id=$1

    if [[ $EUID -ne 0 ]]; then
        return 0
    fi

    local sd_file="${PROMETHEUS_SD_DIR}/amd-worker-${worker_id}.json"
    if [ -f "$sd_file" ]; then
        rm -f "$sd_file"
        log_info "✓ Prometheus SD 文件已移除: $sd_file"
    fi
}

# 注册Worker到Backend
register_worker() {
    log_info "注册Worker到Backend..."

    local worker_name="${HOSTNAME}-amd-${TOKEN:0:8}"
    local worker_hostname=$(hostname)
    local gpu_count=$GPU_COUNT

    log_info "Worker信息:"
    log_info "  名称: $worker_name"
    log_info "  主机名: $worker_hostname"
    log_info "  GPU数量: $gpu_count"
    log_info "  模拟模式: $MOCK_MODE"
    log_info "  检测到的IP: ${DETECTED_IPS[*]}"

    # 1. 验证IP连通性
    log_info "验证IP连通性..."

    local ips_json="["
    local first=true
    for ip in "${DETECTED_IPS[@]}"; do
        if [ "$first" = true ]; then
            ips_json="$ips_json\"$ip\""
            first=false
        else
            ips_json="$ips_json, \"$ip\""
        fi
    done
    ips_json="$ips_json]"

    local verify_response=$(curl -s -X POST "${SERVER_URL}/workers/verify-ips" \
        -H "Content-Type: application/json" \
        -H "Authorization: Bearer ${TOKEN}" \
        -d "{\"ips\": ${ips_json}}" 2>&1)

    if [ $? -ne 0 ]; then
        log_error "IP验证失败: $verify_response"
        log_warn "将使用第一个检测到的IP继续注册"
        REACHABLE_IP="${DETECTED_IPS[0]}"
    else
        REACHABLE_IP="${DETECTED_IPS[0]}"
    fi

    log_info "使用IP地址: $REACHABLE_IP"

    # 2. 注册Worker
    log_info "注册Worker..."

    # 构建GPU信息JSON（模拟模式使用模拟数据）
    local gpu_models_json="[\"AMD Radeon RX 6800 XT (simulated)\"]"
    local memory_json="[\"16384\"]"
    local indices_json="[\"0\"]"

    if [[ $MOCK_MODE -eq 0 ]]; then
        # 真实AMD GPU信息
        gpu_models_json="["
        memory_json="["
        indices_json="["

        first=true
        for gpu_id in $SELECTED_GPUS; do
            local line=$(rocm-smi -i $gpu_id --showproductname 2>/dev/null)
            if [ "$first" = true ]; then
                first=false
            else
                gpu_models_json="$gpu_models_json, "
                memory_json="$memory_json, "
                indices_json="$indices_json, "
            fi
            gpu_models_json="$gpu_models_json\"AMD GPU $gpu_id\""
            memory_json="$memory_json\"16384\""
            indices_json="$indices_json\"$gpu_id\""
        done

        gpu_models_json="$gpu_models_json]"
        memory_json="$memory_json]"
        indices_json="$indices_json]"
    fi

    local register_response=$(curl -s -X POST "${SERVER_URL}/workers/register" \
        -H "Content-Type: application/json" \
        -d "{
            \"token\": \"$TOKEN\",
            \"hostname\": \"$worker_hostname\",
            \"ip\": \"$REACHABLE_IP\",
            \"total_gpu_count\": $gpu_count,
            \"selected_gpu_count\": $(echo $SELECTED_GPUS | wc -w),
            \"gpu_models\": $gpu_models_json,
            \"gpu_memorys\": $memory_json,
            \"selected_indices\": $indices_json,
            \"capabilities\": [\"vLLM\", \"SGLang\", \"ROCm\"],
            \"agent_type\": \"amd\",
            \"agent_version\": \"1.0.0\",
            \"mock_mode\": $MOCK_MODE
        }" 2>&1)

    if [ $? -ne 0 ]; then
        log_error "Worker注册失败: $register_response"
        exit 1
    fi

    log_info "Worker注册响应: $register_response"

    WORKER_ID=$(echo "$register_response" | grep -oP '"worker_id":\s*\K\d+' || echo "")
    WORKER_SECRET=$(echo "$register_response" | grep -oP '"worker_secret"\s*:\s*"\K[^"]+' || echo "")

    if [ -z "$WORKER_ID" ]; then
        log_error "未能获取Worker ID"
        exit 1
    fi

    if [ -z "$WORKER_SECRET" ]; then
        log_warn "未能获取Worker Secret，继续使用Token"
        WORKER_SECRET="$TOKEN"
    fi

    log_info "✓ Worker注册成功"
    log_info "  Worker ID: $WORKER_ID"

    # 保存Worker配置
    cat > "$WORK_DIR/.worker_config" << EOF
WORKER_ID=$WORKER_ID
WORKER_SECRET=$WORKER_SECRET
WORKER_NAME=$worker_name
WORKER_IP=$REACHABLE_IP
MOCK_MODE=$MOCK_MODE
EOF

    log_info "Worker配置已保存到 $WORK_DIR/.worker_config"

    # 更新 Prometheus 服务发现文件
    update_prometheus_sd "$REACHABLE_IP" "$WORKER_ID" "$worker_name"
}

# 复制二进制文件
copy_binaries() {
    log_info "复制程序文件..."

    # 复制occupier目录
    if [ -d "$SCRIPT_DIR/occupier" ]; then
        rm -rf "$WORK_DIR/occupier"
        cp -rf "$SCRIPT_DIR/occupier" "$WORK_DIR/"
        log_info "复制occupier目录完成"
    fi

    # 复制预编译的 Exporter
    if [ -f "$SCRIPT_DIR/Exporter/amd_exporter_main" ]; then
        rm -rf "$WORK_DIR/Exporter"
        cp -rf "$SCRIPT_DIR/Exporter" "$WORK_DIR/"
        log_info "使用预编译的 amd_exporter_main"
    fi

    # 复制预编译的 Receiver
    if [ -f "$SCRIPT_DIR/Receiver/receiver" ]; then
        rm -rf "$WORK_DIR/Receiver"
        cp -rf "$SCRIPT_DIR/Receiver" "$WORK_DIR/"
        log_info "使用预编译的 receiver"
    fi

    # 复制脚本文件
    cp -f "$SCRIPT_DIR/tm_agent.sh" "$WORK_DIR/"
    cp -f "$SCRIPT_DIR/heartbeat.sh" "$WORK_DIR/"

    # 创建环境变量配置文件
    log_info "创建环境变量配置..."
    cat > "$WORK_DIR/.env" << EOF
# TokenMachine AMD Agent 环境变量
TM_SERVER_URL=$SERVER_URL
TM_AGENT_PORT=$AGENT_PORT
TM_MOCK_MODE=$MOCK_MODE
EOF

    log_info "服务器地址: $SERVER_URL"
    log_info "Agent 端口: $AGENT_PORT"
    log_info "模拟模式: $MOCK_MODE"

    # 设置权限
    if [ -f "$WORK_DIR/occupier/occupy_gpu" ]; then
        chmod +x "$WORK_DIR/occupier/occupy_gpu"
        log_info "occupy_gpu 权限已设置"
    fi
    chmod +x "$WORK_DIR/tm_agent.sh"
    chmod +x "$WORK_DIR/heartbeat.sh"
    if [ -d "$WORK_DIR/Exporter" ]; then
        chmod +x "$WORK_DIR/Exporter/"*
    fi
    if [ -d "$WORK_DIR/Receiver" ]; then
        chmod +x "$WORK_DIR/Receiver/receiver"
    fi

    log_info "程序文件复制完成"
}

# 创建选中的 GPU 配置
create_gpu_config() {
    log_info "创建 GPU 配置..."

    > "$RUN_DIR/selected_gpus"

    for gpu_id in $SELECTED_GPUS; do
        echo "$gpu_id" >> "$RUN_DIR/selected_gpus"
    done

    local gpu_count=$(echo $SELECTED_GPUS | wc -w)
    log_info "已选择 $gpu_count 个GPU: $SELECTED_GPUS"
}

# 启动服务
start_services() {
    log_info "启动服务..."

    cd "$WORK_DIR"

    # 启动 GPU 占用
    for gpu_id in $SELECTED_GPUS; do
        log_info "启动 GPU ${gpu_id} 占用..."
        if [[ $MOCK_MODE -eq 1 ]]; then
            ./occupier/occupy_gpu --gpu "$gpu_id" --percent 90 --mock --log "$RUN_DIR/occupy_${gpu_id}.log" &
        else
            ./occupier/occupy_gpu --gpu "$gpu_id" --percent 90 --log "$RUN_DIR/occupy_${gpu_id}.log" &
        fi
        echo $! > "$RUN_DIR/occupy_${gpu_id}.pid"
    done

    # 启动 exporter
    log_info "启动 AMD exporter..."
    cd "$WORK_DIR/Exporter"
    export TM_MOCK_MODE=$MOCK_MODE
    local gpu_count=$(echo $SELECTED_GPUS | wc -w)
    export TM_SELECTED_GPU_COUNT=$gpu_count
    local exporter_port=$((AGENT_PORT + 91))  # AMD Exporter 使用 AGENT_PORT+91

    if [[ $MOCK_MODE -eq 1 ]]; then
        nohup ./amd_exporter_main --port $exporter_port --mock > "$RUN_DIR/exporter.log" 2>&1 &
    else
        nohup ./amd_exporter_main --port $exporter_port > "$RUN_DIR/exporter.log" 2>&1 &
    fi
    echo $! > "$RUN_DIR/exporter.pid"

    # 启动 receiver
    log_info "启动 Receiver..."
    cd "$WORK_DIR/Receiver"
    export TM_RECEIVER_PORT=$AGENT_PORT
    export TM_WORK_DIR="$WORK_DIR"
    export TM_RECEIVER_LOG="$RUN_DIR/receiver.log"
    nohup ./receiver > "$RUN_DIR/receiver.log" 2>&1 &
    echo $! > "$RUN_DIR/receiver.pid"

    # 启动心跳守护进程
    log_info "启动心跳守护进程..."
    cd "$WORK_DIR"
    export TM_MOCK_MODE=$MOCK_MODE
    nohup ./heartbeat.sh > "$RUN_DIR/heartbeat.log" 2>&1 &
    echo $! > "$RUN_DIR/heartbeat.pid"
    log_info "心跳守护进程已启动，PID: $(cat $RUN_DIR/heartbeat.pid)"

    sleep 3
    log_info "服务启动完成"
}

# 创建systemd服务
create_systemd_service() {
    if [[ $EUID -ne 0 ]]; then
        log_info "用户目录模式: 跳过 systemd 服务创建"
        return 0
    fi

    log_info "创建systemd服务..."

    local service_file="/etc/systemd/system/tokenmachine-amd-agent.service"

    cat > "$service_file" << EOF
[Unit]
Description=TokenMachine AMD Agent
After=network-online.target
Wants=network-online.target

[Service]
Type=forking
WorkingDirectory=$WORK_DIR
EnvironmentFile=-$WORK_DIR/.env
ExecStart=$WORK_DIR/tm_agent.sh start
ExecStop=$WORK_DIR/tm_agent.sh stop
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

    systemctl daemon-reload
    systemctl enable tokenmachine-amd-agent.service

    log_info "✓ systemd服务已创建并启用"
}

# 显示结果
show_results() {
    echo ""
    echo -e "${GREEN}=================================${NC}"
    echo -e "${GREEN}      安装完成！${NC}"
    echo -e "${GREEN}=================================${NC}"
    echo ""
    echo "服务状态:"
    echo "  AMD GPU 占用: $(ps aux | grep occupy_gpu | grep -v grep | wc -l) 个进程"
    echo "  Exporter: $(ps aux | grep amd_exporter_main | grep -v grep | wc -l) 个进程"
    echo "  Receiver: $(ps aux | grep receiver | grep -v grep | wc -l) 个进程"
    echo "  Heartbeat: $(ps aux | grep heartbeat.sh | grep -v grep | wc -l) 个进程"
    echo ""
    echo "模式: $([[ $MOCK_MODE -eq 1 ]] && echo '模拟模式 (无真实AMD硬件)' || echo '真实模式 (AMD ROCm)')"
    echo ""

    if [[ $MOCK_MODE -eq 0 ]]; then
        echo "AMD GPU 状态:"
        rocm-smi --query-gpu=index,memory.used,memory.total --format=csv 2>/dev/null || echo "  无法获取GPU状态"
    else
        echo "模拟 GPU 状态:"
        echo "  模拟 GPU 0: 90% 内存占用 (模拟值)"
    fi
    echo ""

    echo "管理命令:"
    echo "  查看状态: $WORK_DIR/tm_agent.sh status"
    echo "  停止服务: $WORK_DIR/tm_agent.sh stop"
    echo "  重启服务: $WORK_DIR/tm_agent.sh restart"
    echo ""

    echo "API 端点:"
    echo "  Receiver: http://localhost:${AGENT_PORT}"
    echo "  Exporter: http://localhost:$((AGENT_PORT + 91))/metrics"
    echo ""

    echo "故障排查:"
    echo "  查看服务日志: journalctl -u tokenmachine-amd-agent -f"
    echo "  查看 Receiver 日志: tail -f $RUN_DIR/receiver.log"
}

# 卸载功能
uninstall() {
    log_info "开始卸载 TokenMachine AMD Agent"

    check_root

    local saved_worker_id=""
    if [ -f "$WORK_DIR/.worker_config" ]; then
        source "$WORK_DIR/.worker_config"
        saved_worker_id="$WORKER_ID"
    fi

    log_info "正在停止服务..."

    if systemctl is-active --quiet tokenmachine-amd-agent; then
        systemctl stop tokenmachine-amd-agent
    fi

    if systemctl is-enabled --quiet tokenmachine-amd-agent; then
        systemctl disable tokenmachine-amd-agent
    fi

    if [ -f "/etc/systemd/system/tokenmachine-amd-agent.service" ]; then
        rm -f /etc/systemd/system/tokenmachine-amd-agent.service
        systemctl daemon-reload
    fi

    log_info "正在停止所有相关进程..."

    pkill -f "occupy_gpu.*amd" || true
    pkill -f "amd_exporter_main" || true
    pkill -f "receiver.*amd" || true
    pkill -f "tm_agent.sh.*amd" || true

    if [ -n "$saved_worker_id" ]; then
        remove_prometheus_sd "$saved_worker_id"
    fi

    log_info "正在删除文件和目录..."

    if [ -d "$WORK_DIR" ]; then
        rm -rf "$WORK_DIR"
    fi

    log_info "卸载完成！"
}

# 显示帮助信息
show_help() {
    echo "TokenMachine AMD Agent 安装脚本"
    echo "================================"
    echo ""
    echo "用法:"
    echo "  $0 [选项]"
    echo "  $0 install [选项]    - 安装 AMD Agent"
    echo "  $0 uninstall         - 卸载 AMD Agent"
    echo ""
    echo "安装选项:"
    echo "  -s, --server URL    - 服务器地址 (必需)"
    echo "  -p, --port PORT     - Agent 端口 (必需)"
    echo "  -t, --token TOKEN   - Worker Token (必需)"
    echo "  --gpus GPU_IDS      - GPU ID 列表 (默认: 0)"
    echo "  --mock              - 模拟模式 (无真实AMD硬件时使用)"
    echo "  -h, --help          - 显示此帮助信息"
    echo ""
    echo "示例:"
    echo "  $0 install -s http://192.168.247.76:8000 -p 9001 -t mytoken"
    echo "  $0 install -s http://192.168.247.76:8000 -p 9001 -t mytoken --mock"
    echo "  $0 uninstall"
    echo ""
}

# 主流程
main() {
    case "${1:-install}" in
        install)
            shift
            while [[ $# -gt 0 ]]; do
                case $1 in
                    -s|--server)
                        SERVER_URL="$2"
                        shift 2
                        ;;
                    -p|--port)
                        AGENT_PORT="$2"
                        shift 2
                        ;;
                    -t|--token)
                        TOKEN="$2"
                        shift 2
                        ;;
                    --gpus)
                        SELECTED_GPUS="$2"
                        shift 2
                        ;;
                    --mock)
                        MOCK_MODE=1
                        shift
                        ;;
                    -h|--help)
                        show_help
                        exit 0
                        ;;
                    *)
                        log_error "未知参数: $1"
                        show_help
                        exit 1
                        ;;
                esac
            done

            if [ -z "$SERVER_URL" ]; then
                log_error "服务器地址是必需的"
                show_help
                exit 1
            fi
            if [ -z "$AGENT_PORT" ]; then
                log_error "Agent 端口是必需的"
                show_help
                exit 1
            fi
            if [ -z "$TOKEN" ]; then
                log_error "Worker Token是必需的"
                show_help
                exit 1
            fi

            log_info "开始安装 TokenMachine AMD Agent"
            log_info "服务器地址: $SERVER_URL"
            log_info "Agent 端口: $AGENT_PORT"
            log_info "Worker Token: ${TOKEN:0:16}..."
            log_info "模拟模式: $MOCK_MODE"

            check_root
            check_dependencies
            check_rocm
            get_local_ips
            create_directories
            check_precompiled_binaries
            compile_occupy_gpu
            register_worker
            copy_binaries
            create_gpu_config
            start_services

            if [[ $EUID -eq 0 ]]; then
                create_systemd_service
            fi

            show_results
            ;;
        uninstall)
            uninstall
            ;;
        -h|--help)
            show_help
            ;;
        *)
            log_error "未知命令: $1"
            show_help
            exit 1
            ;;
    esac
}

# 运行主函数
main "$@"
