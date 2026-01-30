#!/bin/bash
# Pre-flight check for local GPU agent testing

echo "=========================================="
echo "GPU Agent 本地测试预检查"
echo "=========================================="
echo ""

FAILED=0

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check function
check() {
    local name=$1
    local command=$2
    local expected=$3
    
    echo -n "Checking $name... "
    
    if eval "$command" > /dev/null 2>&1; then
        echo -e "${GREEN}✓ PASS${NC}"
        return 0
    else
        echo -e "${RED}✗ FAIL${NC}"
        if [ -n "$expected" ]; then
            echo "  Expected: $expected"
        fi
        FAILED=1
        return 1
    fi
}

# 1. Backend
echo "=== Backend 检查 ==="
check "Backend运行" "curl -sf http://localhost:8000/health" "http://localhost:8000/health"
check "Workers API" "curl -sf http://localhost:8000/workers" "http://localhost:8000/workers"
echo ""

# 2. GPU
echo "=== GPU 检查 ==="
check "NVIDIA驱动" "nvidia-smi" "nvidia-smi command"
check "GPU数量" "nvidia-smi --list-gpus | grep -q GPU" "至少1个GPU"

# GPU 0 available
GPU_COUNT=$(nvidia-smi --list-gpus 2>/dev/null | wc -l)
echo -e "  ${GREEN}检测到 $GPU_COUNT 个GPU${NC}"
echo ""

# 3. Ports
echo "=== 端口检查 ==="
check "9090端口未占用" "! netstat -tlnp 2>/dev/null | grep -q ':9090'" "端口9090应该未被占用"
check "9001端口未占用" "! netstat -tlnp 2>/dev/null | grep -q ':9001'" "端口9001应该未被占用"
echo ""

# 4. Sudo
echo "=== 权限检查 ==="
check "Sudo权限" "sudo -n true" "sudo无密码访问"
echo ""

# 5. CUDA
echo "=== CUDA 检查 ==="
check "NVCC编译器" "which nvcc" "nvcc in PATH"
check "CUDA路径" "test -d /usr/local/cuda" "/usr/local/cuda directory"

if command -v nvcc &> /dev/null; then
    CUDA_VERSION=$(nvcc --version | grep release | head -1)
    echo -e "  ${GREEN}$CUDA_VERSION${NC}"
fi
echo ""

# 6. Binaries (if testing deployment)
echo "=== 二进制文件检查 ==="
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
GPU_AGENT_DIR="$SCRIPT_DIR/../gpu-agent"

check "Exporter二进制" "test -f $GPU_AGENT_DIR/Exporter/gpu_exporter_main" "$GPU_AGENT_DIR/Exporter/gpu_exporter_main"
check "Receiver二进制" "test -f $GPU_AGENT_DIR/Receiver/receiver" "$GPU_AGENT_DIR/Receiver/receiver"
check "occupy_gpu源码" "test -f $GPU_AGENT_DIR/occupier/occupy_gpu.cu" "$GPU_AGENT_DIR/occupier/occupy_gpu.cu"
echo ""

# Summary
echo "=========================================="
if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}所有预检查通过！可以运行测试${NC}"
    echo ""
    echo "运行测试："
    echo "  cd worker/tests"
    echo "  TEST_MODE=local pytest test_gpu_agent.py::TestCompleteDeployment -v"
    exit 0
else
    echo -e "${RED}部分预检查失败！请先解决上述问题${NC}"
    exit 1
fi
