from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.database import get_db_session
from app.core.errors import success_response
from app.core.security import require_roles
from app.models import User
from app.models.enums import UserRole
from app.schemas.common import ErrorResponse, SuccessResponse
from app.schemas.warrior import WarriorApplicationCreate, WarriorApplicationResponse
from app.services.warrior_service import WarriorApplicationService

router = APIRouter(prefix="/warrior-applications", tags=["warrior-applications"])
WarriorUser = Annotated[User, Depends(require_roles(UserRole.CYBER_WARRIOR))]


@router.post("", status_code=status.HTTP_201_CREATED, response_model=SuccessResponse[WarriorApplicationResponse], responses={403: {"model": ErrorResponse}})
def create_application(payload: WarriorApplicationCreate, session: Annotated[Session, Depends(get_db_session)], current_user: WarriorUser) -> dict[str, object]:
    return success_response(WarriorApplicationResponse.model_validate(WarriorApplicationService.create(session, payload, current_user)), message="Application draft created.")


@router.post("/{application_id}/submit", response_model=SuccessResponse[WarriorApplicationResponse], responses={403: {"model": ErrorResponse}, 404: {"model": ErrorResponse}, 409: {"model": ErrorResponse}})
def submit_application(application_id: UUID, session: Annotated[Session, Depends(get_db_session)], current_user: WarriorUser) -> dict[str, object]:
    return success_response(WarriorApplicationResponse.model_validate(WarriorApplicationService.submit(session, application_id, current_user)), message="Application submitted.")


@router.get("/my", response_model=SuccessResponse[list[WarriorApplicationResponse]], responses={403: {"model": ErrorResponse}})
def list_my_applications(session: Annotated[Session, Depends(get_db_session)], current_user: WarriorUser) -> dict[str, object]:
    return success_response([WarriorApplicationResponse.model_validate(item) for item in WarriorApplicationService.list_mine(session, current_user)])
