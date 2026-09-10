from typing import Annotated, Literal

from fastapi import APIRouter, Query, Response

from app.core.errors import success_response
from app.schemas.common import ErrorResponse, SuccessResponse
from app.schemas.secure_india import SecureIndiaSource, SecureIndiaSummary
from app.services.secure_india_service import SecureIndiaService


router = APIRouter(prefix="/secure-india", tags=["secure-india"])


@router.get("/metadata", response_model=SuccessResponse[SecureIndiaSource])
def get_secure_india_metadata(response: Response) -> dict[str, object]:
    response.headers["Cache-Control"] = "public, max-age=300"
    return success_response(SecureIndiaService.metadata())


@router.get("/summary", response_model=SuccessResponse[SecureIndiaSummary], responses={422: {"model": ErrorResponse}})
def get_secure_india_summary(
    response: Response,
    crime_type: Annotated[str, Query(max_length=32)] = "all",
    state: Annotated[str, Query(max_length=80)] = "all",
    city: Annotated[str, Query(max_length=80)] = "all",
    period: Literal["7d", "30d", "1y"] = "30d",
    view: Literal["count", "per_lakh"] = "count",
) -> dict[str, object]:
    response.headers["Cache-Control"] = "public, max-age=300"
    return success_response(SecureIndiaService.summary(crime_type=crime_type, state=state, city=city, period=period, view=view))
