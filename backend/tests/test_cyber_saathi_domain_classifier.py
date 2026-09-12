"""Semantic domain classification: recall for the lexicon, without spending precision.

The suite runs with hosted embeddings disabled, so ``classify_semantically``
returns None here and the service falls back to the lexicon. That degradation is
itself the contract - it is what keeps Cyber Saathi working when no provider is
configured - so it is tested directly, and the ranking maths is tested against a
controlled set of centroids rather than a live model.
"""

from __future__ import annotations

import json

import pytest

from app.schemas.cyber_saathi import (
    ConfidenceBand,
    ConversationCreate,
    ConversationMessageRequest,
    CrimeDomain,
    Intent,
    LanguageCode,
)
from app.services import cyber_saathi_domain_classifier as classifier
from app.services.cyber_saathi_service import CyberSaathiService
from app.services.cyber_saathi_understanding import UnderstandingEngine


def _install_centroids(monkeypatch, centroids: dict[str, list[float]], query: list[float]) -> None:
    index = {
        "version": "test",
        "provider": "gemini",
        "model": "gemini-embedding-001",
        "dimension": len(query),
        "centroids": centroids,
    }
    monkeypatch.setattr(classifier, "_load_centroids", lambda: index)

    class _Provider:
        provider = "gemini"
        model = "gemini-embedding-001"
        dimensions = len(query)
        configured = True

        def query_embedding(self, text: str) -> list[float]:
            return query

    monkeypatch.setattr(classifier, "GeminiSemanticEmbeddingProvider", _Provider)


# ------------------------------------------------------------------ the assets

def test_every_crime_domain_has_exemplar_phrasings() -> None:
    """A domain with no exemplars can never be recovered from an unknown."""
    payload = json.loads(classifier.EXEMPLARS_PATH.read_text(encoding="utf-8"))
    covered = set(payload["exemplars"])
    expected = {
        domain.value
        for domain in CrimeDomain
        if domain not in {CrimeDomain.UNKNOWN, CrimeDomain.OTHER}
    }
    assert covered == expected


def test_the_committed_centroids_match_the_exemplars() -> None:
    """The centroids are built from the exemplars; a mismatch means a stale build."""
    exemplars = json.loads(classifier.EXEMPLARS_PATH.read_text(encoding="utf-8"))
    centroids = json.loads(classifier.CENTROIDS_PATH.read_text(encoding="utf-8"))
    assert set(centroids["centroids"]) == set(exemplars["exemplars"])
    assert centroids["version"] == exemplars["version"]
    assert all(len(vector) == centroids["dimension"] for vector in centroids["centroids"].values())


def test_exemplars_are_citizen_phrasings_not_domain_names() -> None:
    """Matching against the label "online harassment" defeats the purpose - people
    do not type that."""
    payload = json.loads(classifier.EXEMPLARS_PATH.read_text(encoding="utf-8"))
    for domain, phrases in payload["exemplars"].items():
        for phrase in phrases:
            assert phrase.casefold() != domain.replace("_", " "), phrase
            assert len(phrase.split()) >= 4, f"too short to be a real message: {phrase}"


# ----------------------------------------------------------- the ranking rules

def test_a_clear_winner_is_returned(monkeypatch) -> None:
    _install_centroids(
        monkeypatch,
        {"online_harassment": [1.0, 0.0], "financial_fraud": [0.0, 1.0]},
        query=[1.0, 0.0],
    )
    assert classifier.classify_semantically("anything") == CrimeDomain.ONLINE_HARASSMENT


def test_an_off_topic_message_is_refused(monkeypatch) -> None:
    """Off-topic text topped out at 0.695 when measured; the floor sits above it.

    Without a floor every message gets *some* nearest domain, and confidently
    wrong guidance is worse than asking what happened.
    """
    _install_centroids(
        monkeypatch,
        {"online_harassment": [1.0, 0.0], "financial_fraud": [0.0, 1.0]},
        query=[0.6, 0.1],  # similarity well under MIN_SIMILARITY
    )
    assert classifier.classify_semantically("banana bread recipe") is None


