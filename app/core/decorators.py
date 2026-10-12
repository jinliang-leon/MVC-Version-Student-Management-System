"""装饰器鉴权（JWT + RBAC）

用「装饰器」而非 FastAPI 的 Depends 依赖注入实现鉴权：

- @auth_required：校验 Authorization: Bearer <token>，成功后把用户对象挂到
  request.state.user；失败抛 UnauthorizedException(401)。
- @require_role("admin")：在 auth_required 基础上校验角色码，不匹配抛
  ForbiddenException(403)。严格角色码匹配，超级管理员也不会自动等于 admin。
- @require_permission("student:delete")：在 auth_required 基础上按权限码校验。
  用户若拥有 is_system 角色（超级管理员）则直接放行；否则校验该权限码是否
  出现在 request.state.user.permission_codes 中，不满足抛 ForbiddenException(403)。

约定
----
- 被装饰的路由函数必须包含 request: Request 参数（装饰器从其中取 Token）。
- 同时兼容 async def 与 def 路由：按函数类型返回对应的 async / sync 包装器，
  不会用同步方式阻塞包装异步函数。
- 鉴权后以数据库为准加载用户角色/权限（权限变更即时生效，无需重新登录）。
- 所有鉴权失败走 UnauthorizedException / ForbiddenException，由 app/core/response.py
  的全局异常处理器统一转成项目统一响应格式 {code, message, data}。
"""
import functools
import inspect
from typing import Callable

from fastapi import Request

from app.core.database import SessionLocal
from app.core.exceptions import ForbiddenException, UnauthorizedException
from app.core.security import decode_token
from app.crud.user import crud_user
from app.models.user import User


def _get_request(func: Callable, args: tuple, kwargs: dict) -> Request:
    """从被装饰函数的调用实参中取出 Request 对象"""
    # FastAPI 会把 request: Request 作为关键字参数传入，直接取最快
    req = kwargs.get("request")
    if isinstance(req, Request):
        return req
    # 兜底：通过签名绑定在全部实参里查找 Request
    sig = inspect.signature(func)
    bound = sig.bind(*args, **kwargs)
    for value in bound.arguments.values():
        if isinstance(value, Request):
            return value
    raise RuntimeError("装饰器要求路由函数包含 request: Request 参数")


def _extract_token(request: Request) -> str:
    """从请求头 Authorization: Bearer <token> 提取 Token"""
    header = request.headers.get("Authorization", "")
    if not header.startswith("Bearer "):
        raise UnauthorizedException("未提供认证凭据，请先登录")
    token = header[len("Bearer "):].strip()
    if not token:
        raise UnauthorizedException("未提供认证凭据，请先登录")
    return token


def _authenticate(request: Request) -> User:
    """校验 Token，成功后把用户对象挂到 request.state.user 并返回

    用户按 get_with_roles 加载，连同角色、权限一并带出，供后续 RBAC 校验。
    """
    token = _extract_token(request)
    payload = decode_token(token)                      # 失败抛 401
    try:
        user_id = int(payload.get("sub"))
    except (TypeError, ValueError):
        raise UnauthorizedException("Token 无效")

    # 用独立短会话加载用户，不依赖路由自身注入的 db，保证装饰器可单独使用
    db = SessionLocal()
    try:
        user = crud_user.get_with_roles(db, user_id)   # 预加载 roles + permissions
    finally:
        db.close()

    if user is None:
        raise UnauthorizedException("用户不存在或已被删除")
    if not user.is_active:
        raise UnauthorizedException("账号已被禁用")
    request.state.user = user
    return user


def _check_role(user: User, role: str) -> None:
    """RBAC 角色码校验：不匹配抛 403（严格匹配，无超级管理员放行）"""
    if role not in user.role_codes:
        raise ForbiddenException(f"缺少权限：需要角色「{role}」")


def _check_permission(user: User, code: str) -> None:
    """RBAC 权限码校验：不匹配抛 403

    - 用户拥有 is_system 角色（超级管理员）→ 直接放行；
    - 否则校验 code 是否在用户经所有角色汇总的权限码集合中。
    """
    if any(r.is_system for r in user.roles):
        return
    if code not in user.permission_codes:
        raise ForbiddenException(f"缺少权限：{code}")


def auth_required(func: Callable) -> Callable:
    """JWT 鉴权装饰器：校验 Bearer Token，成功后 request.state.user 挂用户对象"""

    if inspect.iscoroutinefunction(func):
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            _authenticate(_get_request(func, args, kwargs))
            return await func(*args, **kwargs)

        return async_wrapper

    @functools.wraps(func)
    def sync_wrapper(*args, **kwargs):
        _authenticate(_get_request(func, args, kwargs))
        return func(*args, **kwargs)

    return sync_wrapper


def require_role(role: str):
    """角色码鉴权装饰器：在 @auth_required 基础上再校验角色码

    用法：@require_role("admin")，不匹配抛 ForbiddenException(403)。
    """

    def decorator(func: Callable) -> Callable:
        if inspect.iscoroutinefunction(func):
            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                user = _authenticate(_get_request(func, args, kwargs))
                _check_role(user, role)
                return await func(*args, **kwargs)

            return async_wrapper

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            user = _authenticate(_get_request(func, args, kwargs))
            _check_role(user, role)
            return func(*args, **kwargs)

        return sync_wrapper

    return decorator


def require_permission(code: str):
    """权限码鉴权装饰器：在 @auth_required 基础上按权限码校验

    用法：@require_permission("student:delete")。用户若拥有 is_system 角色
    （超级管理员）则直接放行，否则校验权限码，不满足抛 ForbiddenException(403)。
    """

    def decorator(func: Callable) -> Callable:
        if inspect.iscoroutinefunction(func):
            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                user = _authenticate(_get_request(func, args, kwargs))
                _check_permission(user, code)
                return await func(*args, **kwargs)

            return async_wrapper

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            user = _authenticate(_get_request(func, args, kwargs))
            _check_permission(user, code)
            return func(*args, **kwargs)

        return sync_wrapper

    return decorator
