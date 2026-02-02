#!/bin/bash

# TokenMachine Ascend Agent 安装脚本
# 适配华为昇腾 NPU (Ascend) 设备

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# 自动检测用户目录模式（非 root 用户自动使用用户目录）
if [[ $EUID -ne 0 ]]; then
    USER_HOME="${HOME:-/tmp}"
    WORK_DIR="${USER_HOME}/.local/tokenmachine-ascend"
    LOG_DIR="${USER_HOME}/.local/logs/tokenmachine-ascend"
    RUN_DIR="${USER_HOME}/.local/run/tokenmachine-ascend"
    echo "[INFO] 用户目录模式: $WORK_DIR"
else
    WORK_DIR="/opt/tokenmachine-ascend"
    LOG_DIR="/var/log/tokenmachine-ascend"
    RUN_DIR="/var/run/tokenmachine-ascend"
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
SELECTED_NPUS=""  # 选中的NPU列表（空=自动检测）
NPU_COUNT=0       # 实际NPU数量

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
    local required_commands=("npu-smi" "git" "curl" "systemctl")

    for cmd in "${required_commands[@]}"; do
        if ! command -v "$cmd" &> /dev/null; then
            log_error "缺少必要的命令: $cmd"
            exit 1
        fi
    done

    # 检查 CANN 环境
    if [ -z "$ASCEND_HOME" ]; then
        if [ -d "/usr/local/Ascend" ]; then
            export ASCEND_HOME="/usr/local/Ascend"
            log_info "检测到 ASCEND_HOME: $ASCEND_HOME"
        else
            log_error "ASCEND_HOME 未设置，请确保 CANN 已安装"
            exit 1
        fi
    fi

    # 检查 ACL 库
    if [ ! -d "$ASCEND_HOME/ascend-toolkit/latest/lib64" ]; then
        log_error "ACL 库未找到，请检查 CANN 安装"
        exit 1
    fi

    log_info "所有依赖检查通过"
}

# 检查 NPU 环境
check_npu() {
    if ! npu-smi info &> /dev/null; then
        log_error "NPU 驱动未工作"
        exit 1
    fi

    # 检测实际NPU数量
    NPU_COUNT=$(npu-smi list | grep -c "Ascend" || echo "0")
    if [ "$NPU_COUNT" -eq 0 ]; then
        # 备用方法
        NPU_COUNT=$(npu-smi info -l | wc -l)
    fi

    log_info "检测到 $NPU_COUNT 个 NPU"

    # 如果没有指定NPU，自动选择第一个
    if [ -z "$SELECTED_NPUS" ]; then
        if [ $NPU_COUNT -eq 1 ]; then
            SELECTED_NPUS="0"
            log_info "自动选择 NPU: $SELECTED_NPUS"
        else
            # 多 NPU 时，默认使用前两个（保持向后兼容）
            SELECTED_NPUS="0 1"
            log_info "自动选择 NPU: $SELECTED_NPUS"
        fi
    else
        log_info "使用指定的 NPU: $SELECTED_NPUS"
    fi

    log_info "NPU 环境检查通过"
    npu-smi list
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
    mkdir -p "$RUN_DIR/occupy_npu"
    mkdir -p "$RUN_DIR/npu_exporter"
    log_info "目录创建完成"
}

