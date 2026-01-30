#!/bin/bash

# GPU Agent Test Environment Setup Script

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKER_DIR="$(dirname "$SCRIPT_DIR")"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}GPU Agent Test Environment Setup${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Check Python
echo -e "${BLUE}[1/5] Checking Python...${NC}"
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Error: Python 3 not found${NC}"
    exit 1
fi

PYTHON_VERSION=$(python3 --version | awk '{print $2}')
echo -e "${GREEN}✓ Python version: $PYTHON_VERSION${NC}"
echo ""

# Check pip
echo -e "${BLUE}[2/5] Checking pip...${NC}"
if ! command -v pip3 &> /dev/null; then
    echo -e "${RED}Error: pip3 not found${NC}"
    exit 1
fi
echo -e "${GREEN}✓ pip3 available${NC}"
echo ""

# Install dependencies
echo -e "${BLUE}[3/5] Installing test dependencies...${NC}"
pip3 install -r "$SCRIPT_DIR/requirements.txt"
echo -e "${GREEN}✓ Dependencies installed${NC}"
echo ""

# Setup environment file
echo -e "${BLUE}[4/5] Setting up environment...${NC}"
ENV_FILE="$SCRIPT_DIR/.env.test"

if [ -f "$ENV_FILE" ]; then
    echo -e "${YELLOW}⚠ Environment file already exists: $ENV_FILE${NC}"
    read -p "Overwrite? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Skipping environment setup"
    else
        setup_environment
    fi
else
    setup_environment
fi

setup_environment() {
    cp "$SCRIPT_DIR/.env.test.example" "$ENV_FILE"

    # Prompt for values
    echo ""
    echo "Please enter test configuration values:"
    echo "(Press Enter to use default values)"
    echo ""

    # TARGET_HOST
    read -p "TARGET_HOST [ht706@192.168.247.76]: " target_host
    target_host=${target_host:-ht706@192.168.247.76}
    sed -i "s|^TARGET_HOST=.*|TARGET_HOST=$target_host|" "$ENV_FILE"

    # TARGET_IP
    read -p "TARGET_IP [192.168.247.76]: " target_ip
    target_ip=${target_ip:-192.168.247.76}
    sed -i "s|^TARGET_IP=.*|TARGET_IP=$target_ip|" "$ENV_FILE"

    # BACKEND_URL
    read -p "BACKEND_URL [http://localhost:8000]: " backend_url
    backend_url=${backend_url:-http://localhost:8000}
    sed -i "s|^BACKEND_URL=.*|BACKEND_URL=$backend_url|" "$ENV_FILE"

    # WORKER_TOKEN
    read -p "WORKER_TOKEN [test_token_$(date +%s)]: " worker_token
    worker_token=${worker_token:-test_token_$(date +%s)}
    sed -i "s|^WORKER_TOKEN=.*|WORKER_TOKEN=$worker_token|" "$ENV_FILE"

    echo ""
    echo -e "${GREEN}✓ Environment file created: $ENV_FILE${NC}"
}

echo ""

# Check SSH connection
echo -e "${BLUE}[5/5] Testing SSH connection...${NC}"
if [ -f "$ENV_FILE" ]; then
    source "$ENV_FILE"
    if ssh -o ConnectTimeout=5 -o BatchMode=yes "$TARGET_HOST" "echo 'SSH connection successful'" 2>/dev/null; then
        echo -e "${GREEN}✓ SSH connection successful${NC}"
    else
        echo -e "${YELLOW}⚠ SSH connection failed or requires password${NC}"
        echo "  Tests requiring SSH will fail"
        echo "  Ensure SSH key-based auth is set up, or run:"
        echo "  ssh-copy-id $TARGET_HOST"
    fi
else
    echo -e "${YELLOW}⚠ Skipping SSH test (no .env.test file)${NC}"
fi

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Setup Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "Next steps:"
echo "  1. Review environment: cat $ENV_FILE"
echo "  2. Run tests: cd $WORKER_DIR && pytest"
echo "  3. Or use make: cd $WORKER_DIR && make test"
echo ""
