"""成绩 Schema"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.validators import make_text_validator

_validate_subject = make_text_validator("考试科目")


class ScoreBase(BaseModel):
    """成绩公共字段"""

    student_id: int = Field(..., description="学生ID")
    teacher_id: int = Field(..., description="授课教师ID")
    subject: str = Field(..., min_length=1, max_length=50, description="考试科目")
    score: float = Field(..., ge=0, le=750, description="考试分数")

    @field_validator("subject")
    @classmethod
    def _subject_format(cls, v):
        return _validate_subject(v)


class ScoreCreate(ScoreBase):
    """新增成绩请求体"""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "student_id": 1,
                "teacher_id": 1,
                "subject": "Python程序设计",
                "score": 95.5,
            }
        }
    )


class ScoreUpdate(BaseModel):
    """更新成绩请求体（所有字段可选）"""

    student_id: Optional[int] = Field(None, description="学生ID")
    teacher_id: Optional[int] = Field(None, description="授课教师ID")
    subject: Optional[str] = Field(None, min_length=1, max_length=50, description="考试科目")
    score: Optional[float] = Field(None, ge=0, le=750, description="考试分数")

    @field_validator("subject")
    @classmethod
    def _subject_format(cls, v):
        return _validate_subject(v)

    model_config = ConfigDict(json_schema_extra={"example": {"score": 98.0}})


class ScoreOut(ScoreBase):
    """成绩响应模型"""

    model_config = ConfigDict(from_attributes=True)

    score_id: int = Field(..., description="成绩主键ID")
    student_name: Optional[str] = Field(None, description="学生姓名")
    teacher_name: Optional[str] = Field(None, description="教师姓名")
    created_at: Optional[datetime] = Field(None, description="创建时间")
    updated_at: Optional[datetime] = Field(None, description="更新时间")
    is_deleted: Optional[bool] = Field(None, description="逻辑删除标记")


class ScoreSimple(BaseModel):
    """成绩简要信息"""

    model_config = ConfigDict(from_attributes=True)

    score_id: int
    subject: str
    score: float
