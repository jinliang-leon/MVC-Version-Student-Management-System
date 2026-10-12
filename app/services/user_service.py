"""用户与认证业务服务

承载用户域的全部业务规则：
    - 登录鉴权（用户名 + 密码校验，统一文案防用户名枚举）
    - 注册（密码哈希 + 默认绑定 student 角色）
    - 明文密码 -> bcrypt 哈希后入库
    - RBAC：按角色码分配/重设用户角色；服务账号赋 super_admin
    - super_admin 保护（见 _guard_super_admin / count_super_admins）：
        * 只有超级管理员可授予 / 操作 super_admin 角色与账号
        * 禁止删除最后一个超级管理员

约定：所有会改变角色或危险操作的方法都接收 operator（发起操作的当前登录用户，
来自 Controller 层的 request.state.user）。operator=None 时跳过保护——仅用于注册
默认绑 student、网关服务账号等无鉴权内部场景。
"""
from typing import Optional

from sqlalchemy.orm import Session

from app.core.exceptions import (
    ConflictException,
    ForbiddenException,
    NotFoundException,
    UnauthorizedException,
)
from app.core.security import hash_password, verify_password
from app.models.user import User
from app.repositories.role import role_repository
from app.repositories.user import SUPER_ADMIN_ROLE, user_repository


class UserService:
    """用户域业务逻辑"""

    # ---------- 超级管理员保护 ----------
    @staticmethod
    def is_super(user: User) -> bool:
        """用户是否拥有 is_system 角色（即超级管理员）"""
        return any(r.is_system for r in user.roles)

    def _guard_super_admin(
        self, target: User, operator: Optional[User] = None, action: str = "操作"
    ) -> None:
        """非超级管理员不能操作超级管理员账号"""
        if self.is_super(target) and not (operator and self.is_super(operator)):
            raise ForbiddenException(f"无权限{action}超级管理员账号")

    # ---------- 查询 ----------
    def get_multi(
        self,
        db: Session,
        *,
        page: int = 1,
        page_size: int = 10,
        keyword: Optional[str] = None,
        keyword_fields: Optional[list[str]] = None,
        include_deleted: bool = False,
    ) -> dict:
        return user_repository.get_multi(
            db,
            page=page,
            page_size=page_size,
            keyword=keyword,
            keyword_fields=keyword_fields,
            include_deleted=include_deleted,
        )

    def get_with_roles(self, db: Session, user_id: int, include_deleted: bool = False) -> User:
        """按主键查询用户（预加载角色），不存在抛 404"""
        user = user_repository.get_with_roles(db, user_id)
        if user is None:
            raise NotFoundException("用户不存在或已被删除")
        return user

    # ---------- 认证 ----------
    def authenticate(self, db: Session, username: str, password: str) -> User:
        """校验用户名密码：通过返回 User，失败抛 401（统一文案避免用户名枚举）"""
        user = user_repository.get_by_username(db, username)
        if user is None or not verify_password(password, user.password_hash):
            raise UnauthorizedException("用户名或密码错误")
        if not user.is_active:
            raise UnauthorizedException("账号已被禁用")
        return user

    # ---------- 写 ----------
    def register(self, db: Session, payload) -> User:
        """注册新用户：密码哈希 + 默认绑定 student 角色"""
        data = payload.model_dump()
        data["password_hash"] = hash_password(data.pop("password"))
        user = user_repository.create_user(db, data)
        user_repository.set_roles(db, user, ["student"])
        return user_repository.get_with_roles(db, user.user_id)

    def create_user(self, db: Session, payload) -> User:
        """管理员新建用户（密码哈希）"""
        data = payload.model_dump()
        data["password_hash"] = hash_password(data.pop("password"))
        return user_repository.create_user(db, data)

    def update_user(
        self, db: Session, user: User, payload, operator: Optional[User] = None
    ) -> User:
        """局部更新用户（密码变更走 bcrypt 哈希；不接收角色字段）"""
        self._guard_super_admin(user, operator, action="修改")
        data = payload.model_dump(exclude_unset=True)
        if data.get("password"):
            user.password_hash = hash_password(data.pop("password"))
        for field, value in data.items():
            if hasattr(user, field):
                setattr(user, field, value)
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    def delete_user(
        self, db: Session, user_id: int, operator: Optional[User] = None
    ) -> User:
        """逻辑删除用户（带超级管理员保护）"""
        user = user_repository.get(db, user_id)
        if user is None:
            raise NotFoundException("用户不存在或已被删除")
        self._guard_super_admin(user, operator, action="删除")
        # 禁止删除最后一个超级管理员（业务不变量冲突，返回 409）
        if self.is_super(user) and user_repository.count_super_admins(db) <= 1:
            raise ConflictException("不能删除最后一个超级管理员账号", code=409)
        user_repository.soft_delete(db, user)
        return user

    def assign_roles(
        self,
        db: Session,
        user: User,
        role_codes: list[str],
        operator: Optional[User] = None,
    ) -> User:
        """重设用户的角色集合（按角色码解析后整体替换）

        super_admin 保护：
            - 只有超级管理员可授予 super_admin 角色；
            - 只有超级管理员可操作超级管理员账号。
        """
        if "super_admin" in role_codes and not (operator and self.is_super(operator)):
            raise ForbiddenException("只有超级管理员可授予 super_admin 角色")
        self._guard_super_admin(user, operator, action="操作")
        user_repository.set_roles(db, user, role_codes)
        return user_repository.get_with_roles(db, user.user_id)

    def get_or_create_service_user(self, db: Session) -> User:
        """获取或创建网关内部转发的服务账号（赋 super_admin）"""
        return user_repository.get_or_create_service_user(db)


user_service = UserService()
