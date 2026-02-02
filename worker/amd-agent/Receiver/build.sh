#!/bin/bash

# TokenMachine AMD Agent Receiver Build Script
# Builds static Go binary for AMD GPU Agent Receiver

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "================================================"
echo "  Building AMD Agent Receiver"
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

# Build Receiver
echo ""
echo "[1/1] Building receiver..."
cd "$SCRIPT_DIR"

# Build with static linking
go build -ldflags="-linkmode external -extldflags=-static" -o receiver main.go

if [ $? -ne 0 ]; then
    echo "ERROR: Failed to build receiver"
    exit 1
fi

# Verify static linking
echo ""
echo "[Verify] Checking if binary is statically linked..."
if file receiver | grep -q "statically linked"; then
    echo "✓ receiver is statically linked"
else
    echo "⚠ Warning: receiver may not be statically linked"
fi

echo ""
echo "================================================"
echo "  Build Complete!"
echo "================================================"
echo ""
echo "Binary: $SCRIPT_DIR/receiver"
echo ""
echo "Usage:"
echo "  ./receiver --help"
echo "  TM_RECEIVER_PORT=9001 ./receiver"
echo ""
