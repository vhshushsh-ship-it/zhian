@echo off
chcp 936 >nul
title zhian 本地开发环境
setlocal

rem 项目根目录（脚本所在目录，%~dp0 自带尾部反斜杠）
set "ROOT=%~dp0"
set "BACKEND_DIR=%ROOT%backend"
set "FRONTEND_DIR=%ROOT%frontend"
set "TIMEOUT=%SystemRoot%\System32\timeout.exe"

echo ========================================
echo   zhian 一键启动本地开发环境
echo ========================================
echo.

rem ---------- 启动前检查 ----------
if not exist "%BACKEND_DIR%\app\main.py" (
    echo [错误] 找不到后端入口：%BACKEND_DIR%\app\main.py
    echo        请确认后端目录结构是否为 backend\app\main.py
    echo.
    pause
    exit /b 1
)

if not exist "%BACKEND_DIR%\.venv\Scripts\activate.bat" (
    echo [错误] 找不到虚拟环境：%BACKEND_DIR%\.venv\Scripts\activate.bat
    echo        请先在 backend 下创建 venv 并安装依赖：
    echo            python -m venv .venv
    echo            .venv\Scripts\activate
    echo            pip install -r requirements.txt
    echo.
    pause
    exit /b 1
)

if not exist "%FRONTEND_DIR%\package.json" (
    echo [错误] 找不到前端目录：%FRONTEND_DIR%\package.json
    echo.
    pause
    exit /b 1
)

rem ---------- 1) 后端 FastAPI ----------
echo [1/3] 启动后端 FastAPI (端口 8000)...
start "Backend - FastAPI" /d "%BACKEND_DIR%" cmd /k ".venv\Scripts\activate && uvicorn app.main:app --reload --port 8000"

"%TIMEOUT%" /t 3 /nobreak >nul

rem ---------- 2) 前端 Vite ----------
echo [2/3] 启动前端 Vite (端口 5173)...
start "Frontend - Vite" /d "%FRONTEND_DIR%" cmd /k "npm run dev"

rem ---------- 3) 等前端编译完成后打开浏览器 ----------
echo [3/3] 等待前端编译，随后打开浏览器...
"%TIMEOUT%" /t 8 /nobreak >nul
start "" "http://localhost:5173"

echo.
echo ========================================
echo   启动完成！
echo   后端 API:  http://localhost:8000/docs
echo   前端页面:  http://localhost:5173
echo ========================================
echo.
echo 两个服务分别在独立窗口运行，关闭对应窗口即可停止服务
echo.
pause
