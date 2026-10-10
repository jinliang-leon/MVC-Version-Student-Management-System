"""成绩表模型（score）

需求文档 2.1.4：
    score_id    Integer  成绩主键ID      主键、自增
    student_id  Integer  学生ID         外键关联 student.student_id，非空
    teacher_id  Integer  授课教师ID      外键关联 teacher.teacher_id，非空
    subject     String   考试科目        非空
    score       Float    考试分数        非空
"""
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin

if TYPE_CHECKING:
    from app.models.student import Student
    from app.models.teacher import Teacher


class Score(Base, TimestampMixin):
    """成绩"""

    __tablename__ = "score"

    score_id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True, comment="成绩主键ID"
    )
    student_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("student.student_id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
        index=True,
        comment="学生ID",
    )
    teacher_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("teacher.teacher_id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
        index=True,
        comment="授课教师ID",
    )
    subject: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True, comment="考试科目"
    )
    score: Mapped[float] = mapped_column(
        Float, nullable=False, comment="考试分数"
    )

    # ---------- 关系 ----------
    student: Mapped[Optional["Student"]] = relationship(
        "Student",
        back_populates="scores",
        lazy="joined",
    )
    teacher: Mapped[Optional["Teacher"]] = relationship(
        "Teacher",
        back_populates="scores",
        lazy="joined",
    )

    def __repr__(self) -> str:
        return (
            f"<Score(id={self.score_id}, student_id={self.student_id}, "
            f"subject={self.subject!r}, score={self.score})>"
        )
