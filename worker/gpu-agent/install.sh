#!/bin/bash

# TokenMachine GPU Agent 安装脚本

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# 自动检测用户目录模式（非 root 用户自动使用用户目录）
if [[ $EUID -ne 0 ]]; then
    USER_HOME="${HOME:-/tmp}"
    WORK_DIR="${USER_HOME}/.local/tokenmachine"
    LOG_DIR="${USER_HOME}/.local/logs/tokenmachine"
    RUN_DIR="${USER_HOME}/.local/run/tokenmachine"
    echo "[INFO] 用户目录模式: $WORK_DIR"
else
    WORK_DIR="/opt/tokenmachine"
    LOG_DIR="/var/log/tokenmachine"
    RUN_DIR="/var/run/tokenmachine"
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

# Prometheus 服务发现配置
PROMETHEUS_SD_DIR="/etc/prometheus/workers"  # Prometheus SD 文件目录

# 检查是否以 root 运行（非 root 用户自动使用用户目录）
check_root() {
    if [[ $EUID -ne 0 ]]; then
        log_warn "非 root 用户运行，将使用用户目录模式"
    fi
}

# 检查系统依赖
check_dependencies() {
    log_info "检查系统依赖..."

    # 检查必要的命令
    local required_commands=("nvidia-smi" "git" "curl" "systemctl")

    for cmd in "${required_commands[@]}"; do
        if ! command -v "$cmd" &> /dev/null; then
            log_error "缺少必要的命令: $cmd"
            exit 1
        fi
    done

    # 检查nvcc
    if ! command -v nvcc &> /dev/null; then
        log_warn "nvcc 未在 PATH 中，检查 /usr/local/cuda..."
        if [ -d "/usr/local/cuda" ] && [ -f "/usr/local/cuda/bin/nvcc" ]; then
            export CUDA_PATH="/usr/local/cuda"
            export PATH="$CUDA_PATH/bin:$PATH"
            log_info "找到 CUDA 安装: $CUDA_PATH"
        else
            if [ -f "/usr/local/cuda-12.1/bin/nvcc" ]; then
                export CUDA_PATH="/usr/local/cuda-12.1"
                export PATH="$CUDA_PATH/bin:$PATH"
                log_info "找到 CUDA 安装: $CUDA_PATH"
            elif [ -f "/usr/local/cuda-12.8/bin/nvcc" ]; then
                export CUDA_PATH="/usr/local/cuda-12.8"
                export PATH="$CUDA_PATH/bin:$PATH"
                log_info "找到 CUDA 安装: $CUDA_PATH"
            else
                log_error "nvcc 未找到，请确保 CUDA Toolkit 已安装"
                exit 1
            fi
        fi
    fi

    log_info "所有依赖检查通过"
    log_info "CUDA 版本: $(nvcc --version | grep release)"
}

# 检查 GPU 环境
check_gpu() {
    if ! nvidia-smi &> /dev/null; then
        log_error "NVIDIA 驱动未工作"
        exit 1
    fi

    # 检测实际GPU数量
    GPU_COUNT=$(nvidia-smi --list-gpus | wc -l)
    log_info "检测到 $GPU_COUNT 个GPU"

    # 如果没有指定GPU，自动选择第一个
    if [ -z "$SELECTED_GPUS" ]; then
        if [ $GPU_COUNT -eq 1 ]; then
            SELECTED_GPUS="0"
            log_info "自动选择GPU: $SELECTED_GPUS"
        else
            # 多GPU时，默认使用前两个（保持向后兼容）
            SELECTED_GPUS="0 1"
            log_info "自动选择GPU: $SELECTED_GPUS"
        fi
    else
        log_info "使用指定的GPU: $SELECTED_GPUS"
    fi

    log_info "GPU 环境检查通过"
    nvidia-smi --query-gpu=index,name --format=csv,noheader,nounits
}

