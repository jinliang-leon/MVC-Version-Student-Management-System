"""业务服务层（Service / 业务逻辑层）

对应 MVC 中的「控制器与模型之间的业务编排层」：
    - 实现业务规则（密码哈希、RBAC 守卫、super_admin 保护、删除前关联检查等）
    - 编排多个 Repository 完成跨实体操作
    - 不直接处理 HTTP、不序列化响应（响应由 Controller + View 层完成）

调用顺序：Controller -> Service -> Repository -> DB。
"""
from app.services.class_service import class_service
from app.services.employment_service import employment_service
from app.services.permission_service import permission_service
from app.services.role_service import role_service
from app.services.score_service import score_service
from app.services.stats_service import stats_service
from app.services.student_service import student_service
from app.services.teacher_service import teacher_service
from app.services.user_service import user_service

__all__ = [
    "user_service",
    "role_service",
    "permission_service",
    "class_service",
    "student_service",
    "teacher_service",
    "score_service",
    "employment_service",
    "stats_service",
]
