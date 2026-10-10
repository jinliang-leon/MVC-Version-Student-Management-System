"""CRUD 统一导出"""
from app.crud.base import CRUDBase
from app.crud.class_ import crud_class
from app.crud.student import crud_student
from app.crud.teacher import crud_teacher
from app.crud.score import crud_score
from app.crud.employment import crud_employment
from app.crud.stats import crud_stats

__all__ = [
    "CRUDBase",
    "crud_class",
    "crud_student",
    "crud_teacher",
    "crud_score",
    "crud_employment",
    "crud_stats",
]
