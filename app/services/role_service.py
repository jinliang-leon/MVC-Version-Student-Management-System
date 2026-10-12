"""角色业务服务

承载角色域业务规则：
    - 接口禁止创建系统角色（is_system=True，超级管理员角色仅由 seed_rbac.py 创建）
    - 删除保护：系统角色（is_system）不可删；已分配给用户的角色不可删
"""
from typing import Optional

from sqlalchemy.orm import Session

from app.core.exceptions import ConflictException, ForbiddenException
from app.repositories.role import role_repository


class RoleService:
    def list_with_permissions(self, db: Session) -> list:
        return role_repository.list_with_permissions(db)

    def get_with_permissions(self, db: Session, role_id: int):
        return role_repository.get_with_permissions(db, role_id)

    def create_role(self, db: Session, payload) -> "object":
        """新增角色：接口禁止创建系统角色"""
        if payload.is_system:
            raise ForbiddenException(
                "系统角色（is_system=True）仅允许由初始化脚本创建，接口禁止创建"
            )
        return role_repository.create_role(db, payload)

    def update_role(self, db: Session, role_id: int, payload) -> "object":
        return role_repository.update_role(db, role_id, payload)

    def assign_permissions(self, db: Session, role_id: int, codes: list[str]) -> "object":
        return role_repository.assign_permissions(db, role_id, codes)

    def delete_role(self, db: Session, role_id: int) -> "object":
        """删除角色：系统角色或已被用户引用的角色拒绝删除"""
        role = role_repository.get_or_404(db, role_id)
        if role.is_system:
            raise ConflictException("系统角色不可删除", code=409)
        in_use = role_repository.count_users(db, role_id)
        if in_use > 0:
            raise ConflictException("该角色已分配给用户，请先解除分配", code=409)
        return role_repository.soft_delete(db, role)


role_service = RoleService()
