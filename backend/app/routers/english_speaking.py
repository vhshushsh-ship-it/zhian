"""英语口语练习：调用 DeepSeek API 实现 AI 对话。

通过单个 DeepSeek 请求同时获取：
- AI 英文回复（ai_reply）
- AI 回复的中文翻译（translation）
- 用户上一条消息的中文翻译（user_translation）
- 3 句推荐回复（suggestions）
"""

import json

import httpx
from fastapi import APIRouter, Depends, HTTPException, status

from ..config import settings
from ..deps import get_current_user
from ..models import User
from ..schemas import SpeakingChatRequest, SpeakingChatResponse, SpeakingSuggestion

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


@router.post("/chat", response_model=SpeakingChatResponse)
def chat(
    payload: SpeakingChatRequest,
    current_user: User = Depends(get_current_user),
):
    """口语对话：返回 AI 英文回复、中文翻译与推荐句子。"""
    system_prompt = build_system_prompt(payload.topic, payload.level)
    messages = [{"role": "system", "content": system_prompt}]
    messages += [
        {"role": m.role, "content": m.content} for m in payload.messages
    ]

    content = call_deepseek(messages)
    return parse_response(content)
