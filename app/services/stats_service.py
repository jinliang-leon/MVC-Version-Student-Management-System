"""统计分析业务服务

统计分析均为只读聚合，无业务变更，本服务直接委托 StatsRepository。
"""
from typing import Optional

from sqlalchemy.orm import Session

from app.repositories.stats import stats_repository


class StatsService:
    def overview(self, db: Session) -> dict:
        return stats_repository.overview(db)

    def class_count(self, db: Session) -> list:
        return stats_repository.class_count(db)

    def avg_score(
        self,
        db: Session,
        *,
        student_id: Optional[int] = None,
        class_id: Optional[int] = None,
        subject: Optional[str] = None,
    ) -> list:
        return stats_repository.avg_score(
            db, student_id=student_id, class_id=class_id, subject=subject
        )

    def employment_rate(self, db: Session, class_id: Optional[int] = None) -> dict:
        return stats_repository.employment_rate(db, class_id=class_id)

    def score_ranking(
        self, db: Session, *, subject: Optional[str] = None, limit: int = 10
    ) -> list:
        return stats_repository.score_ranking(db, subject=subject, limit=limit)

    def top_salary(self, db: Session, *, limit: int = 10) -> list:
        return stats_repository.top_salary(db, limit=limit)


stats_service = StatsService()
