from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy.orm import Session

from app.core.errors import APIError
from app.models import (
    CyberWarriorProfile,
    Skill,
    User,
    WarriorApplication,
    WarriorCertification,
    WarriorEducation,
    WarriorExperience,
    WarriorReport,
    WarriorSkill,
)
from app.models.enums import (
    UserRole,
    WarriorApplicationStatus,
    WarriorReportStatus,
)
from app.repositories.evidence_repository import EvidenceRepository
from app.repositories.warrior_repository import WarriorRepository
from app.schemas.cyber_warrior import ProfileCreate, ProfileUpdate
from app.schemas.warrior import (
    WarriorApplicationCreate,
    WarriorReportCreate,
    WarriorReportUpdate,
)
from app.services.audit_service import AuditService
from app.services.evidence_service import EvidenceService
from app.services.notification_service import NotificationService


class CyberWarriorService:
    @staticmethod
    def list_skills(session: Session, current_user: User) -> list[Skill]:
        CyberWarriorService.require_warrior(current_user)
        return WarriorRepository.list_skills(session)

    @staticmethod
    def create_profile(
        session: Session,
        payload: ProfileCreate,
        current_user: User,
    ) -> CyberWarriorProfile:
        CyberWarriorService.require_warrior(current_user)
        if WarriorRepository.get_profile_with_details(session, current_user.id) is not None:
            raise APIError(
                status_code=409,
                code="CONFLICT",
                message="A Cyber Warrior profile already exists.",
            )
        profile = CyberWarriorProfile(user_id=current_user.id, **payload.model_dump())
        WarriorRepository.add(session, profile)
        AuditService.record(
            session,
            action="cyber_warrior.profile_created",
            entity_type="cyber_warrior_profile",
            entity_id=profile.id,
            user_id=current_user.id,
        )
        session.commit()
        return CyberWarriorService.get_profile(session, current_user)

    @staticmethod
    def get_profile(session: Session, current_user: User) -> CyberWarriorProfile:
        profile = WarriorRepository.get_profile_with_details(session, current_user.id)
        if profile is None:
            raise APIError(
                status_code=404,
                code="NOT_FOUND",
                message="Cyber Warrior profile not found.",
            )
        return profile

    @staticmethod
    def update_profile(
        session: Session,
        payload: ProfileUpdate,
        current_user: User,
    ) -> CyberWarriorProfile:
        profile = CyberWarriorService.get_profile(session, current_user)
        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(profile, field, value)
        AuditService.record(
            session,
            action="cyber_warrior.profile_updated",
            entity_type="cyber_warrior_profile",
            entity_id=profile.id,
            user_id=current_user.id,
        )
        session.commit()
        return CyberWarriorService.get_profile(session, current_user)

    @staticmethod
    def require_warrior(current_user: User) -> None:
        if current_user.role is not UserRole.CYBER_WARRIOR:
            raise APIError(
                status_code=403,
                code="FORBIDDEN",
                message="A Cyber Warrior account is required for this action.",
            )


class WarriorApplicationService:
    @staticmethod
    def create(
        session: Session,
        payload: WarriorApplicationCreate,
        current_user: User,
    ) -> WarriorApplication:
        profile = WarriorApplicationService._profile(session, current_user)
        active_statuses = {
            WarriorApplicationStatus.DRAFT,
            WarriorApplicationStatus.SUBMITTED,
            WarriorApplicationStatus.UNDER_REVIEW,
            WarriorApplicationStatus.APPROVED,
        }
        if any(item.status in active_statuses for item in WarriorRepository.list_applications(session, profile.id)):
            raise APIError(status_code=409, code="CONFLICT", message="An active Cyber Warrior application already exists.")
        application = WarriorApplication(
            warrior_id=profile.id,
            application_number=WarriorApplicationService._number(),
            statement=payload.statement,
        )
        WarriorRepository.add(session, application)
        session.commit()
        session.refresh(application)
        return application

    @staticmethod
    def submit(
        session: Session,
        application_id: UUID,
        current_user: User,
    ) -> WarriorApplication:
        application = WarriorApplicationService._owned_application(
            session, application_id, current_user
        )
        if application.status is not WarriorApplicationStatus.DRAFT:
            raise APIError(
                status_code=409,
                code="CONFLICT",
                message="Only draft applications can be submitted.",
            )
        application.status = WarriorApplicationStatus.UNDER_REVIEW
        application.submitted_at = datetime.now(timezone.utc)
        AuditService.record(
            session,
            action="warrior_application.submitted",
            entity_type="warrior_application",
            entity_id=application.id,
            user_id=current_user.id,
            details={"status": application.status.value},
        )
        NotificationService.create(
            session,
            user_id=current_user.id,
            notification_type="WARRIOR_APPLICATION_SUBMITTED",
            title="Application submitted",
            message="Your Cyber Warrior application has been submitted for review.",
            data={"application_number": application.application_number},
        )
        session.commit()
        session.refresh(application)
        return application

    @staticmethod
    def list_mine(session: Session, current_user: User) -> list[WarriorApplication]:
        profile = WarriorApplicationService._profile(session, current_user)
        return WarriorRepository.list_applications(session, profile.id)

    @staticmethod
    def _profile(session: Session, current_user: User) -> CyberWarriorProfile:
        CyberWarriorService.require_warrior(current_user)
        return CyberWarriorService.get_profile(session, current_user)

    @staticmethod
    def _owned_application(
        session: Session,
        application_id: UUID,
        current_user: User,
    ) -> WarriorApplication:
        profile = WarriorApplicationService._profile(session, current_user)
        application = WarriorRepository.get_application(session, application_id)
        if application is None:
            raise APIError(status_code=404, code="NOT_FOUND", message="Application not found.")
        if application.warrior_id != profile.id:
            raise APIError(status_code=403, code="FORBIDDEN", message="You do not have permission to access this application.")
        return application

    @staticmethod
    def _number() -> str:
        return f"CW-APP-{datetime.now(timezone.utc):%Y}-{uuid4().hex[:10].upper()}"


