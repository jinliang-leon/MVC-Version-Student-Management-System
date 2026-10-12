"""学生 Schema"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.validators import validate_person_name


class StudentBase(BaseModel):
    """学生公共字段"""

    name: str = Field(..., min_length=1, max_length=50, description="学生姓名")
    gender: Optional[str] = Field(None, max_length=10, description="学生性别：男/女")
    age: Optional[int] = Field(None, ge=1, le=150, description="学生年龄")
    class_id: Optional[int] = Field(None, description="所属班级ID")

    @field_validator("name")
    @classmethod
    def _name_format(cls, v):
        return validate_person_name(v)


class StudentCreate(StudentBase):
    """新增学生请求体"""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "张三",
                "gender": "男",
                "age": 18,
                "class_id": 1,
            }
        }
    )


class StudentUpdate(BaseModel):
    """更新学生请求体（所有字段可选）"""

    name: Optional[str] = Field(None, min_length=1, max_length=50, description="学生姓名")
    gender: Optional[str] = Field(None, max_length=10, description="学生性别")
    age: Optional[int] = Field(None, ge=1, le=150, description="学生年龄")
    class_id: Optional[int] = Field(None, description="所属班级ID")

    @field_validator("name")
    @classmethod
    def _name_format(cls, v):
        return validate_person_name(v)

    model_config = ConfigDict(
        json_schema_extra={"example": {"age": 19, "class_id": 2}}
    )


class StudentOut(StudentBase):
    """学生响应模型"""

    model_config = ConfigDict(from_attributes=True)

    student_id: int = Field(..., description="学生主键ID")
    class_name: Optional[str] = Field(None, description="所属班级名称")
    created_at: Optional[datetime] = Field(None, description="创建时间")
    updated_at: Optional[datetime] = Field(None, description="更新时间")
    is_deleted: Optional[bool] = Field(None, description="逻辑删除标记")


class StudentSimple(BaseModel):
    """学生简要信息（用于嵌套展示）"""

    model_config = ConfigDict(from_attributes=True)

    student_id: int
    name: str
    gender: Optional[str] = None
    class_id: Optional[int] = None
