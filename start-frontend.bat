@echo off
REM ========================================
REM  Novel-to-Script 前端启动脚本
REM  启动 Vite 开发服务器 (http://localhost:3000)
REM ========================================

echo 🚀 启动前端...

cd /d "%~dp0frontend"
npm run dev

pause
