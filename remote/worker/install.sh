#!/bin/bash
# ===================================================================
# TokenMachine Remote Worker Installation Script (Passive Mode)
# 用于公网 Worker 节点，Server 在内网通过 SSH 隧道连接
# ===================================================================

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# 配置变量
WORKER_NAME=""
WORKER_ID=""
INSTALL_DIR="/opt/tokenmachine/passive_worker"
LOG_DIR="/var/log/tokenmachine"
PID_FILE="$INSTALL_DIR/.agent.pid"

print_help() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  -n, --name NAME      Worker name (default: remote-\$(hostname))"
    echo "  -i, --id ID         Worker ID (assigned by Server)"
    echo "  -h, --help           Show this help message"
    echo ""
    echo "This script installs a passive worker agent that:"
    echo "  1. Listens on port 9001 for task commands"
    echo "  2. Exposes Prometheus metrics on port 9090"
    echo "  3. Writes status to /tmp/worker_status.json"
    echo "  4. Does NOT actively connect to Server"
    echo ""
    echo "Example:"
    echo "  $0 -n remote-v100-01 -i 123"
    exit 0
}

# 解析参数
while [[ $# -gt 0 ]]; do
    case "$1" in
        -n|--name)
            WORKER_NAME="$2"
            shift 2
            ;;
        -i|--id)
            WORKER_ID="$2"
            shift 2
            ;;
        -h|--help)
            print_help
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            print_help
            ;;
    esac
done

if [[ -z "$WORKER_NAME" ]]; then
    WORKER_NAME="remote-$(hostname)"
fi

echo -e "${GREEN}=== TokenMachine Passive Worker Installation ===${NC}"
echo ""
echo "Configuration:"
echo "  Worker Name: $WORKER_NAME"
echo "  Worker ID: ${WORKER_ID:-'Not assigned yet'}"
echo "  Install Dir: $INSTALL_DIR"
echo "  Log Dir: $LOG_DIR"
echo ""

# 检查依赖
echo -e "${YELLOW}Checking dependencies...${NC}"

if ! command -v curl &> /dev/null; then
    echo -e "${RED}Error: curl is not installed${NC}"
    exit 1
fi

if ! command -v jq &> /dev/null; then
    echo -e "${YELLOW}Installing jq...${NC}"
    apt-get update -qq
    apt-get install -y jq
fi

if ! command -v nvidia-smi &> /dev/null; then
    echo -e "${RED}Error: nvidia-smi not found${NC}"
    exit 1
fi

echo -e "${GREEN}✓ All dependencies OK${NC}"

# 创建目录
echo ""
echo -e "${YELLOW}Creating directories...${NC}"
sudo mkdir -p "$INSTALL_DIR"
sudo mkdir -p "$LOG_DIR"
sudo mkdir -p /tmp/tokenmachine

# 脚本目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

sudo cp "$SCRIPT_DIR/tm_passive_agent.sh" "$INSTALL_DIR/"
sudo cp "$SCRIPT_DIR/task_handler.sh" "$INSTALL_DIR/"
sudo cp "$SCRIPT_DIR/gpu_monitor.sh" "$INSTALL_DIR/"

sudo chmod +x "$INSTALL_DIR"/*.sh

# 创建配置
echo -e "${YELLOW}Creating configuration...${NC}"

sudo tee "$INSTALL_DIR/.config" > /dev/null <<EOF
WORKER_NAME="$WORKER_NAME"
WORKER_ID="$WORKER_ID"
TASK_PORT=9001
METRICS_PORT=9090
STATUS_FILE=/tmp/tokenmachine/worker_status.json
EOF

# 创建 systemd 服务
echo -e "${YELLOW}Creating systemd service...${NC}"

sudo tee /etc/systemd/system/tm-passive-agent.service > /dev/null <<EOF
[Unit]
Description=TokenMachine Passive Worker Agent
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=$INSTALL_DIR
ExecStart=$INSTALL_DIR/tm_passive_agent.sh start
Restart=on-failure
RestartSec=10
StandardOutput=append:$LOG_DIR/passive-agent.log
StandardError=append:$LOG_DIR/passive-agent.error.log

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload

echo -e "${GREEN}✓ Installation complete${NC}"

echo ""
echo "Useful commands:"
echo "  Start:   sudo systemctl start tm-passive-agent"
echo "  Stop:    sudo systemctl stop tm-passive-agent"
echo "  Status:  sudo systemctl status tm-passive-agent"
echo "  Logs:    sudo tail -f $LOG_DIR/passive-agent.log"
echo ""
echo "To start now: sudo systemctl start tm-passive-agent"
