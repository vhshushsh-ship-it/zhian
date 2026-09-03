from datetime import datetime

from sqlalchemy import Boolean, DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    # 昵称：可空，登录身份已改为邮箱
    username: Mapped[str | None] = mapped_column(String(50), nullable=True)
    # 邮箱：唯一、非空，作为登录凭证
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    # 角色：admin / user
    role: Mapped[str] = mapped_column(String(20), server_default="user", nullable=False)
    # 状态：active / banned
    status: Mapped[str] = mapped_column(String(20), server_default="active", nullable=False)
    # 封禁到期时间（未封禁为 NULL）
    banned_until: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    # 最后活跃时间
    last_active_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class VerificationCode(Base):
    """邮箱验证码：发送后 5 分钟有效，使用后标记 is_used 防止重复使用"""

    __tablename__ = "verification_codes"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    code: Mapped[str] = mapped_column(String(6), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    is_used: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
