@echo off
chcp 65001
echo ==============================================
echo      MemoryHunter V2.0 - GPU Launcher
echo ==============================================

if not exist "test_photos" (
    echo [INFO] 正在创建 'test_photos' 目录...
    mkdir test_photos
    echo [WARN] 请将您的照片复制到项目目录下的 'test_photos' 文件夹中!
    echo.
    pause
)

if not exist "memory-hunter-data" mkdir memory-hunter-data
if not exist "memory-hunter-models" mkdir memory-hunter-models

echo.
echo [INFO] 正在启动 Docker 服务 (GPU模式)...
docker-compose -f docker-compose.gpu.yml up -d --build

echo.
echo [INFO] 服务已启动! 
echo [INFO] 请访问: http://localhost:8000
echo.
echo [INFO] 正在显示日志 (按 Ctrl+C 退出日志查看)...
docker logs -f memory-hunter-gpu
