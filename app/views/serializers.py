"""响应序列化（View 层）

把 ORM 实体转换为对外响应字典（DTO）。所有「拼装响应字段」（如附带 class_name /
student_name）集中在此，Controller 不再手写转换逻辑。

约定：每个 to_out 返回 dict（即 schema.model_dump() 的扩展），便于直接塞进
统一响应体 {code, message, data} 的 data 字段。
"""
from app.schemas.auth import UserOut
from app.schemas.class_ import ClassOut
from app.schemas.employment import EmploymentOut
from app.schemas.score import ScoreOut
from app.schemas.student import StudentOut
from app.schemas.teacher import TeacherOut


def user_to_out(user) -> dict:
    """User ORM -> 响应字典（角色映射为角色码列表）"""
    return UserOut(
        user_id=user.user_id,
        username=user.username,
        roles=user.role_codes,
        is_active=user.is_active,
        email=user.email,
        full_name=user.full_name,
    ).model_dump()


def student_to_out(obj) -> dict:
    """Student ORM -> 响应字典（附带 class_name）"""
    data = StudentOut.model_validate(obj).model_dump()
    if obj.class_ is not None:
        data["class_name"] = obj.class_.class_name
    return data


def class_to_out(obj) -> dict:
    """Class ORM -> 响应字典（附带 student_count）"""
    data = ClassOut.model_validate(obj).model_dump()
    data["student_count"] = len(obj.students) if obj.students is not None else 0
    return data


def teacher_to_out(obj) -> dict:
    """Teacher ORM -> 响应字典"""
    return TeacherOut.model_validate(obj).model_dump()


def score_to_out(obj) -> dict:
    """Score ORM -> 响应字典（附带 student_name / teacher_name）"""
    data = ScoreOut.model_validate(obj).model_dump()
    if obj.student is not None:
        data["student_name"] = obj.student.name
    if obj.teacher is not None:
        data["teacher_name"] = obj.teacher.name
    return data


def employment_to_out(obj) -> dict:
    """Employment ORM -> 响应字典（附带 student_name）"""
    data = EmploymentOut.model_validate(obj).model_dump()
    if obj.student is not None:
        data["student_name"] = obj.student.name
    return data
