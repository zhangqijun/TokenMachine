#!/bin/bash
# tm_agent.sh - TokenMachine GPU Agent (Pure Shell)
#
# This script runs on each GPU and handles:
#  1. GPU memory occupation (via occupy_gpu)
#  2. GPU registration to server
#  3. Periodic heartbeat reporting
#
# Usage:
#   export TM_TOKEN="tm_worker_abc123"
#   export TM_GPU_ID="0"
#   ./tm_agent.sh
#
# Environment Variables:
#   TM_TOKEN:           Worker registration token (required)
#   TM_GPU_ID:          GPU ID to manage (required)
#   TM_SERVER_URL:      Server API URL (default: https://api.tokenmachine.io)
#   TM_AGENT_PORT:      Agent port (default: 9000 + GPU_ID)
#   TM_HEARTBEAT_INTERVAL: Heartbeat interval in seconds (default: 30)

set -e

# ============================================================================
# Configuration
# ============================================================================
TM_TOKEN="${TM_TOKEN:?Missing TM_TOKEN}"
TM_GPU_ID="${TM_GPU_ID:?Missing TM_GPU_ID}"
TM_SERVER_URL="${TM_SERVER_URL:-https://api.tokenmachine.io}"
TM_AGENT_PORT="${TM_AGENT_PORT:-$((9000 + TM_GPU_ID))}"
TM_HEARTBEAT_INTERVAL="${TM_HEARTBEAT_INTERVAL:-30}"

# Work directory
TM_WORK_DIR="/var/run/tokenmachine"
TM_PID_FILE="$TM_WORK_DIR/agent_${TM_GPU_ID}.pid"
TM_OCCUPY_PID_FILE="$TM_WORK_DIR/occupy_${TM_GPU_ID}.pid"
TM_GPU_UUID_FILE="$TM_WORK_DIR/gpu_uuid_${TM_GPU_ID}.txt"

# Log file
LOG_FILE="${TM_LOG_FILE:-/var/log/tokenmachine/agent_${TM_GPU_ID}.log}"

# Occupying program path
OCCUPY_BIN="${OCCUPY_BIN:-./occupy_gpu}"

# ============================================================================
# Logging Functions
# ============================================================================

log() {
    local msg="[$(date '+%Y-%m-%d %H:%M:%S')] [$TM_GPU_ID] $*"
    echo "$msg"
    echo "$msg" >> "$LOG_FILE"
}

log_error() {
    log "ERROR: $*"
}

log_info() {
    log "INFO: $*"
}

log_warn() {
    log "WARN: $*"
}

# ============================================================================
# Utility Functions
# ============================================================================

# Get local IP address
get_local_ip() {
    # Try multiple methods
    ip route get 1 2>/dev/null | awk '{print $7}' | head -1 && return 0
    hostname -I 2>/dev/null | awk '{print $1}' && return 0
    echo "127.0.0.1"
}

# Get hostname
get_hostname() {
    hostname
}

# JSON escape string
json_escape() {
    local str="$1"
    # Escape backslashes, quotes, and newlines
    echo "$str" | sed 's/\\/\\\\/g' | sed 's/"/\\"/g' | sed ':a;N;$!ba;s/\n/\\n/g'
}

# ============================================================================
# GPU Information Functions
# ============================================================================

# Get GPU info using nvidia-smi
get_gpu_info() {
    nvidia-smi -i "$TM_GPU_ID" \
        --query-gpu=name,uuid,memory.total,pci.bus_id \
        --format=csv,noheader,nounits 2>/dev/null || return 1
}

# Get GPU status using nvidia-smi
get_gpu_status() {
    nvidia-smi -i "$TM_GPU_ID" \
        --query-gpu=utilization.gpu,memory.used,memory.total,temperature.gpu \
        --format=csv,noheader,nounits 2>/dev/null || return 1
}

# Parse CSV line and return fields
parse_csv() {
    local csv="$1"
    local field="$2"
    echo "$csv" | awk -F',' -v field="$field" '{
        gsub(/^[ \t]+|[ \t]+$/, "", $field)
        print $field
    }'
}

# ============================================================================
# Occupy GPU Memory
# ============================================================================

start_occupy() {
    log_info "Starting occupy process for GPU $TM_GPU_ID..."

    # Check if already running
    if [ -f "$TM_OCCUPY_PID_FILE" ]; then
        local pid=$(cat "$TM_OCCUPY_PID_FILE")
        if kill -0 "$pid" 2>/dev/null; then
            log_info "Occupy process already running (PID: $pid)"
            return 0
        fi
    fi

    # Create work directory
    mkdir -p "$TM_WORK_DIR"

    # Start occupy process
    "$OCCUPY_BIN" "$TM_GPU_ID" 0.95 > "$TM_WORK_DIR/occupy_${TM_GPU_ID}.log" 2>&1 &
    local occupy_pid=$!

    # Wait for occupy to initialize
    sleep 2

    # Check if process is still running
    if ! kill -0 "$occupy_pid" 2>/dev/null; then
        log_error "Occupy process failed!"
        if [ -f "$TM_WORK_DIR/occupy_${TM_GPU_ID}.log" ]; then
            log_error "Occupy log:"
            cat "$TM_WORK_DIR/occupy_${TM_GPU_ID}.log" | while read line; do
                log_error "  $line"
            done
        fi
        exit 1
    fi

    # Save PID
    echo "$occupy_pid" > "$TM_OCCUPY_PID_FILE"
    log_info "GPU $TM_GPU_ID occupied successfully (PID: $occupy_pid)"
}

