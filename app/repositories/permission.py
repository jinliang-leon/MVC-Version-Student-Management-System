"""权限仓储（纯数据访问层）

权限由种子脚本维护，接口层只读；这里提供按码查询、幂等创建（种子用）、
按模块分组列举三个方法。
"""
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.repositories.base import RepositoryBase
from app.models.permission import Permission


class PermissionRepository(RepositoryBase[Permission]):

    def __init__(self):
        super().__init__(Permission, pk_field="permission_id")

    def get_by_code(self, db: Session, code: str) -> Optional[Permission]:
        """按权限码查询未删除的权限"""
        stmt = select(Permission).where(
            Permission.code == code, Permission.is_deleted == False  # noqa: E712
        )
        return db.execute(stmt).scalars().first()

    def get_or_create(
        self,
        db: Session,
        *,
        code: str,
        name: str,
        module: str,
        description: str | None = None,
    ) -> Permission:
        """按权限码幂等创建（种子脚本用）：已存在则返回，否则新建"""
        perm = self.get_by_code(db, code)
        if perm is not None:
            return perm
        perm = Permission(code=code, name=name, module=module, description=description)
        db.add(perm)
        db.commit()
        db.refresh(perm)
        return perm

    def list_grouped(self, db: Session) -> dict[str, list[Permission]]:
        """按模块分组返回全部权限，组内按权限ID升序"""
        stmt = (
            select(Permission)
            .where(Permission.is_deleted == False)  # noqa: E712
            .order_by(Permission.module, Permission.permission_id)
        )
        items = list(db.execute(stmt).scalars().all())
        grouped: dict[str, list[Permission]] = {}
        for p in items:
            grouped.setdefault(p.module, []).append(p)
        return grouped


permission_repository = PermissionRepository()
