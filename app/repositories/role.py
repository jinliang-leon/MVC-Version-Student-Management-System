"""角色仓储（纯数据访问层）

仅负责与 role / permission 表相关的数据库读写：
    - 按角色码 / 主键查询角色（预加载权限）
    - 解析权限码为权限实体（不存在的码抛 404）
    - 创建 / 更新角色、分配角色权限、逻辑删除角色

业务规则（禁止创建系统角色、禁止删除系统角色或已分配角色）在
app/services/role_service.py。
"""
from typing import List, Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.core.exceptions import NotFoundException
from app.repositories.base import RepositoryBase
from app.models.permission import Permission
from app.models.role import Role, user_role


class RoleRepository(RepositoryBase[Role]):

    def __init__(self):
        super().__init__(
            Role,
            pk_field="role_id",
            unique_specs=[
                {
                    "fields": ("code",),
                    "message": "角色编码「{code}」已存在",
                },
            ],
        )

    def get_by_code(self, db: Session, code: str) -> Optional[Role]:
        """按角色编码查询未删除的角色"""
        stmt = select(Role).where(
            Role.code == code, Role.is_deleted == False  # noqa: E712
        )
        return db.execute(stmt).scalars().first()

    def get_with_permissions(self, db: Session, role_id: int) -> Role:
        """按主键查询角色并预加载权限，不存在抛 404"""
        stmt = (
            select(Role)
            .options(selectinload(Role.permissions))
            .where(Role.role_id == role_id, Role.is_deleted == False)  # noqa: E712
        )
        role = db.execute(stmt).scalars().first()
        if role is None:
            raise NotFoundException(f"角色中不存在 ID = {role_id} 的记录")
        return role

    def list_with_permissions(self, db: Session) -> list[Role]:
        """查询全部角色（预加载权限），按角色ID升序"""
        stmt = (
            select(Role)
            .options(selectinload(Role.permissions))
            .where(Role.is_deleted == False)  # noqa: E712
            .order_by(Role.role_id)
        )
        return list(db.execute(stmt).scalars().all())

    def _resolve_permissions(self, db: Session, codes: list[str]) -> List[Permission]:
        """按权限码解析出权限实体；有不存在的码则抛 404"""
        if not codes:
            return []
        stmt = select(Permission).where(
            Permission.code.in_(codes), Permission.is_deleted == False  # noqa: E712
        )
        perms = list(db.execute(stmt).scalars().all())
        found = {p.code for p in perms}
        missing = [c for c in codes if c not in found]
        if missing:
            raise NotFoundException(f"权限码不存在：{', '.join(missing)}")
        return perms

    def create_role(self, db: Session, obj_in) -> Role:
        """新增角色，并分配初始权限（纯写入，不做 is_system 校验）"""
        data = obj_in.model_dump(exclude={"permission_codes"})
        self._check_unique_on_create(db, data)
        role = Role(**data)
        db.add(role)
        db.flush()
        role.permissions = self._resolve_permissions(db, obj_in.permission_codes)
        db.commit()
        return self.get_with_permissions(db, role.role_id)

    def update_role(self, db: Session, role_id: int, obj_in) -> Role:
        """更新角色基本信息（局部更新），命中唯一规则抛 409"""
        role = self.get_or_404(db, role_id)
        data = obj_in.model_dump(exclude_unset=True)
        self._check_unique_on_update(db, data, role)
        for field, value in data.items():
            if hasattr(role, field):
                setattr(role, field, value)
        db.add(role)
        db.commit()
        return self.get_with_permissions(db, role_id)

    def assign_permissions(self, db: Session, role_id: int, codes: list[str]) -> Role:
        """重设角色的权限集合：按权限码解析后整体替换"""
        role = self.get_or_404(db, role_id)
        role.permissions = self._resolve_permissions(db, codes)
        db.add(role)
        db.commit()
        return self.get_with_permissions(db, role_id)

    def count_users(self, db: Session, role_id: int) -> int:
        """统计已分配该角色的用户数（用于删除保护）"""
        return db.execute(
            select(func.count()).select_from(user_role).where(user_role.c.role_id == role_id)
        ).scalar_one()


role_repository = RoleRepository()
