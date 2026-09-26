"""AI 一对一导师「小岸」：用户学习数据快照。

从已有表查询用户真实学习数据，拼成文本快照，注入 AI 系统提示词，
让「小岸」能基于真实进度给出个性化建议。

- 单词摘要：复用 stats_service.compute_english_stats（口径与 /api/english/stats 一致），
  并补充近 7 天新学/复习、到期积压；
- 口语摘要：查 speaking_conversations / speaking_messages（话题、难度、句子数）；
- 阅读摘要：查 reading_history / reading_articles（篇数、正确率）。
"""

from datetime import date, datetime, timedelta

from sqlalchemy.orm import Session

from .models import (
    ReadingArticle,
    ReadingHistory,
    SpeakingConversation,
    SpeakingMessage,
    User,
    UserWordProgress,
)
from .stats_service import compute_english_stats

# 口语话题 key → 显示名（与 stats_service / english_speaking 保持一致）
TOPIC_LABELS = {
    "daily": "日常对话",
    "interview": "面试",
    "travel": "旅游",
    "campus": "校园",
}

# 口语难度 key → 显示名（与 english_speaking 保持一致）
LEVEL_LABELS = {
    "beginner": "初级",
    "intermediate": "中级",
    "advanced": "高级",
}

# 全部口语话题（用于识别「没练过」的话题）
ALL_TOPICS = list(TOPIC_LABELS.keys())


