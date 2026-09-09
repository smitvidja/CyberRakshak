from uuid import UUID

from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, UploadFile, status
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.core.errors import APIError, success_response
from app.core.database import get_db_session
from app.schemas.common import SuccessResponse
from app.schemas.cyber_saathi import (
    ConversationCreate,
    ConversationFeedback,
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
from app.services.cyber_saathi_persistence import CyberSaathiPersistence
from app.services.cyber_saathi_understanding import UnderstandingEngine


router = APIRouter(prefix="/cyber-saathi", tags=["cyber-saathi"])


@router.post(
    "/conversations",
    response_model=SuccessResponse[ConversationResponse],
    status_code=status.HTTP_201_CREATED,
)
def start_conversation(
    payload: ConversationCreate,
    session: Annotated[Session, Depends(get_db_session)],
) -> dict[str, object]:
    response = CyberSaathiService.start(payload)
    CyberSaathiPersistence.save(session, response.state)
    return success_response(response)


@router.get(
    "/conversations/{conversation_id}",
    response_model=SuccessResponse[ConversationResponse],
)
def resume_conversation(
    conversation_id: UUID,
    session: Annotated[Session, Depends(get_db_session)],
) -> dict[str, object]:
    return success_response(ConversationResponse(state=CyberSaathiPersistence.load(session, conversation_id)))


@router.post(
    "/conversations/{conversation_id}/messages",
    response_model=SuccessResponse[ConversationResponse],
)
def send_message(
    conversation_id: UUID,
    payload: ConversationMessageRequest,
    session: Annotated[Session, Depends(get_db_session)],
) -> dict[str, object]:
    if payload.state.storage_consent:
        try:
            payload = payload.model_copy(update={"state": CyberSaathiPersistence.load(session, conversation_id)})
        except APIError as error:
            if error.code != "CONVERSATION_NOT_FOUND":
                raise
    response = CyberSaathiService.reply(conversation_id, payload)
    CyberSaathiPersistence.save(session, response.state)
    return success_response(response)


@router.post("/conversations/{conversation_id}/feedback", status_code=status.HTTP_204_NO_CONTENT)
def save_conversation_feedback(
    conversation_id: UUID,
    payload: ConversationFeedback,
    session: Annotated[Session, Depends(get_db_session)],
) -> None:
    CyberSaathiPersistence.add_feedback(session, conversation_id, payload.rating, payload.comment)


@router.post(
    "/conversations/{conversation_id}/attachments",
    response_model=SuccessResponse[ConversationResponse],
)
async def analyze_conversation_attachment(
    conversation_id: UUID,
    file: Annotated[UploadFile, File(...)],
    state_json: Annotated[str, Form()],
    session: Annotated[Session, Depends(get_db_session)],
) -> dict[str, object]:
    try:
        state = ConversationState.model_validate_json(state_json)
    except ValidationError:
        raise APIError(
            status_code=422,
            code="INVALID_CONVERSATION_STATE",
            message="The conversation state could not be validated.",
        ) from None
    if state.storage_consent:
        state = CyberSaathiPersistence.load(session, conversation_id)
    analysis, _ = await read_and_analyze_attachment(file)
    response = CyberSaathiService.add_attachment(conversation_id, state, analysis)
    CyberSaathiPersistence.save(session, response.state)
    return success_response(response)


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
