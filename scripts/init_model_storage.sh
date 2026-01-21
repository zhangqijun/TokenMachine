#!/bin/bash
# Initialize model storage for TokenMachine
# This script sets up directories, permissions, and installs dependencies

set -e

echo "========================================="
echo "TokenMachine Model Storage Initialization"
echo "========================================="
echo ""

# Configuration
MODEL_STORAGE_PATH="${MODEL_STORAGE_PATH:-/var/lib/tokenmachine/models}"
MODELSCOPE_CACHE_DIR="${MODELSCOPE_CACHE_DIR:-/var/lib/tokenmachine/cache/modelscope}"
LOG_PATH="${LOG_PATH:-/var/lib/tokenmachine/logs}"
ENABLE_NFS_SERVER="${ENABLE_NFS_SERVER:-false}"

echo "Configuration:"
echo "  MODEL_STORAGE_PATH: $MODEL_STORAGE_PATH"
echo "  MODELSCOPE_CACHE_DIR: $MODELSCOPE_CACHE_DIR"
echo "  LOG_PATH: $LOG_PATH"
echo "  ENABLE_NFS_SERVER: $ENABLE_NFS_SERVER"
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "Error: This script must be run as root"
    exit 1
fi

# 1. Create directories
echo "[1/5] Creating directories..."
mkdir -p "$MODEL_STORAGE_PATH"
mkdir -p "$MODELSCOPE_CACHE_DIR"
mkdir -p "$LOG_PATH/downloads"

echo "  Created: $MODEL_STORAGE_PATH"
echo "  Created: $MODELSCOPE_CACHE_DIR"
echo "  Created: $LOG_PATH/downloads"
echo ""

# 2. Set permissions
echo "[2/5] Setting permissions..."
chmod 755 "$MODEL_STORAGE_PATH"
chmod 755 "$(dirname "$MODELSCOPE_CACHE_DIR")"
chmod 755 "$LOG_PATH"

# Check if tokenmachine user exists
if id "tokenmachine" &>/dev/null; then
    echo "  Changing ownership to tokenmachine:tokenmachine"
    chown -R tokenmachine:tokenmachine /var/lib/tokenmachine
else
    echo "  Warning: tokenmachine user not found, skipping ownership change"
fi

echo "  Permissions set"
echo ""

# 3. Install ModelScope SDK
echo "[3/5] Installing ModelScope SDK..."
if command -v pip3 &> /dev/null; then
    pip3 install modelscope
    echo "  ModelScope SDK installed"
elif command -v pip &> /dev/null; then
    pip install modelscope
    echo "  ModelScope SDK installed"
else
    echo "  Warning: pip not found, skipping ModelScope installation"
    echo "  Please install ModelScope manually: pip install modelscope"
fi
echo ""

# 4. Configure NFS Server (optional)
if [ "$ENABLE_NFS_SERVER" = "true" ]; then
    echo "[4/5] Configuring NFS server..."

    # Install NFS server
    if command -v apt-get &> /dev/null; then
        apt-get update
        apt-get install -y nfs-kernel-server
    elif command -v yum &> /dev/null; then
        yum install -y nfs-utils
    else
        echo "  Error: Unable to install NFS server (package manager not found)"
        exit 1
    fi

    # Configure exports
    EXPORT_LINE="$MODEL_STORAGE_PATH *(rw,sync,no_subtree_check,no_root_squash)"

    if ! grep -q "$MODEL_STORAGE_PATH" /etc/exports 2>/dev/null; then
        echo "$EXPORT_LINE" >> /etc/exports
        echo "  Added NFS export: $MODEL_STORAGE_PATH"
    else
        echo "  NFS export already configured"
    fi

    # Start and enable NFS service
    if systemctl is-active --quiet nfs-server; then
        exportfs -ra
        echo "  NFS server restarted"
    else
        systemctl enable nfs-server
        systemctl start nfs-server
        echo "  NFS server started"
    fi

    echo "  NFS server configured"
else
    echo "[4/5] Skipping NFS server configuration (ENABLE_NFS_SERVER=false)"
fi
echo ""

# 5. Verify setup
echo "[5/5] Verifying setup..."
echo "  Storage path: $(ls -ld "$MODEL_STORAGE_PATH")"
echo "  Cache path: $(ls -ld "$MODELSCOPE_CACHE_DIR")"
echo "  Log path: $(ls -ld "$LOG_PATH")"

if [ -f "$(which python3)" ]; then
    echo "  Python: $(python3 --version)"
fi

if python3 -c "import modelscope" 2>/dev/null; then
    echo "  ModelScope: $(python3 -c 'import modelscope; print(modelscope.__version__)')"
else
    echo "  ModelScope: Not installed"
fi
echo ""

# 6. Create model registry
echo "Creating model registry..."
REGISTRY_FILE="$MODEL_STORAGE_PATH/.registry.json"
if [ ! -f "$REGISTRY_FILE" ]; then
    echo '{"models":[]}' > "$REGISTRY_FILE"
    echo "  Created: $REGISTRY_FILE"
else
    echo "  Registry already exists: $REGISTRY_FILE"
fi
echo ""

echo "========================================="
echo "Initialization complete!"
echo "========================================="
echo ""
echo "Next steps:"
echo "  1. Workers: Mount NFS share"
echo "     mount -t nfs <server>:$MODEL_STORAGE_PATH /mnt/models"
echo ""
echo "  2. Server: Start API server"
echo "     uvicorn backend.main:app --reload"
echo ""
echo "  3. Test: Download a model"
echo "     POST /api/v1/admin/models/{id}/download"
echo ""
