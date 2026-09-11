from uuid import UUID

from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, UploadFile, WebSocket, status
from fastapi.responses import StreamingResponse
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.core.errors import APIError, success_response
from app.core.database import get_db_session
from app.schemas.common import SuccessResponse
from app.schemas.cyber_saathi import (
    ConversationCreate,
    ConversationFeedback,
    CrimeDomain,
    GroundingStatus,
    ConversationMessageRequest,
    ConversationResponse,
    ConversationState,
    KnowledgeSearchRequest,
    KnowledgeSearchResponse,
    LanguageCode,
    UnderstandingRequest,
    UnderstandingResult,
    VoiceCapabilities,
    VoiceSpeechRequest,
    VoiceTranscription,
)
from app.services.cyber_saathi_service import CyberSaathiService
from app.services.cyber_saathi_attachment import read_and_analyze_attachment
from app.services.cyber_saathi_knowledge import KnowledgeService
from app.services.cyber_saathi_persistence import CyberSaathiPersistence
from app.services.cyber_saathi_understanding import UnderstandingEngine
from app.services.knowledge_gap_service import UNFILED_CRIME_DOMAINS, KnowledgeGapService
from app.services.cyber_saathi_voice import SarvamVoiceAdapter, VoiceProviderError


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
            stored = CyberSaathiPersistence.load(session, conversation_id)
            # The stored copy stays authoritative for conversation content, so a
            # stale or tampered client state cannot rewrite the record. The
            # language selector is the exception: it is a live control the
            # citizen just used, and reloading over it silently discarded their
            # choice, so a consented chat could never change language.
            stored.language = payload.state.language
            payload = payload.model_copy(update={"state": stored})
        except APIError as error:
            if error.code != "CONVERSATION_NOT_FOUND":
                raise
    prior_state = payload.state
    response = CyberSaathiService.reply(conversation_id, payload)
    CyberSaathiPersistence.save(session, response.state)
    _record_knowledge_gap(session, payload.message, prior_state, response.state)
    return success_response(response)


# Retrieval found nothing for a question we had classified into a domain. That is
# the signal worth keeping: not the answer given, but the fact that the corpus
# came up short here, so it can be grown against real demand.
_RETRIEVAL_MISS = {GroundingStatus.NO_RESULT, GroundingStatus.DETERMINISTIC_PLAYBOOK}


def _is_citizen_question(message: str, prior_state: ConversationState) -> bool:
    """Distinguish a question from a reply to our own conversation.

    The gap list is only useful if it holds things citizens asked and did not get
    an answer to. Two kinds of message are not that, and both were landing in it:
    an answer to a scripted intake question, and the citizen tapping an action
    Cyber Saathi itself proposed - "Prepare report draft" arrived three times
    before this existed.
    """
    if prior_state.pending_question is not None:
        return False
    previous_assistant = next(
        (turn.content for turn in reversed(prior_state.turns) if turn.role != "user"), ""
    )
    normalised = " ".join(message.split()).casefold()
    return bool(normalised) and normalised not in previous_assistant.casefold()


def _record_knowledge_gap(
    session: Session, message: str, prior_state: ConversationState, state: ConversationState
) -> None:
    # Only for a conversation the citizen agreed to store. Without consent they
    # were told nothing is kept, and a redacted question is still their question.
    if not state.storage_consent or not state.turns:
        return
    if not _is_citizen_question(message, prior_state):
        return
    last = state.turns[-1]
    crime_domain = state.incident.crime_domain
    if crime_domain in {CrimeDomain.UNKNOWN, CrimeDomain.OTHER}:
        # Nothing actionable: a reviewer cannot go and find a source for "unknown".
        return
    # Two shapes of gap. The obvious one is retrieval citing nothing. The other is a
    # crime domain the corpus has no filing for: the search then runs unfiltered,
    # generic safety chunks match, and the citizen is answered from material that is
    # not about their crime - which reads as a hit and is the widest gap of all.
    cited_nothing = last.grounding_status in _RETRIEVAL_MISS or not last.sources
    unfiled_domain = crime_domain.value in UNFILED_CRIME_DOMAINS
    if not (cited_nothing or unfiled_domain):
        return
    try:
        KnowledgeGapService.record(
            session,
            question=message,
            crime_domain=crime_domain.value,
            knowledge_domain=None,
            language=state.language.value,
        )
        session.commit()
    except Exception:  # noqa: BLE001
        # Improving the corpus later must never cost a citizen their answer now.
        session.rollback()


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


@router.get(
    "/voice/capabilities",
    response_model=SuccessResponse[VoiceCapabilities],
)
def voice_capabilities() -> dict[str, object]:
    return success_response(SarvamVoiceAdapter().capabilities())


@router.post(
    "/voice/transcriptions",
    response_model=SuccessResponse[VoiceTranscription],
)
async def transcribe_voice_recording(
    file: Annotated[UploadFile, File(...)],
    language: Annotated[LanguageCode, Form()],
) -> dict[str, object]:
    audio = await file.read()
    try:
        result = await SarvamVoiceAdapter().transcribe(
            audio=audio,
            filename=file.filename or "recording.webm",
            content_type=file.content_type or "application/octet-stream",
            language=language,
        )
    except VoiceProviderError as error:
        raise APIError(
            status_code=error.status_code,
            code=error.code,
            message=error.message,
        ) from error
    return success_response(result)


@router.post("/voice/speech", response_class=StreamingResponse)
async def synthesize_voice_response(payload: VoiceSpeechRequest) -> StreamingResponse:
    try:
        prepared = await SarvamVoiceAdapter().synthesize(
            text=payload.text,
            language=payload.language,
        )
    except VoiceProviderError as error:
        raise APIError(
            status_code=error.status_code,
            code=error.code,
            message=error.message,
        ) from error
    return StreamingResponse(
        prepared.body,
        media_type=prepared.content_type,
        headers={
            "Cache-Control": "no-store",
            "X-Voice-Provider": "sarvam",
            "X-TTS-First-Audio-Ms": str(prepared.first_audio_ms),
        },
    )


@router.websocket("/conversations/{conversation_id}/voice/transcriptions/stream")
async def stream_voice_transcription(
    websocket: WebSocket,
    conversation_id: UUID,
    language: LanguageCode,
) -> None:
    del conversation_id
    await SarvamVoiceAdapter().relay_realtime_transcription(websocket, language)
