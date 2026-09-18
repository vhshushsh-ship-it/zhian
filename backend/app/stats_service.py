"""学习数据统计：每日学习量记录 + 聚合统计。

- update_daily_stats：在背单词 / 口语等接口里记录当天学习动作（upsert）；
- compute_english_stats：聚合英语模块全部学习数据，供 /api/english/stats
  与 AI 导师 build_user_snapshot 共用，保证两处数据完全一致。
"""

from datetime import date, timedelta

from sqlalchemy.orm import Session

from .models import (
    ReadingHistory,
    SpeakingConversation,
    SpeakingMessage,
    UserDailyStats,
    UserWordProgress,
    UserWordSettings,
    Word,
)

# 词书 key → 显示名（与 words.py 的 BOOKS 保持一致）
BOOK_LABELS = {"kaoyan": "考研英语", "cet4": "四级英语", "cet6": "六级英语"}

# 口语话题 key → 显示名（与 english_speaking.py 的 TOPIC_NAMES 保持一致）
TOPIC_LABELS = {
    "daily": "日常对话",
    "interview": "面试",
    "travel": "旅游",
    "campus": "校园",
}

# update_daily_stats 允许累加的字段白名单（避免 setattr 到任意属性）
_DAILY_FIELDS = {
    "words_reviewed",
    "words_new",
    "speaking_messages",
    "reading_minutes",
}


def update_daily_stats(
    db: Session, user_id: int, field: str, increment: int = 1
) -> None:
    """记录当天学习动作：当天有记录则 +increment，没有则新建。

    只修改会话、不 commit，由调用方随主流程统一提交（避免各提交一次）。
    """
    if field not in _DAILY_FIELDS:
        raise ValueError(f"未知的每日统计字段: {field}")

    today = date.today()
    # 本项目会话关闭了 autoflush，需显式 flush：否则同一请求内多次调用时，
    # 上一次调用刚 add 的当天记录尚未入库，本次查询看不到它，会重复插入
    # 撞上 (user_id, stat_date) 唯一索引。
    db.flush()
    row = (
        db.query(UserDailyStats)
        .filter(
            UserDailyStats.user_id == user_id,
            UserDailyStats.stat_date == today,
        )
        .first()
    )
    if row is None:
        row = UserDailyStats(user_id=user_id, stat_date=today)
        setattr(row, field, increment)
        db.add(row)
    else:
        setattr(row, field, (getattr(row, field) or 0) + increment)


def _day_has_activity(row: UserDailyStats | None) -> bool:
    """某天是否有任意学习记录（任一字段 > 0）。"""
    if row is None:
        return False
    return bool(
        row.words_reviewed or row.words_new or row.speaking_messages or row.reading_minutes
    )


def compute_streak_days(daily_rows: list[UserDailyStats], today: date) -> int:
    """连续学习天数：从今天往前（今天没学则从昨天起算）的连续学习天数。"""
    active_days = {r.stat_date for r in daily_rows if _day_has_activity(r)}
    if not active_days:
        return 0

    streak = 0
    cursor = today if today in active_days else today - timedelta(days=1)
    while cursor in active_days:
        streak += 1
        cursor -= timedelta(days=1)
    return streak


