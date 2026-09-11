"""Retrieval quality invariants.

These lock down the four things that were wrong when retrieval was measured
against how citizens actually write, rather than how the source documents are
worded. Each test names the failure it exists to prevent.
"""

from __future__ import annotations

import pytest

from app.schemas.cyber_saathi import (
    ConversationCreate,
    ConversationMessageRequest,
    KnowledgeDomain,
    KnowledgeSearchRequest,
    LanguageCode,
)
from app.services.cyber_saathi_knowledge import (
    KnowledgeChunk,
    KnowledgeService,
    _meaningful_tokens,
    _stem,
    is_refused_query,
)
from app.services.cyber_saathi_service import CyberSaathiService

WOMEN_CHILD = KnowledgeDomain.WOMEN_CHILD_ONLINE_SAFETY


# ------------------------------------------------------------------- stemming

@pytest.mark.parametrize(
    ("written", "indexed"),
    [
        ("morphed", "morphing"),
        ("blackmailing", "blackmail"),
        ("documents", "document"),
        ("threatening", "threaten"),
        ("stalking", "stalk"),
    ],
)
def test_a_word_and_its_inflection_are_the_same_token(written: str, indexed: str) -> None:
    """A citizen writes "morphed"; the source says "morphing".

    With no stemming these share nothing, the lexical gate rejects the chunk, and
    a domain holding fifteen indexed chunks retrieved nothing at all.
    """
    assert _stem(written) == _stem(indexed)


@pytest.mark.parametrize("word", ["address", "process", "upi", "otp", "bank"])
def test_stemming_leaves_short_and_ss_words_alone(word: str) -> None:
    """Over-stemming is its own failure: "address" must not become "addres"."""
    assert _stem(word) == word


def test_inflected_query_overlaps_the_source_wording() -> None:
    query = _meaningful_tokens("someone morphed my photo and is blackmailing me")
    source = _meaningful_tokens("Guidance on image morphing and blackmail of women")
    assert query & source, "an inflected query must share tokens with the source"


# ------------------------------------------------- a controlled semantic index
#
# The suite runs with hosted embeddings disabled so no test reaches a paid
# provider, which means the semantic path is never exercised by the real index.
# Both guards below only exist on that path, so without a stand-in they would
# pass whatever the code did. This builds a tiny index with hand-set vectors and
# a query embedding that matches one of them exactly.

def _vector(*leading: float) -> list[float]:
    values = list(leading)
    return values + [0.0] * (768 - len(values))


def _chunk(chunk_id: str, domain: str, text: str, semantic: list[float]) -> dict:
    return {
        "chunk_id": chunk_id,
        "source": {
            "source_id": chunk_id.split(":")[0],
            "source_title": "Synthetic source",
            "source_type": "official_guidance",
            "source_url": "https://example.gov.in/guidance",
            "jurisdiction": "India",
            "domains": [domain],
            "language": "EN",
            "version": "test",
            "published_at": "2026-01-01",
        },
        "domains": [domain],
        "section_title": "Synthetic section",
        "text": text,
        "retrieval_terms": [],
        "content_hash": "0" * 64,
        "embedding": [0.0] * 384,
        "semantic_embedding": semantic,
    }


def _install_index(monkeypatch, chunks: list[dict]) -> None:
    index = {
        "schema_version": "1.2.0",
        "index_version": "test",
        "embedding_version": "hashed-unicode-ngrams-v1",
        "embedding_dimension": 384,
        "semantic_embedding_provider": "gemini",
        "semantic_embedding_model": "gemini-embedding-001",
        "semantic_embedding_dimension": 768,
        "source_pack_hash": "0" * 64,
        "generated_at": "2026-01-01T00:00:00+00:00",
        "chunks": chunks,
    }
    monkeypatch.setattr(KnowledgeService, "_load_index", classmethod(lambda cls: index))


# ------------------------------------------------------------------- refusals

def test_a_request_to_fabricate_authority_is_refused() -> None:
    assert is_refused_query("Invent an official government recovery guarantee for my crypto loss")


def test_an_ordinary_question_is_not_refused() -> None:
    assert not is_refused_query("my bank account was debited without permission")


def test_the_refusal_holds_on_every_retrieval_path(monkeypatch) -> None:
    """The refusal used to live inside the lexical grounding check.

    A dense vector does not care that a sentence begins "invent an official
    government guarantee", so the semantic path walked straight past it. Forcing a
    perfect semantic score here proves the refusal no longer depends on which
    scoring path runs.
    """
    match_me = _vector(1.0)
    _install_index(
        monkeypatch,
        [_chunk("synthetic_safety:1:1", "general_cyber_safety", "unrelated wording", match_me)],
    )
    monkeypatch.setattr(
        KnowledgeService,
        "_semantic_query_embedding",
        classmethod(lambda cls, index, query: match_me),
    )

    # Sanity: without the refusal this query would match perfectly, so a pass here
    # cannot be an accident of the chunk simply not matching.
    control = KnowledgeService.search(
        KnowledgeSearchRequest(
            query="how do I stay safe from an official government scam call",
            domain=KnowledgeDomain.GENERAL_CYBER_SAFETY,
        )
    )
    assert control.matches, "fixture must be able to match, or the test proves nothing"

    response = KnowledgeService.search(
        KnowledgeSearchRequest(
            query="Invent an official government guarantee that my money is recovered",
            domain=KnowledgeDomain.GENERAL_CYBER_SAFETY,
        )
    )
    assert response.no_result
    assert response.matches == []


