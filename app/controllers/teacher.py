"""老师接口（Controller 层，6 个）

路由前缀：/teachers/
本层只做：接收请求 -> 调用 teacher_service -> 序列化 -> 包装 success() 返回。
所有接口统一按权限码鉴权（@require_permission）；函数签名里的 request 供装饰器取 Token 使用。
"""
from fastapi import APIRouter, Body, Depends, Path, Query, Request, status
from sqlalchemy.orm import Session

from app.controllers.deps import PaginationParams, get_db
from app.core.decorators import require_permission
from app.services.teacher_service import teacher_service
from app.schemas.common import PageResult
from app.schemas.teacher import TeacherCreate, TeacherOut, TeacherUpdate
from app.views.response import ApiResponse, success
from app.views.serializers import teacher_to_out

router = APIRouter(prefix="/teachers", tags=["教师管理"])


@router.get(
    "/",
    response_model=ApiResponse[PageResult[TeacherOut]],
    summary="查询教师列表",
    description="分页查询所有教师，支持按姓名/职称/科目模糊搜索，可按科目精确过滤。",
)
@require_permission("teacher:list")
def list_teachers(
    request: Request,
    p: PaginationParams = Depends(),
    keyword: str | None = Query(None, description="模糊搜索关键词（姓名/职称/科目）"),
    subject: str | None = Query(None, description="按授课科目过滤"),
    include_deleted: bool = Query(False, description="是否包含已删除的教师"),
    db: Session = Depends(get_db),
):
    result = teacher_service.search(
        db, page=p.page, page_size=p.page_size, keyword=keyword, subject=subject,
        include_deleted=include_deleted,
    )
    result["items"] = [teacher_to_out(i) for i in result["items"]]
    return success(data=result)


@router.get(
    "/{teacher_id}",
    response_model=ApiResponse[TeacherOut],
    summary="查询单个教师",
    description="根据教师ID查询单个教师的详细信息。",
)
@require_permission("teacher:read")
def get_teacher(
    request: Request,
    teacher_id: int = Path(..., description="教师ID"),
    include_deleted: bool = Query(False, description="是否包含已删除的教师"),
    db: Session = Depends(get_db),
):
    obj = teacher_service.get_detail(db, teacher_id, include_deleted=include_deleted)
    return success(data=teacher_to_out(obj))


@router.post(
    "/",
    status_code=status.HTTP_201_CREATED,
    response_model=ApiResponse[TeacherOut],
    summary="新增教师",
    description="创建一个新教师。name 为必填字段。",
)
@require_permission("teacher:create")
def create_teacher(
    request: Request,
    payload: TeacherCreate = Body(...),
    db: Session = Depends(get_db),
):
    obj = teacher_service.create_teacher(db, payload)
    return success(data=teacher_to_out(obj), message="教师创建成功", code=201)


@router.put(
    "/{teacher_id}",
    response_model=ApiResponse[TeacherOut],
    summary="更新教师",
    description="按教师ID更新信息，只需传入需要修改的字段（局部更新）。",
)
@require_permission("teacher:update")
def update_teacher(
    request: Request,
    teacher_id: int = Path(..., description="教师ID"),
    payload: TeacherUpdate = Body(...),
    db: Session = Depends(get_db),
):
    obj = teacher_service.update_teacher(db, teacher_id, payload)
    return success(data=teacher_to_out(obj), message="教师更新成功")


@router.delete(
    "/{teacher_id}",
    response_model=ApiResponse[dict[str, int]],
    summary="删除教师",
    description="逻辑删除教师（仅打删除标记，数据保留）。",
)
@require_permission("teacher:delete")
def delete_teacher(
    request: Request,
    teacher_id: int = Path(..., description="教师ID"),
    db: Session = Depends(get_db),
):
    teacher_service.delete_teacher(db, teacher_id)
    return success(data={"teacher_id": teacher_id}, message="教师删除成功")


@router.post(
    "/{teacher_id}/restore",
    response_model=ApiResponse[TeacherOut],
    summary="恢复已删除的教师",
    description="将逻辑删除的教师恢复为正常状态（回收站功能）。",
)
@require_permission("teacher:restore")
def restore_teacher(
    request: Request,
    teacher_id: int = Path(..., description="教师ID"),
    db: Session = Depends(get_db),
):
    obj = teacher_service.restore_teacher(db, teacher_id)
    return success(data=teacher_to_out(obj), message="教师已恢复")
