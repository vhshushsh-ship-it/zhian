from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class SendCodeRequest(BaseModel):
    """发送验证码请求"""

    email: EmailStr


class RegisterRequest(BaseModel):
    """注册请求（邮箱 + 验证码 + 密码）"""

    email: EmailStr
    code: str = Field(..., min_length=6, max_length=6)
    password: str = Field(..., min_length=6, max_length=72)
    confirm_password: str


class LoginRequest(BaseModel):
    """登录请求（邮箱 + 密码）"""

    email: EmailStr
    password: str


class UserResponse(BaseModel):
    """用户信息响应（含角色）"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    username: str | None = None
    role: str
    created_at: datetime


class LoginResponse(BaseModel):
    """登录/注册响应：Token + 用户信息（含角色）"""

    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class AdminUserResponse(BaseModel):
    """管理员视角的用户信息（含状态、封禁、活跃时间）"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    username: str | None = None
    role: str
    status: str
    banned_until: datetime | None = None
    last_active_at: datetime | None = None
    created_at: datetime


class AdminUserListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    users: list[AdminUserResponse]


class BanUserRequest(BaseModel):
    """封禁请求：days 为封禁天数，0 表示永久封禁"""

    days: int


class AdminStatsResponse(BaseModel):
    total_users: int
    online_users: int
    banned_users: int


# ---------- 英语口语练习 ----------

Topic = Literal["daily", "interview", "travel", "campus"]
Level = Literal["beginner", "intermediate", "advanced"]


class ChatMessage(BaseModel):
    """对话中的一条消息（user / assistant）"""

    role: Literal["user", "assistant"]
    content: str


class SpeakingChatRequest(BaseModel):
    """口语对话请求：历史消息 + 话题 + 难度"""

    messages: list[ChatMessage]
    topic: Topic
    level: Level


class SpeakingSuggestion(BaseModel):
    """推荐回复句子（英文 + 中文）"""

    en: str
    zh: str


class SpeakingChatResponse(BaseModel):
    """口语对话响应：AI 英文回复 + 中文翻译 + 推荐句子"""

    ai_reply: str
    translation: str
    suggestions: list[SpeakingSuggestion]
    # 用户上一条消息的中文翻译（用于中栏「翻译」与左栏对话一一对应）
    user_translation: str = ""


class ConversationSummary(BaseModel):
    """对话列表项（不含消息）"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    topic: Topic
    level: Level
    updated_at: datetime


class Message(BaseModel):
    """对话详情中的一条消息"""

    model_config = ConfigDict(from_attributes=True)

    role: Literal["user", "assistant"]
    content: str
    translation: str = ""
    created_at: datetime


class ConversationDetail(BaseModel):
    """对话详情：基本信息 + 全部消息（按时间正序）"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    topic: Topic
    level: Level
    messages: list[Message]


class CreateConversationRequest(BaseModel):
    """新建对话请求：话题 + 难度"""

    topic: Topic
    level: Level


class ConversationIdResponse(BaseModel):
    """新建对话响应：返回对话 id"""

    id: int


class SendMessageRequest(BaseModel):
    """发送消息请求：用户输入的英文"""

    content: str


class SendMessageResponse(BaseModel):
    """发送消息响应：AI 回复 + 中文翻译 + 推荐句子"""

    ai_reply: str
    translation: str
    user_translation: str = ""
    suggestions: list[SpeakingSuggestion]


# ---------- 口语评分 ----------


class ScoreErrorItem(BaseModel):
    """评分中的一处错误分析"""

    type: str = "语法"
    original: str = ""
    issue: str = ""
    fix: str = ""


class SpeakingScoreRequest(BaseModel):
    """口语评分请求：用户句子 + 对话上下文"""

    sentence: str
    context: str = ""


class SpeakingScoreResponse(BaseModel):
    """口语评分响应：总分 + 三项分 + 错误分析 + 优化建议"""

    total: int
    grammar: int
    vocab: int
    fluency: int
    errors: list[ScoreErrorItem]
    suggestion: str = ""