def compute_english_stats(db: Session, user_id: int) -> dict:
    """聚合英语模块全部学习数据，返回与 /api/english/stats 一致的结构。"""
    today = date.today()

    # ---------- 背单词进度 ----------
    progresses = (
        db.query(UserWordProgress)
        .filter(UserWordProgress.user_id == user_id)
        .all()
    )
    learned = len(progresses)
    mastered = sum(1 for p in progresses if p.is_mastered)
    due_today = sum(
        1
        for p in progresses
        if p.next_review_date is not None and p.next_review_date <= today
    )

    known = sum(p.known_count or 0 for p in progresses)
    vague = sum(p.vague_count or 0 for p in progresses)
    forgotten = sum(p.forgotten_count or 0 for p in progresses)
    total_feedback = known + vague + forgotten
    recognition_rate = (
        round(known / total_feedback * 100, 1) if total_feedback else 0.0
    )

    # ---------- 词书设置 ----------
    settings = (
        db.query(UserWordSettings)
        .filter(UserWordSettings.user_id == user_id)
        .first()
    )
    current_book = (
        BOOK_LABELS.get(settings.current_book, settings.current_book)
        if settings
        else "未设置"
    )
    daily_goal = settings.daily_new_goal if settings else 20

    # ---------- 薄弱词 TOP5（按忘记次数降序） ----------
    weak_rows = (
        db.query(UserWordProgress, Word)
        .join(Word, Word.id == UserWordProgress.word_id)
        .filter(UserWordProgress.user_id == user_id)
        .order_by(UserWordProgress.forgotten_count.desc(), UserWordProgress.id.asc())
        .limit(5)
        .all()
    )
    weak_words = [
        {
            "word": w.word,
            "forgotten_count": p.forgotten_count or 0,
            "memory_strength": round(p.memory_strength or 0.0, 2),
        }
        for p, w in weak_rows
    ]

    # ---------- 口语 ----------
    convs = (
        db.query(SpeakingConversation)
        .filter(SpeakingConversation.user_id == user_id)
        .all()
    )
    speaking_sessions = len(convs)
    speaking_total_messages = (
        db.query(SpeakingMessage)
        .join(
            SpeakingConversation,
            SpeakingConversation.id == SpeakingMessage.conversation_id,
        )
        .filter(
            SpeakingConversation.user_id == user_id,
            SpeakingMessage.role == "user",
        )
        .count()
    )
    last_speaking_at = max(
        (c.created_at for c in convs if c.created_at is not None),
        default=None,
    )

    # 常练话题 TOP5（按次数降序）
    topic_counts: dict[str, int] = {}
    for c in convs:
        label = TOPIC_LABELS.get(c.topic, c.topic)
        topic_counts[label] = topic_counts.get(label, 0) + 1
    topics = [
        {"topic": label, "count": count}
        for label, count in sorted(
            topic_counts.items(), key=lambda kv: (-kv[1], kv[0])
        )[:5]
    ]

    # ---------- 外刊精读：已读文章数 ----------
    reading_articles_read = (
        db.query(ReadingHistory)
        .filter(ReadingHistory.user_id == user_id)
        .count()
    )

    # ---------- 每日统计：连续天数 + 近 7 天趋势 ----------
    daily_rows = (
        db.query(UserDailyStats)
        .filter(UserDailyStats.user_id == user_id)
        .all()
    )
    streak_days = compute_streak_days(daily_rows, today)

    daily_by_date = {r.stat_date: r for r in daily_rows}
    weekly_trend: list[dict] = []
    active_week_days = 0
    for offset in range(6, -1, -1):
        d = today - timedelta(days=offset)
        row = daily_by_date.get(d)
        if row is not None:
            weekly_trend.append(
                {
                    "date": d,
                    "words_reviewed": row.words_reviewed or 0,
                    "words_new": row.words_new or 0,
                    "speaking_messages": row.speaking_messages or 0,
                }
            )
        else:
            weekly_trend.append(
                {
                    "date": d,
                    "words_reviewed": 0,
                    "words_new": 0,
                    "speaking_messages": 0,
                }
            )
        if _day_has_activity(row):
            active_week_days += 1

    weekly_completion_rate = round(active_week_days / 7 * 100, 1)

    return {
        "overview": {
            "streak_days": streak_days,
            "total_words_learned": learned,
            "total_words_mastered": mastered,
            "words_today_due": due_today,
            "recognition_rate": recognition_rate,
            "speaking_sessions": speaking_sessions,
            "speaking_total_messages": speaking_total_messages,
            "last_speaking_at": last_speaking_at,
            "weekly_completion_rate": weekly_completion_rate,
            "reading_articles_read": reading_articles_read,
        },
        "words": {
            "current_book": current_book,
            "daily_goal": daily_goal,
            "weak_words": weak_words,
        },
        "speaking": {"topics": topics},
        "weekly_trend": weekly_trend,
    }
