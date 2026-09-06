"""背单词：基于记忆强度 S 的抗遗忘调度。

调度算法（参数集中在下方常量，便于调整）：
- 复习后按「认识 / 模糊 / 忘记」反馈调整记忆强度 S；
- S 通过自然衰减实时计算（不入库），复习时取衰减后的当前值；
- 新 S 映射到下次复习间隔，下次复习日期写入 next_review_date。
"""

import math
from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user
from ..models import User, UserWordProgress, Word
from ..schemas import (
    ReviewRequest,
    ReviewResponse,
    TodayQueueItem,
    TodayQueueResponse,
    WordDetailResponse,
    WordDefinitionResponse,
    WordExampleResponse,
    WordStatsResponse,
)

router = APIRouter(prefix="/words", tags=["words"])

# ---------- 算法参数 ----------

# 「认识」增量：按当前 S 所在区间（先慢中快后慢），封顶 100
KNOWN_INCREMENT: list[tuple[float, float, float]] = [
    (0, 25, 10),
    (25, 60, 18),
    (60, 85, 12),
    (85, 100, 4),
]

# 「忘记」减量：按当前 S 所在区间，封底 0
FORGOTTEN_DECREMENT: list[tuple[float, float, float]] = [
    (0, 25, 3),
    (25, 60, 10),
    (60, 85, 18),
    (85, 100, 25),
]

# 「模糊」：S 不变，本次复习间隔 ×0.7
VAGUE_INTERVAL_FACTOR = 0.7

# 新 S → 下次复习间隔
INTERVAL_MAP: list[tuple[float, float, timedelta]] = [
    (0, 15, timedelta(hours=12)),
    (15, 30, timedelta(days=1)),
    (30, 45, timedelta(days=2)),
    (45, 60, timedelta(days=4)),
    (60, 70, timedelta(days=7)),
    (70, 80, timedelta(days=12)),
    (80, 90, timedelta(days=21)),
    (90, 100, timedelta(days=36)),
]

# 每日新增单词上限
NEW_WORDS_PER_DAY = 20


def _known_increment(s: float) -> float:
    """按当前 S 查「认识」增量。"""
    for lo, hi, inc in KNOWN_INCREMENT:
        if lo <= s < hi:
            return inc
    return KNOWN_INCREMENT[-1][2] if s >= 100 else KNOWN_INCREMENT[0][2]


def _forgotten_decrement(s: float) -> float:
    """按当前 S 查「忘记」减量。"""
    for lo, hi, dec in FORGOTTEN_DECREMENT:
        if lo <= s < hi:
            return dec
    return FORGOTTEN_DECREMENT[-1][2] if s >= 100 else FORGOTTEN_DECREMENT[0][2]


def _interval_for(s: float) -> timedelta:
    """按新 S 查下次复习间隔。"""
    for lo, hi, delta in INTERVAL_MAP:
        if lo <= s < hi:
            return delta
    return INTERVAL_MAP[-1][2] if s >= 100 else INTERVAL_MAP[0][2]


def current_strength(last_s: float, last_review_at: datetime | None) -> float:
    """自然衰减后的当前记忆强度 S。

    cur = last_s × exp(-t/τ)，t 为距上次复习的天数，τ = 1 + last_s/10（天）。
    从未复习（last_review_at 为空）的词不衰减，当前 S 视为 0。
    """
    if last_review_at is None:
        return 0.0
    t = (datetime.now() - last_review_at).total_seconds() / 86400.0
    tau = 1.0 + last_s / 10.0
    return last_s * math.exp(-t / tau)


def apply_feedback(cur_s: float, feedback: str) -> tuple[float, timedelta]:
    """根据反馈返回 (新 S, 下次间隔)。

    - known：S 按区间增量，封顶 100；
    - forgotten：S 按区间减量，封底 0；
    - vague：S 不变，间隔 ×0.7。
    """
    if feedback == "known":
        new_s = min(100.0, cur_s + _known_increment(cur_s))
    elif feedback == "forgotten":
        new_s = max(0.0, cur_s - _forgotten_decrement(cur_s))
    elif feedback == "vague":
        new_s = cur_s
    else:
        raise ValueError(f"未知反馈类型: {feedback}")

    delta = _interval_for(new_s)
    if feedback == "vague":
        delta = delta * VAGUE_INTERVAL_FACTOR
    return new_s, delta


