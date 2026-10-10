"""班级接口（Controller 层，6 个）

路由前缀：/classes/
    GET    /classes/            查询班级列表（分页/搜索）
    GET    /classes/{class_id}  查询单个班级
    POST   /classes/            新增班级
    PUT    /classes/{class_id}  更新班级
    DELETE /classes/{class_id}  删除班级（逻辑删除，有学生则拒绝）
    POST   /classes/{class_id}/restore  恢复已删除班级（回收站）

本层只做：接收请求 -> 调用 crud -> 包装 success() 返回。
"""
from fastapi import APIRouter, Body, Depends, Path, Query, status
from sqlalchemy.orm import Session

from app.api.deps import PaginationParams, get_db
from app.core.response import ApiResponse, success
from app.crud import crud_class
from app.schemas.class_ import ClassCreate, ClassOut, ClassUpdate
from app.schemas.common import PageResult

router = APIRouter(prefix="/classes", tags=["班级管理"])


@router.get(
    "/",
    response_model=ApiResponse[PageResult[ClassOut]],
    summary="查询班级列表",
    description="分页查询所有班级，支持按班级名称/年级/备注模糊搜索。返回结构含 total/page/page_size/total_pages/items。",
)
def list_classes(
    p: PaginationParams = Depends(),
    keyword: str | None = Query(None, description="模糊搜索关键词（班级名称/年级/备注）"),
    include_deleted: bool = Query(False, description="是否包含已删除的班级"),
    db: Session = Depends(get_db),
):
    return success(
        data=crud_class.search(
            db,
            page=p.page,
            page_size=p.page_size,
            keyword=keyword,
            include_deleted=include_deleted,
        )
    )


@router.get(
    "/{class_id}",
    response_model=ApiResponse[ClassOut],
    summary="查询单个班级",
    description="根据班级ID查询单个班级的详细信息。",
)
def get_class(
    class_id: int = Path(..., description="班级ID"),
    include_deleted: bool = Query(False, description="是否包含已删除的班级"),
    db: Session = Depends(get_db),
):
    return success(
        data=crud_class.get_detail(db, class_id, include_deleted=include_deleted)
    )


@router.post(
    "/",
    status_code=status.HTTP_201_CREATED,
    response_model=ApiResponse[ClassOut],
    summary="新增班级",
    description="创建一个新的班级。class_name 为必填字段。",
)
def create_class(
    payload: ClassCreate = Body(...),
    db: Session = Depends(get_db),
):
    return success(
        data=crud_class.create_class(db, payload), message="班级创建成功", code=201
    )


@router.put(
    "/{class_id}",
    response_model=ApiResponse[ClassOut],
    summary="更新班级",
    description="按班级ID更新班级信息，只需传入需要修改的字段（局部更新）。",
)
def update_class(
    class_id: int = Path(..., description="班级ID"),
    payload: ClassUpdate = Body(...),
    db: Session = Depends(get_db),
):
    return success(
        data=crud_class.update_class(db, class_id, payload), message="班级更新成功"
    )


@router.delete(
    "/{class_id}",
    response_model=ApiResponse[dict[str, int]],
    summary="删除班级",
    description="逻辑删除班级（仅打删除标记，数据保留）。若班级下仍有学生，将拒绝删除并返回提示。",
)
def delete_class(
    class_id: int = Path(..., description="班级ID"),
    db: Session = Depends(get_db),
):
    crud_class.delete_class(db, class_id)
    return success(data={"class_id": class_id}, message="班级删除成功")


@router.post(
    "/{class_id}/restore",
    response_model=ApiResponse[ClassOut],
    summary="恢复已删除的班级",
    description="将逻辑删除的班级恢复为正常状态（回收站功能）。",
)
def restore_class(
    class_id: int = Path(..., description="班级ID"),
    db: Session = Depends(get_db),
):
    return success(
        data=crud_class.restore_class(db, class_id), message="班级已恢复"
    )
