"""就业接口（Controller 层，6 个）

路由前缀：/employments/

本层只做：接收请求 -> 调用 crud -> 包装 success() 返回。
"""
from fastapi import APIRouter, Body, Depends, Path, Query, status
from sqlalchemy.orm import Session

from app.api.deps import PaginationParams, get_db
from app.core.response import ApiResponse, success
from app.crud import crud_employment
from app.schemas.common import PageResult
from app.schemas.employment import (
    EmploymentCreate,
    EmploymentOut,
    EmploymentUpdate,
)

router = APIRouter(prefix="/employments", tags=["就业管理"])


@router.get(
    "/",
    response_model=ApiResponse[PageResult[EmploymentOut]],
    summary="查询就业记录列表",
    description="分页查询所有就业记录，支持按公司/岗位模糊搜索，可按学生ID过滤。结果含学生姓名。",
)
def list_employments(
    p: PaginationParams = Depends(),
    keyword: str | None = Query(None, description="模糊搜索关键词（公司/岗位）"),
    student_id: int | None = Query(None, description="按学生ID过滤"),
    company: str | None = Query(None, description="按公司名称精确过滤"),
    include_deleted: bool = Query(False, description="是否包含已删除的记录"),
    db: Session = Depends(get_db),
):
    return success(
        data=crud_employment.search(
            db,
            page=p.page,
            page_size=p.page_size,
            keyword=keyword,
            student_id=student_id,
            company=company,
            include_deleted=include_deleted,
        )
    )


@router.get(
    "/{employment_id}",
    response_model=ApiResponse[EmploymentOut],
    summary="查询单条就业记录",
    description="根据就业记录ID查询详情，含学生姓名。",
)
def get_employment(
    employment_id: int = Path(..., description="就业记录ID"),
    include_deleted: bool = Query(False, description="是否包含已删除的记录"),
    db: Session = Depends(get_db),
):
    return success(
        data=crud_employment.get_detail(
            db, employment_id, include_deleted=include_deleted
        )
    )


@router.post(
    "/",
    status_code=status.HTTP_201_CREATED,
    response_model=ApiResponse[EmploymentOut],
    summary="新增就业记录",
    description="创建一条就业记录。student_id 与 company 为必填，学生必须存在。",
)
def create_employment(
    payload: EmploymentCreate = Body(...),
    db: Session = Depends(get_db),
):
    return success(
        data=crud_employment.create_employment(db, payload),
        message="就业记录创建成功",
        code=201,
    )


@router.put(
    "/{employment_id}",
    response_model=ApiResponse[EmploymentOut],
    summary="更新就业记录",
    description="按就业记录ID更新，只需传入需要修改的字段（局部更新）。",
)
def update_employment(
    employment_id: int = Path(..., description="就业记录ID"),
    payload: EmploymentUpdate = Body(...),
    db: Session = Depends(get_db),
):
    return success(
        data=crud_employment.update_employment(db, employment_id, payload),
        message="就业记录更新成功",
    )


@router.delete(
    "/{employment_id}",
    response_model=ApiResponse[dict[str, int]],
    summary="删除就业记录",
    description="逻辑删除就业记录（仅打删除标记，数据保留）。",
)
def delete_employment(
    employment_id: int = Path(..., description="就业记录ID"),
    db: Session = Depends(get_db),
):
    crud_employment.delete_employment(db, employment_id)
    return success(data={"employment_id": employment_id}, message="就业记录删除成功")


@router.post(
    "/{employment_id}/restore",
    response_model=ApiResponse[EmploymentOut],
    summary="恢复已删除的就业记录",
    description="将逻辑删除的就业记录恢复为正常状态（回收站功能）。",
)
def restore_employment(
    employment_id: int = Path(..., description="就业记录ID"),
    db: Session = Depends(get_db),
):
    return success(
        data=crud_employment.restore_employment(db, employment_id),
        message="就业记录已恢复",
    )
