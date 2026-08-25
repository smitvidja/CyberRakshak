from uuid import UUID

from sqlalchemy.orm import Session

from app.core.errors import APIError
from app.core.security import ensure_resource_owner
from app.models import ReportedSuspect, User
from app.models.enums import ReportedSuspectStatus
from app.repositories.reported_suspect_repository import ReportedSuspectRepository
from app.schemas.suspect import ReportedSuspectCreate


class ReportedSuspectService:
    @staticmethod
    def create(
        session: Session,
        payload: ReportedSuspectCreate,
        current_user: User,
    ) -> ReportedSuspect:
        report = ReportedSuspect(
            user_id=current_user.id,
            identifier_type=payload.identifier_type,
            identifier_value=payload.identifier_value,
            description=payload.description,
            status=ReportedSuspectStatus.SUBMITTED,
        )
        ReportedSuspectRepository.add(session, report)
        session.commit()
        session.refresh(report)
        return report

    @staticmethod
    def list_my_reports(
        session: Session,
        current_user: User,
    ) -> list[ReportedSuspect]:
        return ReportedSuspectRepository.list_for_user(session, current_user.id)

    @staticmethod
    def get_owned_report(
        session: Session,
        report_id: UUID,
        current_user: User,
    ) -> ReportedSuspect:
        report = ReportedSuspectRepository.get_by_id(session, report_id)
        if report is None:
            raise APIError(
                status_code=404,
                code="NOT_FOUND",
                message="Reported suspect entry not found.",
            )
        ensure_resource_owner(report.user_id, current_user)
        return report
