from uuid import UUID

from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.core.errors import APIError
from app.core.security import ensure_resource_owner
from app.models import Evidence, User
from app.models.enums import ComplaintStatus, UserRole
from app.repositories.complaint_repository import ComplaintRepository
from app.repositories.evidence_repository import EvidenceRepository
from app.repositories.reported_suspect_repository import ReportedSuspectRepository
from app.schemas.evidence import EvidenceUploadTarget
from app.services.audit_service import AuditService
from app.services.notification_service import NotificationService
from app.services.storage_service import (
    FileTooLargeError,
    StorageError,
    UnsupportedFileTypeError,
    get_storage_adapter,
)


class EvidenceService:
    @staticmethod
    async def upload(
        session: Session,
        *,
        upload_file: UploadFile,
        target: EvidenceUploadTarget,
        current_user: User | None,
    ) -> Evidence:
        parent_field, parent_id, owner_user_id = EvidenceService._authorize_upload_target(
            session,
            target,
            current_user,
        )
        storage_adapter = get_storage_adapter()
        try:
            stored_file = await storage_adapter.store(upload_file, prefix="evidence")
        except UnsupportedFileTypeError:
            raise APIError(
                status_code=422,
                code="UNSUPPORTED_FILE_TYPE",
                message="The uploaded file type is not supported.",
            ) from None
        except FileTooLargeError:
            raise APIError(
                status_code=422,
                code="FILE_TOO_LARGE",
                message="The uploaded file exceeds the allowed size.",
            ) from None
        except StorageError:
            raise APIError(
                status_code=503,
                code="STORAGE_UNAVAILABLE",
                message="Evidence storage is currently unavailable.",
            ) from None

        evidence = Evidence(
            **{parent_field: parent_id},
            file_name=upload_file.filename or "uploaded-file",
            file_url=stored_file.file_url,
            storage_key=stored_file.storage_key,
            mime_type=upload_file.content_type or "application/octet-stream",
            file_size=stored_file.file_size,
            checksum=stored_file.checksum,
            description=target.description,
        )
        EvidenceRepository.add(session, evidence)
        session.flush()
        AuditService.record(
            session,
            action="evidence.uploaded",
            entity_type="evidence",
            entity_id=evidence.id,
            user_id=owner_user_id,
            details={"parent_type": parent_field.removesuffix("_id")},
        )
        if owner_user_id is not None:
            NotificationService.create(
                session,
                user_id=owner_user_id,
                notification_type="EVIDENCE_UPLOADED",
                title="Evidence uploaded",
                message="Your evidence file was uploaded successfully.",
                data={"evidence_id": str(evidence.id)},
            )

        try:
            session.commit()
        except Exception:
            session.rollback()
            try:
                storage_adapter.delete(stored_file.storage_key)
            except StorageError:
                pass
            raise APIError(
                status_code=500,
                code="EVIDENCE_PERSISTENCE_FAILED",
                message="Evidence metadata could not be saved.",
            ) from None

        session.refresh(evidence)
        return evidence

    @staticmethod
    def get_accessible(
        session: Session,
        evidence_id: UUID,
        current_user: User,
    ) -> Evidence:
        evidence = EvidenceRepository.get_by_id(session, evidence_id)
        if evidence is None:
            raise APIError(
                status_code=404,
                code="NOT_FOUND",
                message="Evidence not found.",
            )
        EvidenceService._authorize_existing_evidence(session, evidence, current_user)
        return evidence

    @staticmethod
    def read_file(
        session: Session,
        evidence_id: UUID,
        current_user: User,
    ) -> tuple[bytes, str, str]:
        evidence = EvidenceService.get_accessible(session, evidence_id, current_user)
        storage_adapter = get_storage_adapter()
        try:
            content = storage_adapter.read(evidence.storage_key)
        except StorageError:
            raise APIError(
                status_code=503,
                code="STORAGE_UNAVAILABLE",
                message="Evidence storage is currently unavailable.",
            ) from None
        return content, evidence.mime_type, evidence.file_name

    @staticmethod
    def list_for_warrior_report(
        session: Session,
        warrior_report_id: UUID,
        current_user: User,
    ) -> list[Evidence]:
        report = EvidenceRepository.get_warrior_report_with_owner(session, warrior_report_id)
        if report is None:
            raise APIError(
                status_code=404,
                code="NOT_FOUND",
                message="Warrior report not found.",
            )
        EvidenceService._require_owner(report.warrior.user_id, current_user)
        return EvidenceRepository.list_by_warrior_report(session, warrior_report_id)

    @staticmethod
    def delete(
        session: Session,
        evidence_id: UUID,
        current_user: User,
    ) -> None:
        evidence = EvidenceService.get_accessible(session, evidence_id, current_user)
        storage_adapter = get_storage_adapter()
        try:
            storage_adapter.delete(evidence.storage_key)
        except StorageError:
            raise APIError(
                status_code=503,
                code="STORAGE_UNAVAILABLE",
                message="Evidence storage is currently unavailable.",
            ) from None

        EvidenceRepository.delete(session, evidence)
        AuditService.record(
            session,
            action="evidence.deleted",
            entity_type="evidence",
            entity_id=evidence_id,
            user_id=current_user.id,
        )
        try:
            session.commit()
        except Exception:
            session.rollback()
            raise APIError(
                status_code=500,
                code="EVIDENCE_DELETE_FAILED",
                message="Evidence could not be deleted completely.",
            ) from None

    @staticmethod
    def _authorize_upload_target(
        session: Session,
        target: EvidenceUploadTarget,
        current_user: User | None,
    ) -> tuple[str, UUID, UUID | None]:
        if target.complaint_id is not None:
            complaint = ComplaintRepository.get_with_details(session, target.complaint_id)
            if complaint is None:
                raise APIError(
                    status_code=404,
                    code="NOT_FOUND",
                    message="Complaint not found.",
                )
            if complaint.is_anonymous:
                is_admin = (
                    current_user is not None and current_user.role is UserRole.ADMIN
                )
                if complaint.status is not ComplaintStatus.DRAFT and not is_admin:
                    raise APIError(
                        status_code=403,
                        code="FORBIDDEN",
                        message="Anonymous complaint evidence can only be added to a draft.",
                    )
                return "complaint_id", complaint.id, None
            EvidenceService._require_owner(complaint.user_id, current_user)
            return "complaint_id", complaint.id, complaint.user_id

        if target.suspect_report_id is not None:
            report = ReportedSuspectRepository.get_by_id(session, target.suspect_report_id)
            if report is None:
                raise APIError(
                    status_code=404,
                    code="NOT_FOUND",
                    message="Reported suspect entry not found.",
                )
            EvidenceService._require_owner(report.user_id, current_user)
            return "suspect_report_id", report.id, report.user_id

        if target.warrior_report_id is not None:
            report = EvidenceRepository.get_warrior_report_with_owner(
                session,
                target.warrior_report_id,
            )
            if report is None:
                raise APIError(
                    status_code=404,
                    code="NOT_FOUND",
                    message="Warrior report not found.",
                )
            EvidenceService._require_owner(report.warrior.user_id, current_user)
            return "warrior_report_id", report.id, report.warrior.user_id

        raise APIError(
            status_code=422,
            code="VALIDATION_ERROR",
            message="Evidence must include exactly one supported parent.",
        )

    @staticmethod
    def _authorize_existing_evidence(
        session: Session,
        evidence: Evidence,
        current_user: User,
    ) -> None:
        if evidence.complaint_id is not None:
            complaint = ComplaintRepository.get_with_details(session, evidence.complaint_id)
            if complaint is None:
                raise APIError(
                    status_code=404,
                    code="NOT_FOUND",
                    message="Evidence parent not found.",
                )
            if complaint.is_anonymous and current_user.role is not UserRole.ADMIN:
                raise APIError(
                    status_code=403,
                    code="FORBIDDEN",
                    message="You do not have permission to access this evidence.",
                )
            ensure_resource_owner(complaint.user_id, current_user)
            return

        if evidence.suspect_report_id is not None:
            report = ReportedSuspectRepository.get_by_id(session, evidence.suspect_report_id)
            if report is None:
                raise APIError(
                    status_code=404,
                    code="NOT_FOUND",
                    message="Evidence parent not found.",
                )
            ensure_resource_owner(report.user_id, current_user)
            return

        if evidence.warrior_report_id is not None:
            report = EvidenceRepository.get_warrior_report_with_owner(
                session,
                evidence.warrior_report_id,
            )
            if report is None:
                raise APIError(
                    status_code=404,
                    code="NOT_FOUND",
                    message="Evidence parent not found.",
                )
            ensure_resource_owner(report.warrior.user_id, current_user)
            return

        raise APIError(
            status_code=404,
            code="NOT_FOUND",
            message="Evidence parent not found.",
        )

    @staticmethod
    def _require_owner(resource_user_id: UUID | None, current_user: User | None) -> None:
        if current_user is None:
            raise APIError(
                status_code=401,
                code="UNAUTHORIZED",
                message="Authentication is required for this evidence.",
            )
        ensure_resource_owner(resource_user_id, current_user)
