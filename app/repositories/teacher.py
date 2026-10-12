"""教师仓储（纯数据访问层）

仅负责与 teacher 表相关的读写。响应拼装在 View 层。
"""
from typing import Optional

from sqlalchemy.orm import Session

from app.repositories.base import RepositoryBase
from app.models.teacher import Teacher


class TeacherRepository(RepositoryBase[Teacher]):

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
        """分页查询老师（按姓名/职称/科目模糊搜索，可按科目过滤）"""
        filters = {}
        if subject is not None:
            filters["subject"] = subject
        return self.get_multi(
            db,
            page=page,
            page_size=page_size,
            keyword=keyword,
            keyword_fields=["name", "title", "subject"],
            filters=filters or None,
            include_deleted=include_deleted,
        )

    def get_detail(self, db: Session, teacher_id: int, include_deleted: bool = False) -> Teacher:
        """查询单个教师详情"""
        return self.get_or_404(db, teacher_id, include_deleted=include_deleted)


teacher_repository = TeacherRepository()
