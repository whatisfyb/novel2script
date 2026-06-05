@echo off
REM ========================================
REM  Novel-to-Script 后端启动脚本
REM  启动 FastAPI 服务 (http://localhost:8000)
REM ========================================

echo 🚀 启动后端...

REM 杀掉占用 8000 端口的旧进程
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8000.*LISTENING"') do (
    echo 发现旧进程 PID: %%a，正在关闭...
    taskkill /f /pid %%a >nul 2>&1
)

REM 启动服务
cd /d "%~dp0pipeline-service"
if exist ".venv\Scripts\python.exe" (
    .venv\Scripts\python.exe -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload
) else (
    echo [warn] .venv not found, falling back to system python
    python -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload
)

pause
