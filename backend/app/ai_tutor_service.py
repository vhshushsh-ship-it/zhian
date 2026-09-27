"""AI 一对一导师「小岸」：用户学习数据快照。

从已有表查询用户真实学习数据，拼成文本快照，注入 AI 系统提示词，
让「小岸」能基于真实进度给出个性化建议。

- 单词摘要：复用 stats_service.compute_english_stats（口径与 /api/english/stats 一致），
  并补充近 7 天新学/复习、到期积压；
- 口语摘要：查 speaking_conversations / speaking_messages（话题、难度、句子数）；
- 阅读摘要：查 reading_history / reading_articles（篇数、正确率）。
"""

import json
from datetime import date, datetime, timedelta

from sqlalchemy.orm import Session

from .models import (
    ReadingArticle,
    ReadingHistory,
    SpeakingConversation,
    SpeakingMessage,
    SpeakingScore,
    User,
    UserWordProgress,
    WritingSubmission,
)
from .speaking_topics import GROUP_LABELS, topic_display, topic_group_label
from .stats_service import compute_english_stats

# 口语难度 key → 显示名（与 english_speaking 保持一致）
LEVEL_LABELS = {
    "beginner": "初级",
    "intermediate": "中级",
    "advanced": "高级",
}


def _count_error_types(scores: list[SpeakingScore]) -> dict[str, int]:
    """统计若干条评分里各类错误出现的次数（错误类型 → 次数）。"""
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
    return counts


def _build_score_text(scores: list[SpeakingScore]) -> str:
    """把最近若干条评分拼成一句话：平均分 + 语法分趋势 + 常见错误。

    scores 已按时间倒序（最新在前），最多 10 条。
    """
    if not scores:
        return ""

    n = len(scores)
    avg_total = round(sum(s.total for s in scores) / n)
    avg_grammar = round(sum(s.grammar for s in scores) / n)
    avg_vocab = round(sum(s.vocab for s in scores) / n)
    avg_fluency = round(sum(s.fluency for s in scores) / n)

    text = (
        f"最近{n}次评分平均{avg_total}分"
        f"（语法{avg_grammar}/用词{avg_vocab}/流利{avg_fluency}）"
    )

    # 趋势：取最近 5 次（按时间正序比较最早与最新一次）
    recent5 = list(reversed(scores[:5]))
    if len(recent5) >= 2:
        first = recent5[0].grammar
        last = recent5[-1].grammar
        diff = last - first
        if diff >= 5:
            text += f"，语法分从{first}升到{last}，进步明显"
        elif diff <= -5:
            text += f"，语法分从{first}降到{last}，需要加强"
        else:
            text += f"，语法分稳定在{last}左右"
    text += "。"

    # 常见错误：按出现次数降序，最多列 3 类
    top = sorted(_count_error_types(scores).items(), key=lambda kv: (-kv[1], kv[0]))[:3]
    if top:
        text += "常见错误：" + "、".join(f"{t}({c}次)" for t, c in top) + "。"

    return text


def get_speaking_summary(db: Session, user_id: int) -> str:
    """口语练习摘要：对话次数 / 话题覆盖 + 评分历史 / 趋势 / 常见错误。

    评分数据来自 speaking_scores（/english/speaking/score 已持久化）。
    无对话也无评分时返回「尚未开始」。
    """
    now = datetime.now()
    week_ago = now - timedelta(days=7)

    convs = (
        db.query(SpeakingConversation)
        .filter(SpeakingConversation.user_id == user_id)
        .order_by(SpeakingConversation.updated_at.desc())
        .all()
    )
    scores = (
        db.query(SpeakingScore)
        .filter(SpeakingScore.user_id == user_id)
        .order_by(SpeakingScore.created_at.desc(), SpeakingScore.id.desc())
        .limit(10)
        .all()
    )

    if not convs and not scores:
        return "口语练习：尚未开始"

    parts: list[str] = []

    if convs:
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
        practiced_labels = "、".join(topic_display(t) for t in practiced)
        practiced_groups = {topic_group_label(t) for t in practiced if topic_group_label(t)}
        missing_groups = [label for label in GROUP_LABELS.values() if label not in practiced_groups]

        latest = convs[0]  # 已按 updated_at 倒序
        latest_topic = topic_display(latest.topic)
        latest_level = LEVEL_LABELS.get(latest.level, latest.level)

        parts.append(f"最近7天对话{convs_7d}次，累计说{total_sentences}句英语。")
        parts.append(f"练过话题：{practiced_labels or '无'}。")
        if missing_groups:
            parts.append(f"还没练过：{'、'.join(missing_groups)}。")
        parts.append(f"最近一次是{latest_topic}（{latest_level}）。")

    score_text = _build_score_text(scores)
    if score_text:
        parts.append(score_text)

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


