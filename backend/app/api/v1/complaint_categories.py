from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db_session
from app.core.errors import success_response
from app.schemas.common import SuccessResponse
from app.schemas.complaint import ComplaintCategoryResponse
from app.services.complaint_service import ComplaintService

router = APIRouter(prefix="/complaint-categories", tags=["complaint-categories"])


@router.get("", response_model=SuccessResponse[list[ComplaintCategoryResponse]])
def list_complaint_categories(
    session: Annotated[Session, Depends(get_db_session)],
) -> dict[str, object]:
    categories = ComplaintService.list_categories(session)
    return success_response(
        [ComplaintCategoryResponse.model_validate(category) for category in categories]
    )
