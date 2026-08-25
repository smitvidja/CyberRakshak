from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, UploadFile, status
from sqlalchemy.orm import Session

from app.core.database import get_db_session
from app.core.errors import success_response
from app.core.security import require_roles
from app.models import User
from app.models.enums import UserRole
from app.schemas.common import ErrorResponse, SuccessResponse
from app.schemas.cyber_warrior import CyberWarriorProfileResponse, ResumeConfirmationRequest
from app.schemas.resume import ResumeParsingResultResponse
from app.services.resume_service import ResumeService

router = APIRouter(prefix="/resume", tags=["resume"])
WarriorUser = Annotated[User, Depends(require_roles(UserRole.CYBER_WARRIOR))]


@router.post("/upload", status_code=status.HTTP_201_CREATED, response_model=SuccessResponse[ResumeParsingResultResponse], responses={403: {"model": ErrorResponse}, 422: {"model": ErrorResponse}, 503: {"model": ErrorResponse}})
async def upload_resume(file: Annotated[UploadFile, File(...)], session: Annotated[Session, Depends(get_db_session)], current_user: WarriorUser) -> dict[str, object]:
    result = await ResumeService.upload(session, file, current_user)
    return success_response(ResumeParsingResultResponse.model_validate(result), message="Resume uploaded for processing.")


@router.get("/parsing-results/{result_id}", response_model=SuccessResponse[ResumeParsingResultResponse], responses={403: {"model": ErrorResponse}, 404: {"model": ErrorResponse}})
def get_parsing_result(result_id: UUID, session: Annotated[Session, Depends(get_db_session)], current_user: WarriorUser) -> dict[str, object]:
    return success_response(ResumeParsingResultResponse.model_validate(ResumeService.get_owned(session, result_id, current_user)))


@router.post("/parsing-results/{result_id}/confirm", response_model=SuccessResponse[CyberWarriorProfileResponse], responses={403: {"model": ErrorResponse}, 404: {"model": ErrorResponse}, 409: {"model": ErrorResponse}})
def confirm_parsing_result(result_id: UUID, payload: ResumeConfirmationRequest, session: Annotated[Session, Depends(get_db_session)], current_user: WarriorUser) -> dict[str, object]:
    profile = ResumeService.confirm(session, result_id, payload, current_user)
    return success_response(CyberWarriorProfileResponse.model_validate(profile), message="Reviewed resume details confirmed.")
