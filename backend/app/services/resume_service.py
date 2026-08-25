from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID

from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.core.errors import APIError
from app.models import (
    ResumeParsingResult,
    User,
    WarriorCertification,
    WarriorEducation,
    WarriorExperience,
    WarriorSkill,
)
from app.models.enums import ResumeParsingStatus
from app.repositories.warrior_repository import WarriorRepository
from app.schemas.cyber_warrior import ResumeConfirmationRequest
from app.services.audit_service import AuditService
from app.services.notification_service import NotificationService
from app.services.resume_parser_service import get_resume_parser
from app.services.storage_service import (
    FileTooLargeError,
    StorageError,
    UnsupportedFileTypeError,
    get_storage_adapter,
)
from app.services.warrior_service import CyberWarriorService


class ResumeService:
    @staticmethod
    async def upload(
        session: Session,
        upload_file: UploadFile,
        current_user: User,
    ) -> ResumeParsingResult:
        profile = CyberWarriorService.get_profile(session, current_user)
        ResumeService._validate_resume_type(upload_file)
        try:
            stored = await get_storage_adapter().store(upload_file, prefix="resumes")
        except (UnsupportedFileTypeError, FileTooLargeError):
            raise APIError(status_code=422, code="INVALID_RESUME_FILE", message="Resume files must be a supported PDF, DOC, or DOCX file.") from None
        except StorageError:
            raise APIError(status_code=503, code="STORAGE_UNAVAILABLE", message="Resume storage is currently unavailable.") from None

        result = ResumeParsingResult(
            warrior_id=profile.id,
            resume_file_name=upload_file.filename or "resume",
            resume_storage_key=stored.storage_key,
            status=ResumeParsingStatus.PROCESSING,
        )
        WarriorRepository.add(session, result)
        session.flush()
        try:
            result.extracted_data = await get_resume_parser().parse(
                storage_key=stored.storage_key,
                file_name=result.resume_file_name,
            )
            result.status = ResumeParsingStatus.COMPLETED
            result.processed_at = datetime.now(timezone.utc)
        except Exception:
            result.status = ResumeParsingStatus.FAILED
            result.error_message = "Resume processing could not be completed."
            result.processed_at = datetime.now(timezone.utc)
        AuditService.record(
            session,
            action="resume.processed",
            entity_type="resume_parsing_result",
            entity_id=result.id,
            user_id=current_user.id,
            details={"status": result.status.value},
        )
        session.commit()
        session.refresh(result)
        return result

    @staticmethod
    def get_owned(session: Session, result_id: UUID, current_user: User) -> ResumeParsingResult:
        profile = CyberWarriorService.get_profile(session, current_user)
        result = WarriorRepository.get_resume_result(session, result_id)
        if result is None:
            raise APIError(status_code=404, code="NOT_FOUND", message="Resume parsing result not found.")
        if result.warrior_id != profile.id:
            raise APIError(status_code=403, code="FORBIDDEN", message="You do not have permission to access this resume result.")
        return result

    @staticmethod
    def confirm(
        session: Session,
        result_id: UUID,
        payload: ResumeConfirmationRequest,
        current_user: User,
    ):
        result = ResumeService.get_owned(session, result_id, current_user)
        if result.status is not ResumeParsingStatus.COMPLETED:
            raise APIError(status_code=409, code="CONFLICT", message="Only completed resume results can be confirmed.")
        if result.confirmed_at is not None:
            raise APIError(status_code=409, code="CONFLICT", message="This resume result has already been confirmed.")
        profile = CyberWarriorService.get_profile(session, current_user)
        for field, value in payload.model_dump(exclude={"skills", "education", "experience", "certifications"}).items():
            setattr(profile, field, value)
        for skill in payload.skills:
            if WarriorRepository.get_skill(session, skill.skill_id) is None:
                raise APIError(status_code=404, code="SKILL_NOT_FOUND", message="A selected skill was not found.")
        profile.skills = [WarriorSkill(**item.model_dump()) for item in payload.skills]
        profile.education = [WarriorEducation(**item.model_dump()) for item in payload.education]
        profile.experience = [WarriorExperience(**item.model_dump()) for item in payload.experience]
        profile.certifications = [WarriorCertification(**item.model_dump()) for item in payload.certifications]
        result.confirmed_at = datetime.now(timezone.utc)
        AuditService.record(session, action="resume.confirmed", entity_type="resume_parsing_result", entity_id=result.id, user_id=current_user.id)
        NotificationService.create(session, user_id=current_user.id, notification_type="RESUME_CONFIRMED", title="Resume details confirmed", message="Your reviewed resume details were saved to your profile.")
        session.commit()
        return CyberWarriorService.get_profile(session, current_user)

    @staticmethod
    def _validate_resume_type(upload_file: UploadFile) -> None:
        extension = Path(upload_file.filename or "").suffix.lower()
        if extension not in {".pdf", ".doc", ".docx"}:
            raise APIError(status_code=422, code="INVALID_RESUME_FILE", message="Resume files must be PDF, DOC, or DOCX.")
