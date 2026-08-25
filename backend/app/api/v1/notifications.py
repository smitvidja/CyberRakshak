from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db_session
from app.core.errors import success_response
from app.core.security import get_current_user
from app.models import User
from app.schemas.common import ErrorResponse, SuccessResponse
from app.schemas.notification import NotificationResponse
from app.services.notification_service import NotificationService

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get(
    "",
    response_model=SuccessResponse[list[NotificationResponse]],
    responses={401: {"model": ErrorResponse}},
)
def list_notifications(
    session: Annotated[Session, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict[str, object]:
    notifications = NotificationService.list_for_current_user(session, current_user)
    return success_response(
        [NotificationResponse.model_validate(item) for item in notifications]
    )


@router.patch(
    "/{notification_id}/read",
    response_model=SuccessResponse[NotificationResponse],
    responses={
        401: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
    },
)
def mark_notification_read(
    notification_id: UUID,
    session: Annotated[Session, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict[str, object]:
    notification = NotificationService.mark_read(
        session,
        notification_id,
        current_user,
    )
    return success_response(
        NotificationResponse.model_validate(notification),
        message="Notification marked as read.",
    )
