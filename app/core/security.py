"""安全工具：密码哈希与 JWT 生成/校验

职责划分：
    - 本模块只做纯逻辑（不依赖 FastAPI / Request）。
    - 装饰器（app/core/decorators.py）调用 decode_token 完成鉴权。
    - 登录接口调用 create_access_token 生成 Token。

JWT 设计（鉴权约定）：
    - access_token **仅存放身份信息**（sub=user_id + username），不携带角色/权限。
    - 鉴权装饰器每次都从数据库重新加载用户角色与权限（见 decorators._authenticate），
      因此修改权限/角色后即时生效，无需重新登录。
    - refresh_token 的生成函数（create_refresh_token）已就绪，登录接口暂只签发 access_token，
      刷新流程后续迭代接入。
"""
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from app.core.config import settings
from app.core.exceptions import UnauthorizedException


def hash_password(password: str) -> str:
    """用 bcrypt 对明文密码加盐哈希，返回可入库的字符串"""
    # bcrypt 只接受 bytes；哈希结果自带盐，无需单独存盐
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    """校验明文密码与库中哈希是否匹配"""
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except ValueError:
        # 库中哈希格式非法时返回 False，避免抛异常
        return False


def create_access_token(user_id: int, username: str, roles: list[str] | None = None) -> str:
    """生成 JWT（仅含身份信息）

    载荷固定为：sub（用户ID）、username、iat、exp。
    roles 参数为兼容保留，已不再写入 Token 载荷——角色/权限一律以数据库为准。

    鉴权装饰器每次都按 sub 重新查库加载角色与权限，故权限变更即时生效。
    """
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "username": username,
        "iat": now,
        "exp": now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_refresh_token(user_id: int, username: str) -> str:
    """生成刷新令牌：当前登录接口暂不签发，后续迭代接入刷新流程时使用。

    载荷额外带 type=refresh，用于校验时区分 token 类型。
    """
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "username": username,
        "type": "refresh",
        "iat": now,
        "exp": now + timedelta(minutes=settings.REFRESH_TOKEN_EXPIRE_MINUTES),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_token(token: str) -> dict:
    """解析并校验 JWT；过期/无效统一抛 UnauthorizedException(401)"""
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise UnauthorizedException("Token 已过期，请重新登录")
    except jwt.InvalidTokenError:
        raise UnauthorizedException("Token 无效")
