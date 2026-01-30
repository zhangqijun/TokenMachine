#!/bin/bash
# ===================================================================
# GPU 监控器 - 定期采集 GPU 信息并写入状态文件
# ===================================================================

STATUS_FILE="/tmp/tokenmachine/worker_status.json"
LOG_FILE="/var/log/tokenmachine/passive-agent.log"

# 采集 GPU 信息
collect_gpu_info() {
    # 获取 GPU 信息（JSON 格式）
    gpu_info=$(nvidia-smi --query-gpu=index,name,memory.total,memory.used,utilization.gpu,temperature.gpu --format=json,noheader)
    
    # 解析并转换为标准格式
    if command -v jq &> /dev/null; then
        echo "$gpu_info" | jq -c '
            .gpu[] | {
                "index": .index,
                "uuid": ("GPU-" + (index | tostring)),
                "name": .name,
                "vendor": "nvidia",
                "memory_used": (.memory.used * 1024 * 1024 | floor),
                "memory_total": (.memory.total * 1024 * 1024 | floor),
                "utilization": .utilization.gpu,
                "temperature": .temperature.gpu,
                "state": (if .utilization.gpu > 0 then "IN_USE" else "AVAILABLE" end)
            }
        '
    else
        # 如果没有 jq，使用简单的文本格式
        echo "[{\"error\": \"jq not installed\"}]"
    fi
}

# 更新状态文件
update_status() {
    local gpu_list=$1
    local timestamp=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
    
    # 构建完整状态
    local status="{
        \"worker_type\": \"passive\",
        \"last_updated\": \"$timestamp\",
        \"gpu_devices\": $gpu_list,
        \"status\": \"READY\"
    }"
    
    # 写入文件（原子操作）
    local temp_file="/tmp/worker_status.json.tmp"
    echo "$status" > "$temp_file"
    mv "$temp_file" "$STATUS_FILE"
    
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] GPU status updated" >> "$LOG_FILE"
}

# 主循环
main() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] GPU monitor started" >> "$LOG_FILE"
    
    while true; do
        # 采集 GPU 信息
        gpu_list=$(collect_gpu_info)
        
        # 更新状态文件
        update_status "$gpu_list"
        
        # 等待 30 秒
        sleep 30
    done
}

# 如果直接运行脚本，启动监控
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main
fi
