#!/bin/bash

# Go GPU Exporter Build Script (Static)

echo "Building TokenMachine GPU Exporter (Static)..."

# Build the Go application with static linking
cd "$(dirname "$0")"

# 清理旧的工具链缓存以避免模块冲突
rm -rf ~/go/pkg/mod/golang.org/toolchain 2>/dev/null || true

# 完全静态编译，去除所有GLIBC依赖
# -tags netgo: 强制使用纯Go网络库，避免系统C库依赖
# -ldflags '-w -s': 去除调试信息和符号表，减小体积
# -trimpath: 去除路径信息
CGO_ENABLED=0 GOOS=linux GOARCH=amd64 \
  go build \
  -a \
  -tags netgo \
  -trimpath \
  -ldflags '-w -s -extldflags "-static"' \
  -o gpu_exporter_main .

echo "Build completed!"
echo "Binary location: $(pwd)/gpu_exporter_main"
echo "Size: $(ls -lh gpu_exporter_main | awk '{print $5}')"

# Verify it's a fully static binary
echo "Binary type: $(file gpu_exporter_main)"
echo ""
echo "=== 静态编译验证 ==="

# Check if binary is statically linked
if file gpu_exporter_main | grep -q "statically linked"; then
    echo "✓ 静态链接检查通过"
else
    echo "✗ 警告：二进制可能不是静态链接"
    exit 1
fi

# Check for dynamic dependencies
if ldd gpu_exporter_main 2>&1 | grep -q "not a dynamic executable"; then
    echo "✓ 无动态依赖检查通过"
else
    echo "✗ 警告：二进制包含动态依赖"
    ldd gpu_exporter_main
    exit 1
fi

# Check for GLIBC dependencies in dynamic section
if readelf -d gpu_exporter_main 2>&1 | grep -q "NEEDED"; then
    echo "✗ 警告：发现动态库依赖"
    readelf -d gpu_exporter_main | grep NEEDED
    exit 1
else
    echo "✓ 无GLIBC动态依赖检查通过"
fi

echo "✓ 所有静态编译检查通过，二进制可在任何Linux系统运行"

# Test the binary
echo -e "\nTesting the binary..."
./gpu_exporter_main --version
./gpu_exporter_main --help

echo -e "\nTo run the exporter:"
echo "  ./gpu_exporter_main serve --port 9090"
echo ""
echo "To install remotely:"
echo "  scp -P <port> gpu_exporter_main user@server:/usr/local/bin/"