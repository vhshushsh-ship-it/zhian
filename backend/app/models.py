from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
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


class Word(Base):
    """词库单词：公共数据，所有用户共享。一个词可有多条释义与例句。"""

    __tablename__ = "words"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    # 词条（词库全局去重）
    word: Mapped[str] = mapped_column(
        String(100), unique=True, index=True, nullable=False
    )
    # 音标
    phonetic: Mapped[str | None] = mapped_column(String(100), nullable=True)
    # 发音音频 URL（MVP 可空，后续接 TTS / OSS）
    audio_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    # 标签，如 "考研,CET4,CET6"
    tags: Mapped[str | None] = mapped_column(String(200), nullable=True)
    # 难度等级
    difficulty: Mapped[int] = mapped_column(
        Integer, server_default="1", nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    # 释义 / 例句：删除单词时级联删除
    definitions: Mapped[list["WordDefinition"]] = relationship(
        back_populates="word",
        cascade="all, delete-orphan",
        order_by="WordDefinition.order_index",
    )
    examples: Mapped[list["WordExample"]] = relationship(
        back_populates="word",
        cascade="all, delete-orphan",
        order_by="WordExample.order_index",
    )


class WordDefinition(Base):
    """单词释义：一词多义，按 order_index 排序展示。"""

    __tablename__ = "word_definitions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    word_id: Mapped[int] = mapped_column(
        ForeignKey("words.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # 词性，如 n. / v. / adj.
    pos: Mapped[str | None] = mapped_column(String(20), nullable=True)
    # 中文释义
    meaning: Mapped[str] = mapped_column(String(200), nullable=False)
    # 展示顺序
    order_index: Mapped[int] = mapped_column(
        Integer, server_default="0", nullable=False
    )

    word: Mapped["Word"] = relationship(back_populates="definitions")


class WordExample(Base):
    """单词例句：英文例句 + 中文翻译，按 order_index 排序展示。"""

    __tablename__ = "word_examples"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    word_id: Mapped[int] = mapped_column(
        ForeignKey("words.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # 英文例句
    en: Mapped[str] = mapped_column(Text, nullable=False)
    # 中文翻译
    zh: Mapped[str | None] = mapped_column(String(500), nullable=True)
    # 展示顺序
    order_index: Mapped[int] = mapped_column(
        Integer, server_default="0", nullable=False
    )

    word: Mapped["Word"] = relationship(back_populates="examples")


class UserWordProgress(Base):
    """用户单词学习进度：按用户隔离，记录记忆强度、复习次数等。"""

    __tablename__ = "user_word_progress"
    __table_args__ = (
        UniqueConstraint("user_id", "word_id", name="uq_user_word_progress_user_word"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"), nullable=False, index=True
    )
    word_id: Mapped[int] = mapped_column(
        ForeignKey("words.id"), nullable=False, index=True
    )
    # 记忆强度 S：存上次复习后的值（非衰减值）
    memory_strength: Mapped[float] = mapped_column(
        Float, server_default="0", nullable=False
    )
    # 上次复习时间
    last_review_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    # 下次复习日期：查今日复习队列走此索引
    next_review_date: Mapped[date | None] = mapped_column(
        Date, nullable=True, index=True
    )
    # 总复习次数
    review_count: Mapped[int] = mapped_column(
        Integer, server_default="0", nullable=False
    )
    # "认识"次数
    known_count: Mapped[int] = mapped_column(
        Integer, server_default="0", nullable=False
    )
    # "模糊"次数
    vague_count: Mapped[int] = mapped_column(
        Integer, server_default="0", nullable=False
    )
    # "忘记"次数
    forgotten_count: Mapped[int] = mapped_column(
        Integer, server_default="0", nullable=False
    )
    # 是否标记熟知
    is_mastered: Mapped[bool] = mapped_column(
        Boolean, server_default="0", nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )


class UserWordSettings(Base):
    """用户背单词设置：当前词书 + 每日新词上限，按用户唯一。"""

    __tablename__ = "user_word_settings"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), unique=True, index=True, nullable=False
    )
    # 当前学习词书 key：kaoyan / cet4 / cet6
    current_book: Mapped[str] = mapped_column(
        String(20), server_default="kaoyan", nullable=False
    )
    # 每日新词上限（复习词超 30 时递减）
    daily_new_goal: Mapped[int] = mapped_column(
        Integer, server_default="20", nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )


class UserDailyStats(Base):
    """用户每日学习统计：按 (user_id, stat_date) 唯一，记录当天各类学习量。"""

    __tablename__ = "user_daily_stats"
    __table_args__ = (
        UniqueConstraint("user_id", "stat_date", name="uq_user_daily_stats_user_date"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # 统计日期
    stat_date: Mapped[date] = mapped_column(Date, nullable=False)
    # 当天复习的旧词数
    words_reviewed: Mapped[int] = mapped_column(
        Integer, server_default="0", nullable=False
    )
    # 当天学的新词数
    words_new: Mapped[int] = mapped_column(
        Integer, server_default="0", nullable=False
    )
    # 当天口语用户消息数
    speaking_messages: Mapped[int] = mapped_column(
        Integer, server_default="0", nullable=False
    )
    # 预留：当天阅读时长（分钟）
    reading_minutes: Mapped[int] = mapped_column(
        Integer, server_default="0", nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )


class AiTutorConversation(Base):
    """AI 一对一导师「小岸」：对话会话。"""

    __tablename__ = "ai_tutor_conversations"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(100), default="新对话", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    # 关联消息：删除对话时级联删除其所有消息
    messages: Mapped[list["AiTutorMessage"]] = relationship(
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="AiTutorMessage.id",
    )


class AiTutorMessage(Base):
    """AI 一对一导师：对话消息（user / assistant）。"""

    __tablename__ = "ai_tutor_messages"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    conversation_id: Mapped[int] = mapped_column(
        ForeignKey("ai_tutor_conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    conversation: Mapped["AiTutorConversation"] = relationship(
        back_populates="messages"
    )


class UserAiProfile(Base):
    """用户 AI 导师长期画像：每个用户一条（学习目标/考试日期/薄弱项等）。"""

    __tablename__ = "user_ai_profile"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), unique=True, index=True, nullable=False
    )
    # 学习目标，如「考研英语 70 分」
    goal: Mapped[str | None] = mapped_column(String(200), nullable=True)
    # 考试日期
    exam_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    # 薄弱项列表（JSON 字符串）
    weak_points: Mapped[str | None] = mapped_column(Text, nullable=True)
    # 学习风格
    learning_style: Mapped[str | None] = mapped_column(String(200), nullable=True)
    # 偏好（JSON 字符串）
    preferences: Mapped[str | None] = mapped_column(Text, nullable=True)
    # AI 的观察记录（MVP 阶段用户不可编辑）
    ai_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )
