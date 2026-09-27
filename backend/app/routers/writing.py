"""英语写作练习：AI 批改作文 + 写作历史。

- 提交作文（/submit）：保存到 writing_submissions，调用 DeepSeek 批改，
  把总分与结构化反馈写回，返回完整批改结果；
- 历史列表（/history）：返回当前用户最近的写作记录；
- 单篇详情（/{id}）：返回作文内容 + 批改结果。
"""

import json

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user
from ..models import User, WritingSubmission
from ..schemas import (
    WritingDetailResponse,
    WritingErrorItem,
    WritingFeedback,
    WritingHistoryItem,
    WritingSubmitRequest,
    WritingSubmitResponse,
)
from .english_speaking import call_deepseek

router = APIRouter(prefix="/writing", tags=["writing"])

# 三项分数满分：语法 40 / 结构 30 / 用词 30
SCORE_MAX = {"grammar_score": 40, "structure_score": 30, "vocab_score": 30}

# 分类 key → 显示名（用于 prompt）
CATEGORY_NAMES = {"考研": "考研作文", "四六级": "四六级", "日常": "日常邮件"}

# 难度 key → 显示名（与前端一致）
DIFFICULTY_NAMES = {"初级": "初级", "中级": "中级", "高级": "高级"}


def build_writing_prompt(topic: str, category: str, difficulty: str, content: str) -> str:
    """构建写作批改系统提示词：扮演英语写作老师，逐句标注错误并给分。"""
    category_name = CATEGORY_NAMES.get(category, category)
    difficulty_name = DIFFICULTY_NAMES.get(difficulty, difficulty)
    return (
        "你是一名严格的英语写作老师，请批改学生的英语作文，并用中文给出分析。\n\n"
        f"作文题目：{topic}\n"
        f"作文分类：{category_name}\n"
        f"难度：{difficulty_name}\n"
        f"学生作文：\n{content}\n\n"
        "评分要求：\n"
        "1. grammar_score 满分 40 分，考察语法、时态、主谓一致、拼写、标点。\n"
        "2. structure_score 满分 30 分，考察文章结构、逻辑衔接、段落组织。\n"
        "3. vocab_score 满分 30 分，考察词汇丰富度、搭配是否地道。\n"
        "4. total 必须等于 grammar_score + structure_score + vocab_score 三项之和。\n"
        "5. errors 逐句列出作文中的具体错误：sentence 为错误原句（英文），"
        "error 为错误说明（中文），fix 为修改建议（英文）；没有错误时 errors 返回空数组。\n"
        "6. suggestions 用中文给出整体改进建议。\n"
        "7. sample 给出一篇参考范文（英文）。\n\n"
        "你必须只输出一个 JSON 对象，不要输出任何多余文字或代码块标记，格式如下：\n"
        '{"total": 82, "grammar_score": 28, "structure_score": 27, "vocab_score": 27, '
        '"errors": [{"sentence": "I very like it", "error": "very不能直接修饰动词", '
        '"fix": "I like it very much"}], '
        '"suggestions": "开头可以更扣题，第二段缺少衔接词", "sample": "参考范文..."}'
    )


def _clamp_score(value, max_val: int) -> int:
    """把模型返回的分值安全转成 0..max_val 内的整数，异常时给 0。"""
    try:
        n = int(float(value))
    except (TypeError, ValueError):
        n = 0
    return max(0, min(n, max_val))


def _feedback_from_dict(data: dict) -> WritingFeedback:
    """从字典解析出结构化批改反馈（AI 文本与落库 JSON 共用）。"""
    grammar = _clamp_score(data.get("grammar_score"), SCORE_MAX["grammar_score"])
    structure = _clamp_score(data.get("structure_score"), SCORE_MAX["structure_score"])
    vocab = _clamp_score(data.get("vocab_score"), SCORE_MAX["vocab_score"])

    errors: list[WritingErrorItem] = []
    raw_errors = data.get("errors")
    if isinstance(raw_errors, list):
        for e in raw_errors:
            if isinstance(e, dict):
                errors.append(
                    WritingErrorItem(
                        sentence=str(e.get("sentence") or "").strip(),
                        error=str(e.get("error") or "").strip(),
                        fix=str(e.get("fix") or "").strip(),
                    )
                )

    return WritingFeedback(
        grammar_score=grammar,
        structure_score=structure,
        vocab_score=vocab,
        errors=errors,
        suggestions=str(data.get("suggestions") or "").strip(),
        sample=str(data.get("sample") or "").strip(),
    )


