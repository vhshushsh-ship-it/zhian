"""AI 一对一导师「小岸」：场景感知 + 短期记忆 + 长期画像 + 数据驱动的 AI 对话。

- 场景感知：前端传入当前页面（背单词/口语/阅读/英语主页），注入系统提示词；
- 短期记忆：每次请求携带该对话最近 20 条消息；
- 长期画像：读 user_ai_profile（学习目标/考试日期/薄弱项等），每次都能看到；
- 数据驱动：调用 build_user_snapshot 拼入实时学习数据快照。
"""

import json
from datetime import datetime

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..config import settings
from ..database import get_db
from ..deps import get_current_user
from ..models import AiTutorConversation, AiTutorMessage, User, UserAiProfile
from ..schemas import (
    AiProfileResponse,
    AiTutorConversationDetail,
    AiTutorConversationSummary,
    AiTutorSendRequest,
    AiTutorSendResponse,
    ConversationIdResponse,
    UpdateAiProfileRequest,
)
from ..ai_tutor_service import build_user_snapshot

router = APIRouter(prefix="/ai-tutor", tags=["ai-tutor"])

# 调用超时（秒）
REQUEST_TIMEOUT = 60.0

# 短期记忆：每次只带最近 N 条历史消息
RECENT_MESSAGE_LIMIT = 20

# 页面标识 → 中文名（场景感知）
PAGE_NAMES = {
    "words": "背单词",
    "speaking": "口语练习",
    "reading": "外刊精读",
    "english": "英语主页",
}


def _call_deepseek_text(messages: list[dict]) -> str:
    """调用 DeepSeek Chat Completions，返回纯文本回复（导师对话非 JSON）。"""
    if not settings.deepseek_api_key:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="AI 服务暂时不可用",
        )

    url = f"{settings.deepseek_base_url.rstrip('/')}/chat/completions"
    headers = {
        "Authorization": f"Bearer {settings.deepseek_api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": settings.deepseek_model,
        "messages": messages,
        "temperature": 0.7,
    }

    try:
        resp = httpx.post(url, json=payload, headers=headers, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
        return (data["choices"][0]["message"]["content"] or "").strip()
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="AI 服务暂时不可用",
        )


def _get_profile(db: Session, user_id: int) -> UserAiProfile:
    """取用户 AI 画像，无记录时自动创建默认空画像。"""
    profile = (
        db.query(UserAiProfile).filter(UserAiProfile.user_id == user_id).first()
    )
    if profile is None:
        profile = UserAiProfile(user_id=user_id)
        db.add(profile)
        db.commit()
        db.refresh(profile)
    return profile


def _parse_list(raw: str | None) -> list:
    """解析 JSON 字符串为列表，失败返回空列表。"""
    try:
        data = json.loads(raw) if raw else []
        return data if isinstance(data, list) else []
    except (json.JSONDecodeError, TypeError):
        return []


def _parse_dict(raw: str | None) -> dict:
    """解析 JSON 字符串为字典，失败返回空字典。"""
    try:
        data = json.loads(raw) if raw else {}
        return data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, TypeError):
        return {}


def _profile_to_response(profile: UserAiProfile) -> AiProfileResponse:
    """模型 → 响应体（JSON 字段反序列化为结构化字段）。"""
    return AiProfileResponse(
        goal=profile.goal,
        exam_date=profile.exam_date,
        weak_points=_parse_list(profile.weak_points),
        learning_style=profile.learning_style,
        preferences=_parse_dict(profile.preferences),
        ai_notes=profile.ai_notes,
    )


def build_system_prompt(
    db: Session, user: User, profile: UserAiProfile, page: str
) -> str:
    """构建导师系统提示词：角色 + 场景 + 长期画像 + 数据快照 + 对话要求。"""
    page_name = PAGE_NAMES.get(page, "英语学习")
    snapshot = build_user_snapshot(db, user.id)

    weak_points = _parse_list(profile.weak_points)
    weak_text = "、".join(weak_points) if weak_points else "未填写"

    return (
        "你是「知岸」英语学习平台的一对一 AI 导师「小岸」，一位亲切、专业、善于鼓励的学习伙伴。\n\n"
        f"用户当前所在页面：{page_name}。\n\n"
        "## 用户长期画像\n"
        f"- 学习目标：{profile.goal or '未设置'}\n"
        f"- 考试日期：{profile.exam_date or '未设置'}\n"
        f"- 薄弱项：{weak_text}\n"
        f"- 学习风格：{profile.learning_style or '未填写'}\n\n"
        "## 用户学习数据快照（实时）\n"
        f"{snapshot}\n\n"
        "## 数据使用建议\n"
        "你可以结合上面的学习数据快照给出针对性建议：\n"
        "1. 口语分数低或语法/用词错误多 → 建议多练对应句型和常见错误。\n"
        "2. 阅读细节题错得多 → 建议带着问题定位细节的阅读方法。\n"
        "3. 某模块（口语/阅读/单词）很久没练 → 主动提醒并给出计划。\n"
        "4. 建议要具体到「今天花10分钟练中级口语话题xxx」这种可执行的颗粒度。\n\n"
        "对话要求：\n"
        "1. 用中文、亲切、简洁地回复，像一位耐心的老师。\n"
        "2. 结合上面的学习数据与当前页面，给出个性化、可执行的建议。\n"
        "3. 若用户目标/考试日期未设置，可主动引导其设定。\n"
        "4. 回答控制在 150 字以内，除非用户要求详细展开。"
    )


