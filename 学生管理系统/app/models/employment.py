"""就业表模型（employment）

需求文档 2.1.5：
    employment_id  Integer  就业记录主键ID  主键、自增
    student_id     Integer  学生ID         外键关联 student.student_id，非空
    company        String   就业单位名称    非空
    position       String   就职岗位        可空
    salary         Float    薪资待遇        可空
    employ_date    Date     入职日期        可空
"""
from datetime import date
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Date, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin

if TYPE_CHECKING:
    from app.models.student import Student


class Employment(Base, TimestampMixin):
    """就业记录"""

    __tablename__ = "employment"

    employment_id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True, comment="就业记录主键ID"
    )
    student_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("student.student_id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
        index=True,
        comment="学生ID",
    )
    company: Mapped[str] = mapped_column(
        String(200), nullable=False, index=True, comment="就业单位名称"
    )
    position: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True, comment="就职岗位"
    )
    salary: Mapped[Optional[float]] = mapped_column(
        Float, nullable=True, comment="薪资待遇"
    )
    employ_date: Mapped[Optional[date]] = mapped_column(
        Date, nullable=True, comment="入职日期"
    )

    # ---------- 关系 ----------
    student: Mapped[Optional["Student"]] = relationship(
        "Student",
        back_populates="employments",
        lazy="joined",
    )

    def __repr__(self) -> str:
        return (
            f"<Employment(id={self.employment_id}, student_id={self.student_id}, "
            f"company={self.company!r})>"
        )
