"""班级 Schema

- ClassCreate：新增校验模型
- ClassUpdate：更新校验模型（全部字段可选）
- ClassOut：响应模型
"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.validators import make_text_validator

_validate_class_name = make_text_validator("班级名称")


class ClassBase(BaseModel):
    """班级公共字段"""

    class_name: str = Field(..., min_length=1, max_length=100, description="班级名称")
    grade: Optional[str] = Field(None, max_length=50, description="所属年级")
    remark: Optional[str] = Field(None, max_length=500, description="班级备注信息")

    @field_validator("class_name")
    @classmethod
    def _class_name_format(cls, v):
        return _validate_class_name(v)


class ClassCreate(ClassBase):
    """新增班级请求体"""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "class_name": "Python全栈1班",
                "grade": "2026级",
                "remark": "主修Python后端开发方向",
            }
        }
    )


class ClassUpdate(BaseModel):
    """更新班级请求体（所有字段可选，只传需要修改的字段）"""

    class_name: Optional[str] = Field(None, min_length=1, max_length=100, description="班级名称")
    grade: Optional[str] = Field(None, max_length=50, description="所属年级")
    remark: Optional[str] = Field(None, max_length=500, description="班级备注信息")

    @field_validator("class_name")
    @classmethod
    def _class_name_format(cls, v):
        return _validate_class_name(v)

    model_config = ConfigDict(
        json_schema_extra={
            "example": {"class_name": "Python全栈2班", "remark": "调整班级名称"}
        }
    )


class ClassOut(ClassBase):
    """班级响应模型"""

    model_config = ConfigDict(from_attributes=True)

    class_id: int = Field(..., description="班级主键ID")
    student_count: Optional[int] = Field(None, description="班级学生人数")
    created_at: Optional[datetime] = Field(None, description="创建时间")
    updated_at: Optional[datetime] = Field(None, description="更新时间")
    is_deleted: Optional[bool] = Field(None, description="逻辑删除标记")


class ClassSimple(BaseModel):
    """班级简要信息（用于嵌套展示）"""

    model_config = ConfigDict(from_attributes=True)

    class_id: int
    class_name: str
    grade: Optional[str] = None
