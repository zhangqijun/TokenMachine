#!/bin/bash

# Test script to verify CUDA compilation functionality

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORK_DIR="/opt/tokenmachine"

log_info() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [INFO] $*"
}

log_error() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [ERROR] $*" >&2
}

log_info "开始测试 CUDA 编译功能..."

# 1. 检查 CUDA 环境
log_info "检查 CUDA 环境..."
if ! command -v nvcc &> /dev/null; then
    log_warn "nvcc 未在 PATH 中，检查 /usr/local/cuda..."
    if [ -d "/usr/local/cuda" ] && [ -f "/usr/local/cuda/bin/nvcc" ]; then
        export CUDA_PATH="/usr/local/cuda"
        export PATH="$CUDA_PATH/bin:$PATH"
        log_info "找到 CUDA 安装: $CUDA_PATH"
    else
        log_error "nvcc 未找到，请确保 CUDA Toolkit 已安装"
        exit 1
    fi
fi

log_info "CUDA 版本: $(nvcc --version | grep release)"

# 2. 创建工作目录
log_info "创建工作目录..."
mkdir -p "$WORK_DIR"

# 3. 检查 CUDA 源文件
log_info "检查 CUDA 源文件..."
if [ ! -f "$SCRIPT_DIR/occupier/occupy_gpu.cu" ]; then
    log_error "CUDA 源文件不存在: $SCRIPT_DIR/occupier/occupy_gpu.cu"
    exit 1
fi

log_info "找到 CUDA 源文件: $SCRIPT_DIR/occupier/occupy_gpu.cu"

# 4. 编译 occupy_gpu
log_info "编译 occupy_gpu.cu..."
cd "$SCRIPT_DIR"

if ! nvcc -O3 -o occupy_gpu_test occupier/occupy_gpu.cu; then
    log_error "编译失败，尝试使用完整路径..."
    if [ -n "$CUDA_PATH" ] && [ -f "$CUDA_PATH/bin/nvcc" ]; then
        if ! "$CUDA_PATH/bin/nvcc" -O3 -o occupy_gpu_test occupier/occupy_gpu.cu; then
            log_error "编译 occupy_gpu.cu 失败"
            exit 1
        fi
    else
        log_error "编译 occupy_gpu.cu 失败"
        exit 1
    fi
fi

# 5. 优化二进制文件
if command -v strip &> /dev/null; then
    strip occupy_gpu_test
fi

# 6. 设置权限
chmod +x occupy_gpu_test
log_info "编译成功！"

# 7. 验证编译的程序
log_info "验证编译的程序..."
if [ ! -f "occupy_gpu_test" ]; then
    log_error "编译后的文件不存在"
    exit 1
fi

log_info "文件大小: $(du -h occupy_gpu_test | cut -f1)"
log_info "文件权限: $(ls -la occupy_gpu_test | awk '{print $1}')"

# 8. 测试运行（快速测试）
log_info "测试程序运行（2秒超时）..."
timeout 2s ./occupy_gpu_test --gpu 0 --log /tmp/test_compile.log 2>&1 | head -10
if [ ${PIPESTATUS[0]} -eq 0 ] || [ ${PIPESTATUS[0]} -eq 124 ]; then
    log_info "程序测试运行成功（超时是正常的）"
else
    log_error "程序测试运行失败"
    exit 1
fi

# 9. 清理
rm -f occupy_gpu_test
log_info "清理完成"

log_info "✅ CUDA 编译功能测试完成！"
log_info "所有功能正常："
log_info "  ✅ CUDA 环境检测"
log_info "  ✅ 源文件检查"
log_info "  ✅ nvcc 编译"
log_info "  ✅ 程序执行验证"