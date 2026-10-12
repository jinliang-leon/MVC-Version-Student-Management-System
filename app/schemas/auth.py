"""认证相关 Schema：登录 / 注册 / Token / 当前用户"""
from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.validators import make_text_validator

_validate_username = make_text_validator("用户名")


class LoginRequest(BaseModel):
    """登录请求体"""

    username: str = Field(..., min_length=1, max_length=50, description="登录用户名")
    password: str = Field(..., min_length=1, max_length=64, description="登录密码")

    model_config = ConfigDict(
        json_schema_extra={"example": {"username": "admin", "password": "123456"}}
    )


class RegisterRequest(BaseModel):
    """注册请求体（用户名做格式校验，密码最短 6 位）"""

    username: str = Field(..., min_length=1, max_length=50, description="登录用户名")
    password: str = Field(..., min_length=6, max_length=64, description="登录密码（6~64 位）")

    @field_validator("username")
    @classmethod
    def _username_format(cls, v):
        return _validate_username(v)

    model_config = ConfigDict(
        json_schema_extra={"example": {"username": "admin", "password": "123456"}}
    )


class TokenResponse(BaseModel):
    """登录成功返回的 Token"""

    access_token: str = Field(..., description="JWT 访问令牌")
    token_type: str = Field("bearer", description="令牌类型")
    expires_in: int = Field(..., description="有效期（秒）")


class UserOut(BaseModel):
    """用户信息（注册返回 / 用户列表）"""

    user_id: int = Field(..., description="用户主键ID")
    username: str = Field(..., description="登录用户名")
    roles: list[str] = Field(default_factory=list, description="角色编码列表")
    is_active: bool = Field(..., description="是否启用")


class CurrentUserOut(BaseModel):
    """当前登录用户（/auth/me）：含角色码与权限码"""

    user_id: int = Field(..., description="用户主键ID")
    username: str = Field(..., description="登录用户名")
    roles: list[str] = Field(default_factory=list, description="角色编码列表")
    permissions: list[str] = Field(default_factory=list, description="权限码列表")
    is_active: bool = Field(..., description="是否启用")


def user_to_out(user) -> UserOut:
    """把 User ORM 对象序列化为 UserOut（角色映射为角色码列表）"""
    return UserOut(
        user_id=user.user_id,
        username=user.username,
        roles=user.role_codes,
        is_active=user.is_active,
    )
