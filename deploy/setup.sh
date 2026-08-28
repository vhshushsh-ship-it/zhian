#!/usr/bin/env bash
# login-demo 服务器环境初始化脚本（全新服务器只跑一次）
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_DIR="$PROJECT_DIR/backend"
FRONTEND_DIR="$PROJECT_DIR/frontend"
SERVICE_NAME="login-demo"

echo "=== 1. 更新系统并安装基础工具 ==="
apt update && apt upgrade -y
apt install -y git curl wget build-essential ufw

echo "=== 2. 安装 Python 环境 ==="
apt install -y python3 python3-pip python3-venv

echo "=== 3. 安装 Node.js 20.x ==="
curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
apt install -y nodejs

echo "=== 4. 安装 Nginx ==="
apt install -y nginx
systemctl enable nginx

echo "=== 5. 安装 MySQL ==="
apt install -y mysql-server
systemctl enable mysql
systemctl start mysql

echo "=== 6. 创建数据库和用户 ==="
mysql -u root -e "CREATE DATABASE IF NOT EXISTS zhian CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
mysql -u root -e "CREATE USER IF NOT EXISTS 'zhian'@'localhost' IDENTIFIED BY 'Zxw200403149893@';"
mysql -u root -e "GRANT ALL PRIVILEGES ON zhian.* TO 'zhian'@'localhost';"
mysql -u root -e "FLUSH PRIVILEGES;"

echo "=== 7. 配置防火墙 ==="
ufw allow 22
ufw allow 80
ufw allow 443
ufw --force enable

echo "=== 8. 创建前端静态文件目录 ==="
mkdir -p /var/www/login-demo

echo "=== 9. 创建后端虚拟环境并安装依赖 ==="
cd "$BACKEND_DIR"
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
deactivate

echo "=== 10. 配置 systemd 服务 ==="
cp "$PROJECT_DIR/deploy/$SERVICE_NAME.service" /etc/systemd/system/
systemctl daemon-reload
systemctl enable "$SERVICE_NAME"

echo "=== 11. 配置 Nginx ==="
cp "$PROJECT_DIR/nginx/login-demo.conf" /etc/nginx/conf.d/
rm -f /etc/nginx/sites-enabled/default
nginx -t

echo "=== 12. 前端首次构建 ==="
cd "$FRONTEND_DIR"
npm install
npm run build
rm -rf /var/www/login-demo/dist
cp -r dist /var/www/login-demo/

echo ""
echo "=== 初始化完成！接下来执行：==="
echo "1. 编辑 $BACKEND_DIR/.env，填入生产环境配置"
echo "   cp $BACKEND_DIR/.env.example $BACKEND_DIR/.env"
echo "2. cd $BACKEND_DIR && source .venv/bin/activate && alembic upgrade head"
echo "3. systemctl start $SERVICE_NAME && systemctl start nginx"
echo "4. 浏览器访问 http://8.130.208.205"
