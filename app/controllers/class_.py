"""班级接口（Controller 层，6 个）

路由前缀：/classes/
    GET    /classes/            查询班级列表（分页/搜索）
    GET    /classes/{class_id}  查询单个班级
    POST   /classes/            新增班级
    PUT    /classes/{class_id}  更新班级
    DELETE /classes/{class_id}  删除班级（逻辑删除，有学生则拒绝）
    POST   /classes/{class_id}/restore  恢复已删除班级（回收站）

本层只做：接收请求 -> 调用 class_service -> 序列化 -> 包装 success() 返回。
所有接口统一按权限码鉴权（@require_permission）；函数签名里的 request 供装饰器取 Token 使用。
"""
from fastapi import APIRouter, Body, Depends, Path, Query, Request, status
from sqlalchemy.orm import Session

from app.controllers.deps import PaginationParams, get_db
from app.core.decorators import require_permission
from app.services.class_service import class_service
from app.schemas.class_ import ClassCreate, ClassOut, ClassUpdate
from app.schemas.common import PageResult
from app.views.response import ApiResponse, success
from app.views.serializers import class_to_out

router = APIRouter(prefix="/classes", tags=["班级管理"])


@router.get(
    "/",
    response_model=ApiResponse[PageResult[ClassOut]],
    summary="查询班级列表",
    description="分页查询所有班级，支持按班级名称/年级/备注模糊搜索。",
)
@require_permission("class:list")
def list_classes(
    request: Request,
    p: PaginationParams = Depends(),
    keyword: str | None = Query(None, description="模糊搜索关键词（班级名称/年级/备注）"),
    include_deleted: bool = Query(False, description="是否包含已删除的班级"),
    db: Session = Depends(get_db),
):
    result = class_service.search(
        db, page=p.page, page_size=p.page_size, keyword=keyword, include_deleted=include_deleted
    )
    result["items"] = [class_to_out(i) for i in result["items"]]
    return success(data=result)


@router.get(
    "/{class_id}",
    response_model=ApiResponse[ClassOut],
    summary="查询单个班级",
    description="根据班级ID查询单个班级的详细信息。",
)
@require_permission("class:read")
def get_class(
    request: Request,
    class_id: int = Path(..., description="班级ID"),
    include_deleted: bool = Query(False, description="是否包含已删除的班级"),
    db: Session = Depends(get_db),
):
    obj = class_service.get_detail(db, class_id, include_deleted=include_deleted)
    return success(data=class_to_out(obj))


@router.post(
    "/",
    status_code=status.HTTP_201_CREATED,
    response_model=ApiResponse[ClassOut],
    summary="新增班级",
    description="创建一个新的班级。class_name 为必填字段。",
)
@require_permission("class:create")
def create_class(
    request: Request,
    payload: ClassCreate = Body(...),
    db: Session = Depends(get_db),
):
    obj = class_service.create_class(db, payload)
    return success(data=class_to_out(obj), message="班级创建成功", code=201)


@router.put(
    "/{class_id}",
    response_model=ApiResponse[ClassOut],
    summary="更新班级",
    description="按班级ID更新班级信息，只需传入需要修改的字段（局部更新）。",
)
@require_permission("class:update")
def update_class(
    request: Request,
    class_id: int = Path(..., description="班级ID"),
    payload: ClassUpdate = Body(...),
    db: Session = Depends(get_db),
):
    obj = class_service.update_class(db, class_id, payload)
    return success(data=class_to_out(obj), message="班级更新成功")


@router.delete(
    "/{class_id}",
    response_model=ApiResponse[dict[str, int]],
    summary="删除班级",
    description="逻辑删除班级（仅打删除标记，数据保留）。若班级下仍有学生，将拒绝删除并返回提示。",
)
@require_permission("class:delete")
def delete_class(
    request: Request,
    class_id: int = Path(..., description="班级ID"),
    db: Session = Depends(get_db),
):
    class_service.delete_class(db, class_id)
    return success(data={"class_id": class_id}, message="班级删除成功")


@router.post(
    "/{class_id}/restore",
    response_model=ApiResponse[ClassOut],
    summary="恢复已删除的班级",
    description="将逻辑删除的班级恢复为正常状态（回收站功能）。",
)
@require_permission("class:restore")
def restore_class(
    request: Request,
    class_id: int = Path(..., description="班级ID"),
    db: Session = Depends(get_db),
):
    obj = class_service.restore_class(db, class_id)
    return success(data=class_to_out(obj), message="班级已恢复")
