"""Small, persistent, source-traceable retrieval for Cyber Saathi.

The corpus is intentionally separate from the supplementary datasets inspected in
Session 9.2. ``rebuild_index`` is the only ingestion path; application startup
only reads the generated index after a citizen asks a knowledge question.
"""

import argparse
import hashlib
import json
import math
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx
from pydantic import BaseModel, Field

from app.core.errors import APIError
from app.schemas.cyber_saathi import (
    KnowledgeChunk,
    KnowledgeDomain,
    KnowledgeMatch,
    KnowledgeSearchRequest,
    KnowledgeSearchResponse,
    KnowledgeSourceMetadata,
    LanguageCode,
)
from app.services.cyber_saathi_semantic_embeddings import (
    GeminiSemanticEmbeddingProvider,
    SemanticEmbeddingError,
)
from app.services.cyber_saathi_understanding import DATA_DIR


KNOWLEDGE_DIR = DATA_DIR / "authoritative_knowledge"
SOURCE_PACK_PATH = KNOWLEDGE_DIR / "sources.json"
INDEX_PATH = KNOWLEDGE_DIR / "knowledge_index.json"
EVALUATION_CASES_PATH = DATA_DIR / "knowledge_evaluation_cases.json"
EMBEDDING_DIMENSION = 384
EMBEDDING_VERSION = "hashed-unicode-ngrams-v1"
INDEX_SCHEMA_VERSION = "1.2.0"
MAX_CHUNK_CHARS = 900
MAX_CONTEXT_CHARS = 2200
MAX_INDEX_BYTES = 8 * 1024 * 1024
MAX_INDEX_CHUNKS = 500
# ``\w`` splits Devanagari vowel and virama marks. Keep a full Devanagari
# sequence together so Hindi source/query lexical grounding is meaningful.
WORD_PATTERN = re.compile(r"[a-zA-Z0-9]+|[\u0900-\u097F]+", re.UNICODE)
SENTENCE_BOUNDARY = re.compile(r"(?<=[.!?।])\s+")
STOPWORDS = frozenset(
    {
        "a", "about", "an", "and", "are", "can", "do", "for", "give", "how", "i", "in", "is",
        "it", "me", "my", "of", "on", "or", "please", "should", "tell", "the", "to", "what",
        "with", "you", "aur", "hai", "ka", "ke", "ki", "ko", "kya", "main", "mere",
        "mujhe", "par", "se", "sirf", "ye", "this", "that", "today",
    }
)
HIGH_SIGNAL_TERMS = frozenset(
    {
        "cyberstalking", "harassment", "impersonation", "malware", "phishing",
        "ransomware", "sexting", "stalking", "upi",
    }
)


