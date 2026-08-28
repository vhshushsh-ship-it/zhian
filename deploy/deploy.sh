#!/usr/bin/env bash
# login-demo 更新部署脚本（每次代码更新后执行）
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_DIR="$PROJECT_DIR/backend"
FRONTEND_DIR="$PROJECT_DIR/frontend"
SERVICE_NAME="login-demo"

cd "$PROJECT_DIR"

# 检查 .env 是否存在（在 backend 目录下）
if [ ! -f "$BACKEND_DIR/.env" ]; then
    echo "错误：$BACKEND_DIR/.env 不存在，请先 cp .env.example .env 并配置"
    exit 1
fi

echo "=== 1. 拉取最新代码 ==="
git pull

echo "=== 2. 后端：安装依赖 + 数据库迁移 ==="
cd "$BACKEND_DIR"
source .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
deactivate

echo "=== 3. 重启后端服务 ==="
systemctl restart "$SERVICE_NAME"

echo "=== 4. 前端：安装依赖并构建 ==="
cd "$FRONTEND_DIR"
npm install
npm run build

echo "=== 5. 复制构建产物到 Nginx 目录 ==="
rm -rf /var/www/login-demo/dist
cp -r dist /var/www/login-demo/

echo "=== 部署完成 ==="