# ============================================================================
# GPU Registration
# ============================================================================

register_gpu() {
    log_info "Registering GPU $TM_GPU_ID to server..."

    # Get GPU info
    local gpu_info
    gpu_info=$(get_gpu_info)

    if [ $? -ne 0 ]; then
        log_error "Failed to get GPU info using nvidia-smi"
        return 1
    fi

    # Parse CSV output
    local gpu_name=$(parse_csv "$gpu_info" 1)
    local gpu_uuid=$(parse_csv "$gpu_info" 2)
    local gpu_memory_total=$(parse_csv "$gpu_info" 3)
    local pci_bus=$(parse_csv "$gpu_info" 4)

    # Remove spaces from UUID (nvidia-smi adds them)
    gpu_uuid=$(echo "$gpu_uuid" | tr -d ' ')

    local gpu_ip=$(get_local_ip)
    local gpu_hostname=$(get_hostname)
    local gpu_index=$TM_GPU_ID
    local memory_allocated=$((gpu_memory_total * 95 / 100))  # 95%
    local agent_pid=$$

    # Save UUID for later use
    echo "$gpu_uuid" > "$TM_GPU_UUID_FILE"

    log_info "GPU Info:"
    log_info "  Name: $gpu_name"
    log_info "  UUID: $gpu_uuid"
    log_info "  Memory: $((gpu_memory_total / 1024 / 1024 / 1024)) GB"
    log_info "  IP: $gpu_ip"
    log_info "  Hostname: $gpu_hostname"

    # Construct JSON payload
    local json_payload="{\"gpu\": {"
    json_payload+="\"gpu_uuid\": \"$(json_escape "$gpu_uuid")\","
    json_payload+="\"gpu_index\": $gpu_index,"
    json_payload+="\"ip\": \"$gpu_ip\","
    json_payload+="\"port\": $TM_AGENT_PORT,"
    json_payload+="\"memory_total\": $gpu_memory_total,"
    json_payload+="\"memory_allocated\": $memory_allocated,"
    json_payload+="\"memory_utilization_rate\": 0.0,"
    json_payload+="\"temperature\": 35.0,"
    json_payload+="\"agent_pid\": $agent_pid,"
    json_payload+="\"vllm_pid\": null,"
    json_payload+="\"timestamp\": \"$(date -u +"%Y-%m-%dT%H:%M:%SZ")\","
    json_payload+="\"state\": \"in_use\","
    json_payload+="\"extra\": {"
    json_payload+="\"name\": \"$(json_escape "$gpu_name")\","
    json_payload+="\"hostname\": \"$(json_escape "$gpu_hostname")\","
    json_payload+="\"pci_bus\": \"$(json_escape "$pci_bus")\""
    json_payload+="}"
    json_payload+="}}"

    # Send registration request
    log_info "Sending registration request to $TM_SERVER_URL..."

    local response
    response=$(curl -s -X POST \
        --max-time 10 \
        -H "Authorization: Bearer $TM_TOKEN" \
        -H "Content-Type: application/json" \
        -d "$json_payload" \
        "$TM_SERVER_URL/api/v1/gpus/workers/register-gpu" 2>&1)

    local curl_exit=$?

    if [ $curl_exit -eq 0 ]; then
        log_info "Registration successful: $response"

        # Save registration response
        echo "$response" > "$TM_WORK_DIR/register_response_${TM_GPU_ID}.json"

        return 0
    else
        log_error "Registration failed: curl exit code $curl_exit"
        log_error "Response: $response"
        return 1
    fi
}

# ============================================================================
# Heartbeat Functions
# ============================================================================

