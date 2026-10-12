"""RBAC 相关 Schema：角色 / 权限 / 分配关系

约定：
    - 编码（角色码 / 权限码）只做格式校验：单词或 `资源:动作`，
      禁止空白、斜杠等，防注入与拼接问题。
    - 写入路径（Create / Update）才校验；Out 模型不校验。
"""
import re

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.validators import make_text_validator

# 编码格式：单词（如 super_admin）或 `资源:动作`（如 student:delete）
_CODE_RE = re.compile(r"^[A-Za-z0-9_-]+(:[A-Za-z0-9_-]+)?$")

_validate_role_name = make_text_validator("角色名称")


def _validate_code(v: str) -> str:
    v2 = v.strip()
    if not v2:
        raise ValueError("编码不能为空白")
    if not _CODE_RE.fullmatch(v2):
        raise ValueError("编码只能包含字母、数字、下划线、短横线，格式为单词或 `资源:动作`")
    return v2


class PermissionOut(BaseModel):
    """权限（只读）"""

    model_config = ConfigDict(from_attributes=True)

    permission_id: int = Field(..., description="权限主键ID")
    code: str = Field(..., description="权限码（资源:动作）")
    name: str = Field(..., description="权限名称")
    module: str = Field(..., description="所属模块")
    description: str | None = Field(None, description="权限描述")


class RoleOut(BaseModel):
    """角色（只读，含其拥有的权限）"""

    model_config = ConfigDict(from_attributes=True)

    role_id: int = Field(..., description="角色主键ID")
    code: str = Field(..., description="角色编码（唯一）")
    name: str = Field(..., description="角色名称")
    description: str | None = Field(None, description="角色描述")
    is_system: bool = Field(..., description="是否系统角色（超级管理员）")
    permissions: list[PermissionOut] = Field(default_factory=list, description="拥有的权限")


class RoleCreate(BaseModel):
    """新增角色请求体"""

    code: str = Field(..., max_length=50, description="角色编码（唯一）")
    name: str = Field(..., min_length=1, max_length=50, description="角色名称")
    description: str | None = Field(None, max_length=200, description="角色描述")
    is_system: bool = Field(False, description="是否系统角色（超级管理员）")
    permission_codes: list[str] = Field(default_factory=list, description="初始权限码列表")

    @field_validator("code")
    @classmethod
    def _code_format(cls, v):
        return _validate_code(v)

    @field_validator("name")
    @classmethod
    def _name_format(cls, v):
        return _validate_role_name(v)


class RoleUpdate(BaseModel):
    """更新角色请求体（局部更新）"""

    name: str | None = Field(None, min_length=1, max_length=50, description="角色名称")
    description: str | None = Field(None, max_length=200, description="角色描述")

    @field_validator("name")
    @classmethod
    def _name_format(cls, v):
        return _validate_role_name(v)


class RolePermissionAssign(BaseModel):
    """角色权限分配请求体（整体替换）"""

    permission_codes: list[str] = Field(..., description="权限码列表（整体替换）")

    @field_validator("permission_codes")
    @classmethod
    def _codes_format(cls, v):
        return [_validate_code(c) for c in v]


class UserRoleAssign(BaseModel):
    """用户角色分配请求体（整体替换）"""

    role_codes: list[str] = Field(..., description="角色编码列表（整体替换）")

    @field_validator("role_codes")
    @classmethod
    def _codes_format(cls, v):
        return [_validate_code(c) for c in v]