# ---------- 背单词 ----------

Feedback = Literal["known", "vague", "forgotten"]


class WordDefinitionResponse(BaseModel):
    """单词释义"""

    pos: str | None = None
    meaning: str


class WordExampleResponse(BaseModel):
    """单词例句"""

    en: str
    zh: str | None = None


class IntervalPreview(BaseModel):
    """单个反馈档位的间隔预览文案，如「今日」「明日」「4天后」"""

    text: str


class TodayQueuePreviews(BaseModel):
    """三档反馈的间隔预览"""

    known: IntervalPreview
    vague: IntervalPreview
    forgotten: IntervalPreview


class TodayQueueItem(BaseModel):
    """今日复习队列中的一项"""

    id: int
    word: str
    phonetic: str | None = None
    audio_url: str | None = None
    current_strength: float
    is_new: bool
    index: int
    previews: TodayQueuePreviews


class TodayQueueResponse(BaseModel):
    """今日复习队列"""

    total: int
    review_count: int
    new_count: int
    items: list[TodayQueueItem]


class WordDetailResponse(BaseModel):
    """单词详情 + 当前用户学习进度"""

    id: int
    word: str
    phonetic: str | None = None
    audio_url: str | None = None
    definitions: list[WordDefinitionResponse]
    examples: list[WordExampleResponse]
    # 当前用户进度
    current_strength: float
    memory_strength: float
    review_count: int
    known_count: int
    vague_count: int
    forgotten_count: int
    is_mastered: bool


class ReviewRequest(BaseModel):
    """复习反馈请求"""

    feedback: Feedback


class ReviewResponse(BaseModel):
    """复习反馈响应"""

    new_strength: float
    next_review_date: date
    interval_text: str


class WordStatsResponse(BaseModel):
    """背单词学习统计"""

    learned: int
    due_today: int
    learned_today: int
    mastered: int
    known_count: int
    vague_count: int
    forgotten_count: int
    accuracy: float
    streak_days: int


BookKey = Literal["kaoyan", "cet4", "cet6"]


class BookItem(BaseModel):
    """单本词书的统计信息"""

    key: BookKey
    label: str
    total: int
    learned: int
    mastered: int
    familiar: int
    medium: int
    weak: int
    unlearned: int


class WordSettingsResponse(BaseModel):
    """用户背单词设置"""

    current_book: BookKey
    daily_new_goal: int


class SelectBookRequest(BaseModel):
    """切换词书请求"""

    book: BookKey


class UpdateSettingsRequest(BaseModel):
    """更新每日新词量请求"""

    daily_new_goal: int = Field(..., ge=1, le=200)


# ---------- AI 一对一导师 ----------

AiTutorRole = Literal["user", "assistant"]

# 场景感知：前端传入的当前页面标识
AiTutorPage = Literal["words", "speaking", "reading", "english"]


class AiProfileResponse(BaseModel):
    """用户 AI 导师长期画像（弱项/偏好以结构化字段返回）"""

    goal: str | None = None
    exam_date: date | None = None
    weak_points: list[str] = []
    learning_style: str | None = None
    preferences: dict = {}
    ai_notes: str | None = None


class UpdateAiProfileRequest(BaseModel):
    """更新长期画像（缺省字段不修改，显式传 null 表示清空）"""

    goal: str | None = None
    exam_date: date | None = None
    weak_points: list[str] | None = None
    learning_style: str | None = None
    preferences: dict | None = None


class AiTutorConversationSummary(BaseModel):
    """AI 导师对话列表项（不含消息）"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    created_at: datetime


class AiTutorMessageOut(BaseModel):
    """AI 导师对话详情中的一条消息"""

    model_config = ConfigDict(from_attributes=True)

    role: AiTutorRole
    content: str
    created_at: datetime


class AiTutorConversationDetail(BaseModel):
    """AI 导师对话详情：基本信息 + 全部消息（按时间正序）"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    created_at: datetime
    messages: list[AiTutorMessageOut]


