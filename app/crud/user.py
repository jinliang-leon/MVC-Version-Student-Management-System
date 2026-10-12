"""用户 CRUD（Model 层）

除通用数据访问外，本层承担：
    - 用户名唯一性校验（沿用 unique_specs 机制，软删除后允许重建）
    - 明文密码 → bcrypt 哈希后入库
    - 登录鉴权（用户名 + 密码校验，统一文案防用户名枚举）
    - RBAC：按角色码分配/重设用户角色；服务账号赋 super_admin
"""
import secrets
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.exceptions import NotFoundException, UnauthorizedException
from app.core.security import hash_password, verify_password
from app.crud.base import CRUDBase
from app.models.role import Role
from app.models.user import User

# 网关内部转发的服务账号（仅服务端自调用时使用，不对外暴露）
SERVICE_USERNAME = "_gateway_service"
# 服务账号对应的系统角色码（is_system 使其放行所有权限）
SUPER_ADMIN_ROLE = "super_admin"


class CRUDUser(CRUDBase[User]):

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

    def authenticate(self, db: Session, username: str, password: str) -> User:
        """校验用户名密码：通过返回 User，失败抛 401（统一文案避免用户名枚举）"""
        user = self.get_by_username(db, username)
        if user is None or not verify_password(password, user.password_hash):
            raise UnauthorizedException("用户名或密码错误")
        if not user.is_active:
            raise UnauthorizedException("账号已被禁用")
        return user

    def create_user(self, db: Session, obj_in: Any) -> User:
        """创建用户：明文密码先哈希再入库（命中唯一规则抛 409）"""
        data = obj_in.model_dump()
        data["password_hash"] = hash_password(data.pop("password"))
        self._check_unique_on_create(db, data)
        obj = User(**data)
        db.add(obj)
        db.commit()
        db.refresh(obj)
        return obj

    def assign_roles(self, db: Session, user: User, role_codes: list[str]) -> User:
        """重设用户的角色集合：按角色码解析后整体替换"""
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

        # 确保服务账号拥有 super_admin 角色（is_system 使其放行所有权限）
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


crud_user = CRUDUser()
