"""Record what the authoritative corpus could not answer, so it can be grown.

The loop this belongs to is: a citizen asks something, retrieval finds nothing in
that domain, the question is recorded as a *gap*, repeats are counted, and a
reviewer eventually sees "forty-seven people asked about this and we had
nothing" and adds a real source.

What it deliberately does **not** do is harvest answers. Citizen text is not an
authoritative source - it is unverified, and a pipeline that fed it back into
retrieval would let whoever typed it write the guidance the next citizen
receives, which is a poisoning vector with a safety consequence rather than a
data-quality one. Section 0.7 of the Cyber Saathi prompt requires the corpus to
stay separately sourced, attributable and versioned, and this keeps that true:
the loop produces a reading list for a human, not new knowledge.

Consent: a signal is recorded only for a conversation the citizen consented to
store. Without consent they were told nothing is kept, and a redacted question is
still their question.
"""

from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import APIError
from app.models import KnowledgeGapSignal
from app.services.cyber_saathi_persistence import redact_text

MAX_SAMPLE_CHARS = 500
OPEN = "OPEN"
REVIEWED = "REVIEWED"
ACTIONED = "ACTIONED"
DISMISSED = "DISMISSED"
VALID_STATUSES = (OPEN, REVIEWED, ACTIONED, DISMISSED)

_NOISE = re.compile(r"[^a-z0-9ऀ-ॿ]+")


# Crime domains the authoritative corpus has no filing for at all: _knowledge_domain()
# maps them to nothing, so retrieval runs unfiltered and generic cyber-safety chunks
# match almost anything. The citizen is then answered from material that is not about
# their crime, which looks like a hit and is really the widest kind of gap there is.
# test_unfiled_domains_match_the_retrieval_mapping keeps this honest.
UNFILED_CRIME_DOMAINS = frozenset({"misinformation", "cyber_terrorism"})


def _normalise_for_digest(question: str) -> str:
    """Group the same question asked with different punctuation or casing."""
    return _NOISE.sub(" ", question.casefold()).strip()


def digest_question(question: str) -> str:
    return hashlib.sha256(_normalise_for_digest(question).encode("utf-8")).hexdigest()


class KnowledgeGapService:
    @staticmethod
    def record(
        session: Session,
        *,
        question: str,
        crime_domain: str,
        knowledge_domain: str | None,
        language: str,
    ) -> KnowledgeGapSignal | None:
        """Upsert one gap. Returns None when there is nothing worth recording."""
        normalised = _normalise_for_digest(question)
        if len(normalised) < 8:
            # "ok", "haan", "?" - a short acknowledgement is not a knowledge gap,
            # and counting it would bury the real ones.
            return None

        now = datetime.now(timezone.utc)
        question_digest = digest_question(question)
        existing = session.scalar(
            select(KnowledgeGapSignal).where(
                KnowledgeGapSignal.question_digest == question_digest,
                KnowledgeGapSignal.crime_domain == crime_domain,
            )
        )
        if existing is not None:
            existing.occurrences += 1
            existing.last_seen_at = now
            # Status is left alone on purpose. A gap that was actioned and is
            # still arriving is worth seeing as exactly that, and the reviewer can
            # tell from reviewed_at being older than last_seen_at.
            session.flush()
            return existing

        signal = KnowledgeGapSignal(
            question_digest=question_digest,
            # Redacted before it is stored, like the conversation state itself.
            sample_question=redact_text(" ".join(question.split()))[:MAX_SAMPLE_CHARS],
            crime_domain=crime_domain,
            knowledge_domain=knowledge_domain,
            language=language,
            occurrences=1,
            first_seen_at=now,
            last_seen_at=now,
            status=OPEN,
        )
        session.add(signal)
        session.flush()
        return signal

    @staticmethod
    def list_gaps(
        session: Session,
        *,
        status: str | None = None,
        crime_domain: str | None = None,
        min_occurrences: int = 1,
        limit: int = 100,
    ) -> list[KnowledgeGapSignal]:
        """Most-asked first: that ordering is the "do we have enough yet" answer."""
        query = select(KnowledgeGapSignal).where(
            KnowledgeGapSignal.occurrences >= min_occurrences
        )
        if status is not None:
            query = query.where(KnowledgeGapSignal.status == status)
        if crime_domain is not None:
            query = query.where(KnowledgeGapSignal.crime_domain == crime_domain)
        query = query.order_by(
            KnowledgeGapSignal.occurrences.desc(), KnowledgeGapSignal.last_seen_at.desc()
        ).limit(min(limit, 500))
        return list(session.scalars(query))

    @staticmethod
    def update_status(
        session: Session, gap_id: UUID, *, status: str, resolution_note: str | None
    ) -> KnowledgeGapSignal:
        if status not in VALID_STATUSES:
            raise APIError(
                status_code=422,
                code="INVALID_GAP_STATUS",
                message=f"Status must be one of {', '.join(VALID_STATUSES)}.",
            )
        signal = session.get(KnowledgeGapSignal, gap_id)
        if signal is None:
            raise APIError(
                status_code=404,
                code="KNOWLEDGE_GAP_NOT_FOUND",
                message="Knowledge gap signal not found.",
            )
        signal.status = status
        signal.resolution_note = (resolution_note or "").strip()[:2000] or None
        signal.reviewed_at = datetime.now(timezone.utc)
        session.commit()
        session.refresh(signal)
        return signal
