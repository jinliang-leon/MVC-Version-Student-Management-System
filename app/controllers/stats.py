"""统计分析接口（Controller 层，6 个）

路由前缀：/stats/
本层只做：接收请求 -> 调用 stats_service -> 包装 success() 返回。
所有聚合逻辑已下沉到 app/services/stats_service.py（委托 StatsRepository）。
所有接口统一按权限码鉴权（@require_permission("stats:view")）；函数签名里的 request 供装饰器取 Token 使用。
"""
from typing import Optional

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from app.controllers.deps import get_db
from app.core.decorators import require_permission
from app.services.stats_service import stats_service
from app.schemas.stats import (
    AvgScoreOut,
    ClassCountOut,
    EmploymentRateOut,
    OverviewOut,
    ScoreRankingOut,
    TopSalaryOut,
)
from app.views.response import ApiResponse, success

router = APIRouter(prefix="/stats", tags=["统计分析"])


@router.get(
    "/overview",
    response_model=ApiResponse[OverviewOut],
    summary="总体数据概览",
    description="返回班级数、学生数、教师数、成绩记录数、就业记录数，以及平均分、就业率等汇总指标。",
)
@require_permission("stats:view")
def overview(request: Request, db: Session = Depends(get_db)):
    return success(data=stats_service.overview(db))


@router.get(
    "/class-count",
    response_model=ApiResponse[list[ClassCountOut]],
    summary="各班级学生人数统计",
    description="返回每个班级的名称、年级及学生人数，按人数降序。",
)
@require_permission("stats:view")
def class_count(request: Request, db: Session = Depends(get_db)):
    return success(data=stats_service.class_count(db))


@router.get(
    "/avg-score",
    response_model=ApiResponse[list[AvgScoreOut]],
    summary="平均分统计",
    description="按科目统计平均分，可选按学生ID或班级ID过滤。",
)
@require_permission("stats:view")
def avg_score(
    request: Request,
    student_id: Optional[int] = Query(None, description="按学生ID过滤"),
    class_id: Optional[int] = Query(None, description="按班级ID过滤"),
    subject: Optional[str] = Query(None, description="按科目过滤"),
    db: Session = Depends(get_db),
):
    return success(data=stats_service.avg_score(db, student_id=student_id, class_id=class_id, subject=subject))


@router.get(
    "/employment-rate",
    response_model=ApiResponse[EmploymentRateOut],
    response_model_exclude_unset=True,
    summary="就业率统计",
    description="统计学生总数、已就业人数、就业率，可按班级过滤。",
)
@require_permission("stats:view")
def employment_rate(
    request: Request,
    class_id: Optional[int] = Query(None, description="按班级ID过滤"),
    db: Session = Depends(get_db),
):
    return success(data=stats_service.employment_rate(db, class_id=class_id))


@router.get(
    "/score-ranking",
    response_model=ApiResponse[list[ScoreRankingOut]],
    summary="成绩排行榜",
    description="按分数降序返回成绩排名，可选按科目过滤，可指定返回条数。",
)
@require_permission("stats:view")
def score_ranking(
    request: Request,
    subject: Optional[str] = Query(None, description="按科目过滤"),
    limit: int = Query(10, ge=1, le=100, description="返回条数"),
    db: Session = Depends(get_db),
):
    return success(data=stats_service.score_ranking(db, subject=subject, limit=limit))


@router.get(
    "/top-salary",
    response_model=ApiResponse[list[TopSalaryOut]],
    summary="高薪就业榜",
    description="按薪资降序返回就业记录，可指定条数。",
)
@require_permission("stats:view")
def top_salary(
    request: Request,
    limit: int = Query(10, ge=1, le=100, description="返回条数"),
    db: Session = Depends(get_db),
):
    return success(data=stats_service.top_salary(db, limit=limit))
