"""权限业务服务

权限由种子脚本维护，接口层只读；本服务仅做薄封装，便于 Controller 统一走
「Controller -> Service -> Repository」分层。
"""
from sqlalchemy.orm import Session

from app.repositories.permission import permission_repository


class PermissionService:
    def list_grouped(self, db: Session) -> dict:
        """按模块分组返回全部权限"""
        return permission_repository.list_grouped(db)


permission_service = PermissionService()
