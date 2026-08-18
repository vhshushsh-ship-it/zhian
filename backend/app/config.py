from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# 项目根目录：backend/app/config.py -> 上溯两级到项目根
BASE_DIR = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # 数据库
    database_url: str = "mysql+pymysql://root:password@localhost:3306/login_demo?charset=utf8mb4"

    # 认证
    secret_key: str = "change-me-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60

    # CORS（逗号分隔的允许来源）
    backend_cors_origins: str = "http://localhost:5173"

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.backend_cors_origins.split(",") if o.strip()]


settings = Settings()
