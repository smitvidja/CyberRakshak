from uuid import UUID

from typing import Annotated

from fastapi import APIRouter, File, Form, UploadFile, status
from pydantic import ValidationError

from app.core.errors import APIError, success_response
from app.schemas.common import SuccessResponse
from app.schemas.cyber_saathi import (
    ConversationCreate,
    ConversationMessageRequest,
    ConversationResponse,
    ConversationState,
    KnowledgeSearchRequest,
    KnowledgeSearchResponse,
    UnderstandingRequest,
    UnderstandingResult,
)
from app.services.cyber_saathi_service import CyberSaathiService
from app.services.cyber_saathi_attachment import read_and_analyze_attachment
from app.services.cyber_saathi_knowledge import KnowledgeService
from app.services.cyber_saathi_understanding import UnderstandingEngine


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


@router.post(
    "/conversations/{conversation_id}/attachments",
    response_model=SuccessResponse[ConversationResponse],
)
async def analyze_conversation_attachment(
    conversation_id: UUID,
    file: Annotated[UploadFile, File(...)],
    state_json: Annotated[str, Form()],
) -> dict[str, object]:
    try:
        state = ConversationState.model_validate_json(state_json)
    except ValidationError:
        raise APIError(
            status_code=422,
            code="INVALID_CONVERSATION_STATE",
            message="The conversation state could not be validated.",
        ) from None
    analysis, _ = await read_and_analyze_attachment(file)
    return success_response(CyberSaathiService.add_attachment(conversation_id, state, analysis))


@router.post(
    "/understand",
    response_model=SuccessResponse[UnderstandingResult],
)
def understand_message(payload: UnderstandingRequest) -> dict[str, object]:
    return success_response(
        UnderstandingEngine.analyze(payload.message, payload.preferred_language)
    )


@router.post(
    "/knowledge/search",
    response_model=SuccessResponse[KnowledgeSearchResponse],
)
def search_knowledge(payload: KnowledgeSearchRequest) -> dict[str, object]:
    return success_response(KnowledgeService.search(payload))
