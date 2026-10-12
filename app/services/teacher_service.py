"""教师业务服务

教师域业务较简单，本服务主要做对 Repository 的薄编排。
"""
from typing import Optional

from sqlalchemy.orm import Session

from app.core.exceptions import ConflictException
from app.repositories.teacher import teacher_repository


class TeacherService:
    def search(
        self,
        db: Session,
        *,
        page: int = 1,
        page_size: int = 10,
        keyword: Optional[str] = None,
        subject: Optional[str] = None,
        include_deleted: bool = False,
    ) -> dict:
        return teacher_repository.search(
            db,
            page=page,
            page_size=page_size,
            keyword=keyword,
            subject=subject,
            include_deleted=include_deleted,
        )

    def get_detail(self, db: Session, teacher_id: int, include_deleted: bool = False):
        return teacher_repository.get_detail(db, teacher_id, include_deleted=include_deleted)

    def create_teacher(self, db: Session, payload):
        return teacher_repository.create(db, payload)

    def update_teacher(self, db: Session, teacher_id: int, payload):
        obj = teacher_repository.get_or_404(db, teacher_id)
        return teacher_repository.update(db, obj, payload)

    def delete_teacher(self, db: Session, teacher_id: int):
        obj = teacher_repository.get_or_404(db, teacher_id)
        return teacher_repository.soft_delete(db, obj)

    def restore_teacher(self, db: Session, teacher_id: int):
        obj = teacher_repository.get_or_404(db, teacher_id, include_deleted=True)
        if not obj.is_deleted:
            raise ConflictException(message="该教师未被删除，无需恢复", code=400)
        return teacher_repository.restore(db, obj)


teacher_service = TeacherService()
