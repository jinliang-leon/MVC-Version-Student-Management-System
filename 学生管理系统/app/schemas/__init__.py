"""Schema 统一导出"""
from app.schemas.common import OperationResult, PageParams, PageResult
from app.schemas.class_ import ClassCreate, ClassOut, ClassSimple, ClassUpdate
from app.schemas.student import StudentCreate, StudentOut, StudentSimple, StudentUpdate
from app.schemas.teacher import TeacherCreate, TeacherOut, TeacherSimple, TeacherUpdate
from app.schemas.score import ScoreCreate, ScoreOut, ScoreSimple, ScoreUpdate
from app.schemas.employment import (
    EmploymentCreate,
    EmploymentOut,
    EmploymentUpdate,
)
from app.schemas.stats import (
    AvgScoreOut,
    ClassCountOut,
    EmploymentRateOut,
    OverviewOut,
    ScoreRankingOut,
    TopSalaryOut,
)

__all__ = [
    "PageParams",
    "PageResult",
    "OperationResult",
    # stats
    "OverviewOut",
    "ClassCountOut",
    "AvgScoreOut",
    "EmploymentRateOut",
    "ScoreRankingOut",
    "TopSalaryOut",
    # class
    "ClassCreate",
    "ClassUpdate",
    "ClassOut",
    "ClassSimple",
    # student
    "StudentCreate",
    "StudentUpdate",
    "StudentOut",
    "StudentSimple",
    # teacher
    "TeacherCreate",
    "TeacherUpdate",
    "TeacherOut",
    "TeacherSimple",
    # score
    "ScoreCreate",
    "ScoreUpdate",
    "ScoreOut",
    "ScoreSimple",
    # employment
    "EmploymentCreate",
    "EmploymentUpdate",
    "EmploymentOut",
]
