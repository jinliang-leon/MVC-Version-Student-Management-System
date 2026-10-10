"""学生 CRUD（Model 层）

除通用数据访问外，本层承担学生相关的业务规则与响应拼装：
    - 关联校验：class_id 若填写则必须对应存在的班级
    - 响应拼装：附带 class_name
"""
from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from app.core.exceptions import ConflictException
from app.crud.base import CRUDBase
from app.crud.class_ import crud_class
from app.models.student import Student
from app.schemas.student import StudentOut


class CRUDStudent(CRUDBase[Student]):

    def __init__(self):
        super().__init__(
            Student,
            pk_field="student_id",
            unique_specs=[
                {
                    "fields": ("name",),
                    "message": "学生姓名「{name}」已存在，不可重复创建",
                },
            ],
        )

    # ----------------------------------------------------------
    # 响应拼装 / 关联校验
    # ----------------------------------------------------------
    def _to_out(self, obj: Student) -> Dict[str, Any]:
        """ORM -> 响应字典，附带 class_name"""
        data = StudentOut.model_validate(obj).model_dump()
        if obj.class_ is not None:
            data["class_name"] = obj.class_.class_name
        return data

    def _check_class_exists(self, db: Session, class_id: Optional[int]) -> None:
        """若指定了班级ID，校验班级是否存在"""
        if class_id is not None:
            crud_class.get_or_404(db, class_id)

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
        class_id: Optional[int] = None,
        gender: Optional[str] = None,
        include_deleted: bool = False,
    ) -> Dict[str, Any]:
        """分页查询学生（按姓名模糊搜索，可按班级/性别过滤），items 已拼装"""
        filters = {}
        if class_id is not None:
            filters["class_id"] = class_id
        if gender is not None:
            filters["gender"] = gender
        result = self.get_multi(
            db,
            page=page,
            page_size=page_size,
            keyword=keyword,
            keyword_fields=["name"],
            filters=filters or None,
            include_deleted=include_deleted,
        )
        result["items"] = [self._to_out(i) for i in result["items"]]
        return result

    def get_detail(
        self, db: Session, student_id: int, include_deleted: bool = False
    ) -> Dict[str, Any]:
        """查询单个学生详情"""
        obj = self.get_or_404(db, student_id, include_deleted=include_deleted)
        return self._to_out(obj)

    def create_student(self, db: Session, obj_in: Any) -> Dict[str, Any]:
        """新增学生（先校验班级存在）"""
        self._check_class_exists(db, getattr(obj_in, "class_id", None))
        obj = self.create(db, obj_in)
        obj = self.get_or_404(db, getattr(obj, "student_id"))
        return self._to_out(obj)

    def update_student(self, db: Session, student_id: int, obj_in: Any) -> Dict[str, Any]:
        """更新学生（若改动 class_id 则校验班级存在）"""
        obj = self.get_or_404(db, student_id)
        changed = obj_in.model_dump(exclude_unset=True) if hasattr(obj_in, "model_dump") else dict(obj_in)
        if "class_id" in changed:
            self._check_class_exists(db, changed.get("class_id"))
        obj = self.update(db, obj, obj_in)
        obj = self.get_or_404(db, student_id)
        return self._to_out(obj)

    def delete_student(self, db: Session, student_id: int) -> None:
        """逻辑删除学生"""
        obj = self.get_or_404(db, student_id)
        self.soft_delete(db, obj)

    def restore_student(self, db: Session, student_id: int) -> Dict[str, Any]:
        """恢复已删除学生（未被删除则拒绝）"""
        obj = self.get_or_404(db, student_id, include_deleted=True)
        if not obj.is_deleted:
            raise ConflictException(message="该学生未被删除，无需恢复", code=400)
        obj = self.restore(db, obj)
        obj = self.get_or_404(db, student_id)
        return self._to_out(obj)


crud_student = CRUDStudent()
