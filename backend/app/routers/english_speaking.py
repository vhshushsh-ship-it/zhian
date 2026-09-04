"""英语口语练习：调用 DeepSeek API 实现 AI 对话。

通过单个 DeepSeek 请求同时获取：
- AI 英文回复（ai_reply）
- AI 回复的中文翻译（translation）
- 用户上一条消息的中文翻译（user_translation）
- 3 句推荐回复（suggestions）

同时提供对话历史的有状态接口：每个用户可创建多段对话，每段对话
持久化保存其消息，支持列表 / 详情 / 发送 / 删除。
"""

import json
from datetime import datetime

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..config import settings
from ..database import get_db
from ..deps import get_current_user
from ..models import SpeakingConversation, SpeakingMessage, User
from ..schemas import (
    ConversationDetail,
    ConversationIdResponse,
    ConversationSummary,
    CreateConversationRequest,
    SendMessageRequest,
    SendMessageResponse,
    SpeakingChatRequest,
    SpeakingChatResponse,
    SpeakingSuggestion,
)

router = APIRouter(prefix="/english/speaking", tags=["english-speaking"])

# 话题中文名与难度中文名映射
TOPIC_NAMES = {
    "daily": "日常对话",
    "interview": "面试",
    "travel": "旅游",
    "campus": "校园",
}

LEVEL_NAMES = {
    "beginner": "初级",
    "intermediate": "中级",
    "advanced": "高级",
}

# 不同难度的表达要求
LEVEL_GUIDE = {
    "beginner": "请使用简单的词汇和短句，表达清晰易懂。",
    "intermediate": "请使用正常难度的词汇和句式。",
    "advanced": "可以使用复杂句式、地道表达和高级词汇。",
}

# 调用超时（秒）
REQUEST_TIMEOUT = 60.0


def build_system_prompt(topic: str, level: str) -> str:
    """构建系统提示词：角色 + 话题 + 难度 + JSON 输出要求。"""
    topic_name = TOPIC_NAMES[topic]
    level_name = LEVEL_NAMES[level]
    level_guide = LEVEL_GUIDE[level]

    return (
        "你是一名英语口语练习伙伴，请全程用纯英文与用户对话。\n\n"
        f"当前话题：{topic_name}。用户水平：{level_name}。{level_guide}\n\n"
        "对话要求：\n"
        "1. 你的每次回复控制在 2-3 句话，内容围绕当前话题展开。\n"
        "2. 回复必须是纯英文，不要夹杂中文。\n"
        "3. 请把「用户最新一条消息」和「你本次的英文回复」都翻译成中文。\n\n"
        "输出格式要求：\n"
        "你必须只输出一个 JSON 对象，不要输出任何多余文字或代码块标记，格式如下：\n"
        '{"ai_reply": "你本次的英文回复", "translation": "你本次回复的中文翻译", '
        '"user_translation": "用户最新一条消息的中文翻译", '
        '"suggestions": [{"en": "推荐用户接下来可以说的英文句子1", "zh": "对应中文1"}, '
        '{"en": "推荐英文句子2", "zh": "对应中文2"}, '
        '{"en": "推荐英文句子3", "zh": "对应中文3"}]}\n'
        "其中 suggestions 必须恰好包含 3 个元素。"
    )


def call_deepseek(messages: list[dict]) -> str:
    """调用 DeepSeek Chat Completions，返回模型输出的原始文本。"""
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
        # 要求模型以 JSON 对象返回（OpenAI 兼容）
        "response_format": {"type": "json_object"},
    }

    try:
        resp = httpx.post(url, json=payload, headers=headers, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="AI 服务暂时不可用",
        )


def parse_response(content: str) -> SpeakingChatResponse:
    """解析模型返回的 JSON 文本，失败时兜底为纯文本回复。"""
    try:
        data = json.loads(content)
        suggestions = [
            SpeakingSuggestion(en=str(s.get("en", "")).strip(), zh=str(s.get("zh", "")).strip())
            for s in (data.get("suggestions") or [])
            if s.get("en")
        ][:3]
        return SpeakingChatResponse(
            ai_reply=str(data.get("ai_reply") or "").strip(),
            translation=str(data.get("translation") or "").strip(),
            suggestions=suggestions,
            user_translation=str(data.get("user_translation") or "").strip(),
        )
    except (json.JSONDecodeError, AttributeError, TypeError, ValueError):
        # 兜底：模型未按 JSON 返回时，把原文当作 AI 回复
        return SpeakingChatResponse(
            ai_reply=content.strip(),
            translation="",
            suggestions=[],
            user_translation="",
        )


