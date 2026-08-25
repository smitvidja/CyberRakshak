from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.errors import APIError
from app.models import ComplaintStatusHistory, User
from app.models.enums import (
    ComplaintStatus,
    WarriorApplicationStatus,
)
from app.repositories.admin_repository import AdminRepository
from app.repositories.complaint_repository import ComplaintRepository
from app.repositories.reported_suspect_repository import ReportedSuspectRepository
from app.repositories.warrior_repository import WarriorRepository
from app.schemas.admin import (
    ComplaintStatusUpdate,
    ReportedSuspectStatusUpdate,
    WarriorApplicationStatusUpdate,
)
from app.services.audit_service import AuditService
from app.services.notification_service import NotificationService


class AdminService:
    @staticmethod
    def list_complaints(session: Session):
        return AdminRepository.list_complaints(session)

    @staticmethod
    def update_complaint_status(session: Session, complaint_id: UUID, payload: ComplaintStatusUpdate, admin: User):
        complaint = ComplaintRepository.get_with_details(session, complaint_id)
        if complaint is None:
            raise APIError(status_code=404, code="NOT_FOUND", message="Complaint not found.")
        if payload.status is ComplaintStatus.DRAFT:
            raise APIError(status_code=422, code="INVALID_STATUS", message="Admin review cannot move a complaint to draft.")
        complaint.status = payload.status
        ComplaintRepository.add_status_history(session, ComplaintStatusHistory(complaint=complaint, status=payload.status, note=payload.note))
        AuditService.record(session, action="complaint.status_updated", entity_type="complaint", entity_id=complaint.id, user_id=admin.id, details={"status": payload.status.value})
        if complaint.user_id is not None:
            NotificationService.create(session, user_id=complaint.user_id, notification_type="COMPLAINT_STATUS_UPDATED", title="Complaint status updated", message="Your complaint status has been updated.", data={"complaint_number": complaint.complaint_number, "status": payload.status.value})
        session.commit()
        return ComplaintRepository.get_with_details(session, complaint.id)

    @staticmethod
    def list_reported_suspects(session: Session):
        return AdminRepository.list_reported_suspects(session)

    @staticmethod
    def update_reported_suspect_status(session: Session, report_id: UUID, payload: ReportedSuspectStatusUpdate, admin: User):
        report = ReportedSuspectRepository.get_by_id(session, report_id)
        if report is None:
            raise APIError(status_code=404, code="NOT_FOUND", message="Reported suspect entry not found.")
        report.status = payload.status
        AuditService.record(session, action="reported_suspect.status_updated", entity_type="reported_suspect", entity_id=report.id, user_id=admin.id, details={"status": payload.status.value})
        NotificationService.create(session, user_id=report.user_id, notification_type="REPORTED_SUSPECT_STATUS_UPDATED", title="Reported suspect status updated", message="Your reported suspect entry status has been updated.", data={"report_id": str(report.id), "status": payload.status.value})
        session.commit()
        session.refresh(report)
        return report

    @staticmethod
    def list_applications(session: Session):
        return WarriorRepository.list_applications(session)

    @staticmethod
    def update_application_status(session: Session, application_id: UUID, payload: WarriorApplicationStatusUpdate, admin: User):
        if payload.status not in {WarriorApplicationStatus.UNDER_REVIEW, WarriorApplicationStatus.APPROVED, WarriorApplicationStatus.REJECTED}:
            raise APIError(status_code=422, code="INVALID_STATUS", message="Invalid administrative application status.")
        application = WarriorRepository.get_application(session, application_id)
        if application is None:
            raise APIError(status_code=404, code="NOT_FOUND", message="Application not found.")
        application.status = payload.status
        application.review_note = payload.review_note
        application.reviewed_at = datetime.now(timezone.utc)
        AuditService.record(session, action="warrior_application.reviewed", entity_type="warrior_application", entity_id=application.id, user_id=admin.id, details={"status": payload.status.value})
        NotificationService.create(session, user_id=application.warrior.user_id, notification_type="WARRIOR_APPLICATION_STATUS_UPDATED", title="Application status updated", message="Your Cyber Warrior application status has been updated.", data={"application_number": application.application_number, "status": payload.status.value})
        session.commit()
        session.refresh(application)
        return application

    @staticmethod
    def list_audit_logs(session: Session):
        return AdminRepository.list_audit_logs(session)
