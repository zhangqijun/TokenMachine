#!/bin/bash
# install.sh - TokenMachine Agent One-Click Installation Script
#
# This script downloads and installs the TokenMachine GPU agent.
#
# Usage:
#   export TM_TOKEN="tm_worker_abc123"
#   export TM_GPU_IDS="0,1,2,3"
#   curl -sfL https://get.tokenmachine.io | bash -
#
# Environment Variables:
#   TM_TOKEN:    Worker registration token (required)
#   TM_GPU_IDS:  Comma-separated GPU IDs (required)
#   TM_VERSION:  Agent version (default: v1.0.0)
#   TM_SERVER_URL: Server API URL (default: https://api.tokenmachine.io)

set -e

# ============================================================================
# Configuration
# ============================================================================
TM_TOKEN="${TM_TOKEN:?Missing TM_TOKEN}"
TM_GPU_IDS="${TM_GPU_IDS:?Missing TM_GPU_IDS}"
TM_VERSION="${TM_VERSION:-v1.0.0}"
TM_SERVER_URL="${TM_SERVER_URL:-https://api.tokenmachine.io}"

# Download URLs
DOWNLOAD_BASE="https://releases.tokenmachine.io/agent/$TM_VERSION"

# Installation directories
INSTALL_DIR="/opt/tokenmachine"
WORK_DIR="/var/run/tokenmachine"
LOG_DIR="/var/log/tokenmachine"

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# ============================================================================
# Logging Functions
# ============================================================================

log_info() {
    echo -e "${GREEN}[INFO]${NC} $*"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $*"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $*"
}

log_step() {
    echo -e "${BLUE}[STEP]${NC} $*"
}

# ============================================================================
# Error Handling
# ============================================================================

error_exit() {
    log_error "$1"
    exit 1
}

# ============================================================================
# Check Dependencies
# ============================================================================

check_dependencies() {
    log_step "Checking dependencies..."

    # Check if nvidia-smi is available
    if ! command -v nvidia-smi &> /dev/null; then
        error_exit "nvidia-smi not found! Please install NVIDIA driver first."
    fi

    # Check if curl is available
    if ! command -v curl &> /dev/null; then
        error_exit "curl not found! Please install curl first."
    fi

    log_info "Dependencies check passed ✓"
}

# ============================================================================
# Download Files
# ============================================================================

download_files() {
    log_step "Downloading TokenMachine Agent files..."

    # Create temp directory
    local tmp_dir="/tmp/tokenmachine"
    mkdir -p "$tmp_dir"
    cd "$tmp_dir"

    # Download occupy_gpu binary
    log_info "Downloading occupy_gpu..."
    curl -sSL -o occupy_gpu "$DOWNLOAD_BASE/occupy_gpu" || {
        error_exit "Failed to download occupy_gpu"
    }
    chmod +x occupy_gpu

    # Download tm_agent.sh script
    log_info "Downloading tm_agent.sh..."
    curl -sSL -o tm_agent.sh "$DOWNLOAD_BASE/tm_agent.sh" || {
        error_exit "Failed to download tm_agent.sh"
    }
    chmod +x tm_agent.sh

    # Verify files
    if [ ! -x occupy_gpu ] || [ ! -x tm_agent.sh ]; then
        error_exit "Downloaded files are not executable"
    fi

    log_info "Download completed ✓"
}

# ============================================================================
# Install Files
# ============================================================================

install_files() {
    log_step "Installing TokenMachine Agent..."

    # Create directories
    sudo mkdir -p "$INSTALL_DIR"
    sudo mkdir -p "$WORK_DIR"
    sudo mkdir -p "$LOG_DIR"

    # Copy files
    sudo cp occupy_gpu "$INSTALL_DIR/"
    sudo cp tm_agent.sh "$INSTALL_DIR/"

    # Set permissions
    sudo chmod +x "$INSTALL_DIR/occupy_gpu"
    sudo chmod +x "$INSTALL_DIR/tm_agent.sh"

    log_info "Installation completed ✓"
}

# ============================================================================
# Create Systemd Service (Optional)
# ============================================================================

