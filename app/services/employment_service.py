"""就业业务服务

承载就业域业务规则：
    - 新增 / 更新时若填写 student_id，校验学生必须存在
    - 恢复已被删除的就业记录前校验其确为已删除状态
"""
from typing import Optional

from sqlalchemy.orm import Session

from app.core.exceptions import ConflictException
from app.repositories.employment import employment_repository


class EmploymentService:
    def search(
        self,
        db: Session,
        *,
        page: int = 1,
        page_size: int = 10,
        keyword: Optional[str] = None,
        student_id: Optional[int] = None,
        company: Optional[str] = None,
        include_deleted: bool = False,
    ) -> dict:
        return employment_repository.search(
            db,
            page=page,
            page_size=page_size,
            keyword=keyword,
            student_id=student_id,
            company=company,
            include_deleted=include_deleted,
        )

    def get_detail(self, db: Session, employment_id: int, include_deleted: bool = False):
        return employment_repository.get_detail(db, employment_id, include_deleted=include_deleted)

    def create_employment(self, db: Session, payload):
        employment_repository._check_student(db, getattr(payload, "student_id", None))
        obj = employment_repository.create(db, payload)
        return employment_repository.get_or_404(db, getattr(obj, "employment_id"))

    def update_employment(self, db: Session, employment_id: int, payload):
        obj = employment_repository.get_or_404(db, employment_id)
        changed = payload.model_dump(exclude_unset=True)
        if "student_id" in changed:
            employment_repository._check_student(db, changed.get("student_id"))
        obj = employment_repository.update(db, obj, payload)
        return employment_repository.get_or_404(db, employment_id)

    def delete_employment(self, db: Session, employment_id: int):
        obj = employment_repository.get_or_404(db, employment_id)
        return employment_repository.soft_delete(db, obj)

    def restore_employment(self, db: Session, employment_id: int):
        obj = employment_repository.get_or_404(db, employment_id, include_deleted=True)
        if not obj.is_deleted:
            raise ConflictException(message="该就业记录未被删除，无需恢复", code=400)
        return employment_repository.restore(db, obj)


employment_service = EmploymentService()