# 检查预编译的二进制文件
check_precompiled_binaries() {
    log_info "检查预编译的二进制文件..."

    # 检查 Exporter 是否存在（必须预编译）
    if [ ! -f "$SCRIPT_DIR/Exporter/npu_exporter_main" ]; then
        log_error "预编译的 npu_exporter_main 不存在"
        log_error "请先在本地运行: cd Exporter && ./build.sh"
        exit 1
    fi
    log_info "✓ 预编译的 npu_exporter_main 存在"

    # 检查 Receiver 是否存在（必须预编译）
    if [ ! -f "$SCRIPT_DIR/Receiver/receiver" ]; then
        log_error "预编译的 receiver 不存在"
        log_error "请先在本地运行: cd Receiver && ./build.sh"
        exit 1
    fi
    log_info "✓ 预编译的 receiver 存在"

    # 检查 npu_occupy 源文件（需要在目标机器编译）
    if [ ! -f "$SCRIPT_DIR/occupier/occupy_npu.cpp" ]; then
        log_error "occupy_npu.cpp 源文件不存在"
        exit 1
    fi
    log_info "✓ occupy_npu.cpp 源文件存在（将在目标机器编译）"

    # 验证预编译二进制是静态链接
    log_info "验证预编译二进制..."

    if command -v file > /dev/null; then
        if ! file "$SCRIPT_DIR/Exporter/npu_exporter_main" | grep -q "statically linked"; then
            log_warn "⚠ npu_exporter_main 可能不是静态链接"
            log_warn "这可能导致兼容性问题"
        else
            log_info "✓ npu_exporter_main 是静态链接"
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

# 编译 occupy_npu（在目标机器上，使用 ACL/CANN）
compile_occupy_npu() {
    log_info "编译 occupy_npu（CANN ACL 程序）..."

    cd "$SCRIPT_DIR"

    # 设置 CANN 环境
    export ASCEND_HOME="${ASCEND_HOME:-/usr/local/Ascend}"
    export ASCEND_TOOLKIT_HOME="$ASCEND_HOME/ascend-toolkit/latest"
    export LD_LIBRARY_PATH="$ASCEND_TOOLKIT_HOME/lib64:$LD_LIBRARY_PATH"
    export PATH="$ASCEND_TOOLKIT_HOME/bin:$PATH"

    # 检查 ACL 头文件
    if [ ! -f "$ASCEND_TOOLKIT_HOME/include/acl/acl.h" ]; then
        log_error "ACL 头文件未找到: $ASCEND_TOOLKIT_HOME/include/acl/acl.h"
        log_error "请确保 CANN 开发包已安装"
        exit 1
    fi

    log_info "使用 ASCEND_HOME: $ASCEND_HOME"

    # 编译 occupy_npu
    if [ ! -f "occupier/occupy_npu.cpp" ]; then
        log_error "找不到 occupy_npu.cpp 源文件"
        exit 1
    fi

    log_info "编译 occupy_npu.cpp..."

    # 使用 g++ 编译，链接 ACL 库
    g++ -O3 -std=c++17 \
        -I"$ASCEND_TOOLKIT_HOME/include" \
        -L"$ASCEND_TOOLKIT_HOME/lib64" \
        -o occupy_npu \
        occupier/occupy_npu.cpp \
        -lacl_op_compiler -lascendcl -lpthread -ldl \
        2>&1

    if [ $? -ne 0 ]; then
        log_error "编译 occupy_npu.cpp 失败"
        exit 1
    fi

    # 优化二进制文件
    if command -v strip &> /dev/null; then
        strip occupy_npu
        log_info "已优化 occupy_npu 二进制"
    fi

    chmod +x occupy_npu
    log_info "✓ occupy_npu 编译完成"
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
      "instance": "${worker_name}",
      "accelerator": "ascend"
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
    local worker_name="${HOSTNAME}-ascend-${TOKEN:0:8}"
    local worker_hostname=$(hostname)
    local npu_count=$(npu-smi list | grep -c "Ascend" || echo "0")

    log_info "Worker信息:"
    log_info "  名称: $worker_name"
    log_info "  主机名: $worker_hostname"
    log_info "  NPU数量: $npu_count"
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

    local verify_response=$(curl -s -X POST "${SERVER_URL}/workers/verify-ips" \
        -H "Content-Type: application/json" \
        -H "Authorization: Bearer ${TOKEN}" \
        -d "{\"ips\": ${ips_json}}" 2>&1)

    if [ $? -ne 0 ]; then
        log_error "IP验证失败: $verify_response"
        log_warn "将使用第一个检测到的IP继续注册"
        REACHABLE_IP="${DETECTED_IPS[0]}"
    else
        log_info "IP验证响应: $verify_response"
        REACHABLE_IP="${DETECTED_IPS[0]}"
    fi

    log_info "使用IP地址: $REACHABLE_IP"

    # 2. 注册Worker
    log_info "注册Worker..."

    # 收集SELECTED_NPUS的NPU信息用于注册
    local npu_models=()
    local npu_memorys=()
    local selected_indices=()

    for npu_id in $SELECTED_NPUS; do
        local info_line=$(npu-smi info -i $npu_id 2>/dev/null)
        if [ -n "$info_line" ]; then
            local model=$(echo "$info_line" | grep "Board" | awk '{print $2}' | head -1)
            local memory=$(echo "$info_line" | grep "HBM" | awk '{print $2}' | head -1)

            # 提取内存数值
            memory=$(echo "$memory" | grep -oP '\d+' | head -1)

            npu_models+=("$model")
            npu_memorys+=("$memory")
            selected_indices+=("$npu_id")
        fi
    done

    local total_npu_count=$NPU_COUNT
    local selected_npu_count=${#selected_indices[@]}

    # 构建JSON数组
    local npu_models_json="["
    local memory_json="["
    local indices_json="["

    for i in "${!npu_models[@]}"; do
        if [ $i -gt 0 ]; then
            npu_models_json="$npu_models_json, "
            memory_json="$memory_json, "
            indices_json="$indices_json, "
        fi
        npu_models_json="$npu_models_json\"${npu_models[$i]}\""
        memory_json="$memory_json\"${npu_memorys[$i]}\""
        indices_json="$indices_json\"${selected_indices[$i]}\""
    done

    npu_models_json="$npu_models_json]"
    memory_json="$memory_json]"
    indices_json="$indices_json]"

    local register_response=$(curl -s -X POST "${SERVER_URL}/workers/register" \
        -H "Content-Type: application/json" \
        -d "{
            \"token\": \"$TOKEN\",
            \"hostname\": \"$worker_hostname\",
            \"ip\": \"$REACHABLE_IP\",
            \"total_npu_count\": $total_npu_count,
            \"selected_npu_count\": $selected_npu_count,
            \"npu_models\": $npu_models_json,
            \"npu_memorys\": $memory_json,
            \"selected_indices\": $indices_json,
            \"capabilities\": [\"vLLM-SGLang-Ascend\", \"ChatGLM-Ascend\"],
            \"agent_type\": \"ascend\",
            \"agent_version\": \"1.0.0\"
        }" 2>&1)

    if [ $? -ne 0 ]; then
        log_error "Worker注册失败: $register_response"
        exit 1
    fi

    log_info "Worker注册响应: $register_response"

    # 解析响应
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
EOF

    log_info "Worker配置已保存到 $WORK_DIR/.worker_config"

    # 更新 Prometheus 服务发现文件
    update_prometheus_sd "$REACHABLE_IP" "$WORKER_ID" "$worker_name"
}

# 注册单个NPU
register_npu() {
    local npu_id=$1

    log_info "注册NPU $npu_id..."

    # 收集NPU信息
    local npu_info=$(npu-smi info -i $npu_id 2>/dev/null)
    local npu_name=$(echo "$npu_info" | grep "Board" | awk '{print $2}' | head -1)
    local npu_memory=$(echo "$npu_info" | grep "HBM" | awk '{print $2}' | head -1)
    local npu_id_str=$(echo "$npu_info" | grep "NPU ID" | awk '{print $3}' | head -1)

    # 提取内存数值
    memory_value=$(echo "$npu_memory" | grep -oP '\d+' | head -1)
    if [ -z "$memory_value" ]; then
        memory_value=32768  # 默认 32GB
    fi

    log_info "  ID: $npu_id_str"
    log_info "  名称: $npu_name"
    log_info "  内存: ${memory_value}MB"

    # 注册NPU
    local npu_response=$(curl -s -X POST "${SERVER_URL}/api/v1/workers/register-gpu" \
        -H "Content-Type: application/json" \
        -H "Authorization: Bearer ${WORKER_SECRET}" \
        -d "{
            \"worker_id\": $WORKER_ID,
            \"gpu_id\": $npu_id,
            \"uuid\": \"$npu_id_str\",
            \"name\": \"$npu_name\",
            \"memory_total\": $memory_value,
            \"accelerator_type\": \"ascend\"
        }" 2>&1)

    if [ $? -eq 0 ]; then
        log_info "✓ NPU $npu_id 注册成功"
    else
        log_warn "NPU $npu_id 注册失败: $npu_response"
    fi
}

# 复制二进制文件
copy_binaries() {
    log_info "复制程序文件..."

    # 复制occupier目录（包含occupy_npu和occupy_npu.cpp）
    if [ -d "$SCRIPT_DIR/occupier" ]; then
        rm -rf "$WORK_DIR/occupier"
        cp -rf "$SCRIPT_DIR/occupier" "$WORK_DIR/"
        log_info "复制occupier目录完成"
    else
        log_warn "occupier目录不存在，跳过复制"
    fi

    # 复制预编译的 Exporter
    if [ -f "$SCRIPT_DIR/Exporter/npu_exporter_main" ]; then
        rm -rf "$WORK_DIR/Exporter"
        cp -rf "$SCRIPT_DIR/Exporter" "$WORK_DIR/"
        log_info "使用预编译的 npu_exporter_main"
    else
        log_warn "npu_exporter_main 不存在，跳过复制"
    fi

    # 复制预编译的 Receiver
    if [ -f "$SCRIPT_DIR/Receiver/receiver" ]; then
        rm -rf "$WORK_DIR/Receiver"
        cp -rf "$SCRIPT_DIR/Receiver" "$WORK_DIR/"
        log_info "使用预编译的 receiver"
    else
        log_warn "receiver 不存在，跳过复制"
    fi

    # 复制脚本文件（覆盖）
    cp -f "$SCRIPT_DIR/tm_agent.sh" "$WORK_DIR/"
    cp -f "$SCRIPT_DIR/heartbeat.sh" "$WORK_DIR/"

    # 创建环境变量配置文件
    log_info "创建环境变量配置..."
    cat > "$WORK_DIR/.env" << EOF
# TokenMachine Ascend Agent 环境变量
TM_SERVER_URL=$SERVER_URL
TM_AGENT_PORT=$AGENT_PORT
TM_ASCEND_HOME=$ASCEND_HOME
EOF
    log_info "服务器地址: $SERVER_URL"
    log_info "Agent 端口: $AGENT_PORT"
    log_info "ASCEND_HOME: $ASCEND_HOME"

    # 设置权限
    if [ -f "$WORK_DIR/occupier/occupy_npu" ]; then
        chmod +x "$WORK_DIR/occupier/occupy_npu"
        log_info "occupy_npu 权限已设置"
    fi
    chmod +x "$WORK_DIR/tm_agent.sh"
    chmod +x "$WORK_DIR/heartbeat.sh"

    log_info "程序文件复制完成"
}

# 创建选中的 NPU 配置
create_npu_config() {
    log_info "创建 NPU 配置..."

    # 清空旧配置
    > "$RUN_DIR/selected_npus"

    # 写入选中的NPU列表
    for npu_id in $SELECTED_NPUS; do
        echo "$npu_id" >> "$RUN_DIR/selected_npus"
    done

    local npu_count=$(echo $SELECTED_NPUS | wc -w)
    log_info "已选择 $npu_count 个 NPU: $SELECTED_NPUS"
}

# 启动服务
start_services() {
    log_info "启动服务..."

    # 设置 CANN 环境变量
    export ASCEND_HOME="${ASCEND_HOME:-/usr/local/Ascend}"
    export LD_LIBRARY_PATH="$ASCEND_HOME/ascend-toolkit/latest/lib64:$LD_LIBRARY_PATH"

    # 启动 NPU 占用（使用SELECTED_NPUS）
    cd "$WORK_DIR"
    for npu_id in $SELECTED_NPUS; do
        log_info "启动 NPU ${npu_id} 占用..."
        ./occupier/occupy_npu --npu "$npu_id" --log "$RUN_DIR/occupy_${npu_id}.log" &
        echo $! > "$RUN_DIR/occupy_${npu_id}.pid"
    done

    # 启动 exporter（使用SELECTED_NPUS）
    log_info "启动 NPU exporter..."
    cd "$WORK_DIR/Exporter"
    export TM_SELECTED_NPUS="$SELECTED_NPUS"
    local npu_count=$(echo $SELECTED_NPUS | wc -w)
    export TM_SELECTED_NPU_COUNT=$npu_count
    local exporter_port=$((AGENT_PORT + 89))
    nohup ./npu_exporter_main serve -p $exporter_port > "$RUN_DIR/exporter.log" 2>&1 &
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

    local service_file="/etc/systemd/system/tokenmachine-ascend-agent.service"

    cat > "$service_file" << EOF
[Unit]
Description=TokenMachine Ascend Agent
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
    systemctl enable tokenmachine-ascend-agent.service

    log_info "✓ systemd服务已创建并启用"
    log_info "  服务文件: $service_file"
    log_info "  管理命令:"
    log_info "    启动: systemctl start tokenmachine-ascend-agent"
    log_info "    停止: systemctl stop tokenmachine-ascend-agent"
    log_info "    状态: systemctl status tokenmachine-ascend-agent"
    log_info "    日志: journalctl -u tokenmachine-ascend-agent -f"
}

# 显示结果
show_results() {
    echo ""
    echo -e "${GREEN}=================================${NC}"
    echo -e "${GREEN}      安装完成！${NC}"
    echo -e "${GREEN}=================================${NC}"
    echo ""

    echo "服务状态:"
    echo "  NPU 占用: $(ps aux | grep occupy_npu | grep -v grep | wc -l) 个进程"
    echo "  Exporter: $(ps aux | grep npu_exporter_main | grep -v grep | wc -l) 个进程"
    echo "  Receiver: $(ps aux | grep receiver | grep -v grep | wc -l) 个进程"
    echo "  Heartbeat: $(ps aux | grep heartbeat.sh | grep -v grep | wc -l) 个进程"
    echo ""

    echo "NPU 状态:"
    npu-smi list
    echo ""

    echo "管理命令:"
    echo "  查看状态: $WORK_DIR/tm_agent.sh status"
    echo "  停止服务: $WORK_DIR/tm_agent.sh stop"
    echo "  重启服务: $WORK_DIR/tm_agent.sh restart"
    echo ""

    echo "API 端点:"
    echo "  Receiver: http://localhost:${AGENT_PORT}"
    echo "  Exporter: http://localhost:$((AGENT_PORT + 89))/metrics"
    echo ""

    echo "故障排查:"
    echo "  查看服务日志: journalctl -u tokenmachine-ascend-agent -f"
    echo "  查看 Agent 日志: tail -f $LOG_FILE"
    echo "  查看 Receiver 日志: tail -f $RUN_DIR/receiver.log"
    echo "  查看 NPU 状态: npu-smi info"
    echo ""
}

# 卸载功能
uninstall() {
    log_info "开始卸载 TokenMachine Ascend Agent"

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
    if systemctl is-active --quiet tokenmachine-ascend-agent; then
        log_info "停止 tokenmachine-ascend-agent 服务..."
        systemctl stop tokenmachine-ascend-agent
    fi

    if systemctl is-enabled --quiet tokenmachine-ascend-agent; then
        log_info "禁用 tokenmachine-ascend-agent 服务..."
        systemctl disable tokenmachine-ascend-agent
    fi

    # 删除 systemd 服务文件
    if [ -f "/etc/systemd/system/tokenmachine-ascend-agent.service" ]; then
        log_info "删除服务文件..."
        rm -f /etc/systemd/system/tokenmachine-ascend-agent.service
        systemctl daemon-reload
    fi

    log_info "正在停止所有相关进程..."

    # 停止所有 occupy_npu 进程
    pkill -f "occupy_npu" || true
    sleep 2

    # 强制停止残留进程
    pkill -9 -f "occupy_npu" || true
    pkill -9 -f "npu_exporter_main" || true
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

    log_info "卸载完成！"
    echo ""
    echo -e "${GREEN}=================================${NC}"
    echo -e "${GREEN}      卸载完成！${NC}"
    echo -e "${GREEN}=================================${NC}"
    echo ""
    echo "已删除："
    echo "  - 服务文件: /etc/systemd/system/tokenmachine-ascend-agent.service"
    echo "  - 工作目录: $WORK_DIR"
    echo "  - 日志目录: $LOG_DIR"
    echo "  - 运行时目录: $RUN_DIR"
    echo "  - 所有相关进程"
    echo ""
}

# 显示帮助信息
show_help() {
    echo "TokenMachine Ascend Agent 安装脚本"
    echo "================================"
    echo ""
    echo "用法:"
    echo "  $0 [选项]"
    echo "  $0 install [选项]    - 安装 Ascend Agent"
    echo "  $0 uninstall         - 卸载 Ascend Agent"
    echo ""
    echo "安装选项:"
    echo "  -s, --server URL    - 服务器地址 (必需)"
    echo "  -p, --port PORT     - Agent 端口 (必需)"
    echo "  -t, --token TOKEN   - Worker Token (必需)"
    echo "  --npus LIST         - NPU 列表 (可选，如 '0 1')"
    echo "  -h, --help          - 显示此帮助信息"
    echo ""
    echo "示例:"
    echo "  $0 install -s http://192.168.247.76:8000 -p 9001 -t <token>"
    echo "  $0 install -s http://192.168.247.76:8000 -p 9001 -t <token> --npus '0 1'"
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
                    --npus)
                        SELECTED_NPUS="$2"
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

            log_info "开始安装 TokenMachine Ascend Agent (预编译 + ACL编译)"
            log_info "服务器地址: $SERVER_URL"
            log_info "Agent 端口: $AGENT_PORT"
            log_info "Worker Token: ${TOKEN:0:16}..."

            # 检查权限
            check_root

            # 检查依赖
            check_dependencies

            # 检查 NPU
            check_npu

            # 获取本地IP地址
            get_local_ips

            # 创建目录
            create_directories

            # 检查预编译的二进制文件并编译 occupy_npu
            check_precompiled_binaries

            # 编译 occupy_npu（CANN ACL 程序）
            compile_occupy_npu

            # 注册Worker到Backend
            register_worker

            # 复制二进制文件
            copy_binaries

            # 创建 NPU 配置
            create_npu_config

            # 启动服务
            start_services

            # 注册所有选中的NPU到Backend
            for npu_id in $SELECTED_NPUS; do
                register_npu $npu_id
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
