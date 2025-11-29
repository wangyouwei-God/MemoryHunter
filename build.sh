#!/bin/bash
# MemoryHunter V1.0 Lite - 镜像构建脚本 (Mac/Linux)
# 首次使用前必须运行此脚本构建Docker镜像

echo "MemoryHunter V1.0 Lite - Docker Image Builder"
echo "================================================"
echo ""

# 检查Docker是否运行
if ! docker info > /dev/null 2>&1; then
    echo "[ERROR] Docker is not running"
    echo "[TIP] Please start Docker Desktop and try again"
    exit 1
fi

echo ""
echo "[BUILD] Building Docker image: memory-hunter:v1.0"
echo "[TIME] This will take 5-10 minutes (downloading base image + dependencies)"
echo ""

# 构建镜像
docker-compose build --no-cache

# 检查构建结果
if [ $? -eq 0 ]; then
    echo ""
    echo "[OK] Build completed successfully!"
    echo ""
    echo "[INFO] Image details:"
    docker images memory-hunter:v1.0
    echo ""
    echo "[INFO] Next steps:"
    echo "   1. Run: ./start.sh"
    echo "   2. Open: http://localhost:8000"
else
    echo ""
    echo "[ERROR] Build failed. Please check the error messages above."
    exit 1
fi
