"""用户管理接口（Controller 层，RBAC）

路由前缀：/users/
    GET    /users/                查询用户列表
    GET    /users/{user_id}       查询单个用户
    POST   /users/                新增用户（管理员）
    PUT    /users/{user_id}       更新用户（管理员）
    DELETE /users/{user_id}       删除用户（管理员）
    PUT    /users/{user_id}/roles 分配/重设用户角色

本层只做：接收请求 -> 调用 user_service -> 序列化 -> 包装 success() 返回。
每个接口按权限码鉴权（@require_permission）；被装饰函数签名里都带 request: Request，
供装饰器从 Authorization 头取 Token，并把当前登录用户（request.state.user）作为
operator 透传给 Service，由 Service 执行 super_admin 保护。
"""
from fastapi import APIRouter, Body, Depends, Path, Query, Request, status
from sqlalchemy.orm import Session

from app.controllers.deps import PaginationParams, get_db
from app.core.decorators import require_permission
from app.services.user_service import user_service
from app.schemas.auth import UserCreate, UserOut, UserUpdate
from app.schemas.common import PageResult
from app.schemas.rbac import UserRoleAssign
from app.views.response import ApiResponse, success
from app.views.serializers import user_to_out

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
    result = user_service.get_multi(
        db, page=p.page, page_size=p.page_size, keyword=keyword, keyword_fields=["username"]
    )
    result["items"] = [user_to_out(u) for u in result["items"]]
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
    user = user_service.get_with_roles(db, user_id)
    return success(data=user_to_out(user))


@router.post(
    "/",
    status_code=status.HTTP_201_CREATED,
    response_model=ApiResponse[UserOut],
    summary="新增用户",
    description="管理员新建用户；角色通过 /users/{user_id}/roles 单独分配，本接口不接收角色。",
)
@require_permission("user:create")
def create_user(
    request: Request,
    payload: UserCreate = Body(...),
    db: Session = Depends(get_db),
):
    user = user_service.create_user(db, payload)
    return success(data=user_to_out(user), message="用户创建成功", code=201)


@router.put(
    "/{user_id}",
    response_model=ApiResponse[UserOut],
    summary="更新用户",
    description="管理员局部更新用户（用户名/密码/启用状态）；不修改角色。",
)
@require_permission("user:update")
def update_user(
    request: Request,
    user_id: int = Path(..., description="用户ID"),
    payload: UserUpdate = Body(...),
    db: Session = Depends(get_db),
):
    user = user_service.get_with_roles(db, user_id)
    user = user_service.update_user(db, user, payload, operator=request.state.user)
    return success(data=user_to_out(user), message="用户更新成功")


@router.delete(
    "/{user_id}",
    response_model=ApiResponse[dict[str, int]],
    summary="删除用户",
    description="逻辑删除用户；受 super_admin 保护（非超管不能删超管，且不能删最后一个超管）。",
)
@require_permission("user:delete")
def delete_user(
    request: Request,
    user_id: int = Path(..., description="用户ID"),
    db: Session = Depends(get_db),
):
    user_service.delete_user(db, user_id, operator=request.state.user)
    return success(data={"user_id": user_id}, message="用户删除成功")


@router.put(
    "/{user_id}/roles",
    response_model=ApiResponse[UserOut],
    summary="分配用户角色",
    description="按角色编码整体重设该用户的角色集合。受 super_admin 保护。",
)
@require_permission("user:assign-role")
def assign_user_roles(
    request: Request,
    user_id: int = Path(..., description="用户ID"),
    payload: UserRoleAssign = Body(...),
    db: Session = Depends(get_db),
):
    user = user_service.get_with_roles(db, user_id)
    user = user_service.assign_roles(
        db, user, payload.role_codes, operator=request.state.user
    )
    return success(data=user_to_out(user), message="角色分配成功")