# 获取所有可用的IP地址
get_local_ips() {
    log_info "检测本地IP地址..."

    local ips=()

    # 方法1: 使用ip命令（推荐）
    if command -v ip &> /dev/null; then
        # 获取所有非loopback的IPv4地址
        while IFS= read -r line; do
            local ip=$(echo "$line" | awk '{print $1}')
            # 排除localhost和link-local地址
            if [[ ! "$ip" =~ ^127\. ]] && [[ ! "$ip" =~ ^169\.254\. ]]; then
                ips+=("$ip")
            fi
        done < <(ip -4 addr show | grep -oP '(?<=inet\s)\d+(\.\d+){3}' | sort -u)

    # 方法2: 使用hostname命令（备用）
    elif command -v hostname &> /dev/null; then
        while IFS= read -r ip; do
            if [[ ! "$ip" =~ ^127\. ]] && [[ ! "$ip" =~ ^169\.254\. ]]; then
                ips+=("$ip")
            fi
        done < <(hostname -I 2>/dev/null || echo "")
    fi

    # 如果没有找到任何IP，使用默认
    if [ ${#ips[@]} -eq 0 ]; then
        log_warn "未检测到可用的IP地址，使用默认值"
        ips=("127.0.0.1")
    fi

    # 输出找到的IP
    log_info "检测到 ${#ips[@]} 个IP地址:"
    for ip in "${ips[@]}"; do
        log_info "  - $ip"
    done

    # 将IP数组保存到全局变量
    DETECTED_IPS=("${ips[@]}")
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

# 检查预编译的二进制文件
check_precompiled_binaries() {
    log_info "检查预编译的二进制文件..."

    # 检查 Exporter 是否存在（必须预编译）
    if [ ! -f "$SCRIPT_DIR/Exporter/gpu_exporter_main" ]; then
        log_error "预编译的 gpu_exporter_main 不存在"
        log_error "请先在本地运行: cd Exporter && ./build.sh"
        exit 1
    fi
    log_info "✓ 预编译的 gpu_exporter_main 存在"

    # 检查 Receiver 是否存在（必须预编译）
    if [ ! -f "$SCRIPT_DIR/Receiver/receiver" ]; then
        log_error "预编译的 receiver 不存在"
        log_error "请先在本地运行: cd Receiver && ./build.sh"
        exit 1
    fi
    log_info "✓ 预编译的 receiver 存在"

    # 检查 occupy_gpu 源文件（需要在目标机器编译）
    if [ ! -f "$SCRIPT_DIR/occupier/occupy_gpu.cu" ]; then
        log_error "occupy_gpu.cu 源文件不存在"
        exit 1
    fi
    log_info "✓ occupy_gpu.cu 源文件存在（将在目标机器编译）"

    # 验证预编译二进制是静态链接
    log_info "验证预编译二进制..."

    if command -v file > /dev/null; then
        if ! file "$SCRIPT_DIR/Exporter/gpu_exporter_main" | grep -q "statically linked"; then
            log_warn "⚠ gpu_exporter_main 可能不是静态链接"
            log_warn "这可能导致兼容性问题"
        else
            log_info "✓ gpu_exporter_main 是静态链接"
        fi

        if ! file "$SCRIPT_DIR/Receiver/receiver" | grep -q "statically linked"; then
            log_warn "⚠ receiver 可能不是静态链接"
            log_warn "这可能导致兼容性问题"
        else
            log_info "✓ receiver 是静态链接"
        fi
    fi

    log_info "所有预编译文件检查通过"
}

# 编译 occupy_gpu（在目标机器上）
compile_occupy_gpu() {
    log_info "编译 occupy_gpu（CUDA 程序）..."

    cd "$SCRIPT_DIR"

    # 检查 CUDA 路径
    export CUDA_PATH="/usr/local/cuda"
    if [ ! -f "$CUDA_PATH/bin/nvcc" ]; then
        if [ -f "/usr/local/cuda-12.1/bin/nvcc" ]; then
            CUDA_PATH="/usr/local/cuda-12.1"
        elif [ -f "/usr/local/cuda-12.8/bin/nvcc" ]; then
            CUDA_PATH="/usr/local/cuda-12.8"
        elif [ -f "/usr/local/cuda-12.3/bin/nvcc" ]; then
            CUDA_PATH="/usr/local/cuda-12.3"
        elif [ -f "/usr/local/cuda-11.8/bin/nvcc" ]; then
            CUDA_PATH="/usr/local/cuda-11.8"
        else
            log_error "找不到 CUDA Toolkit 安装"
            log_error "请安装 CUDA Toolkit: apt install nvidia-cuda-toolkit"
            exit 1
        fi
    fi

    export PATH="$CUDA_PATH/bin:$PATH"
    log_info "使用 CUDA 路径: $CUDA_PATH"
    log_info "CUDA 版本: $(nvcc --version | grep release)"

    # 检查 nvcc 是否可用
    if ! command -v nvcc &> /dev/null; then
        log_error "nvcc 不可用，请检查 CUDA 安装"
        exit 1
    fi

    # 编译 occupy_gpu
    if [ ! -f "occupier/occupy_gpu.cu" ]; then
        log_error "找不到 occupy_gpu.cu 源文件"
        exit 1
    fi

    log_info "编译 occupy_gpu.cu..."
    if ! nvcc -O3 -o occupier/occupy_gpu occupier/occupy_gpu.cu 2>&1; then
        log_error "编译 occupy_gpu.cu 失败"
        exit 1
    fi

    # 优化二进制文件
    if command -v strip &> /dev/null; then
        strip occupier/occupy_gpu
        log_info "已优化 occupy_gpu 二进制"
    fi

    chmod +x occupier/occupy_gpu
    log_info "✓ occupy_gpu 编译完成"
}

# 更新 Prometheus 服务发现文件
update_prometheus_sd() {
    local worker_ip=$1
    local worker_id=$2
    local worker_name=$3
    local exporter_port="${AGENT_PORT}90"  # Exporter 端口 = Agent 端口 + 90

    log_info "更新 Prometheus 服务发现文件..."

    # 检查 SD 目录是否存在（需要 root 权限）
    if [[ $EUID -ne 0 ]]; then
        # 非 root 用户模式，跳过 SD 文件创建
        log_warn "非 root 用户模式，跳过 Prometheus SD 文件创建"
        log_info "  如需监控，请手动配置 Prometheus SD:"
        log_info "  - 在 Prometheus 服务器上创建: ~/.prometheus/workers/worker-${worker_id}.json"
        return 0
    fi

    # 创建 SD 目录
    mkdir -p "$PROMETHEUS_SD_DIR"

    # 生成 SD 文件
    local sd_file="${PROMETHEUS_SD_DIR}/worker-${worker_id}.json"
    cat > "$sd_file" << EOF
[
  {
    "targets": ["${worker_ip}:${exporter_port}"],
    "labels": {
      "worker_id": "${worker_id}",
      "worker_name": "${worker_name}",
      "instance": "${worker_name}"
    }
  }
]
EOF

    log_info "✓ Prometheus SD 文件已创建: $sd_file"
    log_info "  Worker IP: $worker_ip"
    log_info "  Exporter 端口: $exporter_port"

    # 尝试通知 Prometheus 重载配置
    if command -v curl &> /dev/null; then
        if curl -s "localhost:9090/-/reload" &>/dev/null; then
            log_info "✓ Prometheus 配置已重载"
        else
            log_info "  (Prometheus 自动重载将在 1 分钟内生效)"
        fi
    fi
}

# 移除 Prometheus 服务发现文件
remove_prometheus_sd() {
    local worker_id=$1

    if [[ $EUID -ne 0 ]]; then
        return 0
    fi

    local sd_file="${PROMETHEUS_SD_DIR}/worker-${worker_id}.json"
    if [ -f "$sd_file" ]; then
        rm -f "$sd_file"
        log_info "✓ Prometheus SD 文件已移除: $sd_file"

        # 通知 Prometheus 重载
        if command -v curl &> /dev/null; then
            curl -s "localhost:9090/-/reload" &>/dev/null || true
        fi
    fi
}

# 注册Worker到Backend
register_worker() {
    log_info "注册Worker到Backend..."

    # 收集机器信息
    local worker_name="${HOSTNAME}-gpu-${TOKEN:0:8}"
    local worker_hostname=$(hostname)
    local gpu_count=$(nvidia-smi --list-gpus | wc -l)

    log_info "Worker信息:"
    log_info "  名称: $worker_name"
    log_info "  主机名: $worker_hostname"
    log_info "  GPU数量: $gpu_count"
    log_info "  检测到的IP: ${DETECTED_IPS[*]}"

    # 1. 验证IP连通性
    log_info "验证IP连通性..."

    # 构建IP数组JSON
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

    log_info "发送IP验证请求: $ips_json"

    local verify_response=$(curl -s --max-time 30 -X POST "${SERVER_URL}/workers/verify-ips" \
        -H "Content-Type: application/json" \
        -H "Authorization: Bearer ${TOKEN}" \
        -d "{\"ips\": ${ips_json}}" 2>&1)

    if [ $? -ne 0 ]; then
        log_error "IP验证失败: $verify_response"
        log_warn "将使用第一个检测到的IP继续注册"
        REACHABLE_IP="${DETECTED_IPS[0]}"
    else
        log_info "IP验证响应: $verify_response"
        # 解析响应中的reachable_ips（简化处理）
        REACHABLE_IP="${DETECTED_IPS[0]}"
    fi

    log_info "使用IP地址: $REACHABLE_IP"

    # 2. 注册Worker
    log_info "注册Worker..."

    # 收集SELECTED_GPUS的GPU信息用于注册
    local gpu_models=()
    local gpu_memorys=()
    local selected_indices=()

    for gpu_id in $SELECTED_GPUS; do
        local line=$(nvidia-smi -i $gpu_id --query-gpu=index,name --format=csv,noheader,nounits 2>/dev/null)
        if [[ $line =~ ^[0-9]+ ]]; then
            local idx=$(echo "$line" | awk -F', ' '{print $1}' | tr -d ' ')
            local model=$(echo "$line" | awk -F', ' '{print $2}' | sed 's/NVIDIA //g' | sed 's/ *//')
            local memory=$(nvidia-smi -i $idx --query-gpu=memory.total --format=csv,noheader,nounits | tr -d ' ')

            gpu_models+=("$model")
            gpu_memorys+=("$memory")
            selected_indices+=("$idx")
        fi
    done

    local total_gpu_count=$GPU_COUNT
    local selected_gpu_count=${#selected_indices[@]}

    # 构建JSON数组
    local gpu_models_json="["
    local memory_json="["
    local indices_json="["

    for i in "${!gpu_models[@]}"; do
        if [ $i -gt 0 ]; then
            gpu_models_json="$gpu_models_json, "
            memory_json="$memory_json, "
            indices_json="$indices_json, "
        fi
        gpu_models_json="$gpu_models_json\"${gpu_models[$i]}\""
        memory_json="$memory_json\"${gpu_memorys[$i]}\""
        indices_json="$indices_json\"${selected_indices[$i]}\""
    done

    gpu_models_json="$gpu_models_json]"
    memory_json="$memory_json]"
    indices_json="$indices_json]"

    local register_response=$(curl -s --max-time 30 -X POST "${SERVER_URL}/workers/register" \
        -H "Content-Type: application/json" \
        -d "{
            \"token\": \"$TOKEN\",
            \"hostname\": \"$worker_hostname\",
            \"ips\": [\"$REACHABLE_IP\"],
            \"total_gpu_count\": $total_gpu_count,
            \"selected_gpu_count\": $selected_gpu_count,
            \"gpu_models\": $gpu_models_json,
            \"gpu_memorys\": $memory_json,
            \"selected_indices\": $indices_json,
            \"capabilities\": [\"vLLM\", \"SGLang\"],
            \"agent_type\": \"gpu\",
            \"agent_version\": \"1.0.0\"
        }" 2>&1)

    # 解析响应（使用简单的文本处理）
    WORKER_ID=$(echo "$register_response" | grep -oP '"worker_id":\s*\K\d+' || echo "")
    WORKER_SECRET=$(echo "$register_response" | grep -oP '"worker_secret"\s*:\s*"\K[^"]+' || echo "")

    # 检查响应是否包含错误
    if echo "$register_response" | grep -q '"error"'; then
        log_warn "Worker注册返回错误: $register_response"
        log_warn "将继续安装本地服务（Backend连接可能失败）"
        # 使用临时 ID 和 secret
        WORKER_ID="temp_$(date +%s)"
        WORKER_SECRET="$TOKEN"
    fi

    if [ -z "$WORKER_ID" ]; then
        log_warn "未能获取Worker ID，使用临时ID"
        WORKER_ID="temp_$(date +%s)"
        WORKER_SECRET="${WORKER_SECRET:-$TOKEN}"
    fi

    if [ -z "$WORKER_SECRET" ]; then
        log_warn "未能获取Worker Secret，继续使用Token"
        WORKER_SECRET="$TOKEN"
    fi

    log_info "使用 Worker ID: $WORKER_ID"

    # 保存Worker配置
    cat > "$WORK_DIR/.worker_config" << EOF
WORKER_ID=$WORKER_ID
WORKER_SECRET=$WORKER_SECRET
WORKER_NAME=$worker_name
WORKER_IP=$REACHABLE_IP
EOF

    log_info "Worker配置已保存到 $WORK_DIR/.worker_config"

    # 更新 Prometheus 服务发现文件
    update_prometheus_sd "$REACHABLE_IP" "$WORKER_ID" "$worker_name"
}

# 注册单个GPU
register_gpu() {
    local gpu_id=$1

    log_info "注册GPU $gpu_id..."

    # 收集GPU信息
    local gpu_uuid=$(nvidia-smi -i $gpu_id --query-gpu=uuid --format=csv,noheader)
    local gpu_name=$(nvidia-smi -i $gpu_id --query-gpu=name --format=csv,noheader)
    local gpu_memory=$(nvidia-smi -i $gpu_id --query-gpu=memory.total --format=csv,noheader,nounits | tr -d ' ')

    log_info "  UUID: $gpu_uuid"
    log_info "  名称: $gpu_name"
    log_info "  内存: ${gpu_memory}MB"

    # 注册GPU
    local gpu_response=$(curl -s --max-time 30 -X POST "${SERVER_URL}/api/v1/workers/register-gpu" \
        -H "Content-Type: application/json" \
        -H "Authorization: Bearer ${WORKER_SECRET}" \
        -d "{
            \"worker_id\": $WORKER_ID,
            \"gpu_id\": $gpu_id,
            \"uuid\": \"$gpu_uuid\",
            \"name\": \"$gpu_name\",
            \"memory_total\": $gpu_memory
        }" 2>&1)

    if [ $? -eq 0 ]; then
        log_info "✓ GPU $gpu_id 注册成功"
    else
        log_warn "GPU $gpu_id 注册失败: $gpu_response"
    fi
}

# 复制二进制文件
copy_binaries() {
    log_info "复制程序文件..."

    # 强制复制预编译的静态二进制文件（覆盖现有文件）
    log_info "强制覆盖所有二进制文件..."

    # 复制occupier目录（包含occupy_gpu和occupy_gpu.cu）
    if [ -d "$SCRIPT_DIR/occupier" ]; then
        rm -rf "$WORK_DIR/occupier"  # 先删除旧目录
        cp -rf "$SCRIPT_DIR/occupier" "$WORK_DIR/"
        log_info "复制occupier目录完成"
    else
        log_warn "occupier目录不存在，跳过复制"
    fi

    # 复制预编译的 Exporter
    if [ -f "$SCRIPT_DIR/Exporter/gpu_exporter_main" ]; then
        rm -rf "$WORK_DIR/Exporter"  # 先删除旧目录
        cp -rf "$SCRIPT_DIR/Exporter" "$WORK_DIR/"
        log_info "使用预编译的 gpu_exporter_main"
        # 验证是否为静态版本
        if command -v file > /dev/null; then
            log_info "gpu_exporter_main 类型: $(file $WORK_DIR/Exporter/gpu_exporter_main)"
        fi
    else
        log_warn "gpu_exporter_main 不存在，跳过复制"
    fi

    # 复制预编译的 Receiver
    if [ -f "$SCRIPT_DIR/Receiver/receiver" ]; then
        rm -rf "$WORK_DIR/Receiver"  # 先删除旧目录
        cp -rf "$SCRIPT_DIR/Receiver" "$WORK_DIR/"
        log_info "使用预编译的 receiver"
        # 验证是否为静态版本
        if command -v file > /dev/null; then
            log_info "receiver 类型: $(file $WORK_DIR/Receiver/receiver)"
        fi
    else
        log_warn "receiver 不存在，跳过复制"
    fi

    # 复制脚本文件（覆盖）
    cp -f "$SCRIPT_DIR/tm_agent.sh" "$WORK_DIR/"
    cp -f "$SCRIPT_DIR/heartbeat.sh" "$WORK_DIR/"

    # 创建环境变量配置文件
    log_info "创建环境变量配置..."
    cat > "$WORK_DIR/.env" << EOF
# TokenMachine GPU Agent 环境变量
TM_SERVER_URL=$SERVER_URL
TM_AGENT_PORT=$AGENT_PORT
EOF
    log_info "服务器地址: $SERVER_URL"
    log_info "Agent 端口: $AGENT_PORT"

    # 设置权限
    if [ -f "$WORK_DIR/occupier/occupy_gpu" ]; then
        chmod +x "$WORK_DIR/occupier/occupy_gpu"
        log_info "occupy_gpu权限已设置"
    fi
    chmod +x "$WORK_DIR/tm_agent.sh"
    if [ -d "$WORK_DIR/Exporter" ]; then
        chmod +x "$WORK_DIR/Exporter/"*
        # 验证是否使用静态版本
        if command -v file > /dev/null; then
            log_info "gpu_exporter_main 类型: $(file $WORK_DIR/Exporter/gpu_exporter_main)"
        fi
    fi
    if [ -d "$WORK_DIR/Receiver" ]; then
        chmod +x "$WORK_DIR/Receiver/receiver"
        # 验证是否使用静态版本
        if command -v file > /dev/null; then
            log_info "receiver 类型: $(file $WORK_DIR/Receiver/receiver)"
        fi
    fi

    log_info "程序文件复制完成"
}

# 创建选中的 GPU 配置
create_gpu_config() {
    log_info "创建 GPU 配置..."

    # 清空旧配置
    > "$RUN_DIR/selected_gpus"

    # 写入选中的GPU列表
    for gpu_id in $SELECTED_GPUS; do
        echo "$gpu_id" >> "$RUN_DIR/selected_gpus"
    done

    local gpu_count=$(echo $SELECTED_GPUS | wc -w)
    log_info "已选择 $gpu_count 个GPU: $SELECTED_GPUS"
}

# 启动服务
start_services() {
    log_info "启动服务..."

    # 启动 GPU 占用（使用SELECTED_GPUS）
    cd "$WORK_DIR"
    for gpu_id in $SELECTED_GPUS; do
        log_info "启动 GPU ${gpu_id} 占用..."
        ./occupier/occupy_gpu --gpu "$gpu_id" --log "$RUN_DIR/occupy_${gpu_id}.log" &
        echo $! > "$RUN_DIR/occupy_${gpu_id}.pid"
    done

    # 启动 exporter（使用SELECTED_GPUS）
    log_info "启动 GPU exporter..."
    cd "$WORK_DIR/Exporter"
    export TM_SELECTED_GPUS="$SELECTED_GPUS"
    local gpu_count=$(echo $SELECTED_GPUS | wc -w)
    export TM_SELECTED_GPU_COUNT=$gpu_count
    local exporter_port=$((AGENT_PORT + 89))  # Exporter使用 AGENT_PORT+89
    nohup ./gpu_exporter_main serve -p $exporter_port > "$RUN_DIR/exporter.log" 2>&1 &
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
    nohup ./heartbeat.sh > "$RUN_DIR/heartbeat.log" 2>&1 &
    echo $! > "$RUN_DIR/heartbeat.pid"
    log_info "心跳守护进程已启动，PID: $(cat $RUN_DIR/heartbeat.pid)"

    sleep 3
    log_info "服务启动完成"
}

# 创建systemd服务
create_systemd_service() {
    log_info "创建systemd服务..."

    local service_file="/etc/systemd/system/tokenmachine-gpu-agent.service"

    cat > "$service_file" << EOF
[Unit]
Description=TokenMachine GPU Agent
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
    systemctl enable tokenmachine-gpu-agent.service

    log_info "✓ systemd服务已创建并启用"
    log_info "  服务文件: $service_file"
    log_info "  管理命令:"
    log_info "    启动: systemctl start tokenmachine-gpu-agent"
    log_info "    停止: systemctl stop tokenmachine-gpu-agent"
    log_info "    状态: systemctl status tokenmachine-gpu-agent"
    log_info "    日志: journalctl -u tokenmachine-gpu-agent -f"
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
    echo "  Heartbeat: $(ps aux | grep heartbeat.sh | grep -v grep | wc -l) 个进程"
    echo ""

    echo "GPU 状态:"
    # 添加超时保护避免 nvidia-smi 挂起
    timeout 10 nvidia-smi --query-gpu=index,memory.used,memory.total --format=csv || echo "  (GPU 状态查询超时或失败)"
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

    echo "故障排查:"
    echo "  查看服务日志: journalctl -u tokenmachine-gpu-agent -f"
    echo "  查看 Agent 日志: tail -f $LOG_FILE"
    echo "  查看 Receiver 日志: tail -f $RUN_DIR/receiver.log"
    echo "  查看 GPU 状态: nvidia-smi --query-gpu=index,name,memory.used,memory.total --format=csv"
    echo ""
}

# 卸载功能
uninstall() {
    log_info "开始卸载 TokenMachine GPU Agent"

    # 检查权限
    check_root

    # 读取 Worker 配置（用于清理 Prometheus SD 文件）
    local saved_worker_id=""
    local saved_worker_ip=""
    if [ -f "$WORK_DIR/.worker_config" ]; then
        source "$WORK_DIR/.worker_config"
        saved_worker_id="$WORKER_ID"
        saved_worker_ip="$WORKER_IP"
    fi

    log_info "正在停止服务..."

    # 停止 systemd 服务
    if systemctl is-active --quiet tokenmachine-gpu-agent; then
        log_info "停止 tokenmachine-gpu-agent 服务..."
        systemctl stop tokenmachine-gpu-agent
    fi

    if systemctl is-enabled --quiet tokenmachine-gpu-agent; then
        log_info "禁用 tokenmachine-gpu-agent 服务..."
        systemctl disable tokenmachine-gpu-agent
    fi

    # 删除 systemd 服务文件
    if [ -f "/etc/systemd/system/tokenmachine-gpu-agent.service" ]; then
        log_info "删除服务文件..."
        rm -f /etc/systemd/system/tokenmachine-gpu-agent.service
        systemctl daemon-reload
    fi

    log_info "正在停止所有相关进程..."

    # 停止所有 occupy_gpu 进程
    pkill -f "occupy_gpu" || true
    sleep 2

    # 强制停止残留进程
    pkill -9 -f "occupy_gpu" || true
    pkill -9 -f "gpu_exporter_main" || true
    pkill -9 -f "receiver" || true
    pkill -9 -f "tm_agent.sh" || true

    # 移除 Prometheus 服务发现文件
    if [ -n "$saved_worker_id" ]; then
        remove_prometheus_sd "$saved_worker_id"
    fi

    log_info "正在删除文件和目录..."

    # 删除工作目录
    if [ -d "$WORK_DIR" ]; then
        log_info "删除工作目录: $WORK_DIR"
        rm -rf "$WORK_DIR"
    fi

    # 删除日志目录
    if [ -d "$LOG_DIR" ]; then
        log_info "删除日志目录: $LOG_DIR"
        rm -rf "$LOG_DIR"
    fi

    # 删除运行时目录
    if [ -d "$RUN_DIR" ]; then
        log_info "删除运行时目录: $RUN_DIR"
        rm -rf "$RUN_DIR"
    fi

    # 删除配置文件
    if [ -f "/etc/profile.d/tokenmachine-gpu-agent.sh" ]; then
        log_info "删除配置文件..."
        rm -f "/etc/profile.d/tokenmachine-gpu-agent.sh"
    fi

    # 清理临时文件
    rm -f /tmp/occupy_*.log
    rm -f /tmp/test_occupy_*.log

    log_info "卸载完成！"
    echo ""
    echo -e "${GREEN}=================================${NC}"
    echo -e "${GREEN}      卸载完成！${NC}"
    echo -e "${GREEN}=================================${NC}"
    echo ""
    echo "已删除："
    echo "  - 服务文件: /etc/systemd/system/tokenmachine-gpu-agent.service"
    echo "  - 工作目录: $WORK_DIR"
    echo "  - 日志目录: $LOG_DIR"
    echo "  - 运行时目录: $RUN_DIR"
    echo "  - 所有相关进程"
    echo ""
    echo "如需完全清除，可以手动执行："
    echo "  rm -rf /home/ht706/worker"
    echo ""
}

# 显示帮助信息
show_help() {
    echo "TokenMachine GPU Agent 安装脚本"
    echo "================================"
    echo ""
    echo "用法:"
    echo "  $0 [选项]"
    echo "  $0 install [选项]    - 安装 GPU Agent"
    echo "  $0 uninstall         - 卸载 GPU Agent"
    echo ""
    echo "安装选项:"
    echo "  -s, --server URL    - 服务器地址 (必需)"
    echo "  -p, --port PORT     - Agent 端口 (必需)"
    echo "  -h, --help           - 显示此帮助信息"
    echo ""
    echo "示例:"
    echo "  $0 install -s http://192.168.247.76:8000 -p 9001"
    echo "  $0 uninstall"
    echo ""
}

# 主流程
main() {
    case "${1:-install}" in
        install)
            # 处理安装参数
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

            # 验证必需参数
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

            log_info "开始安装 TokenMachine GPU Agent (预编译 + CUDA编译)"
            log_info "服务器地址: $SERVER_URL"
            log_info "Agent 端口: $AGENT_PORT"
            log_info "Worker Token: ${TOKEN:0:16}..."

            # 检查权限
            check_root

            # 检查依赖
            check_dependencies

            # 检查 GPU
            check_gpu

            # 获取本地IP地址
            get_local_ips

            # 创建目录
            create_directories

            # 检查预编译的二进制文件并编译 occupy_gpu
            check_precompiled_binaries

            # 编译 occupy_gpu（CUDA 程序）
            compile_occupy_gpu

            # 注册Worker到Backend
            register_worker

            # 复制二进制文件
            copy_binaries

            # 创建 GPU 配置
            create_gpu_config

            # 启动服务
            start_services

            # 注册所有选中的GPU到Backend
            for gpu_id in $SELECTED_GPUS; do
                register_gpu $gpu_id
            done

            # 非root用户模式跳过systemd
            if [[ $EUID -ne 0 ]]; then
                log_info "用户目录模式: 跳过 systemd 服务创建"
            else
                create_systemd_service
            fi

            # 显示完成信息
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