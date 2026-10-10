"""老师 Schema"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.validators import make_text_validator, validate_person_name

_validate_teach_text = make_text_validator("职称/科目")


class TeacherBase(BaseModel):
    """老师公共字段"""

    name: str = Field(..., min_length=1, max_length=50, description="教师姓名")
    title: Optional[str] = Field(None, max_length=50, description="教师职称")
    subject: Optional[str] = Field(None, max_length=50, description="授课科目")

    @field_validator("name")
    @classmethod
    def _name_format(cls, v):
        return validate_person_name(v)

    @field_validator("title", "subject")
    @classmethod
    def _text_format(cls, v):
        return _validate_teach_text(v)


class TeacherCreate(TeacherBase):
    """新增老师请求体"""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {"name": "李老师", "title": "高级讲师", "subject": "Python"}
        }
    )


class TeacherUpdate(BaseModel):
    """更新老师请求体（所有字段可选）"""

    name: Optional[str] = Field(None, min_length=1, max_length=50, description="教师姓名")
    title: Optional[str] = Field(None, max_length=50, description="教师职称")
    subject: Optional[str] = Field(None, max_length=50, description="授课科目")

    @field_validator("name")
    @classmethod
    def _name_format(cls, v):
        return validate_person_name(v)

    @field_validator("title", "subject")
    @classmethod
    def _text_format(cls, v):
        return _validate_teach_text(v)

    model_config = ConfigDict(
        json_schema_extra={"example": {"title": "特级讲师"}}
    )


class TeacherOut(TeacherBase):
    """老师响应模型"""

    model_config = ConfigDict(from_attributes=True)

    teacher_id: int = Field(..., description="教师主键ID")
    created_at: Optional[datetime] = Field(None, description="创建时间")
    updated_at: Optional[datetime] = Field(None, description="更新时间")
    is_deleted: Optional[bool] = Field(None, description="逻辑删除标记")


class TeacherSimple(BaseModel):
    """老师简要信息（用于嵌套展示）"""

    model_config = ConfigDict(from_attributes=True)

    teacher_id: int
    name: str
    subject: Optional[str] = None
