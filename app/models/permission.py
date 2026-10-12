"""权限模型（permission）

权限码约定：`资源:动作`，如 `student:delete`。业务代码与装饰器都按权限码校验，
不再散落 `if role == "xxx"` 的判断。
"""
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin
from app.models.role import role_permission

if TYPE_CHECKING:
    from app.models.role import Role


class Permission(Base, TimestampMixin):
    """权限"""

    __tablename__ = "permission"

    permission_id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True, comment="权限主键ID"
    )
    code: Mapped[str] = mapped_column(
        String(100), nullable=False, index=True, comment="权限码（资源:动作）"
    )
    name: Mapped[str] = mapped_column(
        String(100), nullable=False, comment="权限名称"
    )
    module: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True, comment="所属模块"
    )
    description: Mapped[Optional[str]] = mapped_column(
        String(200), nullable=True, comment="权限描述"
    )

    # ---------- 关系 ----------
    # 拥有该权限的角色：默认懒加载（权限列表接口按模块展示，不需要角色信息）。
    roles: Mapped[List["Role"]] = relationship(
        "Role",
        secondary=role_permission,
        back_populates="permissions",
    )

    def __repr__(self) -> str:
        return f"<Permission(id={self.permission_id}, code={self.code!r})>"
