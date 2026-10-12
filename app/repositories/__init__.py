"""仓储层（Repository / 数据访问层）

对应 MVC 中的 Model 访问层：每个 Repository 只负责「与数据库打交道」的纯数据操作
（增删改查、关联设置、计数），不包含业务规则，也不做任何序列化。

业务规则（密码哈希、RBAC 守卫、唯一性之外的业务校验、关联存在性校验等）统一在
app/services/ 中编排；响应序列化统一在 app/views/serializers.py。
"""
from app.repositories.class_ import class_repository
from app.repositories.employment import employment_repository
from app.repositories.permission import permission_repository
from app.repositories.role import role_repository
from app.repositories.score import score_repository
from app.repositories.stats import stats_repository
from app.repositories.student import student_repository
from app.repositories.teacher import teacher_repository
from app.repositories.user import user_repository

__all__ = [
    "user_repository",
    "role_repository",
    "permission_repository",
    "class_repository",
    "student_repository",
    "teacher_repository",
    "score_repository",
    "employment_repository",
    "stats_repository",
]
