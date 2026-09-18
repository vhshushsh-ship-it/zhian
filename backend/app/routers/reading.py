"""外刊精读：管理员 AI 生成文章 + 用户阅读 / 做题 / 收集生词 / 选中即译。

- 文章库（reading_articles）为公共数据，管理员调用 DeepSeek 一次性生成
  文章正文 + 长难句 + 阅读理解题；
- 每个用户对文章的阅读记录（reading_history）私有，记录已读时间 / 做题分数 /
  收集生词数；
- 选中即译（/explain）为实时接口，不落库。
"""

import json
from datetime import datetime

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..config import settings
from ..database import get_db
from ..deps import get_current_admin, get_current_user
from ..models import ReadingArticle, ReadingHistory, User, UserWordProgress, Word
from ..schemas import (
    CollectWordRequest,
    ExplainRequest,
    ExplainResponse,
    GenerateArticleRequest,
    QuizResultItem,
    QuizSubmitRequest,
    QuizSubmitResponse,
    ReadingArticleDetail,
    ReadingArticleListItem,
    ReadingArticleListResponse,
    ReadingHistoryOut,
    ReadingQuizItem,
)
from ..stats_service import update_daily_stats

router = APIRouter(prefix="/reading", tags=["reading"])

# 调用超时（秒）
REQUEST_TIMEOUT = 60.0

# 难度 / 话题允许值（与前端下拉一致）
DIFFICULTIES = {"考研", "四级", "六级"}
TOPICS = {"科技", "经济", "文化", "教育", "社会"}

# ---------- AI 提示词 ----------

# 文章生成：一次 DeepSeek 调用返回文章 + 长难句 + 题目
ARTICLE_PROMPT = (
    "你是一名资深外刊编辑，为「知岸」英语学习平台编写外刊精读文章。\n"
    "请严格只输出一个 JSON 对象（不要输出任何多余文字或代码块标记），字段如下：\n"
    '{"title": "文章标题（英文）", '
    '"content": "文章正文（英文，约 300-400 词，段落用 \\n\\n 分隔）", '
    '"long_sentences": ["长难句1（英文）", "长难句2", "长难句3"], '
    '"quiz": [{"question": "阅读理解题1（中文）", '
    '"options": ["A选项（英文）", "B选项", "C选项", "D选项"], '
    '"answer": 0, "explanation": "解析（中文，说明为何选该项）"}]}\n\n'
    "要求：\n"
    "1. content 为纯英文文章，不要夹杂中文。\n"
    "2. long_sentences 为 3-5 个从正文中挑选或凝练的长难句。\n"
    "3. quiz 恰好 4 题，每题 4 个选项，answer 为正确选项下标（0-3）。\n"
    "4. 严格按用户要求的难度与话题生成。"
)

# 选中即译：翻译 + 解析
EXPLAIN_PROMPT = (
    "你是「知岸」英语学习平台的外刊精读助手，负责把用户选中的英文单词或句子翻译并解析。\n"
    "请严格只输出一个 JSON 对象（不要输出任何多余文字或代码块标记），字段如下：\n"
    '{"translation": "选中内容的中文翻译", '
    '"analysis": "解析说明（中文，讲解词义、语法结构或句子成分）"}'
)


# ---------- 工具函数 ----------


def _call_deepseek_json(messages: list[dict]) -> dict:
    """调用 DeepSeek Chat Completions，返回解析后的 JSON 对象。"""
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
        "response_format": {"type": "json_object"},
    }

    try:
        resp = httpx.post(url, json=payload, headers=headers, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
        content = data["choices"][0]["message"]["content"]
        return json.loads(content)
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="AI 服务暂时不可用",
        )


def _parse_str_list(raw: str | None) -> list[str]:
    """解析 JSON 字符串为字符串列表，失败返回空列表。"""
    try:
        data = json.loads(raw) if raw else []
        if not isinstance(data, list):
            return []
        return [str(x).strip() for x in data if str(x).strip()]
    except (json.JSONDecodeError, TypeError):
        return []


def _parse_quiz(raw: str | None) -> list[dict]:
    """解析题目 JSON 字符串为题目字典列表，过滤非法项。"""
    try:
        data = json.loads(raw) if raw else []
        if not isinstance(data, list):
            return []
        result: list[dict] = []
        for item in data:
            if not isinstance(item, dict):
                continue
            options = item.get("options")
            if not isinstance(options, list) or len(options) != 4:
                continue
            result.append(
                {
                    "question": str(item.get("question") or "").strip(),
                    "options": [str(o).strip() for o in options],
                    "answer": int(item.get("answer") or 0),
                    "explanation": str(item.get("explanation") or "").strip(),
                }
            )
        return result
    except (json.JSONDecodeError, TypeError, ValueError):
        return []