create_systemd_service() {
    if ! command -v systemctl &> /dev/null; then
        log_warn "systemctl not found, skipping systemd service creation"
        return
    fi

    log_step "Creating systemd services..."

    # Parse GPU IDs
    IFS=',' read -ra GPU_ID_ARRAY <<< "$TM_GPU_IDS"

    for gpu_id in "${GPU_ID_ARRAY[@]}"; do
        local service_file="/etc/systemd/system/tm-agent@${gpu_id}.service"

        sudo tee "$service_file" > /dev/null <<EOF
[Unit]
Description=TokenMachine GPU Agent (GPU ${gpu_id})
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=root
Environment="TM_TOKEN=${TM_TOKEN}"
Environment="TM_GPU_ID=${gpu_id}"
Environment="TM_SERVER_URL=${TM_SERVER_URL}"
Environment="TM_HEARTBEAT_INTERVAL=30"
Environment="PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
ExecStartPre=/bin/mkdir -p ${WORK_DIR} ${LOG_DIR}
ExecStart=$INSTALL_DIR/tm_agent.sh
Restart=always
RestartSec=10
StandardOutput=append:${LOG_DIR}/agent_\%i.log
StandardError=append:${LOG_DIR}/agent_\%i.log

[Install]
WantedBy=multi-user.target
EOF

        sudo systemctl daemon-reload
        sudo systemctl enable "tm-agent@${gpu_id}"
        log_info "Created systemd service: tm-agent@${gpu_id}"
    done
}

# ============================================================================
# Start Agents
# ============================================================================

start_agents() {
    log_step "Starting TokenMachine Agents..."

    IFS=',' read -ra GPU_ID_ARRAY <<< "$TM_GPU_IDS"

    for gpu_id in "${GPU_ID_ARRAY[@]}"; do
        if [ -f "/etc/systemd/system/tm-agent@${gpu_id}.service" ]; then
            # Use systemd
            sudo systemctl start "tm-agent@${gpu_id}"
            log_info "Started tm-agent@${gpu_id} (systemd)"
        else
            # Run directly (manual mode)
            TM_TOKEN="$TM_TOKEN" \
            TM_GPU_ID="$gpu_id" \
            TM_SERVER_URL="$TM_SERVER_URL" \
                nohup "$INSTALL_DIR/tm_agent.sh" \
                    > "$LOG_DIR/agent_${gpu_id}.log" 2>&1 &

            log_info "Started agent for GPU ${gpu_id} (manual mode)"
        fi
    done
}

# ============================================================================
# Check Status
# ============================================================================

check_status() {
    log_step "Checking agent status..."

    sleep 3  # Wait for agents to start

    IFS=',' read -ra GPU_ID_ARRAY <<< "$TM_GPU_IDS"

    local success_count=0
    local total_count=${#GPU_ID_ARRAY[@]}

    for gpu_id in "${GPU_ID_ARRAY[@]}"; do
        # Check agent process
        if pgrep -f "tm_agent.sh.*$gpu_id" > /dev/null; then
            log_info "✓ GPU ${gpu_id}: Agent running"
            ((success_count++))
        else
            log_error "✗ GPU ${gpu_id}: Agent not running"
        fi

        # Check occupy process
        if pgrep -f "occupy_gpu.*$gpu_id" > /dev/null; then
            log_info "  └─ Occupy process: Running"
        else
            log_warn "  └─ Occupy process: Not found"
        fi
    done

    echo ""
    log_info "Status: ${success_count}/${total_count} agents started"
}

# ============================================================================
# Print Usage Info
# ============================================================================

print_usage_info() {
    echo ""
    echo "============================================================"
    echo "TokenMachine Agent Installation Completed!"
    echo "============================================================"
    echo ""
    echo "Installation Info:"
    echo "  Version:     $TM_VERSION"
    echo "  GPUs:        $TM_GPU_IDS"
    echo "  Install Dir: $INSTALL_DIR"
    echo "  Log Dir:     $LOG_DIR"
    echo "  Work Dir:    $WORK_DIR"
    echo ""
    echo "Management Commands:"
    echo "  View logs:    sudo tail -f $LOG_DIR/agent_<GPU_ID>.log"
    echo "  Stop agent:   sudo systemctl stop tm-agent@<GPU_ID>"
    echo "  Start agent:  sudo systemctl start tm-agent@<GPU_ID>"
    echo "  Restart:      sudo systemctl restart tm-agent@<GPU_ID>"
    echo "  Status:       sudo systemctl status tm-agent@<GPU_ID>"
    echo ""
    echo "Troubleshooting:"
    echo "  Check GPU:    nvidia-smi"
    echo "  Check processes: ps aux | grep tm_agent"
    echo "  Check occupy: ps aux | grep occupy_gpu"
    echo ""
    echo "Documentation: https://docs.tokenmachine.io"
    echo "============================================================"
}

# ============================================================================
# Main Program
# ============================================================================

main() {
    echo ""
    echo "============================================================"
    echo "TokenMachine Agent Installer"
    echo "============================================================"
    echo "Version: $TM_VERSION"
    echo "GPUs: $TM_GPU_IDS"
    echo "============================================================"
    echo ""

    # Execute installation steps
    check_dependencies
    download_files
    install_files
    create_systemd_service
    start_agents
    check_status
    print_usage_info
}

# Run main
main "$@"
