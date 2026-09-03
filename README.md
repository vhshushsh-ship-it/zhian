# zhian

前后端分离的登录 + 笔记 CRUD 示例项目。前端 React + Vite + TypeScript，后端 FastAPI + Uvicorn，数据库 MySQL，生产环境用 Nginx 反向代理。

## 技术栈

| 层 | 技术 |
| --- | --- |
| 前端 | React 18 + Vite + TypeScript + React Router + Axios |
| 后端 | Python FastAPI + SQLAlchemy 2.0 + PyMySQL |
| 数据库 | MySQL |
| 认证 | JWT（PyJWT）+ bcrypt 密码哈希 |
| 本地代理 | Vite devServer proxy |
| 生产代理 | Nginx |

## 目录结构

```
.
├── .gitignore            # 排除 .env、node_modules、dist 等
├── backend/              # FastAPI 后端
│   ├── .env.example      # 后端环境变量模板（不含真实值）
│   ├── requirements.txt
│   └── app/
│       ├── main.py       # 应用入口
│       ├── config.py     # 读取 backend/.env 配置
│       ├── database.py   # SQLAlchemy 引擎/会话
│       ├── models.py     # ORM 模型（User / Note）
│       ├── schemas.py    # Pydantic 模型
│       ├── security.py   # 密码哈希 / JWT
│       ├── deps.py       # 依赖（当前用户）
│       └── routers/      # 路由（auth / notes）
├── deploy/
│   └── zhian.service  # systemd 服务
├── frontend/             # React 前端
│   ├── .env.example      # 前端环境变量模板（当前无变量）
│   ├── vite.config.ts    # 含 /api 代理
│   └── src/
│       ├── api/client.ts     # Axios 封装（自动带 token）
│       ├── auth/AuthContext.tsx
│       └── pages/            # 登录 / 注册 / 笔记
└── nginx/
    └── nginx.conf        # Nginx 反向代理配置
```

## 环境变量

环境变量按前后端分文件存放，`.env` 均已被 `.gitignore` 排除，请勿提交：

- 后端：复制 `backend/.env.example` 为 `backend/.env` 并填写真实值
- 前端：复制 `frontend/.env.example` 为 `frontend/.env`（当前无需变量）

后端变量如下：

| 变量 | 说明 |
| --- | --- |
| `DATABASE_URL` | MySQL 连接串，含 `?charset=utf8mb4` |
| `SECRET_KEY` | JWT 签名密钥，生产务必改随机长字符串 |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Token 有效期（分钟） |
| `BACKEND_CORS_ORIGINS` | 允许跨域的前端来源，逗号分隔 |

## 本地开发

### 1. 准备数据库

本地启动 MySQL，并创建数据库：

```sql
CREATE DATABASE zhian CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

### 2. 启动后端

```bash
cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate     Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

后端默认监听 `http://localhost:8000`，启动时会自动建表。健康检查：`GET /api/health`。

### 3. 启动前端

```bash
cd frontend
npm install
npm run dev
```

前端默认监听 `http://localhost:5173`，`/api` 请求会通过 Vite 代理转发到 `http://localhost:8000`。

### 4. 使用

打开 `http://localhost:5173`，注册账号后即可登录并增删改查笔记。

## 部署到阿里云

### 首次部署

1. **服务器准备**：安装 Nginx、MySQL、Python 3.10+、Node.js 18+。
2. **克隆代码**：

   ```bash
   git clone <你的仓库地址> /opt/zhian
   ```

3. **配置 `.env`**：复制 `/opt/zhian/backend/.env.example` 为 `/opt/zhian/backend/.env`，填入生产环境真实值（手动完成，不提交）。
4. **后端**：

   ```bash
   cd /opt/zhian/backend
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

   安装 systemd 服务：

   ```bash
   sudo cp /opt/zhian/deploy/zhian.service /etc/systemd/system/
   # 按实际路径修改 User/WorkingDirectory/ExecStart
   sudo systemctl daemon-reload
   sudo systemctl enable --now zhian
   ```

5. **前端构建**：

   ```bash
   cd /opt/zhian/frontend
   npm install
   npm run build   # 产物在 frontend/dist
   ```

   将 `dist` 放到 Nginx 能访问的位置（或直接改 `root` 指向 `/opt/zhian/frontend/dist`）。

6. **Nginx**：

   ```bash
   sudo cp /opt/zhian/nginx/nginx.conf /etc/nginx/conf.d/zhian.conf
   # 修改 server_name 与 root
   sudo nginx -t && sudo systemctl reload nginx
   ```

请求链路：用户 → Nginx（80）→ 后端 uvicorn（127.0.0.1:8000）→ MySQL。

### 后续更新（一次提交完成部署）

项目已内置一键部署脚本 `deploy/deploy.sh`，服务器上执行即可：

```bash
cd /opt/zhian && bash deploy/deploy.sh
```

脚本会依次执行 `git pull` → 后端装依赖并重启服务 → 前端装依赖并重新构建。之后本地每次只需 `git push`，服务器执行一次该脚本即可完成更新，无需改动任何配置文件。如需全自动，可把该脚本挂到 GitHub webhook 或 crontab 定时执行。

## API 概览

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| POST | `/api/auth/register` | 注册 |
| POST | `/api/auth/login` | 登录，返回 JWT |
| GET | `/api/auth/me` | 当前用户信息 |
| GET | `/api/notes` | 笔记列表 |
| POST | `/api/notes` | 新建笔记 |
| GET | `/api/notes/{id}` | 单条笔记 |
| PUT | `/api/notes/{id}` | 更新笔记 |
| DELETE | `/api/notes/{id}` | 删除笔记 |
| GET | `/api/health` | 健康检查 |
