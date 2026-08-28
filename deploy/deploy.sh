#!/usr/bin/env bash
# login-demo 服务器端一键部署脚本
# 用法：在服务器上执行  cd /opt/login-demo && bash deploy/deploy.sh
# 也可通过 GitHub webhook / crontab 自动触发，实现「一次提交即可部署」。
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_DIR="$PROJECT_DIR/backend"
FRONTEND_DIR="$PROJECT_DIR/frontend"

cd "$PROJECT_DIR"
git pull

# 后端：安装依赖并重启服务
cd "$BACKEND_DIR"
source .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
sudo systemctl restart login-demo

# 前端：安装依赖并构建（产物写入 frontend/dist，供 Nginx 托管）
cd "$FRONTEND_DIR"
npm install
npm run build

echo "部署完成"
