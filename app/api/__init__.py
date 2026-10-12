"""API 路由汇总"""
from fastapi import APIRouter

from app.api import (
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

api_router = APIRouter()

# 认证（白名单，无需 JWT）
api_router.include_router(auth.router)

# 五张业务表
api_router.include_router(class_.router)
api_router.include_router(student.router)
api_router.include_router(teacher.router)
api_router.include_router(score.router)
api_router.include_router(employment.router)

# 统计分析（扩展）
api_router.include_router(stats.router)

# RBAC 角色权限管理
api_router.include_router(roles.router)
api_router.include_router(permissions.router)
api_router.include_router(users.router)

# 内部转发网关（Dify 专用）
api_router.include_router(gateway.router)

__all__ = ["api_router"]
