"""成绩业务服务

承载成绩域业务规则：
    - 新增 / 更新时若填写 student_id / teacher_id，校验学生、教师必须存在
    - 恢复已被删除的成绩前校验其确为已删除状态
"""
from typing import Optional

from sqlalchemy.orm import Session

from app.core.exceptions import ConflictException
from app.repositories.score import score_repository


class ScoreService:
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
    ) -> dict:
        return score_repository.search(
            db,
            page=page,
            page_size=page_size,
            keyword=keyword,
            student_id=student_id,
            teacher_id=teacher_id,
            subject=subject,
            include_deleted=include_deleted,
        )

    def get_detail(self, db: Session, score_id: int, include_deleted: bool = False):
        return score_repository.get_detail(db, score_id, include_deleted=include_deleted)

    def create_score(self, db: Session, payload):
        score_repository._check_refs(
            db, getattr(payload, "student_id", None), getattr(payload, "teacher_id", None)
        )
        obj = score_repository.create(db, payload)
        return score_repository.get_or_404(db, getattr(obj, "score_id"))

    def update_score(self, db: Session, score_id: int, payload):
        obj = score_repository.get_or_404(db, score_id)
        changed = payload.model_dump(exclude_unset=True)
        if "student_id" in changed or "teacher_id" in changed:
            score_repository._check_refs(db, changed.get("student_id"), changed.get("teacher_id"))
        obj = score_repository.update(db, obj, payload)
        return score_repository.get_or_404(db, score_id)

    def delete_score(self, db: Session, score_id: int):
        obj = score_repository.get_or_404(db, score_id)
        return score_repository.soft_delete(db, obj)

    def restore_score(self, db: Session, score_id: int):
        obj = score_repository.get_or_404(db, score_id, include_deleted=True)
        if not obj.is_deleted:
            raise ConflictException(message="该成绩未被删除，无需恢复", code=400)
        return score_repository.restore(db, obj)


score_service = ScoreService()
