"""API 路由汇总"""
from fastapi import APIRouter

from app.api import class_, employment, gateway, score, stats, student, teacher

api_router = APIRouter()

# 五张业务表
api_router.include_router(class_.router)
api_router.include_router(student.router)
api_router.include_router(teacher.router)
api_router.include_router(score.router)
api_router.include_router(employment.router)

# 统计分析（扩展）
api_router.include_router(stats.router)

# 内部转发网关（Dify 专用）
api_router.include_router(gateway.router)

__all__ = ["api_router"]
