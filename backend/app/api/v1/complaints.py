from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.database import get_db_session
from app.core.errors import success_response
from app.core.security import get_current_user, get_optional_current_user
from app.models import User
from app.schemas.common import ErrorResponse, SuccessResponse
from app.schemas.complaint import (
    ComplaintDraftCreate,
    ComplaintDraftUpdate,
    ComplaintResponse,
    ComplaintStatusHistoryResponse,
    ComplaintSummaryResponse,
    ComplaintTrackingHistoryItem,
    ComplaintTrackingResponse,
)
from app.services.complaint_service import ComplaintService

router = APIRouter(prefix="/complaints", tags=["complaints"])


@router.post(
    "/drafts",
    status_code=status.HTTP_201_CREATED,
    response_model=SuccessResponse[ComplaintResponse],
    responses={401: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
)
def create_complaint_draft(
    payload: ComplaintDraftCreate,
    session: Annotated[Session, Depends(get_db_session)],
    current_user: Annotated[User | None, Depends(get_optional_current_user)],
) -> dict[str, object]:
    complaint = ComplaintService.create_draft(session, payload, current_user)
    return success_response(
        ComplaintResponse.model_validate(complaint),
        message="Complaint draft created.",
    )


@router.patch(
    "/{complaint_id}",
    response_model=SuccessResponse[ComplaintResponse],
    responses={
        401: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
    },
)
def update_complaint_draft(
    complaint_id: UUID,
    payload: ComplaintDraftUpdate,
    session: Annotated[Session, Depends(get_db_session)],
    current_user: Annotated[User | None, Depends(get_optional_current_user)],
) -> dict[str, object]:
    complaint = ComplaintService.update_draft(
        session,
        complaint_id,
        payload,
        current_user,
    )
    return success_response(
        ComplaintResponse.model_validate(complaint),
        message="Complaint draft updated.",
    )


@router.post(
    "/{complaint_id}/submit",
    response_model=SuccessResponse[ComplaintResponse],
    responses={
        401: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
    },
)
def submit_complaint(
    complaint_id: UUID,
    session: Annotated[Session, Depends(get_db_session)],
    current_user: Annotated[User | None, Depends(get_optional_current_user)],
) -> dict[str, object]:
    complaint = ComplaintService.submit(session, complaint_id, current_user)
    return success_response(
        ComplaintResponse.model_validate(complaint),
        message="Complaint submitted.",
    )


@router.get(
    "/my",
    response_model=SuccessResponse[list[ComplaintSummaryResponse]],
    responses={401: {"model": ErrorResponse}},
)
def list_my_complaints(
    session: Annotated[Session, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict[str, object]:
    complaints = ComplaintService.list_my_complaints(session, current_user)
    return success_response(
        [ComplaintSummaryResponse.model_validate(complaint) for complaint in complaints]
    )


@router.get(
    "/track/{complaint_number}",
    response_model=SuccessResponse[ComplaintTrackingResponse],
    responses={404: {"model": ErrorResponse}},
)
def track_complaint(
    complaint_number: str,
    session: Annotated[Session, Depends(get_db_session)],
) -> dict[str, object]:
    complaint = ComplaintService.get_tracking(session, complaint_number)
    return success_response(
        ComplaintTrackingResponse(
            complaint_number=complaint.complaint_number,
            status=complaint.status,
            priority=complaint.priority,
            created_at=complaint.created_at,
            submitted_at=complaint.submitted_at,
            history=[
                ComplaintTrackingHistoryItem(status=item.status, created_at=item.created_at)
                for item in sorted(complaint.status_history, key=lambda item: item.created_at)
            ],
        )
    )


@router.get(
    "/{complaint_id}",
    response_model=SuccessResponse[ComplaintResponse],
    responses={
        401: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
    },
)
def get_complaint(
    complaint_id: UUID,
    session: Annotated[Session, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict[str, object]:
    complaint = ComplaintService.get_owned_complaint(session, complaint_id, current_user)
    return success_response(ComplaintResponse.model_validate(complaint))


@router.get(
    "/{complaint_id}/status-history",
    response_model=SuccessResponse[list[ComplaintStatusHistoryResponse]],
    responses={
        401: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
    },
)
def get_complaint_status_history(
    complaint_id: UUID,
    session: Annotated[Session, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict[str, object]:
    complaint = ComplaintService.get_owned_complaint(session, complaint_id, current_user)
    history = sorted(complaint.status_history, key=lambda item: item.created_at)
    return success_response(
        [ComplaintStatusHistoryResponse.model_validate(item) for item in history]
    )
