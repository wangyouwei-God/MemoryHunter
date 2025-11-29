@echo off
REM MemoryHunter V2.0 Pro - 镜像构建脚本 (Windows)
REM 首次使用前必须运行此脚本构建Docker镜像

echo MemoryHunter V2.0 Pro - Docker Image Builder
echo ================================================
echo.

REM 检查Docker Desktop是否运行
docker info >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Docker Desktop is not running
    echo [TIP] Please start Docker Desktop and try again
    pause
    exit /b 1
)

REM 检查是否有NVIDIA GPU
echo [CHECK] Checking GPU availability...
nvidia-smi --query-gpu=name,memory.total --format=csv,noheader 2>nul
if errorlevel 1 (
    echo [WARNING] nvidia-smi not found or no NVIDIA GPU detected
    echo [TIP] V2.0 Pro requires NVIDIA GPU for optimal performance
    echo.
    set /p CONTINUE="Continue anyway? (y/N): "
    if /i not "%CONTINUE%"=="y" (
        exit /b 1
    )
) else (
    echo [OK] NVIDIA GPU detected
)

echo.
echo [BUILD] Building Docker image: memory-hunter:v2.0-pro
echo [TIME] This will take 15-30 minutes (downloading CUDA base + dependencies)
echo.
echo [TIP] You can minimize this window but do not close it
echo.

REM 构建镜像
docker-compose build --no-cache

REM 检查构建结果
if errorlevel 0 (
    echo.
    echo [OK] Build completed successfully!
    echo.
    echo [INFO] Image details:
    docker images memory-hunter:v2.0-pro
    echo.
    echo [INFO] Next steps:
    echo    1. Run: start.bat
    echo    2. Open: http://localhost:8000
    echo.
) else (
    echo.
    echo [ERROR] Build failed. Please check the error messages above.
    echo.
)

pause
