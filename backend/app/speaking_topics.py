"""英语口语话题目录（单一数据源）。

topic 字段存「具体话题」的中文名（如「打招呼」）；
大类仅用于前端分组展示，以及生成 AI 提示词时提供上下文。

本模块被 english_speaking / stats_service / ai_tutor_service / ai_tutor 路由共用，
避免各文件各自维护一份话题映射导致不一致。
"""

# 顺序即前端展示顺序
SPEAKING_TOPIC_GROUPS: list[dict] = [
    {"key": "daily", "label": "日常对话", "topics": ["打招呼", "天气", "兴趣爱好", "食物", "购物", "周末计划"]},
    {"key": "interview", "label": "面试求职", "topics": ["自我介绍", "优缺点", "职业规划", "团队合作", "失败经历", "薪资期望"]},
    {"key": "travel", "label": "旅游出行", "topics": ["机场值机", "酒店入住", "问路点餐", "景点游览", "购物砍价", "迷路求助"]},
    {"key": "campus", "label": "校园生活", "topics": ["选课考试", "宿舍生活", "社团活动", "图书馆", "毕业规划"]},
    {"key": "work", "label": "工作办公", "topics": ["邮件沟通", "会议讨论", "项目汇报", "同事协作", "远程办公"]},
    {"key": "tech", "label": "科技AI", "topics": ["人工智能", "手机APP", "社交媒体", "网购", "未来科技"]},
    {"key": "culture", "label": "文化节日", "topics": ["春节", "中秋", "圣诞节", "生日礼物", "餐桌礼仪"]},
    {"key": "health", "label": "健康运动", "topics": ["健身", "饮食", "睡眠", "跑步", "心理健康"]},
    {"key": "environment", "label": "环境自然", "topics": ["气候变化", "垃圾分类", "动物保护", "城市污染"]},
    {"key": "society", "label": "社会热点", "topics": ["教育公平", "城市化", "老龄化", "远程办公趋势"]},
]

# 具体话题 → 所属大类中文名
TOPIC_TO_GROUP: dict[str, str] = {
    t: g["label"] for g in SPEAKING_TOPIC_GROUPS for t in g["topics"]
}

# 大类 key → 大类中文名（用于「还没练过哪些大类」）
GROUP_LABELS: dict[str, str] = {g["key"]: g["label"] for g in SPEAKING_TOPIC_GROUPS}

# 旧话题 key → 展示名（兼容历史对话数据）
LEGACY_TOPIC_LABELS: dict[str, str] = {
    "daily": "日常对话",
    "interview": "面试",
    "travel": "旅游",
    "campus": "校园",
}


def topic_group_label(topic: str) -> str:
    """具体话题所属大类名；未知 / 旧值返回空串。"""
    return TOPIC_TO_GROUP.get(topic, "")


def topic_display(topic: str) -> str:
    """话题展示名：具体话题返回自身；旧 key 映射为旧中文名；未知原样返回。"""
    return LEGACY_TOPIC_LABELS.get(topic, topic)


def topic_display_with_group(topic: str) -> str:
    """返回「具体话题（大类）」形式；无大类时仅返回话题本身。"""
    name = topic_display(topic)
    group = topic_group_label(topic)
    return f"{name}（{group}）" if group else name
