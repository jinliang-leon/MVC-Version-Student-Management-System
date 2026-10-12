"""成绩 CRUD（Model 层）

除通用数据访问外，本层承担成绩相关的业务规则与响应拼装：
    - 关联校验：student_id / teacher_id 若填写则必须对应存在的记录
    - 响应拼装：附带 student_name、teacher_name
"""
from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from app.core.exceptions import ConflictException
from app.crud.base import CRUDBase
from app.crud.student import crud_student
from app.crud.teacher import crud_teacher
from app.models.score import Score
from app.schemas.score import ScoreOut


class CRUDScore(CRUDBase[Score]):

    def __init__(self):
        super().__init__(
            Score,
            pk_field="score_id",
            unique_specs=[
                {
                    "fields": ("student_id", "subject"),
                    "message": "学生 {student_id} 在科目「{subject}」已有成绩记录，不可重复录入",
                },
            ],
        )

    # ----------------------------------------------------------
    # 响应拼装 / 关联校验
    # ----------------------------------------------------------
    def _to_out(self, obj: Score) -> Dict[str, Any]:
        """ORM -> 响应字典，附带学生姓名、教师姓名"""
        data = ScoreOut.model_validate(obj).model_dump()
        if obj.student is not None:
            data["student_name"] = obj.student.name
        if obj.teacher is not None:
            data["teacher_name"] = obj.teacher.name
        return data

    def _check_refs(
        self, db: Session, student_id: Optional[int], teacher_id: Optional[int]
    ) -> None:
        """校验学生、教师是否都存在"""
        if student_id is not None:
            crud_student.get_or_404(db, student_id)
        if teacher_id is not None:
            crud_teacher.get_or_404(db, teacher_id)

    # ----------------------------------------------------------
    # 业务方法（Controller 只调用这些）
    # ----------------------------------------------------------
    def search(
        self,
        db: Session,
        *,
        page: int = 1,
        page_size: int = 10,
        keyword: Optional[str] = None,
        student_id: Optional[int] = None,
        teacher_id: Optional[int] = None,
        subject: Optional[str] = None,
        include_deleted: bool = False,
    ) -> Dict[str, Any]:
        """分页查询成绩（按科目模糊搜索，可按学生/教师/科目过滤），items 已拼装"""
        filters = {}
        if student_id is not None:
            filters["student_id"] = student_id
        if teacher_id is not None:
            filters["teacher_id"] = teacher_id
        if subject is not None:
            filters["subject"] = subject
        result = self.get_multi(
            db,
            page=page,
            page_size=page_size,
            keyword=keyword,
            keyword_fields=["subject"],
            filters=filters or None,
            include_deleted=include_deleted,
        )
        result["items"] = [self._to_out(i) for i in result["items"]]
        return result

    def get_detail(
        self, db: Session, score_id: int, include_deleted: bool = False
    ) -> Dict[str, Any]:
        """查询单条成绩详情"""
        obj = self.get_or_404(db, score_id, include_deleted=include_deleted)
        return self._to_out(obj)

    def create_score(self, db: Session, obj_in: Any) -> Dict[str, Any]:
        """新增成绩（先校验学生、教师存在）"""
        self._check_refs(
            db,
            getattr(obj_in, "student_id", None),
            getattr(obj_in, "teacher_id", None),
        )
        obj = self.create(db, obj_in)
        obj = self.get_or_404(db, getattr(obj, "score_id"))
        return self._to_out(obj)

    def update_score(self, db: Session, score_id: int, obj_in: Any) -> Dict[str, Any]:
        """更新成绩（若改动 student_id/teacher_id 则校验存在）"""
        obj = self.get_or_404(db, score_id)
        changed = obj_in.model_dump(exclude_unset=True) if hasattr(obj_in, "model_dump") else dict(obj_in)
        if "student_id" in changed or "teacher_id" in changed:
            self._check_refs(db, changed.get("student_id"), changed.get("teacher_id"))
        obj = self.update(db, obj, obj_in)
        obj = self.get_or_404(db, score_id)
        return self._to_out(obj)

    def delete_score(self, db: Session, score_id: int) -> None:
        """逻辑删除成绩"""
        obj = self.get_or_404(db, score_id)
        self.soft_delete(db, obj)

    def restore_score(self, db: Session, score_id: int) -> Dict[str, Any]:
        """恢复已删除成绩（未被删除则拒绝）"""
        obj = self.get_or_404(db, score_id, include_deleted=True)
        if not obj.is_deleted:
            raise ConflictException(message="该成绩未被删除，无需恢复", code=400)
        obj = self.restore(db, obj)
        obj = self.get_or_404(db, score_id)
        return self._to_out(obj)


crud_score = CRUDScore()
