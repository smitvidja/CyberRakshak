from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import ReportedSuspect


class ReportedSuspectRepository:
    @staticmethod
    def add(session: Session, report: ReportedSuspect) -> ReportedSuspect:
        session.add(report)
        return report

    @staticmethod
    def get_by_id(session: Session, report_id: UUID) -> ReportedSuspect | None:
        return session.get(ReportedSuspect, report_id)

    @staticmethod
    def list_for_user(session: Session, user_id: UUID) -> list[ReportedSuspect]:
        statement = (
            select(ReportedSuspect)
            .where(ReportedSuspect.user_id == user_id)
            .order_by(ReportedSuspect.created_at.desc())
        )
        return list(session.scalars(statement))
