"""就业仓储（纯数据访问层）

仅负责与 employment 表相关的读写：分页查询、按主键查询、新增 / 更新 / 逻辑删除 /
恢复，以及关联存在性校验（student_id 必须存在）。响应拼装（student_name）在 View 层。
"""
from typing import Optional

from sqlalchemy.orm import Session

from app.repositories.base import RepositoryBase
from app.repositories.student import student_repository
from app.models.employment import Employment


class EmploymentRepository(RepositoryBase[Employment]):

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
        """分页查询就业记录（按公司/岗位模糊搜索，可按学生/公司过滤）"""
        filters = {}
        if student_id is not None:
            filters["student_id"] = student_id
        if company is not None:
            filters["company"] = company
        return self.get_multi(
            db,
            page=page,
            page_size=page_size,
            keyword=keyword,
            keyword_fields=["company", "position"],
            filters=filters or None,
            include_deleted=include_deleted,
        )

    def get_detail(
        self, db: Session, employment_id: int, include_deleted: bool = False
    ) -> Employment:
        """查询单条就业记录详情"""
        return self.get_or_404(db, employment_id, include_deleted=include_deleted)

    def _check_student(self, db: Session, student_id: Optional[int]) -> None:
        """校验学生是否存在（关联存在性校验，纯数据访问）"""
        if student_id is not None:
            student_repository.get_or_404(db, student_id)


employment_repository = EmploymentRepository()
