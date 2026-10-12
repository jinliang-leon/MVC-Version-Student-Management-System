"""用户管理接口（Controller 层，RBAC）

路由前缀：/users/
    GET  /users/               查询用户列表
    GET  /users/{user_id}      查询单个用户
    PUT  /users/{user_id}/roles  分配/重设用户角色

本层只做：接收请求 -> 调用 crud -> 包装 success() 返回。
每个接口按权限码鉴权（@require_permission）；函数签名里的 request 供装饰器取 Token。
"""
from fastapi import APIRouter, Body, Depends, Path, Query, Request
from sqlalchemy.orm import Session

from app.api.deps import PaginationParams, get_db
from app.core.decorators import require_permission
from app.core.exceptions import NotFoundException
from app.core.response import ApiResponse, success
from app.crud import crud_user
from app.schemas.auth import UserOut, user_to_out
from app.schemas.common import PageResult
from app.schemas.rbac import UserRoleAssign

router = APIRouter(prefix="/users", tags=["RBAC-用户"])


@router.get(
    "/",
    response_model=ApiResponse[PageResult[UserOut]],
    summary="查询用户列表",
    description="分页查询所有用户，支持按用户名模糊搜索。",
)
@require_permission("user:list")
def list_users(
    request: Request,
    p: PaginationParams = Depends(),
    keyword: str | None = Query(None, description="模糊搜索关键词（用户名）"),
    db: Session = Depends(get_db),
):
    result = crud_user.get_multi(
        db,
        page=p.page,
        page_size=p.page_size,
        keyword=keyword,
        keyword_fields=["username"],
    )
    result["items"] = [user_to_out(u).model_dump() for u in result["items"]]
    return success(data=result)


@router.get(
    "/{user_id}",
    response_model=ApiResponse[UserOut],
    summary="查询单个用户",
    description="根据用户ID查询单个用户及其角色。",
)
@require_permission("user:read")
def get_user(
    request: Request,
    user_id: int = Path(..., description="用户ID"),
    db: Session = Depends(get_db),
):
    user = crud_user.get_with_roles(db, user_id)
    if user is None:
        raise NotFoundException("用户不存在或已被删除")
    return success(data=user_to_out(user).model_dump())


@router.put(
    "/{user_id}/roles",
    response_model=ApiResponse[UserOut],
    summary="分配用户角色",
    description="按角色编码整体重设该用户的角色集合。",
)
@require_permission("user:assign-role")
def assign_user_roles(
    request: Request,
    user_id: int = Path(..., description="用户ID"),
    payload: UserRoleAssign = Body(...),
    db: Session = Depends(get_db),
):
    user = crud_user.get_with_roles(db, user_id)
    if user is None:
        raise NotFoundException("用户不存在或已被删除")
    user = crud_user.assign_roles(db, user, payload.role_codes)
    return success(data=user_to_out(user).model_dump(), message="角色分配成功")
