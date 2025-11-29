@echo off
setlocal enabledelayedexpansion
REM MemoryHunter V1.0 Lite - Windows启动脚本
REM 自动检测并挂载Pictures文件夹（支持中英文系统）

echo Starting MemoryHunter V1.0 Lite...
echo.

REM 检查Docker Desktop是否运行
docker info >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Docker Desktop is not running
    echo [TIP] Please start Docker Desktop and try again
    pause
    exit /b 1
)

REM 检查镜像是否已构建
docker images memory-hunter:v1.0 | findstr "v1.0" >nul 2>&1
if errorlevel 1 (
    echo [WARNING] Docker image not found: memory-hunter:v1.0
    echo.
    echo [TIP] Please build the image first:
    echo    build.bat
    echo.
    pause
    exit /b 1
)

echo [OK] Docker image found: memory-hunter:v1.0
echo.

REM 尝试检测Pictures文件夹路径
set "PHOTOS_DIR="

REM 方案1: 英文系统 - Pictures
if exist "%USERPROFILE%\Pictures" (
    set "PHOTOS_PATH=%USERPROFILE%\Pictures"
    echo [INFO] Detected: !PHOTOS_PATH!
    goto :convert_path
)

REM 方案2: 中文系统 - 图片
if exist "%USERPROFILE%\图片" (
    set "PHOTOS_PATH=%USERPROFILE%\图片"
    echo [INFO] Detected: !PHOTOS_PATH!
    goto :convert_path
)

REM 方案3: 其他语言系统 - 尝试读取注册表
for /f "tokens=3*" %%a in ('reg query "HKCU\Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders" /v "My Pictures" 2^>nul') do (
    set "PHOTOS_PATH=%%b"
    if defined PHOTOS_PATH (
        REM 展开环境变量
        call set "PHOTOS_PATH=!PHOTOS_PATH!"
        echo [INFO] Detected from registry: !PHOTOS_PATH!
        goto :convert_path
    )
)

REM 未找到Pictures文件夹
echo [WARNING] Could not auto-detect Pictures folder
echo.
echo [TIP] Please manually set PHOTOS_DIR in docker-compose.yml:
echo    volumes:
echo      - C:/Users/YourName/Pictures:/app/photos:ro
echo.
pause
exit /b 1

:convert_path
REM 转换Windows路径为Docker兼容路径 (反斜杠 -> 正斜杠)
set "PHOTOS_DIR=!PHOTOS_PATH:\=/!"
echo.
echo [OK] Photos directory set: !PHOTOS_DIR!
echo.

REM 启动Docker Compose (环境变量会自动传递)
docker-compose up

pause
