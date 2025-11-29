#!/bin/bash
# MemoryHunter V2.0 Pro - 镜像构建脚本 (Mac/Linux)
# 首次使用前必须运行此脚本构建Docker镜像

echo "MemoryHunter V2.0 Pro - Docker Image Builder"
echo "================================================"
echo ""

# 检查Docker是否运行
if ! docker info > /dev/null 2>&1; then
    echo "[ERROR] Docker is not running"
    echo "[TIP] Please start Docker Desktop and try again"
    exit 1
fi

# 检查是否有NVIDIA GPU
echo "[CHECK] Checking GPU availability..."
if command -v nvidia-smi &> /dev/null; then
    nvidia-smi --query-gpu=name,memory.total --format=csv,noheader
    echo "[OK] NVIDIA GPU detected"
else
    echo "[WARNING] nvidia-smi not found"
    echo "[TIP] V2.0 Pro requires NVIDIA GPU for optimal performance"
    echo ""
    read -p "Continue anyway? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

echo ""
echo "[BUILD] Building Docker image: memory-hunter:v2.0-pro"
echo "[TIME] This will take 15-30 minutes (downloading CUDA base + dependencies)"
echo ""

# 构建镜像
docker-compose build --no-cache

# 检查构建结果
if [ $? -eq 0 ]; then
    echo ""
    echo "[OK] Build completed successfully!"
    echo ""
    echo "[INFO] Image details:"
    docker images memory-hunter:v2.0-pro
    echo ""
    echo "[INFO] Next steps:"
    echo "   1. Run: ./start.sh"
    echo "   2. Open: http://localhost:8000"
else
    echo ""
    echo "[ERROR] Build failed. Please check the error messages above."
    exit 1
fi
