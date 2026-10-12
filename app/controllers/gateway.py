"""内部转发网关（Controller 层）—— 供 Dify Chatflow 的 HTTP 请求节点调用

背景：Dify 的 HTTP 请求节点 method 字段是固定枚举（GET/POST/PUT/DELETE 等），
不支持用变量动态指定请求方法。而本项目的意图路由需要按用户意图决定
GET / POST / PUT / DELETE，因此由后端提供单一入口 POST /gateway，
由网关在服务端完成「按需转发」，Dify 侧只需一个固定 method 的节点。

请求体（application/json）::

    {
        "method": "GET",                  # 转发使用的 HTTP 方法（必填）
        "path": "/students/?gender=男",   # 内部路由，含查询串，必须以 / 开头（必填）
        "body": {"name": "张三"},          # POST/PUT/PATCH 时携带的 JSON 请求体（可选）
        "error": "缺少 class_id"          # 非空时不再转发，返回业务错误（可选）
    }

响应约定（重要）::

    本端点【恒返回 HTTP 200】，真实业务状态码由响应体里的 code 字段承载
    （本项目统一响应格式 {code, message, data}，内部接口的 body.code 与其
    HTTP 状态码本就一致，因此这里只把外层状态码统一为 200）。

本层只做：解析请求体 -> 调用 core.forwarder 转发 -> 返回响应。
"""
from typing import Any, Literal

from fastapi import APIRouter, Request
from fastapi.responses import Response
from pydantic import BaseModel, field_validator

from app.core.forwarder import forward_request

router = APIRouter()


class GatewayPayload(BaseModel):
    """网关转发请求体"""

    method: Literal["GET", "POST", "PUT", "PATCH", "DELETE"]
    path: str
    body: dict[str, Any] | None = None
    error: str | None = None

    @field_validator("path")
    @classmethod
    def _check_path(cls, v: str) -> str:
        if not v.startswith("/"):
            raise ValueError("path 必须以 / 开头")
        if "://" in v or v.startswith("//"):
            raise ValueError("path 不允许携带协议或主机地址")
        return v


@router.post(
    "/gateway",
    tags=["系统"],
    summary="内部转发网关（Dify 专用）",
    status_code=200,
    responses={
        200: {"description": "恒为 200；真实业务状态码见响应体中的 code 字段"},
        422: {"description": "请求体本身不合法（正常调用不会触发）"},
    },
)
async def gateway(payload: GatewayPayload, request: Request) -> Response:
    """按 payload.method 转发到本服务的内部路由，统一以 HTTP 200 返回"""
    return await forward_request(
        method=payload.method,
        path=payload.path,
        body=payload.body,
        error_message=payload.error,
        request=request,
    )
