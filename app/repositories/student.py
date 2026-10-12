"""学生仓储（纯数据访问层）

仅负责与 student 表相关的读写：分页查询、按主键查询、新增 / 更新 / 逻辑删除 / 恢复。
关联校验（class_id 必须存在）、响应拼装（class_name）分别在 Service 与 View 层。
"""
from typing import Optional

from sqlalchemy.orm import Session

from app.repositories.base import RepositoryBase
from app.models.student import Student


class StudentRepository(RepositoryBase[Student]):

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
        """分页查询学生（按姓名模糊搜索，可按班级/性别过滤）"""
        filters = {}
        if class_id is not None:
            filters["class_id"] = class_id
        if gender is not None:
            filters["gender"] = gender
        return self.get_multi(
            db,
            page=page,
            page_size=page_size,
            keyword=keyword,
            keyword_fields=["name"],
            filters=filters or None,
            include_deleted=include_deleted,
        )

    def get_detail(self, db: Session, student_id: int, include_deleted: bool = False) -> Student:
        """查询单个学生详情"""
        return self.get_or_404(db, student_id, include_deleted=include_deleted)


student_repository = StudentRepository()
