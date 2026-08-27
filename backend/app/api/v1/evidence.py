from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, Response, UploadFile, status
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.core.database import get_db_session
from app.core.errors import APIError, success_response
from app.core.security import get_current_user, get_optional_current_user
from app.models import User
from app.schemas.common import ErrorResponse, SuccessResponse
from app.schemas.evidence import EvidenceResponse, EvidenceUploadTarget
from app.services.evidence_service import EvidenceService

router = APIRouter(prefix="/evidence", tags=["evidence"])


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=SuccessResponse[EvidenceResponse],
    responses={
        401: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
        503: {"model": ErrorResponse},
    },
)
async def upload_evidence(
    file: Annotated[UploadFile, File(...)],
    session: Annotated[Session, Depends(get_db_session)],
    current_user: Annotated[User | None, Depends(get_optional_current_user)],
    complaint_id: Annotated[UUID | None, Form()] = None,
    suspect_report_id: Annotated[UUID | None, Form()] = None,
    warrior_report_id: Annotated[UUID | None, Form()] = None,
    description: Annotated[str | None, Form(max_length=2000)] = None,
) -> dict[str, object]:
    try:
        target = EvidenceUploadTarget(
            complaint_id=complaint_id,
            suspect_report_id=suspect_report_id,
            warrior_report_id=warrior_report_id,
            description=description,
        )
    except ValidationError:
        raise APIError(
            status_code=422,
            code="VALIDATION_ERROR",
            message="Evidence must be attached to exactly one supported parent.",
        ) from None

    evidence = await EvidenceService.upload(
        session,
        upload_file=file,
        target=target,
        current_user=current_user,
    )
    return success_response(
        EvidenceResponse.model_validate(evidence),
        message="Evidence uploaded successfully.",
    )


@router.get(
    "/by-warrior-report/{report_id}",
    response_model=SuccessResponse[list[EvidenceResponse]],
    responses={
        401: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
    },
)
def list_warrior_report_evidence(
    report_id: UUID,
    session: Annotated[Session, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict[str, object]:
    items = EvidenceService.list_for_warrior_report(session, report_id, current_user)
    return success_response([EvidenceResponse.model_validate(item) for item in items])


@router.get(
    "/{evidence_id}/file",
    responses={
        401: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        503: {"model": ErrorResponse},
    },
)
def read_evidence_file(
    evidence_id: UUID,
    session: Annotated[Session, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> Response:
    content, mime_type, file_name = EvidenceService.read_file(session, evidence_id, current_user)
    return Response(
        content=content,
        media_type=mime_type,
        headers={"Content-Disposition": f'inline; filename="{file_name}"'},
    )


@router.get(
    "/{evidence_id}",
    response_model=SuccessResponse[EvidenceResponse],
    responses={
        401: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
    },
)
def get_evidence(
    evidence_id: UUID,
    session: Annotated[Session, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict[str, object]:
    evidence = EvidenceService.get_accessible(session, evidence_id, current_user)
    return success_response(EvidenceResponse.model_validate(evidence))


@router.delete(
    "/{evidence_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        401: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        503: {"model": ErrorResponse},
    },
)
def delete_evidence(
    evidence_id: UUID,
    session: Annotated[Session, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> Response:
    EvidenceService.delete(session, evidence_id, current_user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
