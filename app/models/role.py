"""角色模型（role）与「角色↔权限」「用户↔角色」两张关联表

RBAC 数据模型：
    role ──< role_permission >── permission   （角色拥有哪些权限）
    user ──< user_role >────── role             （用户拥有哪些角色）

两张关联表都用 SQLAlchemy Core Table 实现（无需独立 ORM 模型），
仅记录多对多关系，主键为两列组合主键。
"""
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, Table
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin

if TYPE_CHECKING:
    from app.models.permission import Permission
    from app.models.user import User

# 角色 ↔ 权限 多对多关联表
role_permission = Table(
    "role_permission",
    Base.metadata,
    Column(
        "role_id",
        Integer,
        ForeignKey("role.role_id", ondelete="CASCADE"),
        primary_key=True,
        comment="角色ID",
    ),
    Column(
        "permission_id",
        Integer,
        ForeignKey("permission.permission_id", ondelete="CASCADE"),
        primary_key=True,
        comment="权限ID",
    ),
)

# 用户 ↔ 角色 多对多关联表
user_role = Table(
    "user_role",
    Base.metadata,
    Column(
        "user_id",
        Integer,
        ForeignKey("user.user_id", ondelete="CASCADE"),
        primary_key=True,
        comment="用户ID",
    ),
    Column(
        "role_id",
        Integer,
        ForeignKey("role.role_id", ondelete="CASCADE"),
        primary_key=True,
        comment="角色ID",
    ),
)


class Role(Base, TimestampMixin):
    """角色"""

    __tablename__ = "role"

    role_id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True, comment="角色主键ID"
    )
    code: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True, comment="角色编码（唯一）"
    )
    name: Mapped[str] = mapped_column(
        String(50), nullable=False, comment="角色名称"
    )
    description: Mapped[Optional[str]] = mapped_column(
        String(200), nullable=True, comment="角色描述"
    )
    is_system: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="0",
        comment="是否系统角色（超级管理员）：权限校验时直接放行",
    )

    # ---------- 关系 ----------
    # 该角色拥有的权限：多对多，lazy="selectin" 批量加载，角色详情/权限校验都要用。
    permissions: Mapped[List["Permission"]] = relationship(
        "Permission",
        secondary=role_permission,
        back_populates="roles",
        lazy="selectin",
    )
    # 拥有该角色的用户：默认懒加载，避免加载角色时连带拖出全部用户。
    users: Mapped[List["User"]] = relationship(
        "User",
        secondary=user_role,
        back_populates="roles",
    )

    def __repr__(self) -> str:
        return f"<Role(id={self.role_id}, code={self.code!r})>"
