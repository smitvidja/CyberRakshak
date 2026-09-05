from uuid import UUID

from fastapi import APIRouter, status

from app.core.errors import success_response
from app.schemas.common import SuccessResponse
from app.schemas.cyber_saathi import (
    ConversationCreate,
    ConversationMessageRequest,
    ConversationResponse,
)
from app.services.cyber_saathi_service import CyberSaathiService


router = APIRouter(prefix="/cyber-saathi", tags=["cyber-saathi"])


@router.post(
    "/conversations",
    response_model=SuccessResponse[ConversationResponse],
    status_code=status.HTTP_201_CREATED,
)
def start_conversation(payload: ConversationCreate) -> dict[str, object]:
    return success_response(CyberSaathiService.start(payload))


@router.post(
    "/conversations/{conversation_id}/messages",
    response_model=SuccessResponse[ConversationResponse],
)
def send_message(
    conversation_id: UUID, payload: ConversationMessageRequest
) -> dict[str, object]:
    return success_response(CyberSaathiService.reply(conversation_id, payload))