def _get_article(db: Session, article_id: int) -> ReadingArticle:
    """获取文章，不存在返回 404。"""
    article = db.get(ReadingArticle, article_id)
    if article is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="文章不存在"
        )
    return article


def _get_history(
    db: Session, user_id: int, article_id: int
) -> ReadingHistory | None:
    """获取用户对某篇文章的阅读记录，无则返回 None。"""
    return (
        db.query(ReadingHistory)
        .filter(
            ReadingHistory.user_id == user_id,
            ReadingHistory.article_id == article_id,
        )
        .first()
    )


def _get_or_create_history(
    db: Session, user_id: int, article_id: int
) -> ReadingHistory:
    """获取阅读记录，无则新建（不 commit，由调用方统一提交）。"""
    history = _get_history(db, user_id, article_id)
    if history is None:
        history = ReadingHistory(user_id=user_id, article_id=article_id)
        db.add(history)
    return history


def _history_out(history: ReadingHistory | None) -> ReadingHistoryOut | None:
    """阅读记录模型 → 响应体。"""
    if history is None:
        return None
    return ReadingHistoryOut(
        read_at=history.read_at,
        quiz_score=history.quiz_score,
        words_collected=history.words_collected or 0,
    )


def _article_detail(
    db: Session, article: ReadingArticle, user_id: int
) -> ReadingArticleDetail:
    """文章模型 → 详情响应（含长难句 / 题目 / 当前用户阅读记录）。"""
    history = _get_history(db, user_id, article.id)
    return ReadingArticleDetail(
        id=article.id,
        title=article.title,
        content=article.content,
        difficulty=article.difficulty,
        topic=article.topic,
        word_count=article.word_count,
        long_sentences=_parse_str_list(article.long_sentences),
        quiz=[ReadingQuizItem(**q) for q in _parse_quiz(article.quiz)],
        created_at=article.created_at,
        history=_history_out(history),
    )


# ---------- 接口 ----------


@router.post(
    "/generate",
    response_model=ReadingArticleDetail,
    status_code=status.HTTP_201_CREATED,
)
def generate_article(
    payload: GenerateArticleRequest,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
):
    """管理员用 AI 生成一篇外刊精读文章（正文 + 长难句 + 题目）。"""
    difficulty = payload.difficulty.strip()
    topic = payload.topic.strip()
    if difficulty not in DIFFICULTIES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"难度必须是 {'/'.join(sorted(DIFFICULTIES))} 之一",
        )
    if topic not in TOPICS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"话题必须是 {'/'.join(sorted(TOPICS))} 之一",
        )

    messages = [
        {"role": "system", "content": ARTICLE_PROMPT},
        {
            "role": "user",
            "content": f"请生成一篇难度为「{difficulty}」、话题为「{topic}」的外刊精读文章。",
        },
    ]
    data = _call_deepseek_json(messages)

    content = str(data.get("content") or "").strip()
    if not content:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail="AI 生成失败，请重试"
        )

    article = ReadingArticle(
        title=str(data.get("title") or "").strip() or "未命名文章",
        content=content,
        difficulty=difficulty,
        topic=topic,
        word_count=len(content.split()),
        long_sentences=json.dumps(data.get("long_sentences") or [], ensure_ascii=False),
        quiz=json.dumps(data.get("quiz") or [], ensure_ascii=False),
        created_by=current_admin.id,
    )
    db.add(article)
    db.commit()
    db.refresh(article)

    return _article_detail(db, article, current_admin.id)


