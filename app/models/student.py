"""学生表模型（student）

需求文档 2.1.2：
    student_id  Integer  学生主键ID  主键、自增
    name        String   学生姓名    非空
    gender      String   学生性别    可空
    age         Integer  学生年龄    可空
    class_id    Integer  所属班级ID  外键关联 class.class_id

表关系：班级与学生为一对多关系，一个班级可包含多名学生，一名学生仅归属一个班级。
"""
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin

if TYPE_CHECKING:
    from app.models.class_ import Class
    from app.models.employment import Employment
    from app.models.score import Score


class Student(Base, TimestampMixin):
    """学生"""

    __tablename__ = "student"

    student_id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True, comment="学生主键ID"
    )
    name: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True, comment="学生姓名"
    )
    gender: Mapped[Optional[str]] = mapped_column(
        String(10), nullable=True, comment="学生性别"
    )
    age: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True, comment="学生年龄"
    )
    class_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("class.class_id", ondelete="SET NULL", onupdate="CASCADE"),
        nullable=True,
        index=True,
        comment="所属班级ID",
    )

    # ---------- 关系 ----------
    # 所属班级：多对一，lazy="joined" 用左外连接随学生一次性查出班级。
    # 学生详情几乎总要展示 class_name，这样能避免逐条 N+1 查询。
    class_: Mapped[Optional["Class"]] = relationship(
        "Class",
        back_populates="students",
        lazy="joined",
    )
    # 成绩 / 就业：只读「有效数据」视图关系，三点约定需一起理解：
    # - primaryjoin 额外带上 is_deleted == False：自动把已逻辑删除的子记录过滤掉，
    #   因此 obj.scores / obj.employments 拿到的永远是未删除的数据；
    # - viewonly=True：只读，不参与写回——增删改一律走 ORM 实体本身，
    #   防止通过集合反向赋值时绕过 is_deleted 标记；
    # - lazy="selectin"：批量 IN 查询，适合一对多集合，避免 N+1。
    scores: Mapped[List["Score"]] = relationship(
        "Score",
        back_populates="student",
        primaryjoin="and_(Student.student_id == Score.student_id, Score.is_deleted == False)",
        viewonly=True,
        lazy="selectin",
    )
    employments: Mapped[List["Employment"]] = relationship(
        "Employment",
        back_populates="student",
        primaryjoin="and_(Student.student_id == Employment.student_id, Employment.is_deleted == False)",
        viewonly=True,
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<Student(id={self.student_id}, name={self.name!r})>"
