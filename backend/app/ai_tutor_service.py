"""AI 一对一导师「小岸」：用户学习数据快照。

从已有表查询用户真实学习数据，拼成文本快照，注入 AI 系统提示词，
让「小岸」能基于真实进度给出个性化建议。
"""

from datetime import date, datetime

from sqlalchemy.orm import Session

from .models import (
    SpeakingConversation,
    User,
    UserWordProgress,
    UserWordSettings,
    Word,
)

# 词书 key → 显示名（与 words.py 的 BOOKS 保持一致）
BOOK_LABELS = {"kaoyan": "考研英语", "cet4": "四级英语", "cet6": "六级英语"}


def build_user_snapshot(db: Session, user_id: int) -> str:
    """查询用户真实学习数据，返回文本快照，拼进 AI 系统提示词。"""
    user = db.get(User, user_id)

    # 注册天数：从 users.created_at 算
    registered_days = 0
    if user is not None and user.created_at is not None:
        registered_days = max(0, (datetime.now() - user.created_at).days)

    # 当前词书 + 每日新词目标（未设置过则为默认值或「未设置」）
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
    daily_new_goal = (
        f"{settings.daily_new_goal} 个" if settings else "未设置"
    )

    # 单词学习进度
    progresses = (
        db.query(UserWordProgress)
        .filter(UserWordProgress.user_id == user_id)
        .all()
    )
    learned = len(progresses)
    mastered = sum(1 for p in progresses if p.is_mastered)

    today = date.today()
    due_today = sum(
        1
        for p in progresses
        if p.next_review_date is not None and p.next_review_date <= today
    )

    known_count = sum(p.known_count or 0 for p in progresses)
    vague_count = sum(p.vague_count or 0 for p in progresses)
    forgotten_count = sum(p.forgotten_count or 0 for p in progresses)
    total_feedback = known_count + vague_count + forgotten_count
    accuracy = int(round(known_count / total_feedback * 100)) if total_feedback else 0

    # 上次背单词时间：last_review_at 最新值
    last_review_at = max(
        (p.last_review_at for p in progresses if p.last_review_at is not None),
        default=None,
    )

    # 最薄弱 5 词：forgotten_count 降序，join words 取 word 字段
    weak_words: list[str] = []
    weak_rows = (
        db.query(UserWordProgress, Word)
        .join(Word, Word.id == UserWordProgress.word_id)
        .filter(UserWordProgress.user_id == user_id)
        .order_by(UserWordProgress.forgotten_count.desc(), UserWordProgress.id.asc())
        .limit(5)
        .all()
    )
    for _p, w in weak_rows:
        weak_words.append(f"{w.word}（忘记 {_p.forgotten_count or 0} 次）")

    # 口语练习：speaking_conversations 数量与最近一次时间
    speaking_convs = (
        db.query(SpeakingConversation)
        .filter(SpeakingConversation.user_id == user_id)
        .all()
    )
    speaking_count = len(speaking_convs)
    last_speaking_at = max(
        (c.created_at for c in speaking_convs if c.created_at is not None),
        default=None,
    )

    # 组装文本
    lines: list[str] = []
    lines.append(f"- 注册天数：{registered_days} 天")
    lines.append(f"- 当前词书：{current_book}；每日新词目标：{daily_new_goal}")
    lines.append(f"- 已学单词：{learned} 个；已掌握：{mastered} 个")
    lines.append(f"- 今日待复习：{due_today} 个")
    lines.append(
        f"- 总体认识率：{accuracy}%（认识 {known_count} / 模糊 {vague_count} / 忘记 {forgotten_count}）"
    )
    if last_review_at is not None:
        lines.append(f"- 上次背单词：{last_review_at:%Y-%m-%d %H:%M}")
    else:
        lines.append("- 上次背单词：尚未开始")
    if weak_words:
        lines.append(f"- 最薄弱 5 词：{'、'.join(weak_words)}")
    else:
        lines.append("- 最薄弱词：暂无")
    lines.append(f"- 口语练习次数：{speaking_count} 次")
    if last_speaking_at is not None:
        lines.append(f"- 最近口语练习：{last_speaking_at:%Y-%m-%d %H:%M}")

    return "\n".join(lines)
