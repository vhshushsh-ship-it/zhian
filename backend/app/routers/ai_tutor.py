"""AI 一对一导师「小岸」：场景感知 + 短期记忆 + 长期画像 + 数据驱动的 AI 对话。

- 场景感知：前端传入当前页面（背单词/口语/阅读/英语主页），注入系统提示词；
- 短期记忆：每次请求携带该对话最近 20 条消息；
- 长期画像：读 user_ai_profile（学习目标/考试日期/薄弱项等），每次都能看到；
- 数据驱动：调用 build_user_snapshot 拼入实时学习数据快照。
"""

import json
from datetime import date, datetime, timedelta

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..config import settings
from ..database import get_db
from ..deps import get_current_user
from ..models import (
    AiTutorConversation,
    AiTutorMessage,
    ReadingArticle,
    ReadingHistory,
    SpeakingConversation,
    SpeakingScore,
    User,
    UserAiProfile,
    UserDailyTask,
    UserWordProgress,
    Word,
    WritingSubmission,
    WritingTopic,
)
from ..schemas import (
    AiProfileResponse,
    AiTutorConversationDetail,
    AiTutorConversationSummary,
    AiTutorSendRequest,
    AiTutorSendResponse,
    CheckTaskRequest,
    ConversationIdResponse,
    DailyTaskItem,
    DailyTasksResponse,
    UpdateAiProfileRequest,
    WeekDayTasks,
)
from ..ai_tutor_service import build_user_snapshot
from ..speaking_topics import topic_display
from .english_speaking import call_deepseek

router = APIRouter(prefix="/ai-tutor", tags=["ai-tutor"])

# 调用超时（秒）
REQUEST_TIMEOUT = 60.0

# 短期记忆：每次只带最近 N 条历史消息
RECENT_MESSAGE_LIMIT = 20

# 对话自动压缩：超过该条数触发压缩，压缩后保留最近 N 条
COMPRESS_THRESHOLD = 50
KEEP_MESSAGES = 10

