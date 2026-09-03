@echo off
chcp 65001 >nul
title zhian 本地开发环境
echo ========================================
echo   zhian 一键启动本地开发环境
echo ========================================
echo.

echo [1/2] 启动后端 FastAPI (端口 8000)...
start "Backend - FastAPI" cmd /k "cd /d %~dp0backend && .venv\Scripts\activate && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"

timeout /t 2 /nobreak >nul

echo [2/2] 启动前端 Vite (端口 5173)...
start "Frontend - Vite" cmd /k "cd /d %~dp0frontend && npm run dev"

echo.
echo ========================================
echo   启动完成！
echo   后端 API:  http://localhost:8000/docs
echo   前端页面:  http://localhost:5173
echo ========================================
echo.
echo 关闭两个弹窗即可停止服务
pause
