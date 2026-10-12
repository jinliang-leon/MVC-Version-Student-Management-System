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
from app.schemas.auth import (
    CurrentUserOut,
    LoginRequest,
    RegisterRequest,
    TokenResponse,
    UserOut,
    user_to_out,
)
from app.schemas.rbac import (
    PermissionOut,
    RoleCreate,
    RoleOut,
    RolePermissionAssign,
    RoleUpdate,
    UserRoleAssign,
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
    # auth
    "LoginRequest",
    "RegisterRequest",
    "TokenResponse",
    "UserOut",
    "CurrentUserOut",
    "user_to_out",
    # rbac
    "PermissionOut",
    "RoleCreate",
    "RoleUpdate",
    "RoleOut",
    "RolePermissionAssign",
    "UserRoleAssign",
]
