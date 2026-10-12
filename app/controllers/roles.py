"""角色管理接口（Controller 层，RBAC）

路由前缀：/roles/
    GET    /roles/                        查询角色列表（含权限）
    GET    /roles/{role_id}               查询单个角色
    POST   /roles/                        新增角色
    PUT    /roles/{role_id}               更新角色
    DELETE /roles/{role_id}               删除角色
    PUT    /roles/{role_id}/permissions   分配角色权限

本层只做：接收请求 -> 调用 role_service -> 序列化 -> 包装 success() 返回。
每个接口按权限码鉴权（@require_permission）；函数签名里的 request 供装饰器取 Token。
"""
from fastapi import APIRouter, Body, Depends, Path, Request, status
from sqlalchemy.orm import Session

from app.controllers.deps import get_db
from app.core.decorators import require_permission
from app.core.exceptions import ForbiddenException
from app.services.role_service import role_service
from app.schemas.rbac import (
    RoleCreate,
    RoleOut,
    RolePermissionAssign,
    RoleUpdate,
)
from app.views.response import ApiResponse, success

router = APIRouter(prefix="/roles", tags=["RBAC-角色"])


@router.get("/", response_model=ApiResponse[list[RoleOut]], summary="查询角色列表")
@require_permission("role:list")
def list_roles(request: Request, db: Session = Depends(get_db)):
    roles = role_service.list_with_permissions(db)
    return success(data=[RoleOut.model_validate(r).model_dump() for r in roles])


@router.get("/{role_id}", response_model=ApiResponse[RoleOut], summary="查询单个角色")
@require_permission("role:read")
def get_role(request: Request, role_id: int = Path(...), db: Session = Depends(get_db)):
    role = role_service.get_with_permissions(db, role_id)
    return success(data=RoleOut.model_validate(role).model_dump())


@router.post(
    "/",
    status_code=status.HTTP_201_CREATED,
    response_model=ApiResponse[RoleOut],
    summary="新增角色",
    description="新增普通角色。系统角色（is_system=True，如 super_admin）仅允许由 seed_rbac.py 初始化脚本创建，接口禁止。",
)
@require_permission("role:create")
def create_role(
    request: Request,
    payload: RoleCreate = Body(...),
    db: Session = Depends(get_db),
):
    # 接口禁止创建系统角色（超级管理员角色），仅 seed_rbac.py 可建
    if payload.is_system:
        raise ForbiddenException("系统角色（is_system=True）仅允许由初始化脚本创建，接口禁止创建")
    role = role_service.create_role(db, payload)
    return success(data=RoleOut.model_validate(role).model_dump(), message="角色创建成功", code=201)


@router.put("/{role_id}", response_model=ApiResponse[RoleOut], summary="更新角色")
@require_permission("role:update")
def update_role(
    request: Request,
    role_id: int = Path(...),
    payload: RoleUpdate = Body(...),
    db: Session = Depends(get_db),
):
    role = role_service.update_role(db, role_id, payload)
    return success(data=RoleOut.model_validate(role).model_dump(), message="角色更新成功")


@router.delete(
    "/{role_id}",
    response_model=ApiResponse[dict[str, int]],
    summary="删除角色",
)
@require_permission("role:delete")
def delete_role(request: Request, role_id: int = Path(...), db: Session = Depends(get_db)):
    role_service.delete_role(db, role_id)
    return success(data={"role_id": role_id}, message="角色删除成功")


@router.put(
    "/{role_id}/permissions",
    response_model=ApiResponse[RoleOut],
    summary="分配角色权限",
)
@require_permission("role:assign-permission")
def assign_permissions(
    request: Request,
    role_id: int = Path(...),
    payload: RolePermissionAssign = Body(...),
    db: Session = Depends(get_db),
):
    role = role_service.assign_permissions(db, role_id, payload.permission_codes)
    return success(data=RoleOut.model_validate(role).model_dump(), message="权限分配成功")