def _parse_feedback(content: str) -> WritingFeedback:
    """解析 AI 返回的 JSON 批改结果；失败抛出 500。"""
    try:
        data = json.loads(content)
    except (json.JSONDecodeError, AttributeError, TypeError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="AI 批改失败，请重试",
        )
    if not isinstance(data, dict):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="AI 批改失败，请重试",
        )
    return _feedback_from_dict(data)


def _feedback_from_json(raw: str | None) -> WritingFeedback:
    """从落库的 feedback_json 解析出结构化反馈（历史 / 详情复用）。"""
    if not raw:
        return WritingFeedback()
    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return WritingFeedback()
    if not isinstance(data, dict):
        return WritingFeedback()
    return _feedback_from_dict(data)


@router.post(
    "/submit", response_model=WritingSubmitResponse, status_code=status.HTTP_201_CREATED
)
def submit_writing(
    payload: WritingSubmitRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """提交作文：调用 AI 批改，把总分与反馈一起落库，返回完整批改结果。"""
    topic = payload.topic.strip()
    content = payload.content.strip()
    if not topic:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="作文题目不能为空"
        )
    if not content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="作文内容不能为空"
        )

    messages = [
        {
            "role": "system",
            "content": build_writing_prompt(
                topic, payload.category.strip(), payload.difficulty.strip(), content
            ),
        },
        {"role": "user", "content": content},
    ]
    raw = call_deepseek(messages)
    feedback = _parse_feedback(raw)
    total = feedback.grammar_score + feedback.structure_score + feedback.vocab_score

    submission = WritingSubmission(
        user_id=current_user.id,
        topic=topic,
        category=payload.category.strip(),
        difficulty=payload.difficulty.strip(),
        content=content,
        score=total,
        feedback_json=json.dumps(
            {
                "grammar_score": feedback.grammar_score,
                "structure_score": feedback.structure_score,
                "vocab_score": feedback.vocab_score,
                "errors": [e.model_dump() for e in feedback.errors],
                "suggestions": feedback.suggestions,
                "sample": feedback.sample,
            },
            ensure_ascii=False,
        ),
    )
    db.add(submission)
    db.commit()
    db.refresh(submission)

    return WritingSubmitResponse(
        id=submission.id,
        topic=submission.topic,
        category=submission.category,
        difficulty=submission.difficulty,
        content=submission.content,
        score=submission.score,
        feedback=feedback,
        created_at=submission.created_at,
    )


@router.get("/history", response_model=list[WritingHistoryItem])
def writing_history(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """返回当前用户最近的写作记录（题目 + 分数 + 时间），最多 50 条。"""
    subs = (
        db.query(WritingSubmission)
        .filter(WritingSubmission.user_id == current_user.id)
        .order_by(WritingSubmission.created_at.desc(), WritingSubmission.id.desc())
        .limit(50)
        .all()
    )
    return [
        WritingHistoryItem(
            id=s.id,
            topic=s.topic,
            category=s.category,
            difficulty=s.difficulty,
            score=s.score,
            created_at=s.created_at,
        )
        for s in subs
    ]


@router.get("/{submission_id}", response_model=WritingDetailResponse)
def get_submission(
    submission_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """返回单条写作详情（内容 + 批改结果）。"""
    sub = db.get(WritingSubmission, submission_id)
    if sub is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="写作记录不存在"
        )
    if sub.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="无权访问该写作记录"
        )
    return WritingDetailResponse(
        id=sub.id,
        topic=sub.topic,
        category=sub.category,
        difficulty=sub.difficulty,
        content=sub.content,
        score=sub.score,
        feedback=_feedback_from_json(sub.feedback_json),
        created_at=sub.created_at,
    )
