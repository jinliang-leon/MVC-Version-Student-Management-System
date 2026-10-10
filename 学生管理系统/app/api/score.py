"""成绩接口（Controller 层，6 个）

路由前缀：/scores/

本层只做：接收请求 -> 调用 crud -> 包装 success() 返回。
"""
from fastapi import APIRouter, Body, Depends, Path, Query, status
from sqlalchemy.orm import Session

from app.api.deps import PaginationParams, get_db
from app.core.response import ApiResponse, success
from app.crud import crud_score
from app.schemas.common import PageResult
from app.schemas.score import ScoreCreate, ScoreOut, ScoreUpdate

router = APIRouter(prefix="/scores", tags=["成绩管理"])


@router.get(
    "/",
    response_model=ApiResponse[PageResult[ScoreOut]],
    summary="查询成绩列表",
    description="分页查询所有成绩，支持按科目模糊搜索，可按学生ID/教师ID/科目精确过滤。结果含学生姓名与教师姓名。",
)
def list_scores(
    p: PaginationParams = Depends(),
    keyword: str | None = Query(None, description="模糊搜索关键词（考试科目）"),
    student_id: int | None = Query(None, description="按学生ID过滤"),
    teacher_id: int | None = Query(None, description="按教师ID过滤"),
    subject: str | None = Query(None, description="按科目精确过滤"),
    include_deleted: bool = Query(False, description="是否包含已删除的成绩"),
    db: Session = Depends(get_db),
):
    return success(
        data=crud_score.search(
            db,
            page=p.page,
            page_size=p.page_size,
            keyword=keyword,
            student_id=student_id,
            teacher_id=teacher_id,
            subject=subject,
            include_deleted=include_deleted,
        )
    )


@router.get(
    "/{score_id}",
    response_model=ApiResponse[ScoreOut],
    summary="查询单条成绩",
    description="根据成绩ID查询单条成绩详情，含学生姓名与教师姓名。",
)
def get_score(
    score_id: int = Path(..., description="成绩ID"),
    include_deleted: bool = Query(False, description="是否包含已删除的成绩"),
    db: Session = Depends(get_db),
):
    return success(
        data=crud_score.get_detail(db, score_id, include_deleted=include_deleted)
    )


@router.post(
    "/",
    status_code=status.HTTP_201_CREATED,
    response_model=ApiResponse[ScoreOut],
    summary="新增成绩",
    description="创建一条成绩记录。student_id、teacher_id、subject、score 均为必填，且学生与教师必须存在。",
)
def create_score(
    payload: ScoreCreate = Body(...),
    db: Session = Depends(get_db),
):
    return success(
        data=crud_score.create_score(db, payload), message="成绩创建成功", code=201
    )


@router.put(
    "/{score_id}",
    response_model=ApiResponse[ScoreOut],
    summary="更新成绩",
    description="按成绩ID更新，只需传入需要修改的字段（局部更新）。",
)
def update_score(
    score_id: int = Path(..., description="成绩ID"),
    payload: ScoreUpdate = Body(...),
    db: Session = Depends(get_db),
):
    return success(
        data=crud_score.update_score(db, score_id, payload), message="成绩更新成功"
    )


@router.delete(
    "/{score_id}",
    response_model=ApiResponse[dict[str, int]],
    summary="删除成绩",
    description="逻辑删除成绩（仅打删除标记，数据保留）。",
)
def delete_score(
    score_id: int = Path(..., description="成绩ID"),
    db: Session = Depends(get_db),
):
    crud_score.delete_score(db, score_id)
    return success(data={"score_id": score_id}, message="成绩删除成功")


@router.post(
    "/{score_id}/restore",
    response_model=ApiResponse[ScoreOut],
    summary="恢复已删除的成绩",
    description="将逻辑删除的成绩恢复为正常状态（回收站功能）。",
)
def restore_score(
    score_id: int = Path(..., description="成绩ID"),
    db: Session = Depends(get_db),
):
    return success(
        data=crud_score.restore_score(db, score_id), message="成绩已恢复"
    )
