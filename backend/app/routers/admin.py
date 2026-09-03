from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_admin
from ..models import User
from ..schemas import (
    AdminStatsResponse,
    AdminUserListResponse,
    BanUserRequest,
)

router = APIRouter(prefix="/admin", tags=["admin"])

# 在线判定阈值：5 分钟内活跃
ONLINE_THRESHOLD_SECONDS = 300
# 永久封禁的到期时间
PERMANENT_BAN = datetime(2099, 12, 31)


@router.get("/stats", response_model=AdminStatsResponse)
def get_stats(
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """统计：总用户数 / 在线用户数（5 分钟内活跃）/ 封禁用户数。"""
    now = datetime.now()
    online_since = now - timedelta(seconds=ONLINE_THRESHOLD_SECONDS)

    total_users = db.query(func.count(User.id)).scalar() or 0
    online_users = (
        db.query(func.count(User.id))
        .filter(User.last_active_at >= online_since)
        .scalar()
        or 0
    )
    banned_users = (
        db.query(func.count(User.id)).filter(User.status == "banned").scalar() or 0
    )
    return AdminStatsResponse(
        total_users=total_users,
        online_users=online_users,
        banned_users=banned_users,
    )


@router.get("/users", response_model=AdminUserListResponse)
def get_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: str = Query("", description="按邮箱搜索"),
    status_filter: str = Query("all", description="active / banned / all"),
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """分页用户列表，按注册时间倒序，支持邮箱搜索与状态筛选。"""
    query = db.query(User)
    if search:
        query = query.filter(User.email.ilike(f"%{search}%"))
    if status_filter == "active":
        query = query.filter(User.status == "active")
    elif status_filter == "banned":
        query = query.filter(User.status == "banned")

    total = query.count()
    users = (
        query.order_by(User.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return AdminUserListResponse(total=total, page=page, page_size=page_size, users=users)


@router.post("/users/{user_id}/ban")
def ban_user(
    user_id: int,
    payload: BanUserRequest,
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """封禁用户：days 为封禁天数，0 表示永久封禁。"""
    if user_id == current_admin.id:
        raise HTTPException(status_code=400, detail="不能封禁自己")
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="用户不存在")
    if user.role == "admin":
        raise HTTPException(status_code=400, detail="不能封禁管理员")

    user.status = "banned"
    if payload.days <= 0:
        user.banned_until = PERMANENT_BAN
    else:
        user.banned_until = datetime.now() + timedelta(days=payload.days)
    db.commit()
    return {"message": "封禁成功"}


@router.post("/users/{user_id}/unban")
def unban_user(
    user_id: int,
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """解封用户。"""
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="用户不存在")

    user.status = "active"
    user.banned_until = None
    db.commit()
    return {"message": "解封成功"}