def _get_owned_conversation(
    conversation_id: int, user_id: int, db: Session
) -> AiTutorConversation:
    """获取对话并校验归属：不存在返回 404，非本人返回 403。"""
    conv = db.get(AiTutorConversation, conversation_id)
    if conv is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="对话不存在")
    if conv.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="无权访问该对话"
        )
    return conv


def _make_title(content: str) -> str:
    """用第一条用户消息的前 20 字作为标题，超出加省略号。"""
    text = content.strip()
    return text[:20] + ("..." if len(text) > 20 else "")


# ---------- 长期画像 ----------


@router.get("/profile", response_model=AiProfileResponse)
def get_profile(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取用户 AI 导师长期画像（无记录自动创建空画像）。"""
    profile = _get_profile(db, current_user.id)
    return _profile_to_response(profile)


@router.put("/profile", response_model=AiProfileResponse)
def update_profile(
    payload: UpdateAiProfileRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """更新长期画像：仅修改显式传入的字段（传 null 表示清空）。"""
    profile = _get_profile(db, current_user.id)
    data = payload.model_dump(exclude_unset=True)

    if "goal" in data:
        profile.goal = data["goal"]
    if "exam_date" in data:
        profile.exam_date = data["exam_date"]
    if "weak_points" in data:
        profile.weak_points = (
            json.dumps(data["weak_points"], ensure_ascii=False)
            if data["weak_points"] is not None
            else None
        )
    if "learning_style" in data:
        profile.learning_style = data["learning_style"]
    if "preferences" in data:
        profile.preferences = (
            json.dumps(data["preferences"], ensure_ascii=False)
            if data["preferences"] is not None
            else None
        )

    db.commit()
    db.refresh(profile)
    return _profile_to_response(profile)


# ---------- 对话 ----------


@router.get("/conversations", response_model=list[AiTutorConversationSummary])
def list_conversations(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """返回当前用户的所有 AI 导师对话，按创建时间倒序。"""
    return (
        db.query(AiTutorConversation)
        .filter(AiTutorConversation.user_id == current_user.id)
        .order_by(AiTutorConversation.created_at.desc())
        .all()
    )


@router.post(
    "/conversations",
    response_model=ConversationIdResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_conversation(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """新建 AI 导师对话，标题默认为「新对话」。"""
    conv = AiTutorConversation(user_id=current_user.id, title="新对话")
    db.add(conv)
    db.commit()
    db.refresh(conv)
    return ConversationIdResponse(id=conv.id)


@router.get(
    "/conversations/{conversation_id}", response_model=AiTutorConversationDetail
)
def get_conversation(
    conversation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """返回 AI 导师对话详情 + 全部消息（按时间正序）。"""
    return _get_owned_conversation(conversation_id, current_user.id, db)


@router.post(
    "/conversations/{conversation_id}/messages", response_model=AiTutorSendResponse
)
def send_message(
    conversation_id: int,
    payload: AiTutorSendRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """发送消息：带最近 20 条历史 + 画像 + 数据快照，调用 DeepSeek 并保存。"""
    conv = _get_owned_conversation(conversation_id, current_user.id, db)

    # 短期记忆：取该对话最近 N 条消息（时间正序）
    history = [{"role": m.role, "content": m.content} for m in conv.messages]
    recent = history[-RECENT_MESSAGE_LIMIT:] if history else []

    profile = _get_profile(db, current_user.id)

    messages = [
        {
            "role": "system",
            "content": build_system_prompt(db, current_user, profile, payload.page),
        }
    ]
    messages += recent
    messages.append({"role": "user", "content": payload.content})

    reply = _call_deepseek_text(messages)

    is_first = len(history) == 0

    db.add(AiTutorMessage(conversation_id=conv.id, role="user", content=payload.content))
    db.add(AiTutorMessage(conversation_id=conv.id, role="assistant", content=reply))

    # 第一条消息时，用用户消息前 20 字作为标题
    if is_first:
        conv.title = _make_title(payload.content)

    db.commit()

    return AiTutorSendResponse(ai_reply=reply)


@router.delete("/conversations/{conversation_id}")
def delete_conversation(
    conversation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """删除 AI 导师对话及其所有消息（级联删除）。"""
    conv = _get_owned_conversation(conversation_id, current_user.id, db)
    db.delete(conv)
    db.commit()
    return {"message": "删除成功"}
