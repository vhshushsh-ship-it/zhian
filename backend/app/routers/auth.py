import random
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user
from ..models import User, VerificationCode
from ..schemas import (
    LoginRequest,
    LoginResponse,
    RegisterRequest,
    SendCodeRequest,
    UserResponse,
)
from ..security import create_access_token, hash_password, verify_password
from ..utils.email import send_email

router = APIRouter(prefix="/auth", tags=["auth"])

# 验证码有效期（分钟）与发送冷却时间（秒）
CODE_EXPIRE_MINUTES = 5
SEND_COOLDOWN_SECONDS = 60


@router.post("/send-code")
def send_code(payload: SendCodeRequest, db: Session = Depends(get_db)):
    """发送邮箱验证码：同一邮箱 60 秒内不能重复发送。"""
    email = payload.email.lower()
    now = datetime.now()

    # 60 秒冷却：查最近一条未过期验证码的创建时间
    latest = (
        db.query(VerificationCode)
        .filter(VerificationCode.email == email, VerificationCode.expires_at > now)
        .order_by(VerificationCode.id.desc())
        .first()
    )
    if latest and latest.created_at and (now - latest.created_at).total_seconds() < SEND_COOLDOWN_SECONDS:
        raise HTTPException(status_code=429, detail="发送过于频繁，请稍后再试")

    code = str(random.randint(100000, 999999))
    record = VerificationCode(
        email=email,
        code=code,
        expires_at=now + timedelta(minutes=CODE_EXPIRE_MINUTES),
    )
    db.add(record)
    db.commit()

    try:
        send_email(
            email,
            "「知岸」注册验证码",
            f"您的注册验证码是：{code}，5分钟内有效。如非本人操作请忽略。",
        )
    except Exception:
        raise HTTPException(status_code=500, detail="验证码邮件发送失败，请稍后重试")

    return {"message": "验证码已发送"}


@router.post("/register", response_model=LoginResponse, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    """邮箱验证码注册：校验通过后创建普通用户并直接返回 Token（自动登录）。"""
    if payload.password != payload.confirm_password:
        raise HTTPException(status_code=400, detail="两次输入的密码不一致")
    if len(payload.password) < 6:
        raise HTTPException(status_code=400, detail="密码长度至少 6 位")

    email = payload.email.lower()
    if db.query(User).filter(User.email == email).first():
        raise HTTPException(status_code=400, detail="该邮箱已注册")

    now = datetime.now()
    code_record = (
        db.query(VerificationCode)
        .filter(VerificationCode.email == email, VerificationCode.is_used.is_(False))
        .order_by(VerificationCode.id.desc())
        .first()
    )
    if not code_record or code_record.code != payload.code or code_record.expires_at <= now:
        raise HTTPException(status_code=400, detail="验证码错误或已过期")

    # 标记验证码已使用，防止重复使用
    code_record.is_used = True

    user = User(
        email=email,
        username=email.split("@")[0],
        hashed_password=hash_password(payload.password),
        role="user",
        status="active",
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    return LoginResponse(access_token=create_access_token(user.id), user=user)


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    """邮箱 + 密码登录：校验封禁状态并返回 Token + 用户信息（含角色）。"""
    email = payload.email.lower()
    user = db.query(User).filter(User.email == email).first()
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="邮箱或密码错误"
        )

    now = datetime.now()
    # 封禁检查：已到期自动解封，否则拒绝登录
    if user.status == "banned":
        if user.banned_until and user.banned_until > now:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"您已被封禁，解封时间：{user.banned_until:%Y-%m-%d}",
            )
        user.status = "active"
        user.banned_until = None

    user.last_active_at = now
    db.commit()
    db.refresh(user)

    return LoginResponse(access_token=create_access_token(user.id), user=user)


@router.get("/me", response_model=UserResponse)
def me(current_user: User = Depends(get_current_user)):
    return current_user
