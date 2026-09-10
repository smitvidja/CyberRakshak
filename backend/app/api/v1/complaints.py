from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Response, status
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
    ComplaintSubmittedResponse,
    ComplaintStatusHistoryResponse,
    ComplaintSummaryResponse,
    ComplaintTrackingHistoryItem,
    ComplaintTrackingResponse,
)
from app.services.complaint_document_service import ComplaintDocumentService
from app.services.complaint_pdf_renderer import render_complaint_copy
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
    response_model=SuccessResponse[ComplaintSubmittedResponse],
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
    complaint, access_token = ComplaintService.submit(session, complaint_id, current_user)
    payload = ComplaintSubmittedResponse.model_validate(complaint)
    return success_response(
        payload.model_copy(update={"access_token": access_token}),
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


@router.get(
    "/{complaint_id}/copy",
    responses={
        200: {"content": {"application/pdf": {}}, "description": "Complaint copy PDF"},
        401: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
    },
)
def download_complaint_copy(
    complaint_id: UUID,
    session: Annotated[Session, Depends(get_db_session)],
    current_user: Annotated[User | None, Depends(get_optional_current_user)],
    x_complaint_access_token: Annotated[str | None, Header()] = None,
    sec_fetch_mode: Annotated[str | None, Header()] = None,
) -> Response:
    """Return a PDF copy of one submitted complaint.

    Identified complaints authorize through the owner's session; anonymous ones
    through a scoped capability carried in a header, never in the URL, so the
    capability cannot leak via history, referrers or access logs.
    """
    complaint = ComplaintDocumentService.authorize(session, complaint_id, current_user, x_complaint_access_token)
    document = ComplaintDocumentService.build(complaint)
    pdf_bytes = render_complaint_copy(document)
    # The filename is built from the server-side complaint number only.
    safe_number = "".join(ch for ch in complaint.complaint_number if ch.isalnum() or ch in "-_")
    headers = {
        "Cache-Control": "no-store, private",
        "X-Content-Type-Options": "nosniff",
    }
    # Chrome refuses to hand a cross-origin fetch() a response carrying
    # Content-Disposition, and the deployed topology puts the app and the API on
    # different origins - so sending it unconditionally breaks the download in the
    # browser. The web client reads the blob and saves it under this same filename
    # itself, so the header is omitted for a cors-mode fetch and kept for every
    # other consumer (direct navigation, curl, server-side clients), which is what
    # actually needs to be told to save rather than render.
    if (sec_fetch_mode or "").lower() != "cors":
        headers["Content-Disposition"] = f'attachment; filename="CyberRakshak-Complaint-{safe_number}.pdf"'
    return Response(content=pdf_bytes, media_type="application/pdf", headers=headers)
