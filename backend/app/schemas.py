from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class SendCodeRequest(BaseModel):
    """发送验证码请求"""

    email: EmailStr


class RegisterRequest(BaseModel):
    """注册请求（邮箱 + 验证码 + 密码）"""

    email: EmailStr
    code: str = Field(..., min_length=6, max_length=6)
    password: str = Field(..., min_length=6, max_length=72)
    confirm_password: str


class LoginRequest(BaseModel):
    """登录请求（邮箱 + 密码）"""

    email: EmailStr
    password: str


class UserResponse(BaseModel):
    """用户信息响应（含角色）"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    username: str | None = None
    role: str
    created_at: datetime


class LoginResponse(BaseModel):
    """登录/注册响应：Token + 用户信息（含角色）"""

    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class AdminUserResponse(BaseModel):
    """管理员视角的用户信息（含状态、封禁、活跃时间）"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    username: str | None = None
    role: str
    status: str
    banned_until: datetime | None = None
    last_active_at: datetime | None = None
    created_at: datetime


class AdminUserListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    users: list[AdminUserResponse]


class BanUserRequest(BaseModel):
    """封禁请求：days 为封禁天数，0 表示永久封禁"""

    days: int


class AdminStatsResponse(BaseModel):
    total_users: int
    online_users: int
    banned_users: int


# ---------- 英语口语练习 ----------

Topic = Literal["daily", "interview", "travel", "campus"]
Level = Literal["beginner", "intermediate", "advanced"]


class ChatMessage(BaseModel):
    """对话中的一条消息（user / assistant）"""

    role: Literal["user", "assistant"]
    content: str


class SpeakingChatRequest(BaseModel):
    """口语对话请求：历史消息 + 话题 + 难度"""

    messages: list[ChatMessage]
    topic: Topic
    level: Level


class SpeakingSuggestion(BaseModel):
    """推荐回复句子（英文 + 中文）"""

    en: str
    zh: str


class SpeakingChatResponse(BaseModel):
    """口语对话响应：AI 英文回复 + 中文翻译 + 推荐句子"""

    ai_reply: str
    translation: str
    suggestions: list[SpeakingSuggestion]
    # 用户上一条消息的中文翻译（用于中栏「翻译」与左栏对话一一对应）
    user_translation: str = ""


class ConversationSummary(BaseModel):
    """对话列表项（不含消息）"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    topic: Topic
    level: Level
    updated_at: datetime


class Message(BaseModel):
    """对话详情中的一条消息"""

    model_config = ConfigDict(from_attributes=True)

    role: Literal["user", "assistant"]
    content: str
    translation: str = ""
    created_at: datetime


class ConversationDetail(BaseModel):
    """对话详情：基本信息 + 全部消息（按时间正序）"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    topic: Topic
    level: Level
    messages: list[Message]


class CreateConversationRequest(BaseModel):
    """新建对话请求：话题 + 难度"""

    topic: Topic
    level: Level


class ConversationIdResponse(BaseModel):
    """新建对话响应：返回对话 id"""

    id: int


class SendMessageRequest(BaseModel):
    """发送消息请求：用户输入的英文"""

    content: str


class SendMessageResponse(BaseModel):
    """发送消息响应：AI 回复 + 中文翻译 + 推荐句子"""

    ai_reply: str
    translation: str
    user_translation: str = ""
    suggestions: list[SpeakingSuggestion]