@router.get("/articles", response_model=ReadingArticleListResponse)
def list_articles(
    difficulty: str | None = None,
    topic: str | None = None,
    page: int = 1,
    size: int = 10,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """文章列表：支持难度 / 话题筛选，分页，含当前用户是否已读。"""
    page = max(page, 1)
    size = min(max(size, 1), 50)

    q = db.query(ReadingArticle)
    if difficulty:
        q = q.filter(ReadingArticle.difficulty == difficulty)
    if topic:
        q = q.filter(ReadingArticle.topic == topic)

    total = q.count()
    articles = (
        q.order_by(ReadingArticle.created_at.desc(), ReadingArticle.id.desc())
        .offset((page - 1) * size)
        .limit(size)
        .all()
    )

    # 一次性取当前用户所有已读文章 id，避免逐条查询
    read_ids = {
        h.article_id
        for h in db.query(ReadingHistory)
        .filter(ReadingHistory.user_id == current_user.id)
        .all()
    }

    items = [
        ReadingArticleListItem(
            id=a.id,
            title=a.title,
            difficulty=a.difficulty,
            topic=a.topic,
            word_count=a.word_count,
            created_at=a.created_at,
            is_read=a.id in read_ids,
        )
        for a in articles
    ]

    return ReadingArticleListResponse(total=total, page=page, size=size, items=items)


@router.get("/articles/{article_id}", response_model=ReadingArticleDetail)
def get_article(
    article_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """文章详情：正文 + 长难句 + 题目 + 当前用户阅读记录。"""
    article = _get_article(db, article_id)
    return _article_detail(db, article, current_user.id)


@router.post("/articles/{article_id}/read", response_model=ReadingHistoryOut)
def mark_read(
    article_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """标记已读：写入 / 更新 read_at（upsert）。"""
    _get_article(db, article_id)

    history = _get_history(db, current_user.id, article_id)
    if history is None:
        history = ReadingHistory(user_id=current_user.id, article_id=article_id)
        db.add(history)
    else:
        history.read_at = datetime.now()

    # MVP：复用 reading_minutes 字段记录一次阅读动作（+1），避免新增迁移字段
    update_daily_stats(db, current_user.id, "reading_minutes")

    db.commit()
    db.refresh(history)
    return _history_out(history)


@router.post("/articles/{article_id}/quiz", response_model=QuizSubmitResponse)
def submit_quiz(
    article_id: int,
    payload: QuizSubmitRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """提交做题：比对答案，写入 quiz_score，返回得分与逐题解析。"""
    article = _get_article(db, article_id)
    quiz = _parse_quiz(article.quiz)
    if not quiz:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="该文章暂无题目"
        )

    total = len(quiz)
    correct = 0
    results: list[QuizResultItem] = []
    for i, q in enumerate(quiz):
        your = payload.answers[i] if i < len(payload.answers) else None
        is_correct = your is not None and your == q["answer"]
        if is_correct:
            correct += 1
        results.append(
            QuizResultItem(
                question=q["question"],
                your_answer=your,
                correct_answer=q["answer"],
                is_correct=is_correct,
                explanation=q["explanation"],
            )
        )

    score = round(correct / total * 100, 1)

    history = _get_or_create_history(db, current_user.id, article_id)
    history.quiz_score = score
    db.commit()

    return QuizSubmitResponse(
        score=score, correct=correct, total=total, results=results
    )


@router.post("/articles/{article_id}/collect-word")
def collect_word(
    article_id: int,
    payload: CollectWordRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """收集生词：词库命中则 upsert 用户单词进度并标记来源文章，否则报错。"""
    _get_article(db, article_id)

    word_text = payload.word.strip()
    if not word_text:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="单词不能为空"
        )

    word = db.query(Word).filter(Word.word == word_text).first()
    if word is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="词库中暂无该词"
        )

    progress = (
        db.query(UserWordProgress)
        .filter(
            UserWordProgress.user_id == current_user.id,
            UserWordProgress.word_id == word.id,
        )
        .first()
    )
    if progress is None:
        progress = UserWordProgress(
            user_id=current_user.id,
            word_id=word.id,
            memory_strength=0.0,
            source_article_id=article_id,
        )
        db.add(progress)
    elif progress.source_article_id is None:
        # 已有进度（正常背单词来的），补记来源文章
        progress.source_article_id = article_id

    history = _get_or_create_history(db, current_user.id, article_id)
    history.words_collected = (history.words_collected or 0) + 1

    # MVP：复用 reading_minutes 字段记录一次阅读动作（+1）
    update_daily_stats(db, current_user.id, "reading_minutes")

    db.commit()

    return {"message": "已加入生词本", "word": word.word}


@router.post("/explain", response_model=ExplainResponse)
def explain(
    payload: ExplainRequest,
    current_user: User = Depends(get_current_user),
):
    """选中即译：翻译并解析选中的词或句子（实时，不落库）。"""
    text = payload.text.strip()
    if not text:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="请先选中要解析的内容"
        )

    messages = [
        {"role": "system", "content": EXPLAIN_PROMPT},
        {
            "role": "user",
            "content": f"选中内容：{text}\n所在句子：{payload.context.strip()}",
        },
    ]
    data = _call_deepseek_json(messages)

    return ExplainResponse(
        translation=str(data.get("translation") or "").strip(),
        analysis=str(data.get("analysis") or "").strip(),
    )
