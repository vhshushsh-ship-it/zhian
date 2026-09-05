from datetime import datetime

from fastapi import Depends, HTTPException, Query, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from .database import get_db
from .models import User
from .security import decode_access_token

bearer_scheme = HTTPBearer(auto_error=False)


def _authenticate(token: str | None, db: Session) -> User:
    """根据 token 字符串解析并校验当前用户（封禁检查 + 刷新活跃时间）。"""
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="未登录",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user_id = decode_access_token(token)
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="凭证无效或已过期",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user = db.get(User, int(user_id))
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户不存在",
            headers={"WWW-Authenticate": "Bearer"},
        )

    now = datetime.now()
    # 封禁检查：已到期自动解封，否则拒绝
    if user.status == "banned":
        if user.banned_until and user.banned_until > now:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"您已被封禁，解封时间：{user.banned_until:%Y-%m-%d}",
            )
        user.status = "active"
        user.banned_until = None

    # 每次请求刷新最后活跃时间
    user.last_active_at = now
    db.commit()
    return user


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    """从 Authorization 请求头解析当前用户（常规接口）。"""
    return _authenticate(credentials.credentials if credentials else None, db)


def get_current_user_from_query(
    token: str | None = Query(default=None, alias="token"),
    db: Session = Depends(get_db),
) -> User:
    """从 query 参数 token 解析当前用户（用于 <audio>/<img> 等无法携带请求头的场景）。"""
    return _authenticate(token, db)


def get_current_admin(current_user: User = Depends(get_current_user)) -> User:
    """管理员权限依赖：非管理员返回 403。"""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="需要管理员权限"
        )
    return current_user
