#!/bin/bash

# Test script to verify 90% GPU memory allocation

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORK_DIR="/opt/tokenmachine"
LOG_DIR="/var/log/tokenmachine"
RUN_DIR="/var/run/tokenmachine"

log_info() {
    echo -e "\033[0;32m[INFO]\033[0m $*"
}

log_error() {
    echo -e "\033[0;31m[ERROR]\033[0m $*" >&2
}

# Check if we're on the right system
if [[ $(hostname) != "Bulbasaur" ]]; then
    log_error "This script should be run on Bulbasaur"
    exit 1
fi

# Check if CUDA is available
if ! command -v nvidia-smi &> /dev/null; then
    log_error "nvidia-smi not found"
    exit 1
fi

if ! nvidia-smi &> /dev/null; then
    log_error "NVIDIA driver not working"
    exit 1
fi

# Create directories
mkdir -p "$LOG_DIR"
mkdir -p "$RUN_DIR"

# Show initial GPU state
log_info "Initial GPU state:"
nvidia-smi --query-gpu=index,name,memory.used,memory.total,memory.utilization --format=csv

# Test occupy_gpu with 90% memory
log_info "Testing occupy_gpu with 90% memory allocation..."

# Stop any existing processes
pkill -f "occupy_gpu" || true
sleep 2

# Test GPU 0
log_info "Starting occupy_gpu on GPU 0 for 5 seconds..."
./occupy_gpu --gpu 0 --log /tmp/test_occupy_0.log &
OCCUPY_PID0=$!

# Wait a bit for memory allocation
sleep 2

# Check GPU memory usage
log_info "GPU memory usage after 2 seconds:"
nvidia-smi --query-gpu=index,memory.used,memory.total,memory.utilization --format=csv

# Stop the process
kill $OCCUPY_PID0
wait $OCCUPY_PID0 2>/dev/null || true
sleep 1

# Test GPU 1
log_info "Starting occupy_gpu on GPU 1 for 5 seconds..."
./occupy_gpu --gpu 1 --log /tmp/test_occupy_1.log &
OCCUPY_PID1=$!

# Wait a bit for memory allocation
sleep 2

# Check GPU memory usage
log_info "GPU memory usage after 2 seconds:"
nvidia-smi --query-gpu=index,memory.used,memory.total,memory.utilization --format=csv

# Stop the process
kill $OCCUPY_PID1
wait $OCCUPY_PID1 2>/dev/null || true
sleep 1

# Final GPU state
log_info "Final GPU state:"
nvidia-smi --query-gpu=index,name,memory.used,memory.total,memory.utilization --format=csv

# Check log files
if [ -f "/tmp/test_occupy_0.log" ]; then
    log_info "GPU 0 log excerpt:"
    grep -E "(Starting|Successfully|90%)" /tmp/test_occupy_0.log | head -5
fi

if [ -f "/tmp/test_occupy_1.log" ]; then
    log_info "GPU 1 log excerpt:"
    grep -E "(Starting|Successfully|90%)" /tmp/test_occupy_1.log | head -5
fi

# Cleanup
rm -f /tmp/test_occupy_*.log

log_info "Test completed! Check the memory utilization percentages - they should be around 90%."