"""AI 一对一导师「小岸」：用户学习数据快照。

从已有表查询用户真实学习数据，拼成文本快照，注入 AI 系统提示词，
让「小岸」能基于真实进度给出个性化建议。

统计口径与 /api/english/stats 完全一致（复用 stats_service.compute_english_stats）。
"""

from datetime import datetime

from sqlalchemy.orm import Session

from .models import User, UserWordProgress
from .stats_service import compute_english_stats


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
    speaking = stats["speaking"]
    trend = stats["weekly_trend"]

    # 近 7 天趋势简述：学习天数 + 日均词数
    active_days = sum(
        1
        for t in trend
        if t["words_reviewed"] or t["words_new"] or t["speaking_messages"]
    )
    total_words_7d = sum(t["words_reviewed"] + t["words_new"] for t in trend)
    avg_words_7d = round(total_words_7d / 7, 1)

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
    lines.append(f"- 口语练习次数：{overview['speaking_sessions']} 次")
    if overview["last_speaking_at"] is not None:
        lines.append(f"- 最近口语练习：{overview['last_speaking_at']:%Y-%m-%d %H:%M}")
    if speaking["topics"]:
        topic_text = "、".join(
            f"{t['topic']}（{t['count']} 次）" for t in speaking["topics"]
        )
        lines.append(f"- 口语常练话题：{topic_text}")

    return "\n".join(lines)
