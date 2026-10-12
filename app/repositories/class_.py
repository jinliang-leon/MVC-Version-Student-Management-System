"""班级仓储（纯数据访问层）

仅负责与 class 表相关的读写：分页查询、按主键查询（预加载学生用于统计人数）、
新增 / 更新 / 逻辑删除 / 恢复，以及统计班级下学生数。业务规则（删除前检查是否还有
学生）在 app/services/class_service.py。
"""
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.core.exceptions import NotFoundException
from app.repositories.base import RepositoryBase
from app.models.class_ import Class
from app.models.student import Student


class ClassRepository(RepositoryBase[Class]):

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

    def get(self, db: Session, obj_id: int, include_deleted: bool = False) -> Optional[Class]:
        """按主键查询单条，预加载 students（供 student_count 使用）"""
        stmt = select(Class).options(selectinload(Class.students)).where(
            Class.class_id == obj_id
        )
        if not include_deleted:
            stmt = stmt.where(Class.is_deleted == False)  # noqa: E712
        return db.execute(stmt).scalars().first()

    def search(
        self,
        db: Session,
        *,
        page: int = 1,
        page_size: int = 10,
        keyword: Optional[str] = None,
        include_deleted: bool = False,
    ) -> dict:
        """分页查询班级（按名称/年级/备注模糊搜索）"""
        return self.get_multi(
            db,
            page=page,
            page_size=page_size,
            keyword=keyword,
            keyword_fields=["class_name", "grade", "remark"],
            include_deleted=include_deleted,
        )

    def get_detail(self, db: Session, class_id: int, include_deleted: bool = False) -> Class:
        """查询单个班级详情（预加载 students）"""
        obj = self.get(db, class_id, include_deleted=include_deleted)
        if obj is None:
            raise NotFoundException(f"班级中不存在 ID = {class_id} 的记录")
        return obj

    def count_students(self, db: Session, class_id: int) -> int:
        """统计某班级下的学生人数（仅未删除）"""
        stmt = (
            select(func.count())
            .select_from(Student)
            .where(Student.class_id == class_id, Student.is_deleted == False)  # noqa: E712
        )
        return db.execute(stmt).scalar_one()

    def student_ids(self, db: Session, class_id: int) -> list[int]:
        """获取班级下所有学生ID"""
        stmt = select(Student.student_id).where(
            Student.class_id == class_id, Student.is_deleted == False  # noqa: E712
        )
        return list(db.execute(stmt).scalars().all())


class_repository = ClassRepository()