class WarriorReportService:
    @staticmethod
    def create(
        session: Session,
        payload: WarriorReportCreate,
        current_user: User,
    ) -> WarriorReport:
        profile = WarriorReportService._profile(session, current_user)
        report = WarriorReport(warrior_id=profile.id, **payload.model_dump())
        WarriorRepository.add(session, report)
        session.commit()
        session.refresh(report)
        return report

    @staticmethod
    def update(
        session: Session,
        report_id: UUID,
        payload: WarriorReportUpdate,
        current_user: User,
    ) -> WarriorReport:
        report = WarriorReportService._owned_report(session, report_id, current_user)
        if report.status is not WarriorReportStatus.DRAFT:
            raise APIError(status_code=409, code="CONFLICT", message="Only draft reports can be updated.")
        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(report, field, value)
        session.commit()
        session.refresh(report)
        return report

    @staticmethod
    def submit(
        session: Session,
        report_id: UUID,
        current_user: User,
    ) -> WarriorReport:
        report = WarriorReportService._owned_report(session, report_id, current_user)
        if report.status is not WarriorReportStatus.DRAFT:
            raise APIError(status_code=409, code="CONFLICT", message="Only draft reports can be submitted.")
        report.status = WarriorReportStatus.SUBMITTED
        report.submitted_at = datetime.now(timezone.utc)
        AuditService.record(
            session,
            action="warrior_report.submitted",
            entity_type="warrior_report",
            entity_id=report.id,
            user_id=current_user.id,
            details={"status": report.status.value},
        )
        NotificationService.create(
            session,
            user_id=current_user.id,
            notification_type="WARRIOR_REPORT_SUBMITTED",
            title="Cyber report submitted",
            message="Your cyber report has been submitted for review.",
            data={"report_id": str(report.id)},
        )
        session.commit()
        session.refresh(report)
        return report

    @staticmethod
    def delete(
        session: Session,
        report_id: UUID,
        current_user: User,
    ) -> None:
        report = WarriorReportService._owned_report(session, report_id, current_user)
        if report.status is not WarriorReportStatus.DRAFT:
            raise APIError(status_code=409, code="CONFLICT", message="Only draft reports can be deleted.")
        for evidence in EvidenceRepository.list_by_warrior_report(session, report.id):
            EvidenceService.delete(session, evidence.id, current_user)
        WarriorRepository.delete_report(session, report)
        session.commit()

    @staticmethod
    def list_mine(session: Session, current_user: User) -> list[WarriorReport]:
        profile = WarriorReportService._profile(session, current_user)
        return WarriorRepository.list_reports(session, profile.id)

    @staticmethod
    def get_owned(session: Session, report_id: UUID, current_user: User) -> WarriorReport:
        return WarriorReportService._owned_report(session, report_id, current_user)

    @staticmethod
    def _profile(session: Session, current_user: User) -> CyberWarriorProfile:
        CyberWarriorService.require_warrior(current_user)
        return CyberWarriorService.get_profile(session, current_user)

    @staticmethod
    def _owned_report(session: Session, report_id: UUID, current_user: User) -> WarriorReport:
        profile = WarriorReportService._profile(session, current_user)
        report = WarriorRepository.get_report(session, report_id)
        if report is None:
            raise APIError(status_code=404, code="NOT_FOUND", message="Warrior report not found.")
        if report.warrior_id != profile.id:
            raise APIError(status_code=403, code="FORBIDDEN", message="You do not have permission to access this report.")
        return report
