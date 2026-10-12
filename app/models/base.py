"""ORM 模型基类与混入

核心：TimestampMixin 为所有表统一注入三个强制字段
    - created_at  创建时间
    - updated_at  更新时间
    - is_deleted  逻辑删除标记

这是需求文档 2.1 的硬性规定：「除了以下字段，所有表一律要加上
创建时间、更新时间、逻辑删除字段！」
"""
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, func
from sqlalchemy.orm import Mapped, mapped_column


class TimestampMixin:
    """审计字段混入：创建时间 / 更新时间 / 逻辑删除"""

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
        comment="创建时间",
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
        comment="更新时间",
    )

    is_deleted: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="0",
        index=True,
        comment="逻辑删除标记：0-正常 1-已删除",
    )


class PKMixin:
    """通用整型自增主键混入（可选，各表自定义主键名时不必继承）"""

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True, comment="主键ID"
    )
