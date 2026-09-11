from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.orm import Session

from app.core.database import get_db_session
from app.core.errors import success_response
from app.core.client_identity import resolve_client_key
from app.core.config import get_settings
from app.core.public_rate_limit import suspect_correction_rate_limiter, suspect_search_rate_limiter
from app.core.security import get_current_user
from app.models import User
from app.schemas.common import ErrorResponse, SuccessResponse
from app.schemas.suspect import (
    ReportedSuspectCreate,
    ReportedSuspectResponse,
    SuspectCorrectionCreate,
    SuspectCorrectionResponse,
    SuspectSearchRequest,
    SuspectSearchResponse,
)
from app.services.reported_suspect_service import ReportedSuspectService

router = APIRouter(prefix="/suspects", tags=["reported-suspects"])


def _public_client_key(request: Request) -> str:
    return resolve_client_key(request, get_settings().trusted_proxy_hops)


@router.post("/search", response_model=SuccessResponse[SuspectSearchResponse], responses={422: {"model": ErrorResponse}, 429: {"model": ErrorResponse}})
def search_reported_suspects(payload: SuspectSearchRequest, request: Request, session: Annotated[Session, Depends(get_db_session)]) -> dict[str, object]:
    suspect_search_rate_limiter.check(_public_client_key(request))
    return success_response(ReportedSuspectService.search(session, payload))


@router.post("/corrections", status_code=status.HTTP_201_CREATED, response_model=SuccessResponse[SuspectCorrectionResponse], responses={422: {"model": ErrorResponse}, 429: {"model": ErrorResponse}})
def create_suspect_correction(payload: SuspectCorrectionCreate, request: Request, session: Annotated[Session, Depends(get_db_session)]) -> dict[str, object]:
    # An unauthenticated write, so it needs its own budget: without one, anyone
    # could fill the moderation queue faster than it can be read.
    suspect_correction_rate_limiter.check(_public_client_key(request))
    correction = ReportedSuspectService.create_correction(session, payload)
    return success_response(SuspectCorrectionResponse.model_validate(correction), message="Correction request submitted for review.")


@router.post(
    "/reports",
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
    "/reports/my",
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
    "/reports/{report_id}",
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
