"""FastAPI 依赖注入（Controller 层共用）

统一管理数据库会话、分页参数等。
"""
from typing import Optional

from fastapi import Query

from app.core.config import settings
from app.core.database import get_db


class PaginationParams:
    """分页参数依赖类

    用法::

        def list_items(p: PaginationParams = Depends()):
            page, size = p.page, p.page_size
    """

    def __init__(
        self,
        page: int = Query(1, ge=1, description="页码，从 1 开始"),
        page_size: Optional[int] = Query(
            None, ge=1, le=1000, description="每页条数，默认取配置值"
        ),
    ):
        self.page = page
        self.page_size = page_size or settings.DEFAULT_PAGE_SIZE
        # 兜底上限保护
        if self.page_size > settings.MAX_PAGE_SIZE:
            self.page_size = settings.MAX_PAGE_SIZE


__all__ = ["get_db", "PaginationParams"]
