"""老师表模型（teacher）

需求文档 2.1.3：
    teacher_id  Integer  教师主键ID  主键、自增
    name        String   教师姓名    非空
    title       String   教师职称    可空
    subject     String   授课科目    可空
"""
from typing import TYPE_CHECKING, List

from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin

if TYPE_CHECKING:
    from app.models.score import Score


class Teacher(Base, TimestampMixin):
    """老师"""

    __tablename__ = "teacher"

    teacher_id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True, comment="教师主键ID"
    )
    name: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True, comment="教师姓名"
    )
    title: Mapped[str | None] = mapped_column(
        String(50), nullable=True, comment="教师职称"
    )
    subject: Mapped[str | None] = mapped_column(
        String(50), nullable=True, comment="授课科目"
    )

    # ---------- 关系 ----------
    scores: Mapped[List["Score"]] = relationship(
        "Score",
        back_populates="teacher",
        primaryjoin="and_(Teacher.teacher_id == Score.teacher_id, Score.is_deleted == False)",
        viewonly=True,
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<Teacher(id={self.teacher_id}, name={self.name!r})>"
