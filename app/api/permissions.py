"""权限管理接口（Controller 层，只读）

路由前缀：/permissions/
    GET /permissions/  查询权限列表（按模块分组）

权限由种子脚本（seed_rbac.py，位于项目根目录）维护，接口层只读，不提供增删改。
"""
from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.core.decorators import require_permission
from app.core.response import ApiResponse, success
from app.crud import crud_permission
from app.schemas.rbac import PermissionOut

router = APIRouter(prefix="/permissions", tags=["RBAC-权限"])


@router.get(
    "/",
    response_model=ApiResponse[dict[str, list[PermissionOut]]],
    summary="查询权限列表（按模块分组）",
    description="返回 {module: [权限, ...]} 的分组结构，模块与权限均按定义顺序排列。",
)
@require_permission("permission:list")
def list_permissions(request: Request, db: Session = Depends(get_db)):
    grouped = crud_permission.list_grouped(db)
    data = {
        module: [PermissionOut.model_validate(p).model_dump() for p in perms]
        for module, perms in grouped.items()
    }
    return success(data=data)
