"""班级表模型（class）

需求文档 2.1.1：
    class_id    Integer  班级主键ID  主键、自增
    class_name  String   班级名称    非空
    grade       String   所属年级    可空
    remark      String   班级备注信息 可空
"""
from typing import TYPE_CHECKING, List

from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin

if TYPE_CHECKING:
    from app.models.student import Student


class Class(Base, TimestampMixin):
    """班级"""

    __tablename__ = "class"

    class_id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True, comment="班级主键ID"
    )
    class_name: Mapped[str] = mapped_column(
        String(100), nullable=False, comment="班级名称"
    )
    grade: Mapped[str | None] = mapped_column(
        String(50), nullable=True, comment="所属年级"
    )
    remark: Mapped[str | None] = mapped_column(
        String(500), nullable=True, comment="班级备注信息"
    )

    # ---------- 关系：一个班级包含多名学生 ----------
    students: Mapped[List["Student"]] = relationship(
        "Student",
        back_populates="class_",
        primaryjoin="and_(Class.class_id == Student.class_id, Student.is_deleted == False)",
        viewonly=True,
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<Class(id={self.class_id}, name={self.class_name!r})>"