send_heartbeat() {
    # Read UUID
    if [ ! -f "$TM_GPU_UUID_FILE" ]; then
        log_error "GPU UUID file not found, need to register first"
        return 1
    fi

    local gpu_uuid=$(cat "$TM_GPU_UUID_FILE")
    gpu_uuid=$(echo "$gpu_uuid" | tr -d ' ')

    # Get GPU status
    local status
    status=$(get_gpu_status)

    if [ $? -ne 0 ]; then
        log_error "Failed to get GPU status"
        return 1
    fi

    # Parse CSV output
    local gpu_util=$(parse_csv "$status" 1)
    local mem_used=$(parse_csv "$status" 2)
    local mem_total=$(parse_csv "$status" 3)
    local temperature=$(parse_csv "$status" 4)

    # Remove spaces
    gpu_util=$(echo "$gpu_util" | tr -d ' ')
    mem_used=$(echo "$mem_used" | tr -d ' ')
    mem_total=$(echo "$mem_total" | tr -d ' ')
    temperature=$(echo "$temperature" | tr -d ' ')

    # Calculate utilization rate
    local mem_util=$(awk "BEGIN {printf \"%.2f\", $mem_used / $mem_total}")
    local core_util=$(awk "BEGIN {printf \"%.2f\", $gpu_util / 100.0}")

    local agent_pid=$$
    local gpu_ip=$(get_local_ip)

    # Construct JSON payload
    local json_payload="{"
    json_payload+="\"gpu_uuid\": \"$(json_escape "$gpu_uuid")\","
    json_payload+="\"gpu_index\": $TM_GPU_ID,"
    json_payload+="\"ip\": \"$gpu_ip\","
    json_payload+="\"port\": $TM_AGENT_PORT,"
    json_payload+="\"memory_total\": $mem_total,"
    json_payload+="\"memory_used\": $mem_used,"
    json_payload+="\"memory_allocated\": $mem_total,"
    json_payload+="\"memory_utilization_rate\": $mem_util,"
    json_payload+="\"core_utilization_rate\": $core_util,"
    json_payload+="\"temperature\": $temperature,"
    json_payload+="\"agent_pid\": $agent_pid,"
    json_payload+="\"vllm_pid\": null,"
    json_payload+="\"timestamp\": \"$(date -u +"%Y-%m-%dT%H:%M:%SZ")\","
    json_payload+="\"state\": \"in_use\","
    json_payload+="\"extra\": null"
    json_payload+="}"

    # Send heartbeat
    local response
    response=$(curl -s -X POST \
        --max-time 5 \
        -H "Authorization: Bearer $TM_TOKEN" \
        -H "Content-Type: application/json" \
        -d "$json_payload" \
        "$TM_SERVER_URL/api/v1/gpus/heartbeat" 2>&1)

    local curl_exit=$?

    if [ $curl_exit -eq 0 ]; then
        log_info "Heartbeat sent (util=${gpu_util}%, mem=${mem_used}MiB, temp=${temperature}°C)"
        return 0
    else
        log_warn "Heartbeat failed: curl exit code $curl_exit"
        return 1
    fi
}

# ============================================================================
# Heartbeat Loop
# ============================================================================

heartbeat_loop() {
    log_info "Starting heartbeat loop (interval: ${TM_HEARTBEAT_INTERVAL}s)"

    while true; do
        sleep "$TM_HEARTBEAT_INTERVAL"
        send_heartbeat
    done
}

# ============================================================================
# Cleanup Functions
# ============================================================================

cleanup() {
    log_info "Cleaning up..."

    # Stop heartbeat loop (by exiting)
    if [ -f "$TM_PID_FILE" ]; then
        rm -f "$TM_PID_FILE"
    fi

    # Stop occupy process
    if [ -f "$TM_OCCUPY_PID_FILE" ]; then
        local occupy_pid=$(cat "$TM_OCCUPY_PID_FILE")
        if kill -0 "$occupy_pid" 2>/dev/null; then
            log_info "Stopping occupy process (PID: $occupy_pid)"
            kill -TERM "$occupy_pid" 2>/dev/null || true
            sleep 1
            kill -KILL "$occupy_pid" 2>/dev/null || true
        fi
        rm -f "$TM_OCCUPY_PID_FILE"
    fi

    log_info "Cleanup done"
    exit 0
}

# ============================================================================
# Main Program
# ============================================================================

main() {
    # Set up signal handlers
    trap cleanup TERM INT

    # Create log directory
    mkdir -p "$(dirname "$LOG_FILE")"
    mkdir -p "$TM_WORK_DIR"

    # Record PID
    echo $$ > "$TM_PID_FILE"

    # Print startup banner
    log_info "=================================================="
    log_info "TokenMachine GPU Agent starting..."
    log_info "=================================================="
    log_info "Token: ${TM_TOKEN:0:20}..."
    log_info "GPU ID: $TM_GPU_ID"
    log_info "Server: $TM_SERVER_URL"
    log_info "Port: $TM_AGENT_PORT"
    log_info "Heartbeat Interval: ${TM_HEARTBEAT_INTERVAL}s"
    log_info "PID: $$"
    log_info "=================================================="

    # Check nvidia-smi
    if ! command -v nvidia-smi &> /dev/null; then
        log_error "nvidia-smi not found! Please install NVIDIA driver."
        exit 1
    fi

    # Check GPU exists
    if ! nvidia-smi -i "$TM_GPU_ID" &> /dev/null; then
        log_error "GPU $TM_GPU_ID not found!"
        log_error "Available GPUs:"
        nvidia-smi --list-gpus | while read line; do
            log_error "  $line"
        done
        exit 1
    fi

    # Phase 1: Occupy GPU
    start_occupy

    # Phase 2: Register GPU
    if ! register_gpu; then
        log_error "Registration failed, exiting..."
        cleanup
    fi

    # Phase 3: Heartbeat loop
    heartbeat_loop
}

# Start agent
main "$@"
