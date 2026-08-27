from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.core.database import get_db_session
from app.core.errors import success_response
from app.core.security import require_roles
from app.models import User
from app.models.enums import UserRole
from app.schemas.common import ErrorResponse, SuccessResponse
from app.schemas.warrior import WarriorReportCreate, WarriorReportResponse, WarriorReportUpdate
from app.services.warrior_service import WarriorReportService

router = APIRouter(prefix="/warrior-reports", tags=["warrior-reports"])
WarriorUser = Annotated[User, Depends(require_roles(UserRole.CYBER_WARRIOR))]


@router.post("", status_code=status.HTTP_201_CREATED, response_model=SuccessResponse[WarriorReportResponse], responses={403: {"model": ErrorResponse}})
def create_report(payload: WarriorReportCreate, session: Annotated[Session, Depends(get_db_session)], current_user: WarriorUser) -> dict[str, object]:
    return success_response(WarriorReportResponse.model_validate(WarriorReportService.create(session, payload, current_user)), message="Warrior report draft created.")


@router.patch("/{report_id}", response_model=SuccessResponse[WarriorReportResponse], responses={403: {"model": ErrorResponse}, 404: {"model": ErrorResponse}, 409: {"model": ErrorResponse}})
def update_report(report_id: UUID, payload: WarriorReportUpdate, session: Annotated[Session, Depends(get_db_session)], current_user: WarriorUser) -> dict[str, object]:
    return success_response(WarriorReportResponse.model_validate(WarriorReportService.update(session, report_id, payload, current_user)), message="Warrior report updated.")


@router.post("/{report_id}/submit", response_model=SuccessResponse[WarriorReportResponse], responses={403: {"model": ErrorResponse}, 404: {"model": ErrorResponse}, 409: {"model": ErrorResponse}})
def submit_report(report_id: UUID, session: Annotated[Session, Depends(get_db_session)], current_user: WarriorUser) -> dict[str, object]:
    return success_response(WarriorReportResponse.model_validate(WarriorReportService.submit(session, report_id, current_user)), message="Warrior report submitted.")


@router.get("/my", response_model=SuccessResponse[list[WarriorReportResponse]], responses={403: {"model": ErrorResponse}})
def list_my_reports(session: Annotated[Session, Depends(get_db_session)], current_user: WarriorUser) -> dict[str, object]:
    return success_response([WarriorReportResponse.model_validate(item) for item in WarriorReportService.list_mine(session, current_user)])


@router.get("/{report_id}", response_model=SuccessResponse[WarriorReportResponse], responses={403: {"model": ErrorResponse}, 404: {"model": ErrorResponse}})
def get_report(report_id: UUID, session: Annotated[Session, Depends(get_db_session)], current_user: WarriorUser) -> dict[str, object]:
    return success_response(WarriorReportResponse.model_validate(WarriorReportService.get_owned(session, report_id, current_user)))


@router.delete("/{report_id}", status_code=status.HTTP_204_NO_CONTENT, responses={403: {"model": ErrorResponse}, 404: {"model": ErrorResponse}, 409: {"model": ErrorResponse}})
def delete_report(report_id: UUID, session: Annotated[Session, Depends(get_db_session)], current_user: WarriorUser) -> Response:
    WarriorReportService.delete(session, report_id, current_user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