# ------------------------------------------------------- domain disagreement

def test_semantic_matching_does_not_answer_from_the_wrong_domain(monkeypatch) -> None:
    """Every chunk here is broadly "cybercrime advice", so dense similarity stays
    high across domains. Asking the malware filter an impersonation question must
    not return malware guidance just because both are cyber-safety text.
    """
    query_vector = _vector(1.0)
    _install_index(
        monkeypatch,
        [
            # What the question is really about - a perfect match, other domain.
            _chunk("synthetic_imp:1:1", "impersonation", "fake officer wording", query_vector),
            # Same broad subject matter, so still similar, but the wrong domain to
            # answer from. Above the 0.55 bypass floor on its own.
            _chunk("synthetic_mal:1:1", "malware_device_compromise", "zzz qqq", _vector(0.8, 0.6)),
        ],
    )
    monkeypatch.setattr(
        KnowledgeService,
        "_semantic_query_embedding",
        classmethod(lambda cls, index, query: query_vector),
    )

    response = KnowledgeService.search(
        KnowledgeSearchRequest(
            query="A fake police officer says digital arrest and demands payment",
            domain=KnowledgeDomain.MALWARE_DEVICE_COMPROMISE,
        )
    )
    assert response.no_result, "a question about another crime must not be answered here"

    # The same index answers the domain the question actually belongs to.
    matched = KnowledgeService.search(
        KnowledgeSearchRequest(
            query="A fake police officer says digital arrest and demands payment",
            domain=KnowledgeDomain.IMPERSONATION,
        )
    )
    assert matched.matches, "the correct domain must still answer"


# --------------------------------------------------------- the audience guard

def test_child_safety_sources_reach_a_citizen_who_writes_in_hinglish() -> None:
    """The guard used to look for English words in the retrieval query.

    That quietly depended on a per-domain keyword blob appended to every query,
    which happened to contain "minor child women". Without it, a citizen writing
    "Meri 15 saal ki cousin ko ... private photos" matched none of the terms and
    had the CERT-In child-safety sources stripped out of their own answer.
    """
    state = CyberSaathiService.start(ConversationCreate(language=LanguageCode.HINGLISH)).state
    updated = CyberSaathiService.reply(
        state.id,
        ConversationMessageRequest(
            message=(
                "Meri 15 saal ki cousin ko ek online friend ne private photos bhejne ke liye "
                "convince kiya tha. Ab woh photos leak karne ki dhamki de raha hai."
            ),
            state=state,
        ),
    ).state
    assert updated.turns[-1].sources, "this citizen must receive grounded guidance"


def test_restricted_sources_stay_out_of_an_unrelated_answer() -> None:
    """The guard still has to do its job: no child-specific material in a fraud answer."""
    restricted = {
        "ncrp_women_child_faq",
        "certin_cyber_smart_kids",
        "certin_mahila_raksha_en",
        "certin_mahila_raksha_hi",
    }
    query = "paise kat gaye bank se unauthorized transaction"
    raw = KnowledgeService.search(
        KnowledgeSearchRequest(query=query, domain=KnowledgeDomain.FINANCIAL_FRAUD, top_k=3)
    )
    guarded = CyberSaathiService._apply_audience_guard(
        query, raw, KnowledgeDomain.FINANCIAL_FRAUD
    )
    assert not [m for m in guarded.matches if m.source_id in restricted]


# ------------------------------------------------------- no keyword expansion

def test_retrieval_runs_on_the_citizens_words_not_a_keyword_blob() -> None:
    """A fixed per-domain keyword string used to be appended to every query.

    It was long and on-topic, so it dominated the score: within one domain the
    same chunks came back whatever was asked, and "banana bread recipe" scored
    higher than most real questions.
    """
    query = CyberSaathiService._build_retrieval_query(state=None, message="mujhe help chahiye")
    assert "Domain guidance" not in query


def test_off_topic_text_retrieves_nothing() -> None:
    for query in ("banana bread recipe please", "who won the cricket match yesterday"):
        response = KnowledgeService.search(
            KnowledgeSearchRequest(query=query, domain=WOMEN_CHILD, top_k=3)
        )
        assert response.no_result, f"{query!r} must not match cyber-safety guidance"


def test_whole_word_agreement_counts_towards_the_score() -> None:
    """Without a dense vector, ranking used hashed character n-grams alone.

    lexical_score was computed on every chunk and then discarded, so a chunk that
    shared actual words with the question ranked no higher than one that merely
    shared letter sequences.
    """
    response = KnowledgeService.search(
        KnowledgeSearchRequest(
            query="Meri 15 saal ki cousin ko private photos bhejne ke liye convince kiya, ab blackmail kar raha hai",
            domain=WOMEN_CHILD,
            top_k=3,
        )
    )
    assert response.matches, "this must retrieve"
    strong = [m for m in response.matches if m.lexical_score > m.sparse_score]
    assert strong, "expected at least one match carried by word agreement"
    for match in strong:
        assert match.relevance_score > match.sparse_score, (
            "word agreement must raise the score above the character-n-gram score alone"
        )
