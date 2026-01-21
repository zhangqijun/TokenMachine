#!/bin/bash
# Initialize worker storage for TokenMachine
# This script mounts NFS share and configures worker storage

set -e

echo "========================================="
echo "TokenMachine Worker Storage Initialization"
echo "========================================="
echo ""

# Configuration
NFS_SERVER="${NFS_SERVER:-nfsserver}"
NFS_MOUNT_POINT="${NFS_MOUNT_POINT:-/mnt/models}"
SERVER_STORAGE_PATH="${SERVER_STORAGE_PATH:-/var/lib/tokenmachine/models}"

echo "Configuration:"
echo "  NFS_SERVER: $NFS_SERVER"
echo "  NFS_MOUNT_POINT: $NFS_MOUNT_POINT"
echo "  SERVER_STORAGE_PATH: $SERVER_STORAGE_PATH"
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "Error: This script must be run as root"
    exit 1
fi

# 1. Create mount point
echo "[1/4] Creating mount point..."
mkdir -p "$NFS_MOUNT_POINT"
echo "  Created: $NFS_MOUNT_POINT"
echo ""

# 2. Install NFS client
echo "[2/4] Installing NFS client..."
if command -v apt-get &> /dev/null; then
    apt-get update
    apt-get install -y nfs-common
    echo "  NFS client installed"
elif command -v yum &> /dev/null; then
    yum install -y nfs-utils
    echo "  NFS client installed"
else
    echo "  Warning: Unable to install NFS client (package manager not found)"
fi
echo ""

# 3. Mount NFS share
echo "[3/4] Mounting NFS share..."
NFS_EXPORT="$NFS_SERVER:$SERVER_STORAGE_PATH"

# Check if already mounted
if mount | grep -q "$NFS_MOUNT_POINT"; then
    echo "  Already mounted: $NFS_MOUNT_POINT"
else
    mount -t nfs "$NFS_EXPORT" "$NFS_MOUNT_POINT"
    echo "  Mounted: $NFS_EXPORT -> $NFS_MOUNT_POINT"
fi
echo ""

# Verify mount
if [ -d "$NFS_MOUNT_POINT" ]; then
    echo "  Verification: $(ls -ld "$NFS_MOUNT_POINT")"
    echo "  Contents: $(ls "$NFS_MOUNT_POINT" | head -5)"
else
    echo "  Error: Mount point not accessible"
    exit 1
fi
echo ""

# 4. Add to /etc/fstab for auto-mount on boot
echo "[4/4] Configuring auto-mount..."
FSTAB_ENTRY="$NFS_EXPORT $NFS_MOUNT_POINT nfs defaults,_netdev 0 0"

if ! grep -q "$NFS_MOUNT_POINT" /etc/fstab 2>/dev/null; then
    echo "$FSTAB_ENTRY" >> /etc/fstab
    echo "  Added to /etc/fstab:"
    echo "    $FSTAB_ENTRY"
else
    echo "  Already in /etc/fstab"
fi
echo ""

echo "========================================="
echo "Worker initialization complete!"
echo "========================================="
echo ""
echo "Verification:"
echo "  Mount point: $NFS_MOUNT_POINT"
echo "  Mounted: $(mount | grep "$NFS_MOUNT_POINT" | cut -d' ' -f1-3)"
echo ""
echo "Next steps:"
echo "  1. Start worker service"
echo "     python backend/worker/worker.py"
echo ""
echo "  2. Test: List available models"
echo "     WorkerModelLoader(worker_id).sync_model_cache()"
echo ""
