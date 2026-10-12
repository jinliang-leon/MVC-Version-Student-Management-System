"""成绩接口（Controller 层，6 个）

路由前缀：/scores/
本层只做：接收请求 -> 调用 score_service -> 序列化 -> 包装 success() 返回。
所有接口统一按权限码鉴权（@require_permission）；函数签名里的 request 供装饰器取 Token 使用。
"""
from fastapi import APIRouter, Body, Depends, Path, Query, Request, status
from sqlalchemy.orm import Session

from app.controllers.deps import PaginationParams, get_db
from app.core.decorators import require_permission
from app.services.score_service import score_service
from app.schemas.common import PageResult
from app.schemas.score import ScoreCreate, ScoreOut, ScoreUpdate
from app.views.response import ApiResponse, success
from app.views.serializers import score_to_out

router = APIRouter(prefix="/scores", tags=["成绩管理"])


@router.get(
    "/",
    response_model=ApiResponse[PageResult[ScoreOut]],
    summary="查询成绩列表",
    description="分页查询所有成绩，支持按科目模糊搜索，可按学生ID/教师ID/科目精确过滤。结果含学生姓名与教师姓名。",
)
@require_permission("score:list")
def list_scores(
    request: Request,
    p: PaginationParams = Depends(),
    keyword: str | None = Query(None, description="模糊搜索关键词（考试科目）"),
    student_id: int | None = Query(None, description="按学生ID过滤"),
    teacher_id: int | None = Query(None, description="按教师ID过滤"),
    subject: str | None = Query(None, description="按科目精确过滤"),
    include_deleted: bool = Query(False, description="是否包含已删除的成绩"),
    db: Session = Depends(get_db),
):
    result = score_service.search(
        db,
        page=p.page,
        page_size=p.page_size,
        keyword=keyword,
        student_id=student_id,
        teacher_id=teacher_id,
        subject=subject,
        include_deleted=include_deleted,
    )
    result["items"] = [score_to_out(i) for i in result["items"]]
    return success(data=result)


@router.get(
    "/{score_id}",
    response_model=ApiResponse[ScoreOut],
    summary="查询单条成绩",
    description="根据成绩ID查询单条成绩详情，含学生姓名与教师姓名。",
)
@require_permission("score:read")
def get_score(
    request: Request,
    score_id: int = Path(..., description="成绩ID"),
    include_deleted: bool = Query(False, description="是否包含已删除的成绩"),
    db: Session = Depends(get_db),
):
    obj = score_service.get_detail(db, score_id, include_deleted=include_deleted)
    return success(data=score_to_out(obj))


@router.post(
    "/",
    status_code=status.HTTP_201_CREATED,
    response_model=ApiResponse[ScoreOut],
    summary="新增成绩",
    description="创建一条成绩记录。student_id、teacher_id、subject、score 均为必填，且学生与教师必须存在。",
)
@require_permission("score:create")
def create_score(
    request: Request,
    payload: ScoreCreate = Body(...),
    db: Session = Depends(get_db),
):
    obj = score_service.create_score(db, payload)
    return success(data=score_to_out(obj), message="成绩创建成功", code=201)


@router.put(
    "/{score_id}",
    response_model=ApiResponse[ScoreOut],
    summary="更新成绩",
    description="按成绩ID更新，只需传入需要修改的字段（局部更新）。",
)
@require_permission("score:update")
def update_score(
    request: Request,
    score_id: int = Path(..., description="成绩ID"),
    payload: ScoreUpdate = Body(...),
    db: Session = Depends(get_db),
):
    obj = score_service.update_score(db, score_id, payload)
    return success(data=score_to_out(obj), message="成绩更新成功")


@router.delete(
    "/{score_id}",
    response_model=ApiResponse[dict[str, int]],
    summary="删除成绩",
    description="逻辑删除成绩（仅打删除标记，数据保留）。",
)
@require_permission("score:delete")
def delete_score(
    request: Request,
    score_id: int = Path(..., description="成绩ID"),
    db: Session = Depends(get_db),
):
    score_service.delete_score(db, score_id)
    return success(data={"score_id": score_id}, message="成绩删除成功")


@router.post(
    "/{score_id}/restore",
    response_model=ApiResponse[ScoreOut],
    summary="恢复已删除的成绩",
    description="将逻辑删除的成绩恢复为正常状态（回收站功能）。",
)
@require_permission("score:restore")
def restore_score(
    request: Request,
    score_id: int = Path(..., description="成绩ID"),
    db: Session = Depends(get_db),
):
    obj = score_service.restore_score(db, score_id)
    return success(data=score_to_out(obj), message="成绩已恢复")
