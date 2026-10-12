"""老师 CRUD（Model 层）

除通用数据访问外，本层承担教师响应的拼装。
"""
from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from app.core.exceptions import ConflictException
from app.crud.base import CRUDBase
from app.models.teacher import Teacher
from app.schemas.teacher import TeacherOut


class CRUDTeacher(CRUDBase[Teacher]):

    def __init__(self):
        super().__init__(
            Teacher,
            pk_field="teacher_id",
            unique_specs=[
                {
                    "fields": ("name",),
                    "message": "教师姓名「{name}」已存在，不可重复创建",
                },
            ],
        )

    # ----------------------------------------------------------
    # 响应拼装
    # ----------------------------------------------------------
    def _to_out(self, obj: Teacher) -> Dict[str, Any]:
        return TeacherOut.model_validate(obj).model_dump()

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
        subject: Optional[str] = None,
        include_deleted: bool = False,
    ) -> Dict[str, Any]:
        """分页查询老师（按姓名/职称/科目模糊搜索），items 已拼装"""
        filters = {}
        if subject is not None:
            filters["subject"] = subject
        result = self.get_multi(
            db,
            page=page,
            page_size=page_size,
            keyword=keyword,
            keyword_fields=["name", "title", "subject"],
            filters=filters or None,
            include_deleted=include_deleted,
        )
        result["items"] = [self._to_out(i) for i in result["items"]]
        return result

    def get_detail(
        self, db: Session, teacher_id: int, include_deleted: bool = False
    ) -> Dict[str, Any]:
        """查询单个教师详情"""
        obj = self.get_or_404(db, teacher_id, include_deleted=include_deleted)
        return self._to_out(obj)

    def create_teacher(self, db: Session, obj_in: Any) -> Dict[str, Any]:
        """新增教师"""
        obj = self.create(db, obj_in)
        return self._to_out(obj)

    def update_teacher(self, db: Session, teacher_id: int, obj_in: Any) -> Dict[str, Any]:
        """更新教师"""
        obj = self.get_or_404(db, teacher_id)
        obj = self.update(db, obj, obj_in)
        return self._to_out(obj)

    def delete_teacher(self, db: Session, teacher_id: int) -> None:
        """逻辑删除教师"""
        obj = self.get_or_404(db, teacher_id)
        self.soft_delete(db, obj)

    def restore_teacher(self, db: Session, teacher_id: int) -> Dict[str, Any]:
        """恢复已删除教师（未被删除则拒绝）"""
        obj = self.get_or_404(db, teacher_id, include_deleted=True)
        if not obj.is_deleted:
            raise ConflictException(message="该教师未被删除，无需恢复", code=400)
        obj = self.restore(db, obj)
        return self._to_out(obj)


crud_teacher = CRUDTeacher()