def get_speaking_summary(db: Session, user_id: int) -> str:
    """口语练习摘要：近 7 天对话次数、累计句子数、话题/难度覆盖。

    注意：当前口语评分接口（/english/speaking/score）不持久化，历史库中
    没有评分与错误数据，故此处不统计平均分与常见错误，待评分落库后再补。
    """
    now = datetime.now()
    week_ago = now - timedelta(days=7)

    convs = (
        db.query(SpeakingConversation)
        .filter(SpeakingConversation.user_id == user_id)
        .order_by(SpeakingConversation.updated_at.desc())
        .all()
    )
    if not convs:
        return "口语练习：尚未开始"

    convs_7d = sum(
        1 for c in convs if c.updated_at is not None and c.updated_at >= week_ago
    )

    total_sentences = (
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

    practiced = sorted({c.topic for c in convs if c.topic})
    practiced_labels = "、".join(TOPIC_LABELS.get(t, t) for t in practiced)
    missing = [TOPIC_LABELS.get(t, t) for t in ALL_TOPICS if t not in practiced]

    latest = convs[0]  # 已按 updated_at 倒序
    latest_topic = TOPIC_LABELS.get(latest.topic, latest.topic)
    latest_level = LEVEL_LABELS.get(latest.level, latest.level)

    parts = [f"最近7天对话{convs_7d}次，累计说{total_sentences}句英语。"]
    parts.append(f"练过话题：{practiced_labels or '无'}。")
    if missing:
        parts.append(f"还没练过：{'、'.join(missing)}。")
    parts.append(f"最近一次是{latest_topic}（{latest_level}）。")
    # 评分 / 错误数据尚未落库，避免 AI 臆造分数
    parts.append("暂无评分与错误数据。")

    return "口语练习：" + "".join(parts)


def get_reading_summary(db: Session, user_id: int) -> str:
    """外刊精读摘要：累计篇数、近 7 天篇数、最近 3 篇标题及正确率。

    注意：题目未按类型（主旨/细节/推断/词汇）标注、做题结果未按题持久化，
    故此处不统计错题类型，待题目标注类型并记录答题明细后再补。
    """
    now = datetime.now()
    week_ago = now - timedelta(days=7)

    total = (
        db.query(ReadingHistory)
        .filter(ReadingHistory.user_id == user_id)
        .count()
    )
    if total == 0:
        return "外刊精读：尚未开始"

    read_7d = (
        db.query(ReadingHistory)
        .filter(
            ReadingHistory.user_id == user_id,
            ReadingHistory.read_at >= week_ago,
        )
        .count()
    )

    recent = (
        db.query(ReadingHistory)
        .filter(ReadingHistory.user_id == user_id)
        .order_by(ReadingHistory.read_at.desc())
        .limit(3)
        .all()
    )
    article_ids = [h.article_id for h in recent]
    titles = {
        a.id: a.title
        for a in db.query(ReadingArticle)
        .filter(ReadingArticle.id.in_(article_ids))
        .all()
    }

    recent_parts = []
    for h in recent:
        title = titles.get(h.article_id, "未知文章")
        if h.quiz_score is not None:
            recent_parts.append(f"《{title}》(正确率{int(round(h.quiz_score))}%)")
        else:
            recent_parts.append(f"《{title}》(未做题)")

    text = f"外刊精读：累计读了{total}篇，最近7天读{read_7d}篇。"
    if recent_parts:
        text += "最近读：" + "、".join(recent_parts) + "。"
    text += "暂无错题类型数据。"
    return text


def build_user_snapshot(db: Session, user_id: int) -> str:
    """查询用户真实学习数据，返回文本快照，拼进 AI 系统提示词。"""
    user = db.get(User, user_id)

    # 注册天数：从 users.created_at 算（聚合统计未含，单独查）
    registered_days = 0
    if user is not None and user.created_at is not None:
        registered_days = max(0, (datetime.now() - user.created_at).days)

    # 上次背单词时间：last_review_at 最新值（聚合统计未含，单独查）
    progresses = (
        db.query(UserWordProgress)
        .filter(UserWordProgress.user_id == user_id)
        .all()
    )
    last_review_at = max(
        (p.last_review_at for p in progresses if p.last_review_at is not None),
        default=None,
    )

    # 与 /api/english/stats 共用的聚合统计
    stats = compute_english_stats(db, user_id)
    overview = stats["overview"]
    words = stats["words"]
    trend = stats["weekly_trend"]

    # 近 7 天趋势简述：学习天数 + 日均词数
    active_days = sum(
        1
        for t in trend
        if t["words_reviewed"] or t["words_new"] or t["speaking_messages"]
    )
    total_words_7d = sum(t["words_reviewed"] + t["words_new"] for t in trend)
    avg_words_7d = round(total_words_7d / 7, 1)

    # 单词补充：近 7 天新学 / 复习拆分 + 逾期积压（已过复习日仍没复习的词）
    new_7d = sum(t["words_new"] for t in trend)
    reviewed_7d = sum(t["words_reviewed"] for t in trend)
    today = date.today()
    overdue = sum(
        1
        for p in progresses
        if p.next_review_date is not None and p.next_review_date < today
    )

    # 组装文本
    lines: list[str] = []
    lines.append(f"- 注册天数：{registered_days} 天")
    lines.append(
        f"- 当前词书：{words['current_book']}；每日新词目标：{words['daily_goal']} 个"
    )
    lines.append(
        f"- 已学单词：{overview['total_words_learned']} 个；已掌握：{overview['total_words_mastered']} 个"
    )
    lines.append(f"- 今日待复习：{overview['words_today_due']} 个")
    lines.append(f"- 总体认识率：{overview['recognition_rate']}%")
    lines.append(f"- 连续学习天数：{overview['streak_days']} 天")
    lines.append(f"- 本周完成率：{overview['weekly_completion_rate']}%")
    lines.append(f"- 近7天学习趋势：学习了 {active_days} 天，日均 {avg_words_7d} 词")
    lines.append(f"- 近7天：新学 {new_7d} 词，复习 {reviewed_7d} 词")
    lines.append(f"- 到期未复习（积压）：{overdue} 词")
    if last_review_at is not None:
        lines.append(f"- 上次背单词：{last_review_at:%Y-%m-%d %H:%M}")
    else:
        lines.append("- 上次背单词：尚未开始")
    if words["weak_words"]:
        weak = "、".join(
            f"{w['word']}（忘记 {w['forgotten_count']} 次）"
            for w in words["weak_words"]
        )
        lines.append(f"- 最薄弱 5 词：{weak}")
    else:
        lines.append("- 最薄弱词：暂无")

    # 口语 / 阅读摘要（单独函数，返回自然语言一句话）
    lines.append(get_speaking_summary(db, user_id))
    lines.append(get_reading_summary(db, user_id))

    return "\n".join(lines)
