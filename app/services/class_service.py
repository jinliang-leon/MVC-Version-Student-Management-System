"""班级业务服务

承载班级域业务规则：
    - 删除前检查是否还有学生（有则拒绝，返回 400）
    - 其余为对 Repository 的薄编排
"""
from typing import Optional

from sqlalchemy.orm import Session

from app.core.exceptions import ConflictException
from app.repositories.class_ import class_repository


class ClassService:
    def search(
        self,
        db: Session,
        *,
        page: int = 1,
        page_size: int = 10,
        keyword: Optional[str] = None,
        include_deleted: bool = False,
    ) -> dict:
        return class_repository.search(
            db, page=page, page_size=page_size, keyword=keyword, include_deleted=include_deleted
        )

    def get_detail(self, db: Session, class_id: int, include_deleted: bool = False):
        return class_repository.get_detail(db, class_id, include_deleted=include_deleted)

    def create_class(self, db: Session, payload):
        return class_repository.create(db, payload)

    def update_class(self, db: Session, class_id: int, payload):
        obj = class_repository.get_or_404(db, class_id)
        return class_repository.update(db, obj, payload)

    def delete_class(self, db: Session, class_id: int):
        """逻辑删除班级；班级下若还有学生则拒绝"""
        obj = class_repository.get_or_404(db, class_id)
        self.ensure_deletable(db, class_id)
        return class_repository.soft_delete(db, obj)

    def restore_class(self, db: Session, class_id: int):
        obj = class_repository.get_or_404(db, class_id, include_deleted=True)
        if not obj.is_deleted:
            raise ConflictException(message="该班级未被删除，无需恢复", code=400)
        return class_repository.restore(db, obj)

    def ensure_deletable(self, db: Session, class_id: int) -> None:
        """删除前校验：班级下若还有学生，拒绝删除"""
        n = class_repository.count_students(db, class_id)
        if n > 0:
            raise ConflictException(
                message=f"该班级下还有 {n} 名学生，无法删除。请先转移或删除这些学生。",
                code=400,
                data={"class_id": class_id, "student_count": n},
            )


class_service = ClassService()