def test_a_dead_heat_is_refused(monkeypatch) -> None:
    _install_centroids(
        monkeypatch,
        {"online_harassment": [1.0, 0.0], "cyberstalking": [1.0, 0.0]},
        query=[1.0, 0.0],
    )
    assert classifier.classify_semantically("anything") is None


def test_the_lexicon_is_only_overruled_by_a_strong_reading(monkeypatch) -> None:
    """A medium reading must not overturn a keyword match; a strong one must.

    The lexicon's failures are confident ones - "he recorded me on video call and
    now demands money" is sextortion, but the money words send it to financial
    fraud - so the override has to exist, with a higher bar.
    """
    medium = [0.72, 0.30]
    _install_centroids(
        monkeypatch,
        {"women_child_online_safety": [1.0, 0.0], "financial_fraud": [0.0, 1.0]},
        query=medium,
    )
    assert classifier.classify_semantically("x", lexicon_confident=True) is None
    assert classifier.classify_semantically("x", lexicon_confident=False) is not None

    _install_centroids(
        monkeypatch,
        {"women_child_online_safety": [1.0, 0.0], "financial_fraud": [0.0, 1.0]},
        query=[0.96, 0.10],
    )
    assert (
        classifier.classify_semantically("x", lexicon_confident=True)
        == CrimeDomain.WOMEN_CHILD_ONLINE_SAFETY
    )


# -------------------------------------------------- degradation and the service

def test_without_a_provider_nothing_changes() -> None:
    """The suite runs with embeddings disabled, which is the offline contract."""
    assert classifier.classify_semantically("एक आदमी मुझे गंदे मैसेज भेज रहा है") is None


def test_a_resolved_domain_also_lifts_confidence_and_intent(monkeypatch) -> None:
    """Resolving the domain alone was not enough.

    confidence_band is a stored field on UnderstandingResult, not a computed
    property, so leaving it stale kept the band at "low" beside a confidence of
    0.96 - and the routing reads the band, so the citizen was still told
    "मुझे स्पष्ट नहीं है कि क्या हुआ" about a message we had just understood.
    """
    monkeypatch.setattr(
        "app.services.cyber_saathi_service.classify_semantically",
        lambda message, lexicon_confident=False: CrimeDomain.ONLINE_HARASSMENT,
    )
    state = CyberSaathiService.start(ConversationCreate(language=LanguageCode.HI)).state
    message = "एक आदमी मुझे WhatsApp पर गंदे मैसेज भेज रहा है"
    understanding = UnderstandingEngine.analyze(message, state.language)
    assert understanding.crime_domain == CrimeDomain.UNKNOWN

    resolved = CyberSaathiService._resolve_crime_domain(state, message, understanding)

    assert resolved.crime_domain == CrimeDomain.ONLINE_HARASSMENT
    assert resolved.intent == Intent.REPORT_INCIDENT
    assert resolved.confidence_band == ConfidenceBand.HIGH
    assert resolved.needs_clarification is False


def test_an_incident_that_already_has_a_domain_is_not_reclassified(monkeypatch) -> None:
    """Cost control: this must be about one embedding per conversation, not per turn."""
    calls: list[str] = []
    monkeypatch.setattr(
        "app.services.cyber_saathi_service.classify_semantically",
        lambda message, lexicon_confident=False: calls.append(message) or CrimeDomain.MALWARE,
    )
    state = CyberSaathiService.start(ConversationCreate(language=LanguageCode.HI)).state
    state.incident.crime_domain = CrimeDomain.ONLINE_HARASSMENT
    understanding = UnderstandingEngine.analyze("कुछ और हुआ", state.language)

    CyberSaathiService._resolve_crime_domain(state, "कुछ और हुआ", understanding)

    assert calls == [], "an incident with a domain must not be re-classified"


def test_a_classifier_failure_never_breaks_the_reply(monkeypatch) -> None:
    def explode(message: str, lexicon_confident: bool = False):
        raise RuntimeError("provider down")

    monkeypatch.setattr("app.services.cyber_saathi_service.classify_semantically", explode)
    state = CyberSaathiService.start(ConversationCreate(language=LanguageCode.HI)).state
    updated = CyberSaathiService.reply(
        state.id,
        ConversationMessageRequest(message="मुझे कोई परेशान कर रहा है", state=state),
    ).state
    assert updated.turns[-1].content
