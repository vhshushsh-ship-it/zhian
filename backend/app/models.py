from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

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


class SpeakingConversation(Base):
    """英语口语对话：一个用户可有多段对话，按话题 / 难度区分。"""

    __tablename__ = "speaking_conversations"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(100), default="新对话", nullable=False)
    topic: Mapped[str] = mapped_column(String(20), default="daily", nullable=False)
    level: Mapped[str] = mapped_column(String(20), default="beginner", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # 关联消息：删除对话时级联删除其所有消息
    messages: Mapped[list["SpeakingMessage"]] = relationship(
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="SpeakingMessage.id",
    )


class SpeakingMessage(Base):
    """英语口语消息：属于某段对话的一条消息（user / assistant）。"""

    __tablename__ = "speaking_messages"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    conversation_id: Mapped[int] = mapped_column(
        ForeignKey("speaking_conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    translation: Mapped[str] = mapped_column(Text, default="", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    conversation: Mapped["SpeakingConversation"] = relationship(
        back_populates="messages"
    )
