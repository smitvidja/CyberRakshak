from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.database import get_db_session
from app.core.errors import APIError, success_response
from app.core.security import create_access_token, get_current_user
from app.models import User
from app.schemas.auth import AccessToken, AuthenticatedUser, LoginRequest, RegistrationRequest
from app.schemas.common import ErrorResponse, SuccessResponse
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/register",
    status_code=status.HTTP_201_CREATED,
    response_model=SuccessResponse[AuthenticatedUser],
    responses={409: {"model": ErrorResponse}, 403: {"model": ErrorResponse}},
)
def register(
    payload: RegistrationRequest,
    session: Annotated[Session, Depends(get_db_session)],
) -> dict[str, object]:
    user = AuthService.register(session, payload)
    return success_response(
        AuthenticatedUser.model_validate(user),
        message="Account created successfully.",
    )


@router.post(
    "/login",
    response_model=SuccessResponse[AccessToken],
    responses={401: {"model": ErrorResponse}},
)
def login(
    payload: LoginRequest,
    session: Annotated[Session, Depends(get_db_session)],
) -> dict[str, object]:
    user = AuthService.authenticate(session, payload)
    if user is None:
        raise APIError(
            status_code=401,
            code="INVALID_CREDENTIALS",
            message="Invalid email or password.",
        )

    access_token, expires_in = create_access_token(user.id)
    return success_response(
        AccessToken(access_token=access_token, expires_in=expires_in),
        message="Authentication successful.",
    )


@router.get(
    "/me",
    response_model=SuccessResponse[AuthenticatedUser],
    responses={401: {"model": ErrorResponse}},
)
def read_current_user(
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict[str, object]:
    return success_response(AuthenticatedUser.model_validate(current_user))
