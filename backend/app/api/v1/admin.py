from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db_session
from app.core.errors import success_response
from app.core.security import require_roles
from app.models import User
from app.models.enums import UserRole
from app.schemas.admin import AuditLogResponse, ComplaintStatusUpdate, ReportedSuspectStatusUpdate, WarriorApplicationStatusUpdate
from app.schemas.common import ErrorResponse, SuccessResponse
from app.schemas.complaint import ComplaintResponse, ComplaintSummaryResponse
from app.schemas.suspect import ReportedSuspectResponse
from app.schemas.warrior import WarriorApplicationResponse
from app.services.admin_service import AdminService

router = APIRouter(prefix="/admin", tags=["admin"])
AdminUser = Annotated[User, Depends(require_roles(UserRole.ADMIN))]


@router.get("/complaints", response_model=SuccessResponse[list[ComplaintSummaryResponse]], responses={403: {"model": ErrorResponse}})
def list_complaints(session: Annotated[Session, Depends(get_db_session)], current_user: AdminUser) -> dict[str, object]:
    return success_response([ComplaintSummaryResponse.model_validate(item) for item in AdminService.list_complaints(session)])


@router.patch("/complaints/{complaint_id}/status", response_model=SuccessResponse[ComplaintResponse], responses={403: {"model": ErrorResponse}, 404: {"model": ErrorResponse}})
def update_complaint_status(complaint_id: UUID, payload: ComplaintStatusUpdate, session: Annotated[Session, Depends(get_db_session)], current_user: AdminUser) -> dict[str, object]:
    return success_response(ComplaintResponse.model_validate(AdminService.update_complaint_status(session, complaint_id, payload, current_user)), message="Complaint status updated.")


@router.get("/suspect-reports", response_model=SuccessResponse[list[ReportedSuspectResponse]], responses={403: {"model": ErrorResponse}})
def list_suspect_reports(session: Annotated[Session, Depends(get_db_session)], current_user: AdminUser) -> dict[str, object]:
    return success_response([ReportedSuspectResponse.model_validate(item) for item in AdminService.list_reported_suspects(session)])


@router.patch("/suspect-reports/{report_id}/status", response_model=SuccessResponse[ReportedSuspectResponse], responses={403: {"model": ErrorResponse}, 404: {"model": ErrorResponse}})
def update_suspect_status(report_id: UUID, payload: ReportedSuspectStatusUpdate, session: Annotated[Session, Depends(get_db_session)], current_user: AdminUser) -> dict[str, object]:
    return success_response(ReportedSuspectResponse.model_validate(AdminService.update_reported_suspect_status(session, report_id, payload, current_user)), message="Reported suspect status updated.")


@router.get("/warrior-applications", response_model=SuccessResponse[list[WarriorApplicationResponse]], responses={403: {"model": ErrorResponse}})
def list_applications(session: Annotated[Session, Depends(get_db_session)], current_user: AdminUser) -> dict[str, object]:
    return success_response([WarriorApplicationResponse.model_validate(item) for item in AdminService.list_applications(session)])


@router.patch("/warrior-applications/{application_id}/status", response_model=SuccessResponse[WarriorApplicationResponse], responses={403: {"model": ErrorResponse}, 404: {"model": ErrorResponse}})
def update_application_status(application_id: UUID, payload: WarriorApplicationStatusUpdate, session: Annotated[Session, Depends(get_db_session)], current_user: AdminUser) -> dict[str, object]:
    return success_response(WarriorApplicationResponse.model_validate(AdminService.update_application_status(session, application_id, payload, current_user)), message="Application status updated.")


@router.get("/audit-logs", response_model=SuccessResponse[list[AuditLogResponse]], responses={403: {"model": ErrorResponse}})
def list_audit_logs(session: Annotated[Session, Depends(get_db_session)], current_user: AdminUser) -> dict[str, object]:
    return success_response([AuditLogResponse.model_validate(item) for item in AdminService.list_audit_logs(session)])