class AiTutorSendRequest(BaseModel):
    """发送消息请求：content 用户文本，page 当前页面标识（场景感知）"""

    content: str
    page: AiTutorPage = "english"


class AiTutorSendResponse(BaseModel):
    """发送消息响应：AI 导师回复"""

    ai_reply: str


# ---------- 学习数据统计 ----------


class OverviewStats(BaseModel):
    """概览区：连续天数 / 单词 / 口语 / 阅读 / 完成率等核心指标"""

    streak_days: int
    total_words_learned: int
    total_words_mastered: int
    words_today_due: int
    recognition_rate: float
    speaking_sessions: int
    speaking_total_messages: int
    last_speaking_at: datetime | None = None
    weekly_completion_rate: float
    reading_articles_read: int


class WeakWordItem(BaseModel):
    """薄弱词（按忘记次数降序）"""

    word: str
    forgotten_count: int
    memory_strength: float


class WordsStats(BaseModel):
    """单词学习详情"""

    current_book: str
    daily_goal: int
    weak_words: list[WeakWordItem]


class TopicStatItem(BaseModel):
    """常练话题统计项"""

    topic: str
    count: int


class SpeakingStats(BaseModel):
    """口语练习详情"""

    topics: list[TopicStatItem]


class DailyTrendItem(BaseModel):
    """近 7 天某天的学习量"""

    date: date
    words_reviewed: int
    words_new: int
    speaking_messages: int


class EnglishStatsResponse(BaseModel):
    """英语模块聚合学习数据"""

    overview: OverviewStats
    words: WordsStats
    speaking: SpeakingStats
    weekly_trend: list[DailyTrendItem]


# ---------- 外刊精读 ----------


class ReadingQuizItem(BaseModel):
    """一道阅读理解题"""

    question: str
    options: list[str]
    answer: int
    explanation: str


class ReadingArticleListItem(BaseModel):
    """文章列表项（不含正文，含当前用户是否已读）"""

    id: int
    title: str
    difficulty: str
    topic: str
    word_count: int
    created_at: datetime
    is_read: bool


class ReadingArticleListResponse(BaseModel):
    """文章列表分页响应"""

    total: int
    page: int
    size: int
    items: list[ReadingArticleListItem]


class ReadingHistoryOut(BaseModel):
    """当前用户的阅读记录"""

    read_at: datetime
    quiz_score: float | None = None
    words_collected: int


class ReadingLongSentence(BaseModel):
    """长难句（含预生成的中文翻译与结构分析）"""

    sentence: str
    translation: str = ""
    analysis: str = ""


class ReadingArticleDetail(BaseModel):
    """文章详情（含正文 / 长难句 / 题目）+ 当前用户阅读记录"""

    id: int
    title: str
    content: str
    difficulty: str
    topic: str
    word_count: int
    long_sentences: list[ReadingLongSentence]
    quiz: list[ReadingQuizItem]
    created_at: datetime
    history: ReadingHistoryOut | None = None


class GenerateArticleRequest(BaseModel):
    """管理员生成文章请求"""

    difficulty: str
    topic: str


class QuizSubmitRequest(BaseModel):
    """提交做题答案：用户所选选项索引数组（0 基）"""

    answers: list[int]


class QuizResultItem(BaseModel):
    """单题判分结果"""

    question: str
    your_answer: int | None = None
    correct_answer: int
    is_correct: bool
    explanation: str


class QuizSubmitResponse(BaseModel):
    """做题判分响应"""

    score: float
    correct: int
    total: int
    results: list[QuizResultItem]


class CollectWordRequest(BaseModel):
    """收集生词请求"""

    word: str


class ExplainRequest(BaseModel):
    """选中即译请求：text 选中的词或句子，context 所在完整句子"""

    text: str
    context: str


class ExplainResponse(BaseModel):
    """选中即译响应"""

    translation: str
    analysis: str
