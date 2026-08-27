from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.database import get_db_session
from app.core.errors import success_response
from app.core.security import require_roles
from app.models import User
from app.models.enums import UserRole
from app.schemas.common import ErrorResponse, SuccessResponse
from app.schemas.cyber_warrior import CyberWarriorProfileResponse, ProfileCreate, ProfileUpdate, SkillCatalogResponse
from app.services.warrior_service import CyberWarriorService

router = APIRouter(prefix="/cyber-warriors", tags=["cyber-warriors"])
WarriorUser = Annotated[User, Depends(require_roles(UserRole.CYBER_WARRIOR))]


@router.get("/skills", response_model=SuccessResponse[list[SkillCatalogResponse]], responses={403: {"model": ErrorResponse}})
def list_skills(session: Annotated[Session, Depends(get_db_session)], current_user: WarriorUser) -> dict[str, object]:
    return success_response([SkillCatalogResponse.model_validate(item) for item in CyberWarriorService.list_skills(session, current_user)])


@router.post("/profile", status_code=status.HTTP_201_CREATED, response_model=SuccessResponse[CyberWarriorProfileResponse], responses={403: {"model": ErrorResponse}, 409: {"model": ErrorResponse}})
def create_profile(payload: ProfileCreate, session: Annotated[Session, Depends(get_db_session)], current_user: WarriorUser) -> dict[str, object]:
    return success_response(CyberWarriorProfileResponse.model_validate(CyberWarriorService.create_profile(session, payload, current_user)), message="Cyber Warrior profile created.")


@router.get("/me", response_model=SuccessResponse[CyberWarriorProfileResponse], responses={403: {"model": ErrorResponse}, 404: {"model": ErrorResponse}})
def get_my_profile(session: Annotated[Session, Depends(get_db_session)], current_user: WarriorUser) -> dict[str, object]:
    return success_response(CyberWarriorProfileResponse.model_validate(CyberWarriorService.get_profile(session, current_user)))


@router.patch("/me", response_model=SuccessResponse[CyberWarriorProfileResponse], responses={403: {"model": ErrorResponse}, 404: {"model": ErrorResponse}})
def update_my_profile(payload: ProfileUpdate, session: Annotated[Session, Depends(get_db_session)], current_user: WarriorUser) -> dict[str, object]:
    return success_response(CyberWarriorProfileResponse.model_validate(CyberWarriorService.update_profile(session, payload, current_user)), message="Cyber Warrior profile updated.")