class KnowledgeSection(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    domains: list[KnowledgeDomain] = Field(min_length=1, max_length=6)
    text: str = Field(min_length=1, max_length=5000)
    retrieval_terms: list[str] = Field(default_factory=list, max_length=30)


class KnowledgeSourceDocument(KnowledgeSourceMetadata):
    sections: list[KnowledgeSection] = Field(min_length=1, max_length=50)


class KnowledgeSourcePack(BaseModel):
    version: str = Field(min_length=1, max_length=100)
    reviewed_at: str = Field(min_length=1, max_length=50)
    sources: list[KnowledgeSourceDocument] = Field(min_length=1, max_length=100)


def _normalize_text(value: str) -> str:
    return " ".join(value.strip().split())


def _hash_feature(feature: str) -> tuple[int, float]:
    digest = hashlib.blake2b(feature.encode("utf-8"), digest_size=8).digest()
    number = int.from_bytes(digest, "big")
    return number % EMBEDDING_DIMENSION, 1.0 if number & 1 else -1.0


def _features(value: str) -> list[tuple[str, float]]:
    words = WORD_PATTERN.findall(value.casefold())
    features: list[tuple[str, float]] = []
    for word in words:
        features.append((f"word:{word}", 1.0))
        padded = f"^{word}$"
        if len(padded) >= 5:
            for size in (3, 4):
                for offset in range(len(padded) - size + 1):
                    features.append((f"char:{padded[offset:offset + size]}", 0.16))
    for first, second in zip(words, words[1:]):
        features.append((f"pair:{first}_{second}", 0.35))
    return features


# A citizen writes "someone morphed my photo and is blackmailing me"; the source
# document says "morphing" and "blackmail". Without this the two share no tokens
# at all, the lexical gate rejects the chunk, and a domain with fifteen indexed
# chunks retrieves nothing. Only ASCII words are stemmed - Devanagari is matched
# whole, since WORD_PATTERN already keeps those sequences intact.
_SUFFIXES = ("ingly", "ing", "edly", "ed", "ies", "es", "s")
_MIN_STEM = 4


def _stem(token: str) -> str:
    if not token.isascii() or len(token) < 5:
        return token
    for suffix in _SUFFIXES:
        if not token.endswith(suffix):
            continue
        base = token[: -len(suffix)]
        if len(base) < _MIN_STEM:
            continue
        if suffix == "ies":
            return base + "y"
        # "address"/"process" end in "s" but stripping it is wrong.
        if suffix == "s" and token.endswith("ss"):
            return token
        return base
    return token


def _meaningful_tokens(value: str) -> set[str]:
    return {
        _stem(token)
        for token in WORD_PATTERN.findall(value.casefold())
        if len(token) >= 3 and token not in STOPWORDS
    }


def embed_text(value: str) -> list[float]:
    """Create a deterministic, Unicode-safe sparse embedding without a model download."""
    vector = [0.0] * EMBEDDING_DIMENSION
    for feature, weight in _features(_normalize_text(value)):
        index, sign = _hash_feature(feature)
        vector[index] += sign * weight
    magnitude = math.sqrt(sum(component * component for component in vector))
    if magnitude == 0:
        return vector
    return [round(component / magnitude, 8) for component in vector]


def _content_hash(source_id: str, title: str, text: str, terms: list[str]) -> str:
    payload = "\n".join((source_id, title, text, "|".join(terms)))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _semantic_chunks(text: str) -> list[str]:
    """Keep sections whole when possible; split only at sentence boundaries."""
    normalized = _normalize_text(text)
    if len(normalized) <= MAX_CHUNK_CHARS:
        return [normalized]

    chunks: list[str] = []
    current: list[str] = []
    current_length = 0
    for sentence in SENTENCE_BOUNDARY.split(normalized):
        sentence = sentence.strip()
        if not sentence:
            continue
        projected = current_length + len(sentence) + (1 if current else 0)
        if current and projected > MAX_CHUNK_CHARS:
            chunks.append(" ".join(current))
            current = []
            current_length = 0
        if len(sentence) > MAX_CHUNK_CHARS:
            raise ValueError("Knowledge section sentence exceeds the safe chunk limit")
        current.append(sentence)
        current_length += len(sentence) + (1 if len(current) > 1 else 0)
    if current:
        chunks.append(" ".join(current))
    return chunks


def _source_pack_hash(payload: bytes) -> str:
    """Hash the corpus by its content, not by how the checkout wrote its newlines.

    The index stores this hash and refuses to load when it stops matching, which is
    the right instinct - a stale index must never be served. But it was hashing the
    raw bytes of sources.json, and there is no .gitattributes in this repo, so on
    Windows git rewrites the file to CRLF on checkout. Every byte of content is
    identical and the hash is completely different, so a fresh clone got
    KNOWLEDGE_INDEX_INVALID and Cyber Saathi answered 503 to every question.

    Normalising the line endings first is a no-op for a file already stored with LF,
    so the committed hash does not change; it only stops a checkout from breaking it.
    """
    return hashlib.sha256(payload.replace(b"\r\n", b"\n")).hexdigest()


def load_source_pack(path: Path = SOURCE_PACK_PATH) -> KnowledgeSourcePack:
    return KnowledgeSourcePack.model_validate_json(path.read_text(encoding="utf-8"))


# Ingestion is a one-off command over the whole corpus, so a single transient 503
# should not throw away the work already done - and the query-time timeout is far
# too tight for a document-sized embedding.
INGEST_EMBED_TIMEOUT_SECONDS = 20.0
INGEST_EMBED_ATTEMPTS = 6
# A rate limit is not a transient error, it is an instruction to wait, and the old
# 2/4/6 second backoff was shorter than the window it was waiting out. Rebuilding a
# corpus of a hundred sections sends a hundred requests as fast as the network
# allows, so the per-minute quota is reached every time; the build then failed after
# twelve seconds of backoff and discarded every embedding it had already paid for.
INGEST_RATE_LIMIT_PAUSE_SECONDS = 30.0
INGEST_MAX_PAUSE_SECONDS = 90.0


def _retry_after_seconds(error: BaseException) -> float | None:
    """The pause the server itself asked for, if this was a rate limit."""
    cause = error.__cause__
    if not isinstance(cause, httpx.HTTPStatusError) or cause.response.status_code != 429:
        return None
    try:
        details = cause.response.json()["error"]["details"]
    except Exception:  # noqa: BLE001 - a 429 without a parseable body is still a 429
        return INGEST_RATE_LIMIT_PAUSE_SECONDS
    for detail in details:
        delay = detail.get("retryDelay") if isinstance(detail, dict) else None
        if isinstance(delay, str) and delay.endswith("s"):
            try:
                # A margin, because the quota window is measured on the server clock.
                return min(float(delay[:-1]) + 2.0, INGEST_MAX_PAUSE_SECONDS)
            except ValueError:
                break
    return INGEST_RATE_LIMIT_PAUSE_SECONDS


def _embed_document_with_retry(provider: Any, text: str) -> list[float]:
    last_error: Exception | None = None
    for attempt in range(INGEST_EMBED_ATTEMPTS):
        try:
            return provider.embed(
                text,
                task_type="RETRIEVAL_DOCUMENT",
                timeout_seconds=INGEST_EMBED_TIMEOUT_SECONDS,
            )
        except SemanticEmbeddingError as error:
            last_error = error
            if attempt >= INGEST_EMBED_ATTEMPTS - 1:
                break
            pause = _retry_after_seconds(error)
            time.sleep(pause if pause is not None else 2.0 * (attempt + 1))
    raise last_error if last_error else SemanticEmbeddingError("embedding failed")


def _reusable_semantic_embeddings(
    provider: GeminiSemanticEmbeddingProvider | None,
    index_path: Path,
) -> dict[str, list[float]]:
    """Dense vectors from the existing index that this build can keep.

    An embedding depends only on the text that was sent to the model, and
    ``content_hash`` already covers exactly that text - the section body, its title
    and its retrieval terms. Domains, source metadata and section ordering are not
    part of it, so a chunk whose hash is unchanged would receive a byte-identical
    vector if it were re-embedded.

    Re-sending it anyway is what made a two-tag correction cost a hundred embedding
    calls and exhaust a daily quota, taking the whole rebuild down with it. Matching
    on the hash makes a retag free and makes corpus growth cost only what was added.
    """
    if provider is None or not index_path.exists():
        return {}
    try:
        existing = json.loads(index_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    # A different model or width produces vectors that are not comparable with the
    # ones this build will generate, so nothing may be carried across.
    if (
        existing.get("semantic_embedding_model") != provider.model
        or existing.get("semantic_embedding_dimension") != provider.dimensions
    ):
        return {}
    reusable: dict[str, list[float]] = {}
    for raw_chunk in existing.get("chunks", []):
        vector = raw_chunk.get("semantic_embedding")
        content_hash = raw_chunk.get("content_hash")
        if content_hash and isinstance(vector, list) and len(vector) == provider.dimensions:
            reusable[content_hash] = vector
    return reusable


def build_index(
    source_pack: KnowledgeSourcePack | None = None,
    *,
    semantic_embeddings: bool = False,
    semantic_provider: GeminiSemanticEmbeddingProvider | None = None,
    reuse_from: Path | None = INDEX_PATH,
) -> dict[str, Any]:
    """Build the persisted index.

    Sparse vectors are always present. Dense multilingual vectors are opt-in so
    tests and ordinary ingestion remain offline unless the operator explicitly
    requests the configured hosted embedding provider.

    Dense vectors for unchanged chunks are carried over from ``reuse_from``; pass
    ``None`` to re-embed the whole corpus from scratch.
    """
    pack = source_pack or load_source_pack()
    provider = semantic_provider or (GeminiSemanticEmbeddingProvider() if semantic_embeddings else None)
    if provider is not None and not provider.configured:
        raise ValueError("Semantic ingestion was requested but Gemini embeddings are not configured")
    reusable = _reusable_semantic_embeddings(provider, reuse_from) if reuse_from else {}
    reused = 0
    embedded = 0
    chunks: list[KnowledgeChunk] = []
    seen_hashes: set[str] = set()
    for source in pack.sources:
        metadata = KnowledgeSourceMetadata.model_validate(source.model_dump(exclude={"sections"}))
        for section_number, section in enumerate(source.sections, start=1):
            semantic_parts = _semantic_chunks(section.text)
            for part_number, text in enumerate(semantic_parts, start=1):
                suffix = f"{section_number}:{part_number}"
                content_hash = _content_hash(
                    source.source_id, section.title, text, section.retrieval_terms
                )
                if content_hash in seen_hashes:
                    raise ValueError(f"Duplicate authoritative knowledge chunk: {source.source_id}")
                seen_hashes.add(content_hash)
                embedding_input = " ".join((text, section.title, *section.retrieval_terms))
                semantic_embedding = None
                if provider is not None:
                    semantic_embedding = reusable.get(content_hash)
                    if semantic_embedding is None:
                        semantic_embedding = _embed_document_with_retry(provider, embedding_input)
                        embedded += 1
                    else:
                        reused += 1
                chunks.append(
                    KnowledgeChunk(
                        chunk_id=f"{source.source_id}:{suffix}",
                        source=metadata,
                        domains=section.domains,
                        section_title=section.title,
                        text=text,
                        retrieval_terms=[_normalize_text(term) for term in section.retrieval_terms],
                        content_hash=content_hash,
                        embedding=embed_text(embedding_input),
                        semantic_embedding=semantic_embedding,
                    )
                )
    if not chunks:
        raise ValueError("Authoritative knowledge source pack produced no chunks")
    if len(chunks) > MAX_INDEX_CHUNKS:
        raise ValueError(f"Knowledge index exceeds the {MAX_INDEX_CHUNKS}-chunk runtime limit")
    source_hash = _source_pack_hash(
        SOURCE_PACK_PATH.read_bytes() if source_pack is None else pack.model_dump_json().encode("utf-8")
    )
    return {
        "schema_version": INDEX_SCHEMA_VERSION,
        "index_version": pack.version,
        "embedding_version": EMBEDDING_VERSION,
        "embedding_dimension": EMBEDDING_DIMENSION,
        "semantic_embedding_provider": provider.provider if provider is not None else None,
        "semantic_embedding_model": provider.model if provider is not None else None,
        "semantic_embedding_dimension": provider.dimensions if provider is not None else None,
        "source_pack_hash": source_hash,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "semantic_embeddings_reused": reused,
        "semantic_embeddings_generated": embedded,
        "chunks": [chunk.model_dump(mode="json") for chunk in chunks],
    }


def rebuild_index(
    output_path: Path = INDEX_PATH,
    *,
    semantic_embeddings: bool = False,
    semantic_provider: GeminiSemanticEmbeddingProvider | None = None,
    reuse_existing: bool = True,
) -> dict[str, Any]:
    """Explicitly build the persisted index; never call this from application startup."""
    index = build_index(
        semantic_embeddings=semantic_embeddings,
        semantic_provider=semantic_provider,
        reuse_from=output_path if reuse_existing else None,
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(index, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    index_bytes = output_path.stat().st_size
    if index_bytes > MAX_INDEX_BYTES:
        output_path.unlink(missing_ok=True)
        raise ValueError(f"Knowledge index exceeds the {MAX_INDEX_BYTES}-byte runtime limit")
    KnowledgeService.clear_cache()
    return {
        "status": "passed",
        "index_path": str(output_path),
        "source_count": len({chunk["source"]["source_id"] for chunk in index["chunks"]}),
        "chunk_count": len(index["chunks"]),
        "embedding_dimension": EMBEDDING_DIMENSION,
        "semantic_embedding_dimension": index["semantic_embedding_dimension"],
        "index_version": index["index_version"],
        "index_bytes": index_bytes,
        "semantic_embeddings_reused": index["semantic_embeddings_reused"],
        "semantic_embeddings_generated": index["semantic_embeddings_generated"],
    }


def is_refused_query(query: str) -> bool:
    """Requests to fabricate authority are refused outright, on every path.

    This used to live inside the lexical grounding check, which made it a rule the
    semantic path could walk straight past: a dense vector does not care that the
    sentence begins "invent an official government guarantee". Retrieval must have
    exactly one answer to this, so it is asked before any scoring happens.
    """
    lowered = query.casefold()
    return any(term in lowered for term in ("invent", "fabricate", "make up")) and any(
        term in lowered for term in ("official", "government", "guarantee")
    )


class KnowledgeService:
    _cached_mtime_ns: int | None = None
    _cached_index: dict[str, Any] | None = None
    # Corpus-wide token statistics for lexical ranking. Derived from the index, so
    # they are rebuilt whenever a different index version is loaded.
    _document_frequency_cache: dict[str, int] | None = None
    _document_frequency_version: str | None = None
    _document_frequency_total: int = 0

    @classmethod
    def clear_cache(cls) -> None:
        cls._cached_mtime_ns = None
        cls._cached_index = None
        cls._document_frequency_cache = None
        cls._document_frequency_version = None
        cls._document_frequency_total = 0

    @classmethod
    def _load_index(cls) -> dict[str, Any]:
        if not INDEX_PATH.exists():
            raise APIError(
                status_code=503,
                code="KNOWLEDGE_INDEX_UNAVAILABLE",
                message="Knowledge guidance is temporarily unavailable. Please use safe general guidance or try again later.",
            )
        if INDEX_PATH.stat().st_size > MAX_INDEX_BYTES:
            raise APIError(
                status_code=503,
                code="KNOWLEDGE_INDEX_TOO_LARGE",
                message="Knowledge guidance needs a smaller verified index before it can be used.",
            )
        mtime_ns = INDEX_PATH.stat().st_mtime_ns
        if cls._cached_index is not None and cls._cached_mtime_ns == mtime_ns:
            return cls._cached_index
        try:
            index = json.loads(INDEX_PATH.read_text(encoding="utf-8"))
            current_source_hash = _source_pack_hash(SOURCE_PACK_PATH.read_bytes())
            chunks = [KnowledgeChunk.model_validate(raw) for raw in index.get("chunks", [])]
        except (OSError, ValueError, TypeError, json.JSONDecodeError) as error:
            raise APIError(
                status_code=503,
                code="KNOWLEDGE_INDEX_INVALID",
                message="Knowledge guidance needs a verified re-ingestion before it can be used.",
            ) from error
        content_hashes_valid = all(
            chunk.content_hash
            == _content_hash(
                chunk.source.source_id,
                chunk.section_title,
                chunk.text,
                chunk.retrieval_terms,
            )
            for chunk in chunks
        )
        semantic_vectors = [chunk.semantic_embedding for chunk in chunks]
        semantic_dimension = index.get("semantic_embedding_dimension")
        semantic_index_valid = (
            all(vector is None for vector in semantic_vectors)
            and semantic_dimension is None
        ) or (
            isinstance(semantic_dimension, int)
            and 128 <= semantic_dimension <= 3072
            and all(vector is not None and len(vector) == semantic_dimension for vector in semantic_vectors)
            and bool(index.get("semantic_embedding_provider"))
            and bool(index.get("semantic_embedding_model"))
        )
        if (
            index.get("schema_version") != INDEX_SCHEMA_VERSION
            or index.get("embedding_version") != EMBEDDING_VERSION
            or index.get("embedding_dimension") != EMBEDDING_DIMENSION
            or not chunks
            or len(chunks) > MAX_INDEX_CHUNKS
            or index.get("source_pack_hash") != current_source_hash
            or not content_hashes_valid
            or not semantic_index_valid
        ):
            raise APIError(
                status_code=503,
                code="KNOWLEDGE_INDEX_INVALID",
                message="Knowledge guidance needs a verified re-ingestion before it can be used.",
            )
        cls._cached_mtime_ns = mtime_ns
        cls._cached_index = index
        return index

    @staticmethod
    def _cosine(left: list[float], right: list[float]) -> float:
        return max(0.0, min(1.0, sum(a * b for a, b in zip(left, right))))

    @staticmethod
    def _has_lexical_grounding(query: str, chunk: KnowledgeChunk) -> bool:
        query_tokens = _meaningful_tokens(query)
        if not query_tokens:
            return False
        source_tokens = _meaningful_tokens(
            " ".join((chunk.section_title, chunk.text, *chunk.retrieval_terms))
        )
        overlap = query_tokens.intersection(source_tokens)
        return len(overlap) >= 2 or bool(overlap.intersection(HIGH_SIGNAL_TERMS))

    @classmethod
    def _document_frequency(cls, index: dict[str, Any]) -> tuple[dict[str, int], int]:
        """How many chunks each token appears in, computed once per loaded index."""
        version = str(index.get("index_version"))
        if cls._document_frequency_cache is None or cls._document_frequency_version != version:
            frequency: dict[str, int] = {}
            for raw_chunk in index["chunks"]:
                tokens = _meaningful_tokens(
                    " ".join(
                        (
                            raw_chunk["section_title"],
                            raw_chunk["text"],
                            *raw_chunk.get("retrieval_terms", []),
                        )
                    )
                )
                for token in tokens:
                    frequency[token] = frequency.get(token, 0) + 1
            cls._document_frequency_cache = frequency
            cls._document_frequency_version = version
            cls._document_frequency_total = len(index["chunks"])
        return cls._document_frequency_cache, cls._document_frequency_total

    @staticmethod
    def _token_weight(frequency: dict[str, int], total: int, token: str) -> float:
        """Rarer words say more about what the citizen asked."""
        return math.log((total + 1) / (frequency.get(token, 0) + 1)) + 1.0

    @classmethod
    def _lexical_score(cls, query: str, chunk: KnowledgeChunk, index: dict[str, Any]) -> float:
        # Counting matched tokens and dividing by the query length made every long
        # chunk a good match for every question in its domain: "money", "bank" and
        # "account" appear in most of the financial corpus, so a section on fake job
        # offers scored 0.83 against "money was debited without my permission". The
        # score was fine while the corpus was small and degraded as it grew, which is
        # the wrong direction for adding sources to push.
        #
        # Weighting each token by how rare it is across the corpus fixes the cause:
        # the common words still count, but "debited" and "permission" now decide the
        # ranking instead of being drowned out by them.
        query_tokens = _meaningful_tokens(query)
        if not query_tokens:
            return 0.0
        source_tokens = _meaningful_tokens(
            " ".join((chunk.section_title, chunk.text, *chunk.retrieval_terms))
        )
        overlap = query_tokens.intersection(source_tokens)
        if not overlap:
            return 0.0
        frequency, total = cls._document_frequency(index)
        matched = sum(cls._token_weight(frequency, total, token) for token in overlap)
        asked = sum(cls._token_weight(frequency, total, token) for token in query_tokens)
        coverage = matched / asked if asked else 0.0
        term_matches = sum(
            1 for term in chunk.retrieval_terms if term.casefold() in query.casefold()
        )
        return min(1.0, coverage + min(0.25, term_matches * 0.08))

    @classmethod
    def _semantic_query_embedding(cls, index: dict[str, Any], query: str) -> list[float] | None:
        if index.get("semantic_embedding_provider") != "gemini":
            return None
        provider = GeminiSemanticEmbeddingProvider()
        if not provider.configured or provider.model != index.get("semantic_embedding_model"):
            return None
        try:
            embedding = provider.query_embedding(query)
        except SemanticEmbeddingError:
            return None
        if len(embedding) != index.get("semantic_embedding_dimension"):
            return None
        return embedding

    @classmethod
    def _empty_response(
        cls, request: KnowledgeSearchRequest, started: float, index: dict[str, Any], strategy: str
    ) -> KnowledgeSearchResponse:
        return KnowledgeSearchResponse(
            query=request.query,
            domain_filter=request.domain,
            retrieval_latency_ms=round((time.perf_counter() - started) * 1000, 3),
            index_version=str(index["index_version"]),
            no_result=True,
            matches=[],
            bounded_context="",
            retrieval_strategy=strategy,
        )

    @classmethod
    def search(cls, request: KnowledgeSearchRequest) -> KnowledgeSearchResponse:
        started = time.perf_counter()
        index = cls._load_index()
        query_embedding = embed_text(request.query)
        semantic_query_embedding = cls._semantic_query_embedding(index, request.query)
        strategy = "hybrid_dense_sparse_lexical" if semantic_query_embedding is not None else "sparse_lexical"
        if is_refused_query(request.query):
            return cls._empty_response(request, started, index, strategy)
        # Does the requested domain actually agree with what the query is about?
        # The semantic bypass exists so a paraphrase can be recovered when no words
        # are shared, but on its own it also lets a question about one crime match
        # generic guidance filed under another - every chunk here is broadly
        # "cybercrime advice", so dense similarity alone stays high. Comparing the
        # best in-domain score against the best score anywhere else settles it
        # without a hand-tuned cutoff: for a question that belongs to its domain the
        # in-domain chunk wins, and when another domain wins the filter is being
        # asked for something the query is not about.
        domain_agrees = True
        if semantic_query_embedding is not None and request.domain is not None:
            best_in_domain = 0.0
            best_elsewhere = 0.0
            for raw_chunk in index["chunks"]:
                vector = raw_chunk.get("semantic_embedding")
                if not vector:
                    continue
                score = cls._cosine(semantic_query_embedding, vector)
                if request.domain in raw_chunk["domains"]:
                    best_in_domain = max(best_in_domain, score)
                else:
                    best_elsewhere = max(best_elsewhere, score)
            domain_agrees = best_in_domain >= best_elsewhere
        candidates: list[KnowledgeMatch] = []
        for raw_chunk in index["chunks"]:
            chunk = KnowledgeChunk.model_validate(raw_chunk)
            if request.domain is not None and request.domain not in chunk.domains:
                continue
            lexical_grounded = cls._has_lexical_grounding(request.query, chunk)
            lexical_score = cls._lexical_score(request.query, chunk, index)
            sparse_score = cls._cosine(query_embedding, chunk.embedding)
            semantic_score = (
                cls._cosine(semantic_query_embedding, chunk.semantic_embedding)
                if semantic_query_embedding is not None and chunk.semantic_embedding is not None
                else None
            )
            # Domain-filtered semantic retrieval can recover a natural paraphrase.
            # A non-domain query still needs lexical grounding to avoid broad false positives.
            semantic_grounded = bool(
                request.domain is not None
                and semantic_score is not None
                and semantic_score >= 0.55
                and domain_agrees
            )
            if not lexical_grounded and not semantic_grounded:
                continue
            if semantic_score is None:
                # lexical_score used to be computed and thrown away here, leaving
                # hashed character n-grams as the only ranking signal. Whole-word
                # agreement is the stronger evidence of the two, so it is folded in
                # using the same configured weights, renormalised over the two
                # signals that actually exist without a dense vector.
                settings = GeminiSemanticEmbeddingProvider().settings
                total_weight = settings.rag_sparse_weight + settings.rag_lexical_weight
                relevance = (
                    (settings.rag_sparse_weight * sparse_score
                     + settings.rag_lexical_weight * lexical_score) / total_weight
                    if total_weight > 0
                    else sparse_score
                )
            else:
                settings = GeminiSemanticEmbeddingProvider().settings
                relevance = (
                    settings.rag_dense_weight * semantic_score
                    + settings.rag_sparse_weight * sparse_score
                    + settings.rag_lexical_weight * lexical_score
                )
            if request.language is not None and request.language == chunk.source.language:
                relevance = min(1.0, relevance + 0.02)
            if relevance < request.minimum_relevance:
                continue
            candidates.append(
                KnowledgeMatch(
                    chunk_id=chunk.chunk_id,
                    source_id=chunk.source.source_id,
                    source_title=chunk.source.source_title,
                    source_url=chunk.source.source_url,
                    source_type=chunk.source.source_type,
                    jurisdiction=chunk.source.jurisdiction,
                    domains=chunk.domains,
                    language=chunk.source.language,
                    version=chunk.source.version,
                    section_title=chunk.section_title,
                    text=chunk.text,
                    relevance_score=round(relevance, 4),
                    retrieval_strategy=strategy,
                    lexical_score=round(lexical_score, 4),
                    sparse_score=round(sparse_score, 4),
                    semantic_score=round(semantic_score, 4) if semantic_score is not None else None,
                )
            )
        matches = sorted(candidates, key=lambda match: match.relevance_score, reverse=True)[: request.top_k]
        context_parts: list[str] = []
        context_length = 0
        for match in matches:
            part = f"[{match.source_title} — {match.section_title}] {match.text}"
            if context_parts and context_length + len(part) + 2 > MAX_CONTEXT_CHARS:
                break
            context_parts.append(part)
            context_length += len(part) + 2
        return KnowledgeSearchResponse(
            query=request.query,
            domain_filter=request.domain,
            retrieval_latency_ms=round((time.perf_counter() - started) * 1000, 3),
            index_version=str(index["index_version"]),
            no_result=not matches,
            matches=matches,
            bounded_context="\n\n".join(context_parts),
            retrieval_strategy=strategy,
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the Cyber Saathi authoritative knowledge index")
    parser.add_argument("--output", type=Path, default=INDEX_PATH)
    parser.add_argument(
        "--semantic",
        action="store_true",
        help="Generate hosted multilingual document vectors using the configured Gemini key.",
    )
    parser.add_argument(
        "--reembed-all",
        action="store_true",
        help=(
            "Re-embed every chunk instead of reusing the unchanged vectors already "
            "in the index. Only needed when the embedding model or its configured "
            "width changes; an ordinary corpus edit does not need it."
        ),
    )
    args = parser.parse_args()
    print(
        json.dumps(
            rebuild_index(
                args.output,
                semantic_embeddings=args.semantic,
                reuse_existing=not args.reembed_all,
            ),
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
