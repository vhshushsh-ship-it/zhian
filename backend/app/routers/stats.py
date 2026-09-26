"""英语模块学习数据聚合统计接口。"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user
from ..models import User
from ..schemas import EnglishStatsResponse
from ..stats_service import compute_english_stats

router = APIRouter(prefix="/english", tags=["english-stats"])


@router.get("/stats", response_model=EnglishStatsResponse)
def get_english_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """返回英语模块聚合学习数据（概览 / 单词 / 口语 / 近 7 天趋势）。"""
    return compute_english_stats(db, current_user.id)
