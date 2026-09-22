"""演示模式：演示用户创建 + 演示数据预置 + 数据重置。

比赛展示期间通过 settings.DEMO_MODE 开启免登录访问，所有接口自动使用
演示用户 demo@zhian.com。本模块提供：

- get_or_create_demo_user：获取或创建演示用户（供 deps 依赖注入使用）；
- seed_demo_data：为演示用户预置一套示例学习数据（幂等，可重复执行）；
- clear_demo_data：清空演示用户的全部学习数据（供重置接口调用）。
"""

import json
import random
from datetime import date, datetime, timedelta

from sqlalchemy.orm import Session

from .models import (
    AiTutorConversation,
    ReadingArticle,
    ReadingHistory,
    SpeakingConversation,
    SpeakingMessage,
    User,
    UserAiProfile,
    UserDailyStats,
    UserWordProgress,
    UserWordSettings,
    Word,
)
from .security import hash_password

# 演示用户邮箱（全局唯一，作为登录标识）
DEMO_EMAIL = "demo@zhian.com"

# 演示用户密码：仅占位满足非空约束，不用于真实登录
DEMO_PASSWORD = "demo-demo-2024"

# 预置单词数
DEMO_WORD_COUNT = 50

# 固定随机种子：保证多次执行生成的演示数据一致
_RNG_SEED = 2024


