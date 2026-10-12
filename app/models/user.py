"""用户表模型（user）

用于 JWT 鉴权与 RBAC：
    - username 唯一，password_hash 存 bcrypt 哈希（绝不存明文）
    - roles 多对多关联 Role（RBAC：一个用户可拥有多个角色）
    - role_codes / permission_codes 为只读聚合属性，供装饰器与接口使用
    - is_active 控制账号是否启用（禁用后无法登录）
"""
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import Boolean, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin
from app.models.role import user_role

if TYPE_CHECKING:
    from app.models.role import Role


class User(Base, TimestampMixin):
    """系统用户"""

    __tablename__ = "user"

    user_id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True, comment="用户主键ID"
    )
    username: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True, comment="登录用户名"
    )
    password_hash: Mapped[str] = mapped_column(
        String(128), nullable=False, comment="密码哈希（bcrypt）"
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="1",
        comment="是否启用：1-启用 0-禁用",
    )
    email: Mapped[Optional[str]] = mapped_column(
        String(120), nullable=True, index=True, comment="邮箱（可选）"
    )
    full_name: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True, comment="姓名 / 昵称（可选）"
    )

    # ---------- 关系 ----------
    # 该用户拥有的角色：多对多，lazy="selectin" 随用户一次性批量加载。
    roles: Mapped[List["Role"]] = relationship(
        "Role",
        secondary=user_role,
        back_populates="users",
        lazy="selectin",
    )

    # ---------- 聚合属性（只读） ----------
    @property
    def role_codes(self) -> list[str]:
        """角色编码列表，如 ['super_admin']"""
        return [r.code for r in self.roles]

    @property
    def permission_codes(self) -> set[str]:
        """该用户经所有角色汇总得到的权限码集合（去重）"""
        return {p.code for r in self.roles for p in r.permissions}

    def __repr__(self) -> str:
        return f"<User(id={self.user_id}, username={self.username!r})>"
