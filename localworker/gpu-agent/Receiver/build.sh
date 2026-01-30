#!/bin/bash

# Go Receiver Build Script (静态编译)

echo "Building TokenMachine Receiver (Static)..."

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
  -o receiver .

echo "Build completed!"
echo "Binary location: $(pwd)/receiver"
echo "Size: $(ls -lh receiver | awk '{print $5}')"

# Verify it's a fully static binary
echo "Binary type: $(file receiver)"
echo ""
echo "=== 静态编译验证 ==="

# Check if binary is statically linked
if file receiver | grep -q "statically linked"; then
    echo "✓ 静态链接检查通过"
else
    echo "✗ 警告：二进制可能不是静态链接"
    exit 1
fi

# Check for dynamic dependencies
if ldd receiver 2>&1 | grep -q "not a dynamic executable"; then
    echo "✓ 无动态依赖检查通过"
else
    echo "✗ 警告：二进制包含动态依赖"
    ldd receiver
    exit 1
fi

# Check for GLIBC dependencies in dynamic section
if readelf -d receiver 2>&1 | grep -q "NEEDED"; then
    echo "✗ 警告：发现动态库依赖"
    readelf -d receiver | grep NEEDED
    exit 1
else
    echo "✓ 无GLIBC动态依赖检查通过"
fi

echo "✓ 所有静态编译检查通过，二进制可在任何Linux系统运行"

# Test the binary
echo -e "\nTesting the binary..."
./receiver --help 2>&1 || echo "Receiver built (may not have --help flag)"

echo -e "\nTo run the receiver:"
echo "  ./receiver"
echo ""
echo "To install remotely:"
echo "  scp -P <port> receiver user@server:/usr/local/bin/"