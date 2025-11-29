@echo off
REM MemoryHunter V1.0 Lite - 镜像构建脚本 (Windows)
REM 首次使用前必须运行此脚本构建Docker镜像

echo MemoryHunter V1.0 Lite - Docker Image Builder
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

echo.
echo [BUILD] Building Docker image: memory-hunter:v1.0
echo [TIME] This will take 5-10 minutes (downloading base image + dependencies)
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
    docker images memory-hunter:v1.0
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
