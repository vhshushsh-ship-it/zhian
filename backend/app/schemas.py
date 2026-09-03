from datetime import datetime

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
