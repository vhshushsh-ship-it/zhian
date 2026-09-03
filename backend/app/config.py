from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# 后端目录：backend/app/config.py -> 上溯两级到 backend/
# 后端环境变量文件位于 backend/.env
BACKEND_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(BACKEND_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # 数据库
    database_url: str = "mysql+pymysql://root:password@localhost:3306/zhian?charset=utf8mb4"

    # 认证
    secret_key: str = "change-me-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60

    # CORS（逗号分隔的允许来源）
    backend_cors_origins: str = "http://localhost:5173"

    # SMTP 邮件（QQ 邮箱，发送注册验证码）
    smtp_host: str = "smtp.qq.com"
    smtp_port: int = 465
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = ""

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.backend_cors_origins.split(",") if o.strip()]


settings = Settings()
