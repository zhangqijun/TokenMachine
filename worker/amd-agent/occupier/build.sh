#!/bin/bash

# TokenMachine AMD Agent occupy_gpu Build Script
# Compiles HIP program for AMD GPU memory occupation

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "================================================"
echo "  Building AMD GPU Memory Occupier"
echo "================================================"
echo ""

# Check if we're in mock mode (no HIP available)
MOCK_MODE=0

if ! command -v hipcc &> /dev/null; then
    echo "WARNING: hipcc not found"
    echo "This is expected if ROCm/HIP is not installed"
    echo ""

    # Check for alternative HIP locations
    HIP_PATHS=(
        "/opt/rocm/hip/bin/hipcc"
        "/opt/rocm-*/hip/bin/hipcc"
    )

    FOUND_HIP=0
    for HIP_PATH in "${HIP_PATHS[@]}"; do
        if ls $HIP_PATH &> /dev/null 2>&1; then
            echo "Found HIP at: $HIP_PATH"
            FOUND_HIP=1
            break
        fi
    done

    if [ $FOUND_HIP -eq 0 ]; then
        echo ""
        echo "INFO: Creating mock occupy_gpu binary..."
        echo "      This binary will run in mock/simulation mode"
        MOCK_MODE=1
    fi
fi

if [ $MOCK_MODE -eq 0 ]; then
    # Real HIP compilation
    echo ""
    echo "[1/1] Compiling occupy_gpu.hip..."

    # Find HIP compiler
    HIPCC="hipcc"
    if ! command -v hipcc &> /dev/null; then
        if [ -f "/opt/rocm/hip/bin/hipcc" ]; then
            HIPCC="/opt/rocm/hip/bin/hipcc"
        fi
    fi

    echo "Using HIP compiler: $HIPCC"

    # Compile with optimization
    $HIPCC -O3 -o occupy_gpu occupy_gpu.hip

    if [ $? -ne 0 ]; then
        echo "ERROR: Failed to compile occupy_gpu.hip"
        exit 1
    fi

    echo ""
    echo "[Verify] Checking binary..."
    if file occupy_gpu | grep -q "ELF"; then
        echo "✓ occupy_gpu compiled successfully (ELF executable)"
    else
        echo "⚠ Warning: Binary may not be a valid ELF executable"
    fi
else
    # Create a simple mock binary (shell script that simulates occupation)
    cat > occupy_gpu << 'MOCK_SCRIPT'
#!/bin/bash
# Mock occupy_gpu - simulates memory occupation without real AMD GPU
# This runs in mock/simulation mode

GPU_ID=0
OCCUPY_PERCENT=90
MOCK_MODE=1
LOG_FILE=""

print_help() {
    echo "AMD GPU Memory Occupier (MOCK MODE)"
    echo "==================================="
    echo ""
    echo "Usage: $0 [options]"
    echo ""
    echo "Options:"
    echo "  -g, --gpu <id>        GPU index (default: 0)"
    echo "  -p, --percent <%>     Memory percentage (default: 90)"
    echo "  -m, --mock            Enable mock mode"
    echo "  -l, --log <file>      Log file"
    echo "  -h, --help            Show help"
    echo ""
}

parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            -g|--gpu)
                GPU_ID="$2"
                shift 2
                ;;
            -p|--percent)
                OCCUPY_PERCENT="$2"
                shift 2
                ;;
            -m|--mock)
                MOCK_MODE=1
                shift
                ;;
            -l|--log)
                LOG_FILE="$2"
                shift 2
                ;;
            -h|--help)
                print_help
                exit 0
                ;;
            *)
                echo "Unknown option: $1"
                print_help
                exit 1
                ;;
        esac
    done
}

log_msg() {
    msg="[$(date '+%Y-%m-%d %H:%M:%S')] [MOCK] $*"
    echo "$msg"
    if [ -n "$LOG_FILE" ]; then
        echo "$msg" >> "$LOG_FILE"
    fi
}

parse_args "$@"

log_msg "Starting AMD GPU Memory Occupier (MOCK MODE)"
log_msg "GPU ID: $GPU_ID"
log_msg "Occupy: ${OCCUPY_PERCENT}%"
log_msg "Simulating memory occupation..."

# Simulate memory allocation
MOCK_MEMORY=$((OCCUPY_PERCENT * 100))  # Simple simulation

log_msg "Mock memory allocated: ${MOCK_MEMORY}MB"
log_msg "Holding memory allocation... (PID: $$)"

# Wait for signal
trap 'log_msg "Shutting down, freeing mock memory..."; exit 0' SIGINT SIGTERM SIGHUP

while true; do
    sleep 1
done
MOCK_SCRIPT

    chmod +x occupy_gpu
    echo "✓ Created mock occupy_gpu binary"
fi

echo ""
echo "================================================"
echo "  Build Complete!"
echo "================================================"
echo ""
echo "Binary: $SCRIPT_DIR/occupy_gpu"
echo ""
echo "Usage:"
echo "  ./occupy_gpu --help"
echo "  ./occupy_gpu --gpu 0 --percent 90 --mock"
echo ""
