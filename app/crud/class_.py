"""班级 CRUD（Model 层）

除通用数据访问外，本层承担班级相关的业务规则与响应拼装：
    - search/get_detail/create_class/update_class/restore_class 直接返回拼装好的响应字典
    - delete_class：删除前检查是否还有学生，有则拒绝（Q4 方案 A）
"""
from typing import Any, Dict, List, Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictException
from app.crud.base import CRUDBase
from app.models.class_ import Class
from app.models.student import Student
from app.schemas.class_ import ClassOut


class CRUDClass(CRUDBase[Class]):

    def __init__(self):
        super().__init__(
            Class,
            pk_field="class_id",
            unique_specs=[
                {
                    "fields": ("class_name",),
                    "message": "班级名称「{class_name}」已存在，不可重复创建",
                },
            ],
        )

    # ----------------------------------------------------------
    # 响应拼装
    # ----------------------------------------------------------
    def _to_out(self, obj: Class) -> Dict[str, Any]:
        """ORM -> 响应字典，附带 student_count"""
        data = ClassOut.model_validate(obj).model_dump()
        data["student_count"] = len(obj.students) if obj.students is not None else 0
        return data

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
        include_deleted: bool = False,
    ) -> Dict[str, Any]:
        """分页查询班级（按名称/年级/备注模糊搜索），items 已拼装为响应字典"""
        result = self.get_multi(
            db,
            page=page,
            page_size=page_size,
            keyword=keyword,
            keyword_fields=["class_name", "grade", "remark"],
            include_deleted=include_deleted,
        )
        result["items"] = [self._to_out(i) for i in result["items"]]
        return result

    def get_detail(
        self, db: Session, class_id: int, include_deleted: bool = False
    ) -> Dict[str, Any]:
        """查询单个班级详情"""
        obj = self.get_or_404(db, class_id, include_deleted=include_deleted)
        return self._to_out(obj)

    def create_class(self, db: Session, obj_in: Any) -> Dict[str, Any]:
        """新增班级"""
        obj = self.create(db, obj_in)
        return self._to_out(obj)

    def update_class(self, db: Session, class_id: int, obj_in: Any) -> Dict[str, Any]:
        """更新班级"""
        obj = self.get_or_404(db, class_id)
        obj = self.update(db, obj, obj_in)
        return self._to_out(obj)

    def delete_class(self, db: Session, class_id: int) -> None:
        """逻辑删除班级；班级下若还有学生则拒绝（Q4 方案 A）"""
        obj = self.get_or_404(db, class_id)
        self.ensure_deletable(db, class_id)
        self.soft_delete(db, obj)

    def restore_class(self, db: Session, class_id: int) -> Dict[str, Any]:
        """恢复已删除班级（未被删除则拒绝）"""
        obj = self.get_or_404(db, class_id, include_deleted=True)
        if not obj.is_deleted:
            raise ConflictException(message="该班级未被删除，无需恢复", code=400)
        obj = self.restore(db, obj)
        return self._to_out(obj)

    # ----------------------------------------------------------
    # 关联查询 / 规则
    # ----------------------------------------------------------
    def count_students(self, db: Session, class_id: int) -> int:
        """统计某班级下的学生人数（仅未删除）"""
        stmt = (
            select(func.count())
            .select_from(Student)
            .where(Student.class_id == class_id, Student.is_deleted == False)  # noqa: E712
        )
        return db.execute(stmt).scalar_one()

    def ensure_deletable(self, db: Session, class_id: int) -> None:
        """删除前校验：班级下若还有学生，拒绝删除（Q4 方案 A）"""
        n = self.count_students(db, class_id)
        if n > 0:
            raise ConflictException(
                message=f"该班级下还有 {n} 名学生，无法删除。请先转移或删除这些学生。",
                code=400,
                data={"class_id": class_id, "student_count": n},
            )

    def student_ids(self, db: Session, class_id: int) -> List[int]:
        """获取班级下所有学生ID"""
        stmt = select(Student.student_id).where(
            Student.class_id == class_id, Student.is_deleted == False  # noqa: E712
        )
        return list(db.execute(stmt).scalars().all())


crud_class = CRUDClass()
