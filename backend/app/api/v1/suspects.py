from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.database import get_db_session
from app.core.errors import success_response
from app.core.security import get_current_user
from app.models import User
from app.schemas.common import ErrorResponse, SuccessResponse
from app.schemas.suspect import ReportedSuspectCreate, ReportedSuspectResponse
from app.services.reported_suspect_service import ReportedSuspectService

router = APIRouter(prefix="/suspects/reports", tags=["reported-suspects"])


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=SuccessResponse[ReportedSuspectResponse],
    responses={401: {"model": ErrorResponse}},
)
def create_reported_suspect(
    payload: ReportedSuspectCreate,
    session: Annotated[Session, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict[str, object]:
    report = ReportedSuspectService.create(session, payload, current_user)
    return success_response(
        ReportedSuspectResponse.model_validate(report),
        message="Reported suspect entry submitted.",
    )


@router.get(
    "/my",
    response_model=SuccessResponse[list[ReportedSuspectResponse]],
    responses={401: {"model": ErrorResponse}},
)
def list_my_reported_suspects(
    session: Annotated[Session, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict[str, object]:
    reports = ReportedSuspectService.list_my_reports(session, current_user)
    return success_response(
        [ReportedSuspectResponse.model_validate(report) for report in reports]
    )


@router.get(
    "/{report_id}",
    response_model=SuccessResponse[ReportedSuspectResponse],
    responses={
        401: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
    },
)
def get_reported_suspect(
    report_id: UUID,
    session: Annotated[Session, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict[str, object]:
    report = ReportedSuspectService.get_owned_report(session, report_id, current_user)
    return success_response(ReportedSuspectResponse.model_validate(report))
