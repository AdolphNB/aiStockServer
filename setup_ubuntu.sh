#!/bin/bash

# AIStock Server Ubuntu Deployment Setup Script
# This script sets up a tmpfs (RAM Disk) for the shared_cache directory

CACHE_DIR="shared_cache"
MOUNT_SIZE="512M"

echo "Setting up AIStock shared cache on RAM disk..."

# 1. Create directory if it doesn't exist
if [ ! -d "$CACHE_DIR" ]; then
    mkdir -p "$CACHE_DIR"
    echo "Created $CACHE_DIR directory."
fi

# 2. Check if already mounted
if mount | grep -q "$CACHE_DIR type tmpfs"; then
    echo "$CACHE_DIR is already mounted as tmpfs."
else
    # 3. Mount tmpfs
    echo "Mounting $CACHE_DIR as tmpfs (size=$MOUNT_SIZE)..."
    sudo mount -t tmpfs -o size=$MOUNT_SIZE tmpfs "$CACHE_DIR"
    
    if [ $? -eq 0 ]; then
        echo "Successfully mounted RAM disk."
        # Optional: Add to /etc/fstab for persistence
        # echo "tmpfs $(pwd)/$CACHE_DIR tmpfs defaults,size=$MOUNT_SIZE 0 0" | sudo tee -a /etc/fstab
    else
        echo "Failed to mount RAM disk. Check permissions (sudo required)."
        exit 1
    fi
fi

# 4. Create subdirectories
mkdir -p "$CACHE_DIR/realtime"
mkdir -p "$CACHE_DIR/market_snap"
mkdir -p "$CACHE_DIR/fund_flow"
mkdir -p "$CACHE_DIR/stock_changes"
mkdir -p "$CACHE_DIR/stock_list"
mkdir -p "$CACHE_DIR/kline_daily"

echo "Directory structure created in RAM disk."
echo "Setup complete. You can now run: python run_server.py"
