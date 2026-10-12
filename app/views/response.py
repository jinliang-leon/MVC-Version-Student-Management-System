"""统一响应格式与全局异常处理（View 层）

本模块是 MVC 中 View（视图/表现）层的核心：负责把任意处理结果装配成统一的
JSON 响应体，并注册全局异常处理器，把业务异常转成统一结构：

    {
        "code": 200,
        "message": "success",
        "data": {...} 或 [...]
    }

这种结构对 Dify 的 HTTP 节点非常友好，可通过 code 直接判断成败。
"""
from typing import Any, Generic, Optional, TypeVar

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.logger import get_logger

logger = get_logger("app.views.response")

T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    """统一响应模型"""

    code: int = 200
    message: str = "success"
    data: Optional[T] = None


def success(data: Any = None, message: str = "success", code: int = 200) -> dict:
    """构造成功响应"""
    return {"code": code, "message": message, "data": data}


def error(message: str, code: int = 400, data: Any = None) -> dict:
    """构造错误响应体（仅用于自定义 JSONResponse 内容）

    注意：若需返回非 200 状态码，请使用 BusinessException；
    直接 return error(...) 会被 FastAPI 包装成 200。
    """
    return {"code": code, "message": message, "data": data}


# ---------------------------------------------------------------
# 全局异常处理器
# ---------------------------------------------------------------

# HTTP 状态码 -> 中文提示
_STATUS_TEXT = {
    400: "请求参数错误",
    401: "未授权",
    403: "禁止访问",
    404: "资源不存在",
    405: "请求方法不允许",
    409: "资源冲突",
    422: "参数校验失败",
    500: "服务器内部异常",
}


def register_exception_handlers(app: FastAPI) -> None:
    """注册全局异常处理器到 FastAPI 实例"""

    # 注意：BusinessException 必须先注册，否则会被 Exception 兜底捕获
    from app.core.exceptions import BusinessException

    @app.exception_handler(BusinessException)
    async def business_exception_handler(request: Request, exc: BusinessException):
        """处理业务异常（404 资源不存在 / 400 业务规则拒绝 / 422 校验失败）"""
        logger.warning("业务异常 [code=%s] %s", exc.code, exc.message)
        return JSONResponse(
            status_code=exc.code,
            content=error(message=exc.message, code=exc.code, data=exc.data),
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        """处理 HTTPException（如 404、400）"""
        logger.warning("HTTP 异常 [status=%s] %s", exc.status_code, exc.detail)
        detail = exc.detail
        if isinstance(detail, dict):
            message = detail.get("message", str(detail))
            data = detail.get("data")
        else:
            message = str(detail) if detail else _STATUS_TEXT.get(exc.status_code, "请求异常")
            data = None
        return JSONResponse(
            status_code=exc.status_code,
            content=error(message=message, code=exc.status_code, data=data),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        """处理 Pydantic 参数校验错误（422）"""
        logger.warning("参数校验失败 [%s] 共 %d 处错误", request.url.path, len(exc.errors()))
        errors = []
        for err in exc.errors():
            loc = " -> ".join(str(x) for x in err.get("loc", []) if x != "body")
            errors.append({"field": loc or "body", "message": err.get("msg", "")})

        # message 中带上首条字段错误的可读原因，前端可直接 toast 展示，
        # 避免用户只看到笼统的"参数校验失败"而不知错在哪个字段。
        first = errors[0] if errors else None
        if first:
            msg = f"{first['field']}: {first['message']}"
        else:
            msg = "参数校验失败"

        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=error(
                message=msg,
                code=422,
                data={"errors": errors},
            ),
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        """兜底处理 500 异常"""
        logger.error(
            "未处理的服务器异常 [%s %s]: %s",
            request.method,
            request.url.path,
            exc,
            exc_info=True,
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=error(message=f"服务器内部异常: {exc}", code=500),
        )
