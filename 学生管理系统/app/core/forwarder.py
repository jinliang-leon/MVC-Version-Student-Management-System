"""内部转发网关的转发逻辑（基础设施层）

与数据库无关，故放在 core/ 而非 crud/。Controller（api/gateway.py）
只负责解析请求体并调用本函数。

背景：Dify 的 HTTP 请求节点 method 固定为枚举，不支持变量指定；
因此提供 POST /gateway 单一入口，由服务端按需转发，且【恒返回 HTTP 200】，
真实业务状态码由响应体的 code 字段承载（详见 api/gateway.py 模块说明）。
"""
from typing import Any, Optional

import httpx
from fastapi import Request
from fastapi.responses import JSONResponse, Response

from app.core.config import settings
from app.core.response import error

# 需要携带 JSON 请求体的方法
_FORWARDABLE = {"POST", "PUT", "PATCH"}


async def forward_request(
    *,
    method: str,
    path: str,
    body: Optional[dict[str, Any]],
    error_message: Optional[str],
    request: Request,
) -> Response:
    """按 method 把请求转发到本服务的内部路由，统一以 HTTP 200 返回"""
    # 快速失败：意图参数不完整等业务性错误，直接给出友好信息（HTTP 仍为 200）
    if error_message:
        return JSONResponse(content=error(message=error_message, code=400))

    # 自调用地址：优先用请求里的端口，避免改端口后失效；回退用配置端口
    port = request.url.port or settings.APP_PORT
    url = f"http://127.0.0.1:{port}{path}"
    method = method.upper()

    timeout = httpx.Timeout(connect=10.0, read=30.0, write=30.0, pool=30.0)
    req_kwargs: dict[str, Any] = {}
    if method in _FORWARDABLE:
        req_kwargs["json"] = body or {}

    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=False) as client:
            resp = await client.request(method, url, **req_kwargs)
    except httpx.HTTPError as exc:  # pragma: no cover
        return JSONResponse(content=error(message=f"网关转发失败: {exc}", code=502))

    # 内部接口的响应体本就是统一格式 {code, message, data}（body.code == 原状态码），
    # 这里仅把外层 HTTP 状态码统一为 200，保证 Dify HTTP 节点不因 4xx/5xx 中断。
    return Response(
        content=resp.content,
        status_code=200,
        media_type=resp.headers.get("content-type", "application/json"),
    )
