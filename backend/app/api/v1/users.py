from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db_session
from app.core.errors import APIError, success_response
from app.core.security import get_current_user
from app.models import User
from app.schemas.common import ErrorResponse, SuccessResponse
from app.schemas.user import CitizenProfileInput, CitizenProfileResponse
from app.services.user_service import UserService

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me/profile", response_model=SuccessResponse[CitizenProfileResponse], responses={401: {"model": ErrorResponse}, 404: {"model": ErrorResponse}})
def get_my_profile(session: Annotated[Session, Depends(get_db_session)], current_user: Annotated[User, Depends(get_current_user)]) -> dict[str, object]:
    profile = UserService.get_citizen_profile(session, current_user)
    if profile is None:
        raise APIError(status_code=404, code="PROFILE_NOT_FOUND", message="Profile not found.")
    return success_response(CitizenProfileResponse.model_validate(profile))


@router.put("/me/profile", response_model=SuccessResponse[CitizenProfileResponse], responses={401: {"model": ErrorResponse}})
def put_my_profile(payload: CitizenProfileInput, session: Annotated[Session, Depends(get_db_session)], current_user: Annotated[User, Depends(get_current_user)]) -> dict[str, object]:
    profile = UserService.upsert_citizen_profile(session, current_user, payload)
    return success_response(CitizenProfileResponse.model_validate(profile), message="Profile saved.")
