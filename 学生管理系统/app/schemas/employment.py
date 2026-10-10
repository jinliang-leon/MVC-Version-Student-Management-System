"""就业 Schema"""
from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.validators import make_text_validator

_validate_company = make_text_validator("就业单位名称")
_validate_position = make_text_validator("就职岗位")


class EmploymentBase(BaseModel):
    """就业公共字段"""

    student_id: int = Field(..., description="学生ID")
    company: str = Field(..., min_length=1, max_length=200, description="就业单位名称")
    position: Optional[str] = Field(None, max_length=100, description="就职岗位")
    salary: Optional[float] = Field(None, ge=0, description="薪资待遇（元/月）")
    employ_date: Optional[date] = Field(None, description="入职日期 YYYY-MM-DD")

    @field_validator("company")
    @classmethod
    def _company_format(cls, v):
        return _validate_company(v)

    @field_validator("position")
    @classmethod
    def _position_format(cls, v):
        return _validate_position(v)


class EmploymentCreate(EmploymentBase):
    """新增就业记录请求体"""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "student_id": 1,
                "company": "深圳沃林数字科技有限公司",
                "position": "Python后端开发工程师",
                "salary": 12000.0,
                "employ_date": "2026-07-01",
            }
        }
    )


class EmploymentUpdate(BaseModel):
    """更新就业记录请求体（所有字段可选）"""

    student_id: Optional[int] = Field(None, description="学生ID")
    company: Optional[str] = Field(None, min_length=1, max_length=200, description="就业单位名称")
    position: Optional[str] = Field(None, max_length=100, description="就职岗位")
    salary: Optional[float] = Field(None, ge=0, description="薪资待遇")
    employ_date: Optional[date] = Field(None, description="入职日期")

    @field_validator("company")
    @classmethod
    def _company_format(cls, v):
        return _validate_company(v)

    @field_validator("position")
    @classmethod
    def _position_format(cls, v):
        return _validate_position(v)

    model_config = ConfigDict(json_schema_extra={"example": {"salary": 15000.0}})


class EmploymentOut(EmploymentBase):
    """就业响应模型"""

    model_config = ConfigDict(from_attributes=True)

    employment_id: int = Field(..., description="就业记录主键ID")
    student_name: Optional[str] = Field(None, description="学生姓名")
    created_at: Optional[datetime] = Field(None, description="创建时间")
    updated_at: Optional[datetime] = Field(None, description="更新时间")
    is_deleted: Optional[bool] = Field(None, description="逻辑删除标记")
