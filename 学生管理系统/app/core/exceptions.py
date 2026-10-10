"""公共异常定义

业务异常统一继承 BusinessException，由全局异常处理器捕获。
"""
from typing import Any


class BusinessException(Exception):
    """业务异常基类"""

    def __init__(self, message: str, code: int = 400, data: Any = None):
        self.message = message
        self.code = code
        self.data = data
        super().__init__(message)


class NotFoundException(BusinessException):
    """资源不存在（404）"""

    def __init__(self, message: str = "资源不存在", data: Any = None):
        super().__init__(message=message, code=404, data=data)


class ConflictException(BusinessException):
    """资源冲突 / 存在关联数据不可操作（409 / 400）

    Q4 方案 A：删除班级前检查是否还有学生，有则抛此异常。
    """

    def __init__(self, message: str = "操作冲突", code: int = 400, data: Any = None):
        super().__init__(message=message, code=code, data=data)


class DuplicateException(BusinessException):
    """重复创建 / 唯一性冲突（409 Conflict）

    创建或修改记录时，若同名/同组合的未删除记录已存在，抛此异常。
    由 CRUDBase 的 unique_specs 规则自动触发。
    """

    def __init__(self, message: str = "记录已存在，不可重复创建", data: Any = None):
        super().__init__(message=message, code=409, data=data)


class ValidationException(BusinessException):
    """业务校验失败（422）"""

    def __init__(self, message: str = "参数校验失败", data: Any = None):
        super().__init__(message=message, code=422, data=data)