def get_or_create_demo_user(db: Session) -> User:
    """获取演示用户，不存在则创建（role=user，非管理员）。"""
    user = db.query(User).filter(User.email == DEMO_EMAIL).first()
    if user is None:
        user = User(
            email=DEMO_EMAIL,
            username="demo",
            hashed_password=hash_password(DEMO_PASSWORD),
            role="user",
            status="active",
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    return user


def seed_demo_data(db: Session) -> None:
    """为演示用户预置示例学习数据（幂等：已存在的数据不重复插入）。"""
    user = get_or_create_demo_user(db)
    uid = user.id
    today = date.today()
    rng = random.Random(_RNG_SEED)

    # 1) 背单词设置：当前词书 = 考研，每日新词 20
    settings = (
        db.query(UserWordSettings).filter(UserWordSettings.user_id == uid).first()
    )
    if settings is None:
        settings = UserWordSettings(
            user_id=uid, current_book="kaoyan", daily_new_goal=20
        )
        db.add(settings)
    else:
        settings.current_book = "kaoyan"
        settings.daily_new_goal = 20
    db.flush()

    # 2) 单词进度：随机 50 个考研词，分「已认识 / 待复习 / 模糊」三档
    if db.query(UserWordProgress).filter(UserWordProgress.user_id == uid).count() == 0:
        words = db.query(Word).filter(Word.tags.like("%考研%")).all()
        sampled = rng.sample(words, min(DEMO_WORD_COUNT, len(words)))
        now = datetime.now()
        for i, w in enumerate(sampled):
            if i < 18:
                # 已认识：记忆强，下次复习在未来，部分已掌握
                s = rng.uniform(70.0, 92.0)
                progress = UserWordProgress(
                    user_id=uid,
                    word_id=w.id,
                    memory_strength=s,
                    last_review_at=now - timedelta(days=rng.randint(0, 3)),
                    next_review_date=today + timedelta(days=rng.randint(5, 25)),
                    review_count=rng.randint(3, 8),
                    known_count=rng.randint(3, 8),
                    vague_count=rng.randint(0, 1),
                    forgotten_count=rng.randint(0, 1),
                    is_mastered=s >= 90.0,
                )
            elif i < 35:
                # 待复习：已到期，记忆强度中低
                progress = UserWordProgress(
                    user_id=uid,
                    word_id=w.id,
                    memory_strength=rng.uniform(20.0, 55.0),
                    last_review_at=now - timedelta(days=rng.randint(1, 6)),
                    next_review_date=today - timedelta(days=rng.randint(0, 2)),
                    review_count=rng.randint(1, 3),
                    known_count=rng.randint(0, 2),
                    vague_count=rng.randint(1, 3),
                    forgotten_count=rng.randint(0, 2),
                    is_mastered=False,
                )
            else:
                # 模糊：下次复习就在今天，记忆强度中低
                progress = UserWordProgress(
                    user_id=uid,
                    word_id=w.id,
                    memory_strength=rng.uniform(30.0, 60.0),
                    last_review_at=now - timedelta(days=rng.randint(0, 2)),
                    next_review_date=today,
                    review_count=rng.randint(1, 4),
                    known_count=rng.randint(0, 1),
                    vague_count=rng.randint(2, 5),
                    forgotten_count=rng.randint(0, 1),
                    is_mastered=False,
                )
            db.add(progress)
    db.flush()

    # 3) 每日统计：最近 7 天每天有复习 / 新学 / 口语数据
    existing_dates = {
        r.stat_date
        for r in db.query(UserDailyStats).filter(UserDailyStats.user_id == uid).all()
    }
    for offset in range(6, -1, -1):
        d = today - timedelta(days=offset)
        if d in existing_dates:
            continue
        db.add(
            UserDailyStats(
                user_id=uid,
                stat_date=d,
                words_reviewed=rng.randint(8, 30),
                words_new=rng.randint(5, 20),
                speaking_messages=rng.randint(0, 8),
                reading_minutes=rng.randint(0, 15),
            )
        )
    db.flush()

    # 4) 口语对话：2-3 段示例（日常 / 面试 / 旅行）
    if db.query(SpeakingConversation).filter(SpeakingConversation.user_id == uid).count() == 0:
        samples = [
            {
                "title": "日常问候与自我介绍",
                "topic": "daily",
                "level": "beginner",
                "messages": [
                    ("user", "Hi, could you tell me a bit about yourself?", "嗨，你能介绍一下你自己吗？"),
                    ("assistant", "Sure! Let's start with something simple: what do you usually do on weekends?", "当然！我们从简单的开始：你周末通常做什么？"),
                    ("user", "I usually read books and go jogging in the park.", "我通常读书，还会去公园慢跑。"),
                    ("assistant", "That sounds great! Jogging is a wonderful way to stay healthy.", "听起来很棒！慢跑是保持健康的好方法。"),
                ],
            },
            {
                "title": "英语面试模拟",
                "topic": "interview",
                "level": "intermediate",
                "messages": [
                    ("user", "Good morning, thank you for having me today.", "早上好，感谢您今天给我这次机会。"),
                    ("assistant", "Good morning! Thanks for coming. Could you walk me through your background?", "早上好！感谢你的到来。能介绍一下你的背景吗？"),
                    ("user", "I studied computer science and have two years of experience in web development.", "我学的是计算机科学，有两年网页开发经验。"),
                ],
            },
            {
                "title": "旅行经历分享",
                "topic": "travel",
                "level": "beginner",
                "messages": [
                    ("user", "Have you ever been to any interesting places?", "你去过什么有意思的地方吗？"),
                    ("assistant", "I'd love to hear about your travels! What's the most memorable place you've visited?", "我想听听你的旅行经历！你去过最难忘的地方是哪里？"),
                ],
            },
        ]
        for c in samples:
            conv = SpeakingConversation(
                user_id=uid, title=c["title"], topic=c["topic"], level=c["level"]
            )
            db.add(conv)
            db.flush()
            for role, content, translation in c["messages"]:
                db.add(
                    SpeakingMessage(
                        conversation_id=conv.id,
                        role=role,
                        content=content,
                        translation=translation,
                    )
                )
    db.flush()

    # 5) 阅读历史：读 2-3 篇文章（文章库为空则先补建示例文章）
    articles = db.query(ReadingArticle).order_by(ReadingArticle.id).all()
    if len(articles) < 3:
        for sa in _SAMPLE_ARTICLES[len(articles):]:
            db.add(
                ReadingArticle(
                    title=sa["title"],
                    content=sa["content"],
                    difficulty=sa["difficulty"],
                    topic=sa["topic"],
                    word_count=len(sa["content"].split()),
                    long_sentences=json.dumps(sa["long_sentences"], ensure_ascii=False),
                    quiz=json.dumps(sa["quiz"], ensure_ascii=False),
                    created_by=uid,
                )
            )
        db.flush()
        articles = db.query(ReadingArticle).order_by(ReadingArticle.id).all()

    if db.query(ReadingHistory).filter(ReadingHistory.user_id == uid).count() == 0:
        for i, a in enumerate(articles[:3]):
            db.add(
                ReadingHistory(
                    user_id=uid,
                    article_id=a.id,
                    read_at=datetime.now() - timedelta(days=rng.randint(1, 5)),
                    quiz_score=rng.choice([75.0, 87.5, 100.0]),
                    words_collected=rng.randint(1, 4),
                )
            )
    db.flush()

    # 6) AI 导师画像：目标考研英语，考试日期 2026 年 12 月
    profile = db.query(UserAiProfile).filter(UserAiProfile.user_id == uid).first()
    if profile is None:
        profile = UserAiProfile(user_id=uid)
        db.add(profile)
    profile.goal = "考研英语"
    profile.exam_date = date(2026, 12, 1)
    db.flush()

    db.commit()


def clear_demo_data(db: Session) -> None:
    """删除演示用户的全部学习数据（不删用户本身与公共文章库）。"""
    user = db.query(User).filter(User.email == DEMO_EMAIL).first()
    if user is None:
        return
    uid = user.id

    # 口语对话（消息由外键 ondelete=CASCADE 级联删除）
    db.query(SpeakingConversation).filter(
        SpeakingConversation.user_id == uid
    ).delete(synchronize_session=False)
    # AI 导师对话（消息级联删除）
    db.query(AiTutorConversation).filter(
        AiTutorConversation.user_id == uid
    ).delete(synchronize_session=False)
    # 单词进度 / 设置 / 每日统计 / 阅读历史 / AI 画像
    db.query(UserWordProgress).filter(UserWordProgress.user_id == uid).delete(
        synchronize_session=False
    )
    db.query(UserWordSettings).filter(UserWordSettings.user_id == uid).delete(
        synchronize_session=False
    )
    db.query(UserDailyStats).filter(UserDailyStats.user_id == uid).delete(
        synchronize_session=False
    )
    db.query(ReadingHistory).filter(ReadingHistory.user_id == uid).delete(
        synchronize_session=False
    )
    db.query(UserAiProfile).filter(UserAiProfile.user_id == uid).delete(
        synchronize_session=False
    )
    db.commit()


# 示例外刊文章（仅当文章库不足 3 篇时补建，公共数据）
_SAMPLE_ARTICLES = [
    {
        "title": "The Rise of Artificial Intelligence in Daily Life",
        "difficulty": "考研",
        "topic": "科技",
        "content": (
            "Artificial intelligence has quietly become part of our everyday lives. "
            "From voice assistants to recommendation systems, intelligent algorithms now "
            "shape how we work, learn and communicate.\n\n"
            "In education, adaptive platforms analyze each student's progress and offer "
            "personalized exercises. In healthcare, machine learning models assist doctors "
            "in detecting diseases earlier than ever before.\n\n"
            "However, this transformation also raises questions about privacy and fairness. "
            "Experts argue that society should establish clear rules to ensure these tools "
            "serve everyone equally."
        ),
        "long_sentences": [
            {
                "sentence": "From voice assistants to recommendation systems, intelligent algorithms now shape how we work, learn and communicate.",
                "translation": "从语音助手到推荐系统，智能算法如今正在塑造我们工作、学习和交流的方式。",
                "analysis": "本句主干为 intelligent algorithms now shape...，From...to... 作状语，how 引导宾语从句。",
            }
        ],
        "quiz": [
            {
                "question": "文章主要讨论什么？",
                "options": ["人工智能在日常生活中的应用与影响", "如何开发语音助手", "医疗行业的衰落", "教育的成本问题"],
                "answer": 0,
                "explanation": "全文围绕 AI 在生活各方面的应用及其带来的问题展开。",
            }
        ],
    },
    {
        "title": "Why Reading Still Matters in the Digital Age",
        "difficulty": "四级",
        "topic": "教育",
        "content": (
            "In an age of short videos and instant messages, many people worry that deep "
            "reading is disappearing. Yet researchers find that reading long texts still "
            "builds vocabulary, focus and empathy in ways that fast media cannot.\n\n"
            "Schools are responding by setting aside quiet reading time each day. Students "
            "who read regularly tend to write more clearly and think more critically.\n\n"
            "The goal is not to reject technology, but to balance it. A healthy reading habit "
            "can coexist with digital life, giving the mind a place to slow down."
        ),
        "long_sentences": [
            {
                "sentence": "Yet researchers find that reading long texts still builds vocabulary, focus and empathy in ways that fast media cannot.",
                "translation": "然而研究者发现，阅读长文仍能以短视频所不能的方式积累词汇、专注力与同理心。",
                "analysis": "主干为 researchers find that...，that 引导宾语从句，in ways that... 作方式状语。",
            }
        ],
        "quiz": [
            {
                "question": "作者对数字时代阅读的态度是？",
                "options": ["完全拒绝科技", "阅读应与数字生活平衡共存", "阅读已经过时", "只读短视频字幕"],
                "answer": 1,
                "explanation": "结尾明确表示目标不是拒绝科技，而是取得平衡。",
            }
        ],
    },
    {
        "title": "The Economics of Everyday Choices",
        "difficulty": "六级",
        "topic": "经济",
        "content": (
            "Every purchase we make involves a trade-off. When we choose one product over "
            "another, we give up the benefit the alternative might have offered. Economists "
            "call this opportunity cost.\n\n"
            "Understanding opportunity cost helps people make better decisions. A student "
            "who spends an evening studying rather than working is investing in future "
            "earnings. A company that spends more on research is betting on long-term growth.\n\n"
            "Although the concept seems abstract, it appears in nearly every choice we make."
        ),
        "long_sentences": [
            {
                "sentence": "A student who spends an evening studying rather than working is investing in future earnings.",
                "translation": "一个把整晚用于学习而非打工的学生，其实是在投资于未来的收入。",
                "analysis": "主干为 A student... is investing...，who 引导定语从句修饰 student。",
            }
        ],
        "quiz": [
            {
                "question": "经济学中的「机会成本」指什么？",
                "options": ["商品的实际价格", "做出选择时放弃的其他选项的收益", "利息成本", "运输成本"],
                "answer": 1,
                "explanation": "机会成本即放弃的次优选择的潜在收益。",
            }
        ],
    },
]
