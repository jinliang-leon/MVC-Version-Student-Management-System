"""统计分析 Schema（View 层）

对应 /stats/* 六个接口的响应 data 结构。
字段与重构前的接口返回值逐一对齐，未新增/删除任何键。
"""
from typing import Optional

from pydantic import BaseModel, Field


class OverviewOut(BaseModel):
    """总体数据概览"""

    class_count: int = Field(..., description="班级数")
    student_count: int = Field(..., description="学生数")
    teacher_count: int = Field(..., description="教师数")
    score_count: int = Field(..., description="成绩记录数")
    employment_count: int = Field(..., description="就业记录数")
    avg_score: Optional[float] = Field(None, description="平均分，无成绩时为 null")
    employed_student_count: int = Field(..., description="已就业学生数（去重）")
    employment_rate: float = Field(..., description="就业率（百分比，保留两位）")


class ClassCountOut(BaseModel):
    """各班级学生人数"""

    class_id: int
    class_name: str
    grade: Optional[str] = None
    student_count: int = Field(..., description="班级学生人数")


class AvgScoreOut(BaseModel):
    """按科目聚合的平均分"""

    subject: str
    avg_score: float
    max_score: float
    min_score: float
    record_count: int


class EmploymentRateOut(BaseModel):
    """就业率统计

    注意：学生数为 0 时，接口历史实现不返回 unemployed_count 字段。
    为保持返回值不变，该字段声明为 Optional 并配合路由的
    response_model_exclude_unset=True 使用（未设置则不输出）。
    """

    student_count: int
    employed_count: int
    unemployed_count: Optional[int] = Field(None, description="未就业人数")
    employment_rate: float


class ScoreRankingOut(BaseModel):
    """成绩排行榜条目"""

    rank: int
    student_id: int
    student_name: str
    class_name: Optional[str] = None
    subject: str
    score: float


class TopSalaryOut(BaseModel):
    """高薪就业榜条目"""

    rank: int
    student_id: int
    student_name: str
    company: str
    position: Optional[str] = None
    salary: Optional[float] = None
    employ_date: Optional[str] = Field(None, description="入职日期 YYYY-MM-DD")
