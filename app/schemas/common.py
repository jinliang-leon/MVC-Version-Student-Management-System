"""通用 Schema：分页、响应包装
"""
from typing import Generic, List, Optional, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class PageParams(BaseModel):
    """分页查询参数"""

    page: int = Field(1, ge=1, description="页码，从 1 开始")
    page_size: int = Field(10, ge=1, le=100, description="每页条数，1~100")
    keyword: Optional[str] = Field(None, description="模糊搜索关键词")
    include_deleted: bool = Field(False, description="是否包含已逻辑删除的数据")


class PageResult(BaseModel, Generic[T]):
    """分页结果"""

    total: int = Field(..., description="总记录数")
    page: int = Field(..., description="当前页码")
    page_size: int = Field(..., description="每页条数")
    total_pages: int = Field(..., description="总页数")
    items: List[T] = Field(default_factory=list, description="数据列表")


class OperationResult(BaseModel):
    """简单操作结果"""

    affected: int = Field(..., description="受影响的行数")
    id: Optional[int] = Field(None, description="操作涉及的主键ID")