# 写作错误关键词 → 类型（用于 AI 导师摘要里的「常见错误类型」）
WRITING_ERROR_TYPES = [
    ("时态", "时态"), ("语态", "语态"), ("主谓", "主谓一致"),
    ("拼写", "拼写"), ("标点", "标点"), ("大小写", "大小写"),
    ("冠词", "冠词"), ("介词", "介词"), ("连词", "连词"),
    ("搭配", "搭配"), ("用词", "用词"), ("词汇", "用词"),
    ("句式", "句式"), ("结构", "结构"), ("衔接", "衔接"), ("逻辑", "逻辑"),
]


def _classify_writing_error(text: str) -> str:
    """根据错误说明文字里的关键词，粗分类错误类型。"""
    for kw, label in WRITING_ERROR_TYPES:
        if kw in text:
            return label
    return "其他"


def _count_writing_error_types(subs: list[WritingSubmission]) -> dict[str, int]:
    """统计若干篇写作里各类错误出现的次数（错误类型 → 次数）。"""
    counts: dict[str, int] = {}
    for s in subs:
        try:
            data = json.loads(s.feedback_json) if s.feedback_json else {}
        except (json.JSONDecodeError, TypeError):
            data = {}
        for e in data.get("errors") or []:
            if isinstance(e, dict) and e.get("error"):
                t = _classify_writing_error(str(e["error"]).strip())
                counts[t] = counts.get(t, 0) + 1
    return counts


def get_writing_summary(db: Session, user_id: int) -> str:
    """写作练习摘要：最近写了几篇 + 平均分 + 分项弱项 + 常见错误 + 最近题目。"""
    subs = (
        db.query(WritingSubmission)
        .filter(WritingSubmission.user_id == user_id)
        .order_by(WritingSubmission.created_at.desc(), WritingSubmission.id.desc())
        .limit(10)
        .all()
    )
    if not subs:
        return "写作练习：尚未开始"

    scored = [s for s in subs if s.score is not None]
    if not scored:
        return f"写作练习：最近写了{len(subs)}篇，尚未批改"

    n = len(scored)
    avg_total = round(sum(s.score for s in scored) / n)
    text = f"最近写了{n}篇，平均{avg_total}分"

    # 分项平均（语法40 / 结构30 / 用词30），取最近 3 篇
    dims: dict[str, list[float]] = {"语法": [], "结构": [], "用词": []}
    fulls = {"语法": 40, "结构": 30, "用词": 30}
    for s in scored[:3]:
        try:
            fb = json.loads(s.feedback_json) if s.feedback_json else {}
        except (json.JSONDecodeError, TypeError):
            fb = {}
        for label, field in (
            ("语法", "grammar_score"),
            ("结构", "structure_score"),
            ("用词", "vocab_score"),
        ):
            v = fb.get(field)
            if isinstance(v, (int, float)):
                dims[label].append(float(v))

    # 弱项：三项都有时，按得分率最低的分项
    weak_dim = ""
    if all(dims.values()):
        rates = {
            label: sum(vals) / (len(vals) * fulls[label])
            for label, vals in dims.items()
        }
        weak_dim = min(rates, key=rates.get)

    if weak_dim:
        text += f"，{weak_dim}分偏低"

    top = sorted(
        _count_writing_error_types(scored).items(), key=lambda kv: (-kv[1], kv[0])
    )[:3]
    if top:
        text += "，常见错误：" + "、".join(f"{t}({c}次)" for t, c in top)
    text += "。"

    topics = [s.topic for s in scored[:3] if s.topic]
    if topics:
        text += "最近写了《" + "》《".join(topics) + "》。"

    return "写作练习：" + text


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

    # 口语 / 阅读 / 写作摘要（单独函数，返回自然语言一句话）
    lines.append(get_speaking_summary(db, user_id))
    lines.append(get_reading_summary(db, user_id))
    lines.append(get_writing_summary(db, user_id))

    return "\n".join(lines)
