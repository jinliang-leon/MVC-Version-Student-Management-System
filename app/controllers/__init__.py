"""控制器路由汇总（Controller 层入口）

把各业务控制器（原 app/api 下的路由）汇总为一个 router，供 main.py 挂载。
"""
from fastapi import APIRouter

from app.controllers import (
    auth,
    class_,
    employment,
    gateway,
    permissions,
    roles,
    score,
    stats,
    student,
    teacher,
    users,
)

controller_router = APIRouter()

# 认证（白名单，无需 JWT）
controller_router.include_router(auth.router)

# 五张业务表
controller_router.include_router(class_.router)
controller_router.include_router(student.router)
controller_router.include_router(teacher.router)
controller_router.include_router(score.router)
controller_router.include_router(employment.router)

# 统计分析（扩展）
controller_router.include_router(stats.router)

# RBAC 角色权限管理
controller_router.include_router(roles.router)
controller_router.include_router(permissions.router)
controller_router.include_router(users.router)

# 内部转发网关（Dify 专用）
controller_router.include_router(gateway.router)

__all__ = ["controller_router"]
