from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import ReportedSuspect, SuspectCorrectionRequest
from app.models.enums import ReportedSuspectIdentifierType, ReportedSuspectStatus


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

    @staticmethod
    def count_eligible_exact_matches(
        session: Session,
        identifier_type: ReportedSuspectIdentifierType,
        normalized_identifier: str,
    ) -> int:
        statement = select(func.count(ReportedSuspect.id)).where(
            ReportedSuspect.identifier_type == identifier_type,
            ReportedSuspect.normalized_identifier == normalized_identifier,
            ReportedSuspect.status == ReportedSuspectStatus.VERIFIED,
        )
        return int(session.scalar(statement) or 0)

    @staticmethod
    def add_correction(session: Session, correction: SuspectCorrectionRequest) -> SuspectCorrectionRequest:
        session.add(correction)
        return correction
