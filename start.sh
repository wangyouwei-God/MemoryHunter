#!/bin/bash
# MemoryHunter V2.0 Pro - Mac/Linux启动脚本
# 自动挂载 ~/Pictures 目录

echo "Starting MemoryHunter V2.0 Pro..."
echo ""

# 检查Docker是否运行
if ! docker info > /dev/null 2>&1; then
    echo "[ERROR] Docker is not running"
    echo "[TIP] Please start Docker Desktop and try again"
    exit 1
fi

# 检查镜像是否已构建
if ! docker images memory-hunter:v2.0-pro | grep -q "v2.0-pro"; then
    echo "[WARNING] Docker image not found: memory-hunter:v2.0-pro"
    echo ""
    echo "[TIP] Please build the image first:"
    echo "   ./build.sh"
    echo ""
    exit 1
fi

echo "[OK] Docker image found: memory-hunter:v2.0-pro"
echo ""

# 设置照片目录 (可通过参数覆盖)
if [ -n "$1" ]; then
    PHOTOS_DIR="$1"
    echo "[INFO] Using custom directory: $PHOTOS_DIR"
else
    PHOTOS_DIR="$HOME/Pictures"
    echo "[INFO] Using default directory: ~/Pictures"
fi

# 检查目录是否存在
if [ ! -d "$PHOTOS_DIR" ]; then
    echo "[WARNING] Directory not found: $PHOTOS_DIR"
    echo "[INFO] Creating directory..."
    mkdir -p "$PHOTOS_DIR"
fi

# 导出环境变量供docker-compose使用
export PHOTOS_DIR
echo "[OK] Photos directory set: $PHOTOS_DIR"
echo ""

# 启动Docker Compose
docker-compose up
