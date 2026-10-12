"""学生业务服务

承载学生域业务规则：
    - 新增 / 更新时若填写 class_id，校验班级必须存在
    - 恢复已被删除的学生前校验其确为已删除状态
    - 其余为对 Repository 的薄编排
"""
from typing import Optional

from sqlalchemy.orm import Session

from app.core.exceptions import ConflictException, NotFoundException
from app.repositories.class_ import class_repository
from app.repositories.student import student_repository


class StudentService:
    def search(
        self,
        db: Session,
        *,
        page: int = 1,
        page_size: int = 10,
        keyword: Optional[str] = None,
        class_id: Optional[int] = None,
        gender: Optional[str] = None,
        include_deleted: bool = False,
    ) -> dict:
        return student_repository.search(
            db,
            page=page,
            page_size=page_size,
            keyword=keyword,
            class_id=class_id,
            gender=gender,
            include_deleted=include_deleted,
        )

    def get_detail(self, db: Session, student_id: int, include_deleted: bool = False):
        return student_repository.get_detail(db, student_id, include_deleted=include_deleted)

    def create_student(self, db: Session, payload):
        self._check_class_exists(db, getattr(payload, "class_id", None))
        obj = student_repository.create(db, payload)
        return student_repository.get_or_404(db, getattr(obj, "student_id"))

    def update_student(self, db: Session, student_id: int, payload):
        obj = student_repository.get_or_404(db, student_id)
        changed = payload.model_dump(exclude_unset=True)
        if "class_id" in changed:
            self._check_class_exists(db, changed.get("class_id"))
        obj = student_repository.update(db, obj, payload)
        return student_repository.get_or_404(db, student_id)

    def delete_student(self, db: Session, student_id: int):
        obj = student_repository.get_or_404(db, student_id)
        return student_repository.soft_delete(db, obj)

    def restore_student(self, db: Session, student_id: int):
        obj = student_repository.get_or_404(db, student_id, include_deleted=True)
        if not obj.is_deleted:
            raise ConflictException(message="该学生未被删除，无需恢复", code=400)
        return student_repository.restore(db, obj)

    def _check_class_exists(self, db: Session, class_id: Optional[int]) -> None:
        """若指定了班级ID，校验班级是否存在"""
        if class_id is not None:
            class_repository.get_or_404(db, class_id)


student_service = StudentService()
