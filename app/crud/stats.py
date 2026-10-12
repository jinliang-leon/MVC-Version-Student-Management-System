"""统计分析 CRUD（Model 层）

承接原 api/stats.py 中的全部聚合逻辑：控制器不再直接书写 SQL。
每个方法返回与重构前接口完全一致的 data 结构。
"""
from typing import Any, Dict, List, Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.class_ import Class
from app.models.employment import Employment
from app.models.score import Score
from app.models.student import Student
from app.models.teacher import Teacher


class CRUDStats:
    """跨实体的聚合统计（无单一 ORM 模型，故不继承 CRUDBase）"""

    # ----------------------------------------------------------
    # 总体概览
    # ----------------------------------------------------------
    def overview(self, db: Session) -> Dict[str, Any]:
        """班级数/学生数/教师数/成绩数/就业数 + 平均分 + 就业率"""

        # 统计某张表「未删除」记录数：五张表逻辑相同，抽成闭包复用。
        def count(model):
            return db.execute(
                select(func.count()).select_from(model).where(model.is_deleted == False)  # noqa: E712
            ).scalar_one()

        class_count = count(Class)
        student_count = count(Student)
        teacher_count = count(Teacher)
        score_count = count(Score)
        employment_count = count(Employment)

        # 全表平均分：无任何成绩时 AVG 返回 NULL，下方转 None 输出为 null（历史行为）。
        avg_score = db.execute(
            select(func.avg(Score.score)).where(Score.is_deleted == False)  # noqa: E712
        ).scalar()

        # 已就业学生数：同一学生可能有多条就业记录，用 DISTINCT 去重后计数。
        employed_students = db.execute(
            select(func.count(func.distinct(Employment.student_id))).where(
                Employment.is_deleted == False  # noqa: E712
            )
        ).scalar_one()

        # 就业率 = 已就业(去重) / 学生总数 × 100，保留两位；学生数为 0 时记为 0 避免除零。
        employment_rate = (
            round(employed_students / student_count * 100, 2) if student_count else 0.0
        )

        return {
            "class_count": class_count,
            "student_count": student_count,
            "teacher_count": teacher_count,
            "score_count": score_count,
            "employment_count": employment_count,
            "avg_score": round(float(avg_score), 2) if avg_score is not None else None,
            "employed_student_count": employed_students,
            "employment_rate": employment_rate,
        }

    # ----------------------------------------------------------
    # 各班级人数
    # ----------------------------------------------------------
    def class_count(self, db: Session) -> List[Dict[str, Any]]:
        """每个班级的名称、年级及学生人数，按人数降序"""
        # 关键点：用 LEFT JOIN（outerjoin）而非内连接，并把「未删除」条件放进 ON 子句，
        # 这样没有学生的班级也会以 student_count=0 出现在结果里（COUNT 空集返回 0）。
        stmt = (
            select(
                Class.class_id,
                Class.class_name,
                Class.grade,
                func.count(Student.student_id).label("student_count"),
            )
            .select_from(Class)
            .outerjoin(
                Student,
                (Student.class_id == Class.class_id) & (Student.is_deleted == False),  # noqa: E712
            )
            .where(Class.is_deleted == False)  # noqa: E712
            .group_by(Class.class_id, Class.class_name, Class.grade)
            .order_by(func.count(Student.student_id).desc())
        )
        rows = db.execute(stmt).all()
        return [
            {
                "class_id": r.class_id,
                "class_name": r.class_name,
                "grade": r.grade,
                "student_count": r.student_count,
            }
            for r in rows
        ]

    # ----------------------------------------------------------
    # 平均分
    # ----------------------------------------------------------
    def avg_score(
        self,
        db: Session,
        *,
        student_id: Optional[int] = None,
        class_id: Optional[int] = None,
        subject: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """按科目统计平均分，可选按学生ID/班级ID/科目过滤"""
        # 内连接 Student：即便按 class_id 过滤（班级信息在 student 表）也能正确关联；
        # 聚合函数同时给出平均/最高/最低分与记录条数，便于前端一次渲染。
        stmt = (
            select(
                Score.subject,
                func.avg(Score.score).label("avg_score"),
                func.count(Score.score_id).label("count"),
                func.max(Score.score).label("max_score"),
                func.min(Score.score).label("min_score"),
            )
            .select_from(Score)
            .join(Student, Student.student_id == Score.student_id)
            .where(Score.is_deleted == False)  # noqa: E712
        )
        # 三个可选过滤条件逐层叠加，未传则不加对应 WHERE，等价于「不过滤」。
        if student_id is not None:
            stmt = stmt.where(Score.student_id == student_id)
        if class_id is not None:
            stmt = stmt.where(Student.class_id == class_id)
        if subject is not None:
            stmt = stmt.where(Score.subject == subject)
        stmt = stmt.group_by(Score.subject).order_by(func.avg(Score.score).desc())

        rows = db.execute(stmt).all()
        return [
            {
                "subject": r.subject,
                "avg_score": round(float(r.avg_score), 2),
                "max_score": float(r.max_score),
                "min_score": float(r.min_score),
                "record_count": r.count,
            }
            for r in rows
        ]

    # ----------------------------------------------------------
    # 就业率
    # ----------------------------------------------------------
    def employment_rate(
        self, db: Session, class_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """学生总数、已就业人数、就业率，可按班级过滤

        注意：学生数为 0 时历史实现不返回 unemployed_count 字段，此处保持原样。
        """
        # 第一步：先捞出目标范围内「未删除」学生的 ID 列表（可选按班级过滤）。
        stu_stmt = select(Student.student_id).where(Student.is_deleted == False)  # noqa: E712
        if class_id is not None:
            stu_stmt = stu_stmt.where(Student.class_id == class_id)
        student_ids = list(db.execute(stu_stmt).scalars().all())

        total = len(student_ids)
        # 无学生时提前返回：unemployed_count 键不出现，与历史接口返回值保持一致。
        if total == 0:
            return {
                "student_count": 0,
                "employed_count": 0,
                "employment_rate": 0.0,
            }

        # 第二步：在已筛选学生里统计「已就业（去重）」人数，再据此算就业率。
        emp_stmt = (
            select(func.count(func.distinct(Employment.student_id)))
            .select_from(Employment)
            .where(
                Employment.is_deleted == False,  # noqa: E712
                Employment.student_id.in_(student_ids),
            )
        )
        employed = db.execute(emp_stmt).scalar_one()

        return {
            "student_count": total,
            "employed_count": employed,
            "unemployed_count": total - employed,
            "employment_rate": round(employed / total * 100, 2),
        }

    # ----------------------------------------------------------
    # 成绩排行榜
    # ----------------------------------------------------------
    def score_ranking(
        self, db: Session, *, subject: Optional[str] = None, limit: int = 10
    ) -> List[Dict[str, Any]]:
        """按分数降序的成绩排名，可选按科目过滤"""
        # outerjoin Class：学生可能未分班，此时 class_name 为 NULL，不能因内连接而丢失该行。
        stmt = (
            select(
                Score.score_id,
                Score.subject,
                Score.score,
                Student.student_id,
                Student.name.label("student_name"),
                Class.class_name,
            )
            .select_from(Score)
            .join(Student, Student.student_id == Score.student_id)
            .outerjoin(Class, Class.class_id == Student.class_id)
            .where(Score.is_deleted == False)  # noqa: E712
        )
        if subject is not None:
            stmt = stmt.where(Score.subject == subject)
        stmt = stmt.order_by(Score.score.desc()).limit(limit)

        rows = db.execute(stmt).all()
        return [
            {
                "rank": idx + 1,
                "student_id": r.student_id,
                "student_name": r.student_name,
                "class_name": r.class_name,
                "subject": r.subject,
                "score": r.score,
            }
            for idx, r in enumerate(rows)
        ]

    # ----------------------------------------------------------
    # 高薪就业榜
    # ----------------------------------------------------------
    def top_salary(self, db: Session, *, limit: int = 10) -> List[Dict[str, Any]]:
        """按薪资降序的就业记录"""
        # salary.isnot(None)：薪资为空（未填写）的记录不参与排序榜单。
        stmt = (
            select(
                Employment.employment_id,
                Employment.company,
                Employment.position,
                Employment.salary,
                Employment.employ_date,
                Student.student_id,
                Student.name.label("student_name"),
            )
            .select_from(Employment)
            .join(Student, Student.student_id == Employment.student_id)
            .where(
                Employment.is_deleted == False,  # noqa: E712
                Employment.salary.isnot(None),
            )
            .order_by(Employment.salary.desc())
            .limit(limit)
        )
        rows = db.execute(stmt).all()
        return [
            {
                "rank": idx + 1,
                "student_id": r.student_id,
                "student_name": r.student_name,
                "company": r.company,
                "position": r.position,
                "salary": r.salary,
                "employ_date": r.employ_date.isoformat() if r.employ_date else None,
            }
            for idx, r in enumerate(rows)
        ]


crud_stats = CRUDStats()
