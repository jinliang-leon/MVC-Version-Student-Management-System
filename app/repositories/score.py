"""成绩仓储（纯数据访问层）

仅负责与 score 表相关的读写：分页查询、按主键查询、新增 / 更新 / 逻辑删除 / 恢复，
以及关联存在性校验（student_id / teacher_id 必须存在）。响应拼装（student_name /
teacher_name）在 View 层。
"""
from typing import Optional

from sqlalchemy.orm import Session

from app.repositories.base import RepositoryBase
from app.repositories.student import student_repository
from app.repositories.teacher import teacher_repository
from app.models.score import Score


class ScoreRepository(RepositoryBase[Score]):

    def __init__(self):
        super().__init__(
            Score,
            pk_field="score_id",
            unique_specs=[
                {
                    "fields": ("student_id", "subject"),
                    "message": "学生 {student_id} 在科目「{subject}」已有成绩记录，不可重复录入",
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
        teacher_id: Optional[int] = None,
        subject: Optional[str] = None,
        include_deleted: bool = False,
    ) -> dict:
        """分页查询成绩（按科目模糊搜索，可按学生/教师/科目过滤）"""
        filters = {}
        if student_id is not None:
            filters["student_id"] = student_id
        if teacher_id is not None:
            filters["teacher_id"] = teacher_id
        if subject is not None:
            filters["subject"] = subject
        return self.get_multi(
            db,
            page=page,
            page_size=page_size,
            keyword=keyword,
            keyword_fields=["subject"],
            filters=filters or None,
            include_deleted=include_deleted,
        )

    def get_detail(self, db: Session, score_id: int, include_deleted: bool = False) -> Score:
        """查询单条成绩详情"""
        return self.get_or_404(db, score_id, include_deleted=include_deleted)

    def _check_refs(
        self, db: Session, student_id: Optional[int], teacher_id: Optional[int]
    ) -> None:
        """校验学生、教师是否都存在（关联存在性校验，纯数据访问）"""
        if student_id is not None:
            student_repository.get_or_404(db, student_id)
        if teacher_id is not None:
            teacher_repository.get_or_404(db, teacher_id)


score_repository = ScoreRepository()
