"""安全工具：密码哈希与 JWT 生成/校验

职责划分：
    - 本模块只做纯逻辑（不依赖 FastAPI / Request）。
    - 装饰器（app/core/decorators.py）调用 decode_token 完成鉴权。
    - 登录接口调用 create_access_token 生成 Token。
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


def create_access_token(user_id: int, roles: list[str]) -> str:
    """生成 JWT：sub 存用户ID，roles 写入角色码列表

    鉴权装饰器实际以数据库中的角色/权限为准（权限变更即时生效），
    JWT 里的 roles 仅供前端展示与轻量判断。
    """
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "roles": roles,
        "iat": now,
        "exp": now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
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
