#!/bin/bash

# TokenMachine AMD Agent Exporter Build Script
# Builds static Go binaries for AMD GPU Exporter

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "================================================"
echo "  Building AMD GPU Exporter"
echo "================================================"
echo ""

# Check for Go
if ! command -v go &> /dev/null; then
    echo "ERROR: Go is not installed"
    exit 1
fi

# Print Go version
echo "Go version: $(go version)"

# Set build environment for static linking
export CGO_ENABLED=0
export GOOS=linux
export GOARCH=amd64

# Build Exporter
echo ""
echo "[1/2] Building amd_exporter_main..."
cd "$SCRIPT_DIR"

# Build with static linking
go build -ldflags="-linkmode external -extldflags=-static" -o amd_exporter_main main.go amd_info.go prometheus.go server.go

if [ $? -ne 0 ]; then
    echo "ERROR: Failed to build amd_exporter_main"
    exit 1
fi

# Verify static linking
echo ""
echo "[Verify] Checking if binary is statically linked..."
if file amd_exporter_main | grep -q "statically linked"; then
    echo "✓ amd_exporter_main is statically linked"
else
    echo "⚠ Warning: amd_exporter_main may not be statically linked"
fi

echo ""
echo "================================================"
echo "  Build Complete!"
echo "================================================"
echo ""
echo "Binary: $SCRIPT_DIR/amd_exporter_main"
echo ""
echo "Usage:"
echo "  ./amd_exporter_main --help"
echo "  ./amd_exporter_main --port 9091 --mock"
echo ""