# 压缩时的总结提示词：提炼关键信息存入长期画像
SUMMARIZE_PROMPT = (
    "你是「知岸」英语学习平台的 AI 导师「小岸」。下面是一段已经结束的对话历史，"
    "请总结其中的关键信息：用户的学习目标、薄弱项、学习偏好，以及你给过的建议要点。"
    "用简洁的中文输出一段 150 字以内的摘要，只输出摘要文字，不要任何前缀或标记。"
)

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

    base = (
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
    notes = (profile.ai_notes or "").strip()
    if notes:
        base += f"\n\n## 历史对话摘要（AI 观察，压缩自之前的对话）\n{notes}\n"
    return base


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


def _get_or_create_conversation(db: Session, user_id: int) -> AiTutorConversation:
    """获取用户唯一的 AI 导师对话，不存在则自动创建。"""
    conv = (
        db.query(AiTutorConversation)
        .filter(AiTutorConversation.user_id == user_id)
        .order_by(AiTutorConversation.created_at.asc())
        .first()
    )
    if conv is None:
        conv = AiTutorConversation(user_id=user_id, title="AI 导师小岸")
        db.add(conv)
        db.commit()
        db.refresh(conv)
    return conv


def _summarize_messages(existing: str, history: list[dict]) -> str:
    """调 AI 总结一段对话历史，返回摘要；失败返回空串。"""
    msgs = [{"role": "system", "content": SUMMARIZE_PROMPT}]
    if existing:
        msgs.append(
            {
                "role": "user",
                "content": "之前已记录的历史摘要：\n" + existing + "\n\n"
                "请结合下面这段新的对话，更新并输出合并后的摘要。",
            }
        )
    msgs.extend(history)
    try:
        return _call_deepseek_text(msgs)
    except HTTPException:
        return ""


def _compress_conversation(
    db: Session, user_id: int, conv: AiTutorConversation
) -> None:
    """对话超过阈值时：总结旧消息存入画像，只保留最近 N 条。"""
    messages = conv.messages  # 按 id 正序
    if len(messages) <= COMPRESS_THRESHOLD:
        return
    to_summarize = messages[:-KEEP_MESSAGES]
    history = [{"role": m.role, "content": m.content} for m in to_summarize]

    profile = _get_profile(db, user_id)
    summary = _summarize_messages(profile.ai_notes or "", history)
    if not summary:
        # 总结失败则本次不压缩，保留消息下次再试
        return
    profile.ai_notes = summary
    for m in to_summarize:
        db.delete(m)
    db.commit()


@router.get("/chat", response_model=AiTutorConversationDetail)
def get_chat(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取唯一的 AI 导师对话（不存在则自动创建），含全部消息。"""
    return _get_or_create_conversation(db, current_user.id)


@router.post("/chat", response_model=AiTutorSendResponse)
def send_chat(
    payload: AiTutorSendRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """发送消息：无活跃对话自动创建，存消息后检查条数触发压缩。"""
    conv = _get_or_create_conversation(db, current_user.id)

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

    db.add(AiTutorMessage(conversation_id=conv.id, role="user", content=payload.content))
    db.add(AiTutorMessage(conversation_id=conv.id, role="assistant", content=reply))
    db.commit()

    _compress_conversation(db, current_user.id, conv)

    return AiTutorSendResponse(ai_reply=reply)


@router.post("/clear")
def clear_conversation(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """清空当前用户对话：删除所有对话及其消息，下次发送自动新建。"""
    convs = (
        db.query(AiTutorConversation)
        .filter(AiTutorConversation.user_id == current_user.id)
        .all()
    )
    for conv in convs:
        db.delete(conv)
    db.commit()
    return {"message": "ok"}


# ---------- 学习日历 / 每日任务 ----------

# 周几 → 当天附加任务类型（0=周一 ... 6=周日）
_WEEKDAY_EXTRA = {
    0: "speaking",  # 周一
    1: "reading",   # 周二
    2: "speaking",  # 周三
    3: "reading",   # 周四
    4: "speaking",  # 周五
    5: "writing",   # 周六
    6: "speaking",  # 周日（复习 + 总结）
}

# 语法分低于该值（满分 40）时标注「重点语法」
GRAMMAR_WEAK_THRESHOLD = 28


def _count_due_words(db: Session, user_id: int) -> int:
    """今天到期待复习的单词数。"""
    today = date.today()
    return (
        db.query(UserWordProgress)
        .filter(
            UserWordProgress.user_id == user_id,
            UserWordProgress.next_review_date.isnot(None),
            UserWordProgress.next_review_date <= today,
        )
        .count()
    )


def _speaking_advice(db: Session, user_id: int) -> tuple[str, bool]:
    """推荐口语话题 + 是否语法薄弱（最近评分平均语法分低于阈值）。"""
    scores = (
        db.query(SpeakingScore)
        .filter(SpeakingScore.user_id == user_id)
        .order_by(SpeakingScore.created_at.desc(), SpeakingScore.id.desc())
        .limit(10)
        .all()
    )
    grammar_low = bool(scores) and (
        sum(s.grammar for s in scores) / len(scores) < GRAMMAR_WEAK_THRESHOLD
    )
    conv = (
        db.query(SpeakingConversation)
        .filter(SpeakingConversation.user_id == user_id)
        .order_by(SpeakingConversation.updated_at.desc())
        .first()
    )
    topic = topic_display(conv.topic) if conv else "日常对话"
    return topic, grammar_low


# AI 生成任务标题的系统提示词（结合学习数据快照，产出具体可执行的任务标题）
PLAN_PROMPT = (
    "你是「知岸」英语学习平台的 AI 导师「小岸」，根据用户学习数据，为未来 7 天安排每日学习任务。\n"
    "每天至少安排一个「背单词」任务，再根据到期词数、口语/阅读/写作最近表现与薄弱项，"
    "酌情额外安排 0-3 个模块任务，每天总任务 1-4 个。\n"
    "严格只输出一个 JSON 对象（不要输出任何多余文字或代码块标记），格式如下：\n"
    '{"days": [{"date": "YYYY-MM-DD", "tasks": [{"type": "words", "title": "..."}, '
    '{"type": "speaking", "title": "..."}]}]}\n'
    "要求：\n"
    "1. days 数组必须恰好 7 个，date 按我给的 7 天日期依次排列。\n"
    "2. type 只能是 words / speaking / reading / writing 之一，同一天 type 不重复。\n"
    "3. 每天必须有一个 type=words 的任务。\n"
    "4. 标题具体到词/话题/文章/题目，例如「复习12个到期词（abandon, absorb）」「口语：练日常对话，重点注意时态」「外刊：重做《AI 进课堂》」「写作：写一篇关于环保的作文」。\n"
    "5. 若距上次写作超过 3 天，安排一次写作任务；若结构分偏低，写作任务推荐议论文并带上具体题目。\n"
    "6. 只输出 JSON。"
)


def _due_word_texts(db: Session, user_id: int, limit: int = 3) -> list[str]:
    """到期待复习单词里最该复习的 N 个（按记忆强度升序、忘记次数降序）。"""
    today = date.today()
    rows = (
        db.query(Word.word)
        .join(UserWordProgress, UserWordProgress.word_id == Word.id)
        .filter(
            UserWordProgress.user_id == user_id,
            UserWordProgress.next_review_date.isnot(None),
            UserWordProgress.next_review_date <= today,
        )
        .order_by(
            UserWordProgress.memory_strength.asc(),
            UserWordProgress.forgotten_count.desc(),
        )
        .limit(limit)
        .all()
    )
    return [r[0] for r in rows]


def _reading_recommendation(db: Session, user_id: int) -> str | None:
    """推荐一篇外刊：优先未读的最新文章，否则重做正确率最低的一篇。"""
    read_ids = {
        h.article_id
        for h in db.query(ReadingHistory.article_id)
        .filter(ReadingHistory.user_id == user_id)
        .all()
    }
    articles = db.query(ReadingArticle).order_by(ReadingArticle.created_at.desc()).all()
    for a in articles:
        if a.id not in read_ids:
            return a.title
    worst = (
        db.query(ReadingHistory)
        .filter(
            ReadingHistory.user_id == user_id,
            ReadingHistory.quiz_score.isnot(None),
        )
        .order_by(ReadingHistory.quiz_score.asc())
        .first()
    )
    if worst is not None:
        art = db.get(ReadingArticle, worst.article_id)
        if art is not None:
            return art.title
    return None


def _writing_recommendation(db: Session, user_id: int) -> str | None:
    """推荐一个写作题目：优先还没写过的，否则最新的；无库题目时给兜底题目。"""
    written = {
        s.topic
        for s in db.query(WritingSubmission.topic)
        .filter(WritingSubmission.user_id == user_id)
        .all()
    }
    topics = db.query(WritingTopic).order_by(WritingTopic.created_at.desc()).all()
    for t in topics:
        if t.topic not in written:
            return t.topic
    if topics:
        return topics[0].topic
    return "关于环保的重要性"


def _writing_last_days(db: Session, user_id: int) -> int | None:
    """距上次写作的天数；从未写过返回 None。"""
    last = (
        db.query(WritingSubmission.created_at)
        .filter(WritingSubmission.user_id == user_id)
        .order_by(WritingSubmission.created_at.desc())
        .first()
    )
    if last is None or last[0] is None:
        return None
    return (datetime.now() - last[0]).days


def _writing_structure_low(db: Session, user_id: int) -> bool:
    """最近 3 篇作文的结构分平均是否偏低（满分 30，低于 20 视为偏低）。"""
    subs = (
        db.query(WritingSubmission)
        .filter(
            WritingSubmission.user_id == user_id,
            WritingSubmission.feedback_json.isnot(None),
        )
        .order_by(WritingSubmission.created_at.desc(), WritingSubmission.id.desc())
        .limit(3)
        .all()
    )
    if not subs:
        return False
    structs: list[float] = []
    for s in subs:
        try:
            fb = json.loads(s.feedback_json) if s.feedback_json else {}
        except (json.JSONDecodeError, TypeError):
            fb = {}
        v = fb.get("structure_score")
        if isinstance(v, (int, float)):
            structs.append(float(v))
    if not structs:
        return False
    return sum(structs) / len(structs) < 20


def _speaking_focus(db: Session, user_id: int) -> str:
    """最近口语评分里出现最多的错误类型，作为口语练习重点。"""
    scores = (
        db.query(SpeakingScore)
        .filter(SpeakingScore.user_id == user_id)
        .order_by(SpeakingScore.created_at.desc(), SpeakingScore.id.desc())
        .limit(10)
        .all()
    )
    counts: dict[str, int] = {}
    for s in scores:
        try:
            errors = json.loads(s.errors_json) if s.errors_json else []
        except (json.JSONDecodeError, TypeError):
            errors = []
        for e in errors:
            if isinstance(e, dict) and e.get("type"):
                t = str(e["type"]).strip()
                counts[t] = counts.get(t, 0) + 1
    if counts:
        top = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))[0][0]
        return f"重点注意{top}"
    return ""


def _last_timestamp(db: Session, user_id: int, model, column) -> datetime | None:
    """某模块最近一次时间（按传入列倒序取最新）。"""
    row = (
        db.query(column)
        .filter(model.user_id == user_id)
        .order_by(column.desc())
        .first()
    )
    return row[0] if row else None


def _catchup_flags(db: Session, user_id: int) -> dict[str, bool]:
    """补位开关：某模块很久没练时，把它额外安排到今天/明天。"""
    today = date.today()
    tomorrow = today + timedelta(days=1)
    now = datetime.now()
    extra_today = _WEEKDAY_EXTRA[today.weekday()]
    extra_tomorrow = _WEEKDAY_EXTRA[tomorrow.weekday()]

    last_speaking = _last_timestamp(
        db, user_id, SpeakingConversation, SpeakingConversation.updated_at
    )
    last_reading = _last_timestamp(db, user_id, ReadingHistory, ReadingHistory.read_at)
    last_writing = _last_timestamp(
        db, user_id, WritingSubmission, WritingSubmission.created_at
    )

    return {
        "speaking": extra_today != "speaking"
        and (last_speaking is None or last_speaking < now - timedelta(days=3)),
        "reading": extra_tomorrow != "reading"
        and (last_reading is None or last_reading < now - timedelta(days=7)),
        "writing": extra_tomorrow != "writing"
        and (last_writing is None or last_writing < now - timedelta(days=3)),
    }


def _plan_context(db: Session, user_id: int) -> dict:
    """任务标题所需的模块上下文（AI 与兜底标题共用）。"""
    topic, grammar_low = _speaking_advice(db, user_id)
    return {
        "due_count": _count_due_words(db, user_id),
        "due_words": _due_word_texts(db, user_id, 3),
        "topic": topic,
        "grammar_low": grammar_low,
        "speaking_focus": _speaking_focus(db, user_id),
        "reading_article": _reading_recommendation(db, user_id),
        "writing_topic": _writing_recommendation(db, user_id),
        "writing_last_days": _writing_last_days(db, user_id),
        "writing_structure_low": _writing_structure_low(db, user_id),
    }


# 任务的固定展示顺序（words 为每日锚点，其余按需由 AI 增补）
TYPE_ORDER = ["words", "speaking", "reading", "writing"]

# 每日任务类型（AI 生成与兜底共用这 4 类）
VALID_TASK_TYPES = {"words", "speaking", "reading", "writing"}


def _fallback_title(d: date, task_type: str, ctx: dict) -> str:
    """兜底标题：AI 不可用时，用真实数据拼出具体标题。"""
    if task_type == "words":
        if ctx["due_count"] > 0:
            base = f"复习{ctx['due_count']}个到期单词"
            if ctx["due_words"]:
                base += "（" + "、".join(ctx["due_words"][:2]) + "）"
            return base
        return "学习新单词"
    if task_type == "speaking":
        if d.weekday() == 6:
            return "口语：总结本周所学，练10分钟"
        base = f"口语：练10分钟{ctx['topic']}"
        if ctx["speaking_focus"]:
            base += "，" + ctx["speaking_focus"]
        elif ctx["grammar_low"]:
            base += "，重点语法"
        return base
    if task_type == "reading":
        return (
            f"外刊精读：《{ctx['reading_article']}》"
            if ctx["reading_article"]
            else "外刊精读：读1篇文章"
        )
    if task_type == "writing":
        if ctx["writing_topic"]:
            if ctx.get("writing_structure_low"):
                return f"写作练习：写议论文《{ctx['writing_topic']}》"
            return f"写作练习：{ctx['writing_topic']}"
        return "写作练习：写一篇作文"
    return "学习任务"


def _fallback_plan(
    days: list[date], ctx: dict, catchup: dict[str, bool]
) -> dict[date, list[tuple[str, str]]]:
    """兜底计划：每天背单词 + 一个附加模块（周几决定），很久没练的模块补到今天/明天。"""
    today, tomorrow = days[0], days[1]
    plan: dict[date, list[tuple[str, str]]] = {}
    for d in days:
        tasks = [
            ("words", _fallback_title(d, "words", ctx)),
            (
                _WEEKDAY_EXTRA[d.weekday()],
                _fallback_title(d, _WEEKDAY_EXTRA[d.weekday()], ctx),
            ),
        ]
        if d == today and catchup["speaking"]:
            tasks.append(("speaking", _fallback_title(d, "speaking", ctx)))
        if d == tomorrow:
            if catchup["reading"]:
                tasks.append(("reading", _fallback_title(d, "reading", ctx)))
            if catchup["writing"]:
                tasks.append(("writing", _fallback_title(d, "writing", ctx)))
        # 同一天类型去重，保序
        seen: set[str] = set()
        plan[d] = [t for t in tasks if not (t[0] in seen or seen.add(t[0]))]
    return plan


def _ai_generate_plan(
    db: Session, user_id: int, days: list[date], ctx: dict
) -> dict[date, list[tuple[str, str]]] | None:
    """调 AI 生成未来 7 天计划（每天 1-4 个任务）；失败返回 None（由兜底计划接管）。"""
    if not settings.deepseek_api_key:
        return None
    day_lines = "、".join(d.isoformat() for d in days)
    snapshot = build_user_snapshot(db, user_id)
    user_content = (
        "## 用户学习数据快照\n" + snapshot + "\n\n"
        f"## 到期单词：{ctx['due_count']} 个，最需复习："
        f"{'、'.join(ctx['due_words']) if ctx['due_words'] else '暂无'}\n"
        f"## 口语推荐：话题 {ctx['topic']}；{ctx['speaking_focus'] or '暂无重点'}\n"
        f"## 阅读推荐文章：{ctx['reading_article'] or '暂无'}\n"
        f"## 写作推荐题目：{ctx['writing_topic'] or '暂无'}；"
        f"距上次写作 {ctx['writing_last_days'] if ctx['writing_last_days'] is not None else '从未'} 天"
        f"{'，结构分偏低建议练议论文' if ctx['writing_structure_low'] else ''}\n\n"
        f"## 需要安排的 7 天日期（顺序对应 days 数组）：{day_lines}"
    )
    try:
        raw = call_deepseek(
            [
                {"role": "system", "content": PLAN_PROMPT},
                {"role": "user", "content": user_content},
            ]
        )
        data = json.loads(raw)
        days_data = data.get("days")
        if not isinstance(days_data, list) or len(days_data) != len(days):
            return None
        plan: dict[date, list[tuple[str, str]]] = {}
        for d, day_data in zip(days, days_data):
            tasks_raw = day_data.get("tasks") if isinstance(day_data, dict) else None
            if not isinstance(tasks_raw, list):
                return None
            tasks: list[tuple[str, str]] = []
            seen: set[str] = set()
            for item in tasks_raw:
                if not isinstance(item, dict):
                    continue
                t = str(item.get("type", "")).strip()
                title = str(item.get("title", "")).strip()
                if t in VALID_TASK_TYPES and title and t not in seen:
                    seen.add(t)
                    tasks.append((t, title[:200]))
            if not tasks:
                return None
            plan[d] = tasks
        return plan
    except Exception:
        return None


def _persist_plan(
    db: Session, user_id: int, plan: dict[date, list[tuple[str, str]]]
) -> None:
    """把计划写入 user_daily_tasks（已有行仅更新标题、保留完成状态）。"""
    for d, tasks in plan.items():
        for t, title in tasks:
            row = (
                db.query(UserDailyTask)
                .filter(
                    UserDailyTask.user_id == user_id,
                    UserDailyTask.date == d,
                    UserDailyTask.task_type == t,
                )
                .first()
            )
            if row is None:
                db.add(
                    UserDailyTask(
                        user_id=user_id, date=d, task_type=t, task_title=title, done=False
                    )
                )
            else:
                row.task_title = title
    db.commit()


def _resolve_plan(
    db: Session,
    user_id: int,
    days: list[date],
    ctx: dict,
    catchup: dict[str, bool],
) -> dict[date, list[tuple[str, str]]]:
    """计划来源：库 > AI 生成（首次/全空时）> 兜底，按固定类型顺序组装。"""
    rows = (
        db.query(UserDailyTask)
        .filter(
            UserDailyTask.user_id == user_id,
            UserDailyTask.date >= days[0],
            UserDailyTask.date <= days[-1],
        )
        .all()
    )
    by_key: dict[tuple[date, str], str] = {}
    for r in rows:
        if r.task_title:
            by_key[(r.date, r.task_type)] = r.task_title

    if not by_key:
        plan = _ai_generate_plan(db, user_id, days, ctx) or _fallback_plan(
            days, ctx, catchup
        )
        _persist_plan(db, user_id, plan)
        by_key = {(d, t): title for d, tasks in plan.items() for t, title in tasks}

    result: dict[date, list[tuple[str, str]]] = {}
    for d in days:
        tasks: list[tuple[str, str]] = []
        for t in TYPE_ORDER:
            if (d, t) in by_key:
                tasks.append((t, by_key[(d, t)]))
        result[d] = tasks
    return result


def _build_daily_tasks(db: Session, user_id: int) -> DailyTasksResponse:
    """生成今日任务 + 未来 7 天计划，任务数量与内容由 AI 决定，完成状态从 user_daily_tasks 读取。"""
    today = date.today()
    days = [today + timedelta(days=i) for i in range(7)]
    ctx = _plan_context(db, user_id)
    catchup = _catchup_flags(db, user_id)
    plan = _resolve_plan(db, user_id, days, ctx, catchup)

    done_map = {
        (r.date, r.task_type): r.done
        for r in db.query(UserDailyTask)
        .filter(
            UserDailyTask.user_id == user_id,
            UserDailyTask.date >= days[0],
            UserDailyTask.date <= days[-1],
        )
        .all()
    }

    def _item(d: date, t: str, title: str) -> DailyTaskItem:
        return DailyTaskItem(type=t, title=title, done=done_map.get((d, t), False))

    week = [
        WeekDayTasks(
            date=d, tasks=[_item(d, t, title) for t, title in plan.get(d, [])]
        )
        for d in days
    ]
    today_items = [_item(today, t, title) for t, title in plan.get(today, [])]

    return DailyTasksResponse(today=today_items, week=week)


@router.get("/daily-tasks", response_model=DailyTasksResponse)
def get_daily_tasks(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """返回未来 7 天的学习任务（今日任务 + 本周计划）。"""
    return _build_daily_tasks(db, current_user.id)


@router.post("/refresh-plan", response_model=DailyTasksResponse)
def refresh_plan(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """AI 重新生成未来 7 天任务：调 AI 生成计划并落库，返回最新计划。"""
    today = date.today()
    days = [today + timedelta(days=i) for i in range(7)]
    ctx = _plan_context(db, current_user.id)
    ai = _ai_generate_plan(db, current_user.id, days, ctx)
    if ai:
        _persist_plan(db, current_user.id, ai)
    return _build_daily_tasks(db, current_user.id)


@router.post("/daily-tasks/check")
def check_daily_task(
    payload: CheckTaskRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """标记任务完成 / 取消完成。"""
    row = (
        db.query(UserDailyTask)
        .filter(
            UserDailyTask.user_id == current_user.id,
            UserDailyTask.date == payload.date,
            UserDailyTask.task_type == payload.task_type,
        )
        .first()
    )
    if row is None:
        row = UserDailyTask(
            user_id=current_user.id,
            date=payload.date,
            task_type=payload.task_type,
            task_title="",
            done=payload.done,
        )
        db.add(row)
    else:
        row.done = payload.done
    db.commit()
    return {"message": "ok"}
