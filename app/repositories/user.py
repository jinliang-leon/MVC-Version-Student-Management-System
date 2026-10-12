"""用户仓储（纯数据访问层）

仅负责与 user / role 表相关的数据库读写：
    - 按用户名 / 主键查询用户（预加载角色与权限）
    - 统计超级管理员数量（纯查询）
    - 创建用户（数据写入，密码哈希由 Service 层完成）
    - 整体替换用户角色（按角色码解析后设置，不做权限校验）
    - 获取 / 创建网关内部服务账号

业务规则（密码哈希、RBAC 守卫、super_admin 保护）在 app/services/user_service.py。
"""
import secrets
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.core.exceptions import NotFoundException
from app.core.security import hash_password
from app.repositories.base import RepositoryBase
from app.models.role import Role
from app.models.user import User

# 网关内部转发的服务账号（仅服务端自调用时使用，不对外暴露）
SERVICE_USERNAME = "_gateway_service"
# 服务账号对应的系统角色码（is_system 使其放行所有权限）
SUPER_ADMIN_ROLE = "super_admin"


class UserRepository(RepositoryBase[User]):

    def __init__(self):
        super().__init__(
            User,
            pk_field="user_id",
            unique_specs=[
                {
                    "fields": ("username",),
                    "message": "用户名「{username}」已存在",
                },
            ],
        )

    # ---------- 查询 ----------
    def get_by_username(self, db: Session, username: str) -> Optional[User]:
        """按用户名查询未删除的用户（登录用）"""
        stmt = select(User).where(
            User.username == username, User.is_deleted == False  # noqa: E712
        )
        return db.execute(stmt).scalars().first()

    def get_with_roles(self, db: Session, user_id: int) -> Optional[User]:
        """按主键查询用户，并预加载角色与权限（鉴权装饰器用）"""
        stmt = (
            select(User)
            .options(selectinload(User.roles).selectinload(Role.permissions))
            .where(User.user_id == user_id, User.is_deleted == False)  # noqa: E712
        )
        return db.execute(stmt).scalars().first()

    def count_super_admins(self, db: Session) -> int:
        """统计未删除的超级管理员用户数（用于禁止删除最后一个）"""
        stmt = (
            select(func.count())
            .select_from(User)
            .join(User.roles)
            .where(Role.is_system == True, User.is_deleted == False)  # noqa: E712
        )
        return db.execute(stmt).scalar_one()

    # ---------- 写 ----------
    def create_user(self, db: Session, data: dict) -> User:
        """创建用户：data 须已含 password_hash（哈希由 Service 层完成）。"""
        self._check_unique_on_create(db, data)
        obj = User(**data)
        db.add(obj)
        db.commit()
        db.refresh(obj)
        return obj

    def set_roles(self, db: Session, user: User, role_codes: list[str]) -> User:
        """整体替换用户的角色集合：按角色码解析后设置（纯数据操作，不做权限校验）

        role_codes 中存在不存在的码时抛 404。
        """
        roles: list[Role] = []
        if role_codes:
            stmt = select(Role).where(
                Role.code.in_(role_codes), Role.is_deleted == False  # noqa: E712
            )
            roles = list(db.execute(stmt).scalars().all())
            found = {r.code for r in roles}
            missing = [c for c in role_codes if c not in found]
            if missing:
                raise NotFoundException(f"角色编码不存在：{', '.join(missing)}")
        user.roles = roles
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    def get_or_create_service_user(self, db: Session) -> User:
        """获取或创建网关内部转发的服务账号（赋 super_admin）

        仅用于 forward_request 在服务端自调用时注入内部 Token。密码为随机值，
        不通过登录接口使用；首次调用自动创建，之后复用。
        """
        user = self.get_by_username(db, SERVICE_USERNAME)
        if user is None:
            user = User(
                username=SERVICE_USERNAME,
                password_hash=hash_password(secrets.token_urlsafe(32)),
            )
            db.add(user)
            db.commit()
            db.refresh(user)

        if SUPER_ADMIN_ROLE not in user.role_codes:
            role = db.execute(
                select(Role).where(
                    Role.code == SUPER_ADMIN_ROLE, Role.is_deleted == False  # noqa: E712
                )
            ).scalars().first()
            if role is not None:
                user.roles.append(role)
                db.add(user)
                db.commit()
        return user


user_repository = UserRepository()