def _format_interval(delta: timedelta) -> str:
    """把间隔格式化为中文文本：12小时 / 1天 / 2天 / 36天。"""
    total_hours = delta.total_seconds() / 3600.0
    if total_hours < 24:
        return f"{total_hours:g}小时"
    return f"{total_hours / 24.0:g}天"


def _compute_streak(progresses: list[UserWordProgress], today: date) -> int:
    """连续学习天数：按 last_review_at 日期去重，从今天往前连续计数。

    今天没学则从昨天起算。
    """
    studied_days = {
        p.last_review_at.date() for p in progresses if p.last_review_at is not None
    }
    if not studied_days:
        return 0

    streak = 0
    cursor = today if today in studied_days else today - timedelta(days=1)
    while cursor in studied_days:
        streak += 1
        cursor -= timedelta(days=1)
    return streak


# ---------- 接口 ----------


@router.get("/today-queue", response_model=TodayQueueResponse)
def today_queue(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """今日复习队列：到期词（按当前 S 升序）+ 新词。"""
    today = date.today()

    progresses = (
        db.query(UserWordProgress)
        .filter(UserWordProgress.user_id == current_user.id)
        .all()
    )
    progressed_word_ids = [p.word_id for p in progresses]

    # a. 到期词：next_review_date <= 今天，按当前 S 升序
    due = [
        (current_strength(p.memory_strength, p.last_review_at), p)
        for p in progresses
        if p.next_review_date is not None and p.next_review_date <= today
    ]
    due.sort(key=lambda x: x[0])
    review_count = len(due)

    # c. 新词上限：到期词 > 30 时递减（每多 1 个复习词减 1，最少 0）
    target_new = NEW_WORDS_PER_DAY
    if review_count > 30:
        target_new = max(0, NEW_WORDS_PER_DAY - (review_count - 30))

    new_words: list[Word] = []
    if target_new > 0:
        q = db.query(Word)
        if progressed_word_ids:
            q = q.filter(~Word.id.in_(progressed_word_ids))
        new_words = q.order_by(Word.id.asc()).limit(target_new).all()

    # d. 组装队列：先到期词，再新词
    items: list[TodayQueueItem] = []
    index = 0
    for cur_s, p in due:
        word = db.get(Word, p.word_id)
        if word is None:
            continue
        items.append(
            TodayQueueItem(
                id=word.id,
                word=word.word,
                phonetic=word.phonetic,
                audio_url=word.audio_url,
                current_strength=round(cur_s, 2),
                is_new=False,
                index=index,
            )
        )
        index += 1
    for w in new_words:
        items.append(
            TodayQueueItem(
                id=w.id,
                word=w.word,
                phonetic=w.phonetic,
                audio_url=w.audio_url,
                current_strength=0.0,
                is_new=True,
                index=index,
            )
        )
        index += 1

    return TodayQueueResponse(
        total=len(items),
        review_count=review_count,
        new_count=len(new_words),
        items=items,
    )


@router.get("/stats", response_model=WordStatsResponse)
def stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """背单词学习统计。"""
    today = date.today()

    progresses = (
        db.query(UserWordProgress)
        .filter(UserWordProgress.user_id == current_user.id)
        .all()
    )

    learned = len(progresses)
    due_today = sum(
        1
        for p in progresses
        if p.next_review_date is not None and p.next_review_date <= today
    )
    learned_today = sum(
        1
        for p in progresses
        if p.last_review_at is not None and p.last_review_at.date() == today
    )
    mastered = sum(1 for p in progresses if p.is_mastered)

    known_count = sum(p.known_count or 0 for p in progresses)
    vague_count = sum(p.vague_count or 0 for p in progresses)
    forgotten_count = sum(p.forgotten_count or 0 for p in progresses)

    total_feedback = known_count + vague_count + forgotten_count
    accuracy = round(known_count / total_feedback, 4) if total_feedback else 0.0

    return WordStatsResponse(
        learned=learned,
        due_today=due_today,
        learned_today=learned_today,
        mastered=mastered,
        known_count=known_count,
        vague_count=vague_count,
        forgotten_count=forgotten_count,
        accuracy=accuracy,
        streak_days=_compute_streak(progresses, today),
    )


@router.get("/{word_id}", response_model=WordDetailResponse)
def get_word(
    word_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """单词详情（释义、例句）+ 当前用户学习进度。"""
    word = db.get(Word, word_id)
    if word is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="单词不存在")

    progress = (
        db.query(UserWordProgress)
        .filter(
            UserWordProgress.user_id == current_user.id,
            UserWordProgress.word_id == word_id,
        )
        .first()
    )

    if progress is None:
        cur_s = 0.0
        memory_strength = 0.0
        review_count = 0
        known_count = 0
        vague_count = 0
        forgotten_count = 0
        is_mastered = False
    else:
        cur_s = current_strength(progress.memory_strength, progress.last_review_at)
        memory_strength = progress.memory_strength
        review_count = progress.review_count
        known_count = progress.known_count
        vague_count = progress.vague_count
        forgotten_count = progress.forgotten_count
        is_mastered = progress.is_mastered

    return WordDetailResponse(
        id=word.id,
        word=word.word,
        phonetic=word.phonetic,
        audio_url=word.audio_url,
        definitions=[
            WordDefinitionResponse(pos=d.pos, meaning=d.meaning)
            for d in word.definitions
        ],
        examples=[WordExampleResponse(en=e.en, zh=e.zh) for e in word.examples],
        current_strength=round(cur_s, 2),
        memory_strength=memory_strength,
        review_count=review_count,
        known_count=known_count,
        vague_count=vague_count,
        forgotten_count=forgotten_count,
        is_mastered=is_mastered,
    )


@router.post("/{word_id}/review", response_model=ReviewResponse)
def review_word(
    word_id: int,
    payload: ReviewRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """复习反馈：更新记忆强度 S 与下次复习日期。"""
    word = db.get(Word, word_id)
    if word is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="单词不存在")

    now = datetime.now()
    today = date.today()

    # a. 取 / 建 progress（新词 memory_strength=0、next_review_date=今天）
    progress = (
        db.query(UserWordProgress)
        .filter(
            UserWordProgress.user_id == current_user.id,
            UserWordProgress.word_id == word_id,
        )
        .first()
    )
    if progress is None:
        progress = UserWordProgress(
            user_id=current_user.id,
            word_id=word_id,
            memory_strength=0.0,
            next_review_date=today,
            review_count=0,
            known_count=0,
            vague_count=0,
            forgotten_count=0,
            is_mastered=False,
        )
        db.add(progress)

    # b. 先算衰减后的当前 S
    cur_s = current_strength(progress.memory_strength, progress.last_review_at)

    # c. 反馈更新
    new_s, delta = apply_feedback(cur_s, payload.feedback)

    # d. 下次复习日期 = 当前时刻 + 间隔，再取日期（12 小时档真实落在 12 小时后的那天）
    progress.next_review_date = (now + delta).date()

    # e. 记录复习时间与计数（None 兜底，防历史脏数据导致 += 报错）
    progress.memory_strength = new_s
    progress.last_review_at = now
    progress.review_count = (progress.review_count or 0) + 1
    if payload.feedback == "known":
        progress.known_count = (progress.known_count or 0) + 1
    elif payload.feedback == "vague":
        progress.vague_count = (progress.vague_count or 0) + 1
    else:
        progress.forgotten_count = (progress.forgotten_count or 0) + 1

    # f. 掌握标记：S >= 90 掌握，忘记后解除掌握
    if new_s >= 90:
        progress.is_mastered = True
    elif payload.feedback == "forgotten":
        progress.is_mastered = False

    # g. 保存
    db.commit()

    return ReviewResponse(
        new_strength=round(new_s, 2),
        next_review_date=progress.next_review_date,
        interval_text=_format_interval(delta),
    )
