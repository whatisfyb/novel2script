@echo off
chcp 65001 >nul
REM ========================================
REM  Novel-to-Script 后端启动脚本 (多服务架构)
REM
REM  启动 4 个 FastAPI 服务:
REM    orchestrator :8000  ← 前端入口 (前台, 可见日志)
REM    input        :8001  ← parse + split (后台)
REM    structure    :8002  ← analyze + segment (后台)
REM    beat         :8003  ← LangGraph Extractor+Critic+Refiner (后台)
REM
REM  前置: Redis 已在 :6379 运行 (不在本脚本管理范围)
REM  退出: Ctrl+C 关闭 orchestrator, 自动清理 8001/8002/8003
REM ========================================

cd /d "%~dp0pipeline-service"

set "UVICORN=.venv\Scripts\uvicorn.exe"
if not exist "%UVICORN%" (
    set "UVICORN=uvicorn"
    echo [warn] .venv\Scripts\uvicorn.exe not found, fallback to PATH uvicorn
)

echo 🚀 启动多服务架构...

REM 关闭 8000-8003 旧进程
for %%P in (8000 8001 8002 8003) do (
    for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":%%P.*LISTENING" 2^>nul') do (
        echo 关闭旧进程 PID: %%a (port %%P)
        taskkill /f /pid %%a >nul 2>&1
    )
)

REM 后台启动 3 个子服务
echo [1/4] input_service:8001
start "n2s-input" /B "%UVICORN%" services.input_service:app --host 127.0.0.1 --port 8001

echo [2/4] structure_service:8002
start "n2s-structure" /B "%UVICORN%" services.structure_service:app --host 127.0.0.1 --port 8002

echo [3/4] beat_service:8003
start "n2s-beat" /B "%UVICORN%" services.beat_service:app --host 127.0.0.1 --port 8003

REM 等待子服务就绪 (ping -n N ~= N-1 秒, 兼容 stdin redirected 场景)
ping -n 8 127.0.0.1 >nul

REM 前台启动 orchestrator (Ctrl+C 退出)
echo [4/4] orchestrator:8000 (前端入口)
echo.
echo ========================================
echo   前端: http://localhost:3000
echo   API : http://localhost:8000/docs
echo ========================================
echo.
"%UVICORN%" services.orchestrator:app --host 127.0.0.1 --port 8000 --reload

REM orchestrator 退出后, 清理 8001/8002/8003
echo.
echo 清理子服务...
for %%P in (8001 8002 8003) do (
    for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":%%P.*LISTENING" 2^>nul') do (
        taskkill /f /pid %%a >nul 2>&1
    )
)
pause
