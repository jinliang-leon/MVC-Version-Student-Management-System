"""统计分析仓储（纯数据访问层）

承接原 api/stats.py 中的全部聚合逻辑：本类只负责跨实体的只读 SQL 聚合，
每个方法返回与重构前接口完全一致的 data 结构。业务含义的校验（若有）在
app/services/stats_service.py，这里仅做数据读取。
"""
from typing import Any, Dict, List, Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.class_ import Class
from app.models.employment import Employment
from app.models.score import Score
from app.models.student import Student
from app.models.teacher import Teacher


class StatsRepository:
    """跨实体的聚合统计（无单一 ORM 模型，故不继承 RepositoryBase）"""

    # ----------------------------------------------------------
    # 总体概览
    # ----------------------------------------------------------
    def overview(self, db: Session) -> Dict[str, Any]:
        """班级数/学生数/教师数/成绩数/就业数 + 平均分 + 就业率"""

        def count(model):
            return db.execute(
                select(func.count()).select_from(model).where(model.is_deleted == False)  # noqa: E712
            ).scalar_one()

        class_count = count(Class)
        student_count = count(Student)
        teacher_count = count(Teacher)
        score_count = count(Score)
        employment_count = count(Employment)

        avg_score = db.execute(
            select(func.avg(Score.score)).where(Score.is_deleted == False)  # noqa: E712
        ).scalar()

        employed_students = db.execute(
            select(func.count(func.distinct(Employment.student_id))).where(
                Employment.is_deleted == False  # noqa: E712
            )
        ).scalar_one()

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
        """学生总数、已就业人数、就业率，可按班级过滤"""
        stu_stmt = select(Student.student_id).where(Student.is_deleted == False)  # noqa: E712
        if class_id is not None:
            stu_stmt = stu_stmt.where(Student.class_id == class_id)
        student_ids = list(db.execute(stu_stmt).scalars().all())

        total = len(student_ids)
        if total == 0:
            return {
                "student_count": 0,
                "employed_count": 0,
                "employment_rate": 0.0,
            }

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


stats_repository = StatsRepository()