def get_owned_conversation(
    conversation_id: int, user_id: int, db: Session
) -> SpeakingConversation:
    """获取对话并校验归属：不存在返回 404，非本人返回 403。"""
    conv = db.get(SpeakingConversation, conversation_id)
    if conv is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="对话不存在")
    if conv.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权访问该对话")
    return conv


def make_title(content: str) -> str:
    """用第一条用户消息的前 20 字作为标题，超出加省略号。"""
    text = content.strip()
    return text[:20] + ("..." if len(text) > 20 else "")


# ---------- 有状态接口（对话历史） ----------


@router.get("/conversations", response_model=list[ConversationSummary])
def list_conversations(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """返回当前用户的所有对话，按更新时间倒序。"""
    convs = (
        db.query(SpeakingConversation)
        .filter(SpeakingConversation.user_id == current_user.id)
        .order_by(SpeakingConversation.updated_at.desc())
        .all()
    )
    return convs


@router.post(
    "/conversations", response_model=ConversationIdResponse, status_code=status.HTTP_201_CREATED
)
def create_conversation(
    payload: CreateConversationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """新建对话，标题默认为「新对话」。"""
    conv = SpeakingConversation(
        user_id=current_user.id,
        title="新对话",
        topic=payload.topic,
        level=payload.level,
    )
    db.add(conv)
    db.commit()
    db.refresh(conv)
    return ConversationIdResponse(id=conv.id)


@router.get("/conversations/{conversation_id}", response_model=ConversationDetail)
def get_conversation(
    conversation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """返回对话详情 + 全部消息（按时间正序）。"""
    conv = get_owned_conversation(conversation_id, current_user.id, db)
    return conv


@router.post(
    "/conversations/{conversation_id}/messages", response_model=SendMessageResponse
)
def send_message(
    conversation_id: int,
    payload: SendMessageRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """发送消息：保存用户消息，调用 DeepSeek，保存 AI 消息，更新标题与时间。"""
    conv = get_owned_conversation(conversation_id, current_user.id, db)

    # 构建历史消息上下文（按时间正序，不含 system 提示）
    history = [{"role": m.role, "content": m.content} for m in conv.messages]

    deepseek_messages = [{"role": "system", "content": build_system_prompt(conv.topic, conv.level)}]
    deepseek_messages += history
    deepseek_messages.append({"role": "user", "content": payload.content})

    content = call_deepseek(deepseek_messages)
    parsed = parse_response(content)

    # 第一条消息时，用用户消息前 20 字作为标题
    is_first = len(history) == 0

    user_msg = SpeakingMessage(
        conversation_id=conv.id,
        role="user",
        content=payload.content,
        translation=parsed.user_translation,
    )
    ai_msg = SpeakingMessage(
        conversation_id=conv.id,
        role="assistant",
        content=parsed.ai_reply,
        translation=parsed.translation,
    )
    db.add(user_msg)
    db.add(ai_msg)

    if is_first:
        conv.title = make_title(payload.content)
    conv.updated_at = datetime.now()

    db.commit()

    return SendMessageResponse(
        ai_reply=parsed.ai_reply,
        translation=parsed.translation,
        user_translation=parsed.user_translation,
        suggestions=parsed.suggestions,
    )


@router.delete("/conversations/{conversation_id}")
def delete_conversation(
    conversation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """删除对话及其所有消息（级联删除）。"""
    conv = get_owned_conversation(conversation_id, current_user.id, db)
    db.delete(conv)
    db.commit()
    return {"message": "删除成功"}


# ---------- 无状态接口（保留，供兼容） ----------


@router.post("/chat", response_model=SpeakingChatResponse)
def chat(
    payload: SpeakingChatRequest,
    current_user: User = Depends(get_current_user),
):
    """无状态口语对话：传入历史消息，返回 AI 英文回复、中文翻译与推荐句子。"""
    messages = [{"role": "system", "content": build_system_prompt(payload.topic, payload.level)}]
    messages += [{"role": m.role, "content": m.content} for m in payload.messages]

    content = call_deepseek(messages)
    return parse_response(content)
