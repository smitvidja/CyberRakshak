from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy.orm import Session

from app.core.errors import APIError
from app.core.security import ensure_resource_owner
from app.models import Complaint, ComplaintLocation, ComplaintStatusHistory, ComplaintSuspect, User
from app.models.enums import ComplaintStatus
from app.repositories.complaint_repository import ComplaintRepository
from app.schemas.complaint import ComplaintDraftCreate, ComplaintDraftUpdate
from app.services.audit_service import AuditService
from app.services.notification_service import NotificationService


ANONYMOUS_CATEGORY_CODES = {"WOMEN_AND_CHILD_SAFETY"}


class ComplaintService:
    @staticmethod
    def list_categories(session: Session):
        return ComplaintRepository.list_active_categories(session)

    @staticmethod
    def create_draft(
        session: Session,
        payload: ComplaintDraftCreate,
        current_user: User | None,
    ) -> Complaint:
        category = ComplaintRepository.get_category(session, payload.category_id)
        if category is None or not category.is_active:
            raise APIError(
                status_code=404,
                code="CATEGORY_NOT_FOUND",
                message="The selected complaint category is unavailable.",
            )
        if payload.is_anonymous and category.code not in ANONYMOUS_CATEGORY_CODES:
            raise APIError(
                status_code=403,
                code="ANONYMOUS_REPORTING_NOT_AVAILABLE",
                message="Anonymous reporting is available only for Women and Child Safety.",
            )
        if not payload.is_anonymous and current_user is None:
            raise APIError(
                status_code=401,
                code="UNAUTHORIZED",
                message="Authentication is required for an identified complaint.",
            )

        complaint = Complaint(
            complaint_number=ComplaintService._new_complaint_number(),
            user_id=None if payload.is_anonymous else current_user.id,
            category_id=payload.category_id,
            is_anonymous=payload.is_anonymous,
            title=payload.title,
            description=payload.description,
            incident_at=payload.incident_at,
            financial_loss_amount=payload.financial_loss_amount,
            priority=payload.priority,
        )
        if payload.location is not None:
            complaint.location = ComplaintLocation(**payload.location.model_dump())
        complaint.suspects = [
            ComplaintSuspect(**suspect.model_dump()) for suspect in payload.suspects
        ]
        ComplaintRepository.add(session, complaint)
        session.commit()
        return ComplaintService._get_details_or_not_found(session, complaint.id)

    @staticmethod
    def update_draft(
        session: Session,
        complaint_id: UUID,
        payload: ComplaintDraftUpdate,
        current_user: User | None,
    ) -> Complaint:
        complaint = ComplaintService._get_editable_complaint(
            session, complaint_id, current_user
        )
        updates = payload.model_dump(
            exclude_unset=True,
            exclude={"location", "suspects"},
        )
        if "category_id" in updates:
            category = ComplaintRepository.get_category(session, updates["category_id"])
            if category is None or not category.is_active:
                raise APIError(
                    status_code=404,
                    code="CATEGORY_NOT_FOUND",
                    message="The selected complaint category is unavailable.",
                )
            if complaint.is_anonymous and category.code not in ANONYMOUS_CATEGORY_CODES:
                raise APIError(
                    status_code=403,
                    code="ANONYMOUS_REPORTING_NOT_AVAILABLE",
                    message="Anonymous reporting is available only for Women and Child Safety.",
                )

        for field, value in updates.items():
            setattr(complaint, field, value)

        if "location" in payload.model_fields_set:
            if payload.location is None:
                complaint.location = None
            elif complaint.location is None:
                complaint.location = ComplaintLocation(**payload.location.model_dump())
            else:
                for field, value in payload.location.model_dump().items():
                    setattr(complaint.location, field, value)

        if "suspects" in payload.model_fields_set:
            complaint.suspects = [
                ComplaintSuspect(**suspect.model_dump())
                for suspect in payload.suspects or []
            ]

        session.commit()
        return ComplaintService._get_details_or_not_found(session, complaint.id)

    @staticmethod
    def submit(
        session: Session,
        complaint_id: UUID,
        current_user: User | None,
    ) -> Complaint:
        complaint = ComplaintService._get_editable_complaint(
            session, complaint_id, current_user
        )
        complaint.status = ComplaintStatus.SUBMITTED
        complaint.submitted_at = datetime.now(timezone.utc)
        ComplaintRepository.add_status_history(
            session,
            ComplaintStatusHistory(
                complaint=complaint,
                status=ComplaintStatus.SUBMITTED,
                note="Complaint submitted.",
            ),
        )
        AuditService.record(
            session,
            action="complaint.submitted",
            entity_type="complaint",
            entity_id=complaint.id,
            user_id=complaint.user_id,
            details={"status": ComplaintStatus.SUBMITTED.value},
        )
        if complaint.user_id is not None:
            NotificationService.create(
                session,
                user_id=complaint.user_id,
                notification_type="COMPLAINT_SUBMITTED",
                title="Complaint submitted",
                message="Your complaint has been submitted for review.",
                data={"complaint_number": complaint.complaint_number},
            )
        session.commit()
        return ComplaintService._get_details_or_not_found(session, complaint.id)

    @staticmethod
    def list_my_complaints(session: Session, current_user: User) -> list[Complaint]:
        return ComplaintRepository.list_for_user(session, current_user.id)

    @staticmethod
    def get_owned_complaint(
        session: Session,
        complaint_id: UUID,
        current_user: User,
    ) -> Complaint:
        complaint = ComplaintService._get_details_or_not_found(session, complaint_id)
        ensure_resource_owner(complaint.user_id, current_user)
        return complaint

    @staticmethod
    def get_tracking(session: Session, complaint_number: str) -> Complaint:
        complaint = ComplaintRepository.get_by_number(session, complaint_number)
        if complaint is None or complaint.status is ComplaintStatus.DRAFT:
            raise APIError(
                status_code=404,
                code="NOT_FOUND",
                message="Complaint not found.",
            )
        return complaint

    @staticmethod
    def _get_editable_complaint(
        session: Session,
        complaint_id: UUID,
        current_user: User | None,
    ) -> Complaint:
        complaint = ComplaintService._get_details_or_not_found(session, complaint_id)
        if complaint.status is not ComplaintStatus.DRAFT:
            raise APIError(
                status_code=409,
                code="CONFLICT",
                message="Only draft complaints can be changed or submitted.",
            )
        if not complaint.is_anonymous:
            if current_user is None:
                raise APIError(
                    status_code=401,
                    code="UNAUTHORIZED",
                    message="Authentication is required for this complaint.",
                )
            ensure_resource_owner(complaint.user_id, current_user)
        return complaint

    @staticmethod
    def _get_details_or_not_found(session: Session, complaint_id: UUID) -> Complaint:
        complaint = ComplaintRepository.get_with_details(session, complaint_id)
        if complaint is None:
            raise APIError(
                status_code=404,
                code="NOT_FOUND",
                message="Complaint not found.",
            )
        return complaint

    @staticmethod
    def _new_complaint_number() -> str:
        timestamp = datetime.now(timezone.utc).strftime("%Y")
        return f"CR-{timestamp}-{uuid4().hex[:10].upper()}"
