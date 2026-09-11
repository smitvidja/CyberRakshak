"""Conversation retention: an expired conversation is deleted, not merely hidden."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from sqlalchemy.orm import Session

from app.core.errors import APIError
from app.models import CyberSaathiConversation
from app.repositories.cyber_saathi_repository import CyberSaathiRepository
from app.schemas.cyber_saathi import ConversationCreate
from app.services.cyber_saathi_persistence import CyberSaathiPersistence
from app.services.cyber_saathi_service import CyberSaathiService


def _conversation(session: Session, *, expires_in_days: int) -> CyberSaathiConversation:
    now = datetime.now(timezone.utc)
    state = CyberSaathiService.start(ConversationCreate(storage_consent=True)).state
    state.id = uuid4()
    record = CyberSaathiConversation(
        id=state.id,
        state=state.model_dump(mode="json"),
        feedback=[],
        consented_at=now,
        expires_at=now + timedelta(days=expires_in_days),
    )
    session.add(record)
    session.flush()
    return record


def test_an_expired_conversation_is_actually_deleted(api_client) -> None:
    """Refusing to read is not deleting.

    load() already returned 404 past the retention window, so nothing surfaced
    these rows - and that made it easy to miss that they were still there,
    holding the conversation state of people who were told it would be gone.
    """
    _, session = api_client
    expired = _conversation(session, expires_in_days=-1)
    live = _conversation(session, expires_in_days=30)

    removed = CyberSaathiPersistence.purge_expired(session)

    assert removed >= 1
    assert session.get(CyberSaathiConversation, expired.id) is None
    assert session.get(CyberSaathiConversation, live.id) is not None


def test_purging_is_safe_to_run_repeatedly(api_client) -> None:
    """The container entrypoint runs this on every start."""
    _, session = api_client
    _conversation(session, expires_in_days=-1)

    first = CyberSaathiPersistence.purge_expired(session)
    second = CyberSaathiPersistence.purge_expired(session)

    assert first >= 1
    assert second == 0


def test_a_conversation_inside_its_window_survives(api_client) -> None:
    _, session = api_client
    live = _conversation(session, expires_in_days=30)

    CyberSaathiPersistence.purge_expired(session)

    assert session.get(CyberSaathiConversation, live.id) is not None
    # and is still loadable, so the purge did not disturb usable state
    assert CyberSaathiPersistence.load(session, live.id) is not None


def test_counting_does_not_delete(api_client) -> None:
    """--dry-run has to be genuinely read-only, or it is not a dry run."""
    _, session = api_client
    expired = _conversation(session, expires_in_days=-1)

    counted = CyberSaathiRepository.count_expired(session, datetime.now(timezone.utc))

    assert counted >= 1
    assert session.get(CyberSaathiConversation, expired.id) is not None


def test_an_expired_conversation_is_not_returned_before_it_is_purged(api_client) -> None:
    """The read-side guard still stands on its own; purging is defence in depth."""
    _, session = api_client
    expired = _conversation(session, expires_in_days=-1)

    with pytest.raises(APIError) as error:
        CyberSaathiPersistence.load(session, expired.id)

    assert error.value.code == "CONVERSATION_NOT_FOUND"
