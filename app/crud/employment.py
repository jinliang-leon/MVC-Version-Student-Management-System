"""就业 CRUD（Model 层）

除通用数据访问外，本层承担就业记录相关的业务规则与响应拼装：
    - 关联校验：student_id 必须对应存在的学生
    - 响应拼装：附带 student_name
"""
from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from app.core.exceptions import ConflictException
from app.crud.base import CRUDBase
from app.crud.student import crud_student
from app.models.employment import Employment
from app.schemas.employment import EmploymentOut


class CRUDEmployment(CRUDBase[Employment]):

    def __init__(self):
        super().__init__(
            Employment,
            pk_field="employment_id",
            unique_specs=[
                {
                    "fields": ("student_id", "company"),
                    "message": "学生 {student_id} 已有「{company}」的就业记录，不可重复创建",
                },
            ],
        )

    # ----------------------------------------------------------
    # 响应拼装 / 关联校验
    # ----------------------------------------------------------
    def _to_out(self, obj: Employment) -> Dict[str, Any]:
        """ORM -> 响应字典，附带学生姓名"""
        data = EmploymentOut.model_validate(obj).model_dump()
        if obj.student is not None:
            data["student_name"] = obj.student.name
        return data

    def _check_student(self, db: Session, student_id: Optional[int]) -> None:
        """校验学生是否存在"""
        if student_id is not None:
            crud_student.get_or_404(db, student_id)

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
        company: Optional[str] = None,
        include_deleted: bool = False,
    ) -> Dict[str, Any]:
        """分页查询就业记录（按公司/岗位模糊搜索），items 已拼装"""
        filters = {}
        if student_id is not None:
            filters["student_id"] = student_id
        if company is not None:
            filters["company"] = company
        result = self.get_multi(
            db,
            page=page,
            page_size=page_size,
            keyword=keyword,
            keyword_fields=["company", "position"],
            filters=filters or None,
            include_deleted=include_deleted,
        )
        result["items"] = [self._to_out(i) for i in result["items"]]
        return result

    def get_detail(
        self, db: Session, employment_id: int, include_deleted: bool = False
    ) -> Dict[str, Any]:
        """查询单条就业记录详情"""
        obj = self.get_or_404(db, employment_id, include_deleted=include_deleted)
        return self._to_out(obj)

    def create_employment(self, db: Session, obj_in: Any) -> Dict[str, Any]:
        """新增就业记录（先校验学生存在）"""
        self._check_student(db, getattr(obj_in, "student_id", None))
        obj = self.create(db, obj_in)
        obj = self.get_or_404(db, getattr(obj, "employment_id"))
        return self._to_out(obj)

    def update_employment(
        self, db: Session, employment_id: int, obj_in: Any
    ) -> Dict[str, Any]:
        """更新就业记录（若改动 student_id 则校验学生存在）"""
        obj = self.get_or_404(db, employment_id)
        changed = obj_in.model_dump(exclude_unset=True) if hasattr(obj_in, "model_dump") else dict(obj_in)
        if "student_id" in changed:
            self._check_student(db, changed.get("student_id"))
        obj = self.update(db, obj, obj_in)
        obj = self.get_or_404(db, employment_id)
        return self._to_out(obj)

    def delete_employment(self, db: Session, employment_id: int) -> None:
        """逻辑删除就业记录"""
        obj = self.get_or_404(db, employment_id)
        self.soft_delete(db, obj)

    def restore_employment(self, db: Session, employment_id: int) -> Dict[str, Any]:
        """恢复已删除就业记录（未被删除则拒绝）"""
        obj = self.get_or_404(db, employment_id, include_deleted=True)
        if not obj.is_deleted:
            raise ConflictException(message="该就业记录未被删除，无需恢复", code=400)
        obj = self.restore(db, obj)
        obj = self.get_or_404(db, employment_id)
        return self._to_out(obj)


crud_employment = CRUDEmployment()
