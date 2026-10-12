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
    """注册请求体（用户名做格式校验，密码最短 6 位）

    注意：注册**不接收任何角色字段**，角色由服务端强制绑定 student（见 api/auth.register）。
    email / full_name 为可选字段，留空则不写入。
    """

    username: str = Field(..., min_length=1, max_length=50, description="登录用户名")
    password: str = Field(..., min_length=6, max_length=64, description="登录密码（6~64 位）")
    email: str | None = Field(None, max_length=120, description="邮箱（可选）")
    full_name: str | None = Field(None, max_length=50, description="姓名 / 昵称（可选）")

    @field_validator("username")
    @classmethod
    def _username_format(cls, v):
        return _validate_username(v)

    model_config = ConfigDict(
        json_schema_extra={"example": {"username": "alice", "password": "abc123"}}
    )


class UserCreate(BaseModel):
    """管理员新建用户（角色通过 /users/{user_id}/roles 单独分配，本模型不接收角色）"""

    username: str = Field(..., min_length=1, max_length=50, description="登录用户名")
    password: str = Field(..., min_length=6, max_length=64, description="登录密码（6~64 位）")
    is_active: bool = Field(True, description="是否启用")
    email: str | None = Field(None, max_length=120, description="邮箱（可选）")
    full_name: str | None = Field(None, max_length=50, description="姓名 / 昵称（可选）")

    @field_validator("username")
    @classmethod
    def _username_format(cls, v):
        return _validate_username(v)


class UserUpdate(BaseModel):
    """管理员更新用户（局部更新；不接收角色字段，角色走专用接口）"""

    username: str | None = Field(None, min_length=1, max_length=50, description="登录用户名（可选）")
    password: str | None = Field(None, min_length=6, max_length=64, description="新密码（可选，6~64 位）")
    is_active: bool | None = Field(None, description="是否启用（可选）")
    email: str | None = Field(None, max_length=120, description="邮箱（可选）")
    full_name: str | None = Field(None, max_length=50, description="姓名 / 昵称（可选）")

    @field_validator("username")
    @classmethod
    def _username_format(cls, v):
        return _validate_username(v)


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
    email: str | None = Field(None, description="邮箱（可选）")
    full_name: str | None = Field(None, description="姓名 / 昵称（可选）")


class CurrentUserOut(BaseModel):
    """当前登录用户（/auth/me）：含角色码、权限码、是否超级管理员"""

    user_id: int = Field(..., description="用户主键ID")
    username: str = Field(..., description="登录用户名")
    roles: list[str] = Field(default_factory=list, description="角色编码列表")
    permissions: list[str] = Field(default_factory=list, description="权限码列表")
    is_super: bool = Field(..., description="是否为超级管理员（拥有 is_system 角色）")
