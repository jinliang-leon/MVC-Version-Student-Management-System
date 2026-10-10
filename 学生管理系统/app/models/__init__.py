"""ORM 模型统一导出

注意：导入顺序需保证被依赖的模型先注册，避免 relationship 解析失败。
"""
from app.models.base import PKMixin, TimestampMixin
from app.models.class_ import Class
from app.models.teacher import Teacher
from app.models.student import Student
from app.models.score import Score
from app.models.employment import Employment

__all__ = [
    "PKMixin",
    "TimestampMixin",
    "Class",
    "Teacher",
    "Student",
    "Score",
    "Employment",
]
