@echo off
echo Stopping MemoryHunter GPU Service...
docker-compose -f docker-compose.gpu.yml down
echo Stopped.
pause
