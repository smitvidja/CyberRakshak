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
from app.services.cyber_saathi_understanding import DATA_DIR


KNOWLEDGE_DIR = DATA_DIR / "authoritative_knowledge"
SOURCE_PACK_PATH = KNOWLEDGE_DIR / "sources.json"
INDEX_PATH = KNOWLEDGE_DIR / "knowledge_index.json"
EVALUATION_CASES_PATH = DATA_DIR / "knowledge_evaluation_cases.json"
EMBEDDING_DIMENSION = 384
EMBEDDING_VERSION = "hashed-unicode-ngrams-v1"
INDEX_SCHEMA_VERSION = "1.1.0"
MAX_CHUNK_CHARS = 900
MAX_CONTEXT_CHARS = 2200
MAX_INDEX_BYTES = 2 * 1024 * 1024
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


def _meaningful_tokens(value: str) -> set[str]:
    return {
        token
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


def load_source_pack(path: Path = SOURCE_PACK_PATH) -> KnowledgeSourcePack:
    return KnowledgeSourcePack.model_validate_json(path.read_text(encoding="utf-8"))


def build_index(source_pack: KnowledgeSourcePack | None = None) -> dict[str, Any]:
    pack = source_pack or load_source_pack()
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
                    )
                )
    if not chunks:
        raise ValueError("Authoritative knowledge source pack produced no chunks")
    if len(chunks) > MAX_INDEX_CHUNKS:
        raise ValueError(f"Knowledge index exceeds the {MAX_INDEX_CHUNKS}-chunk runtime limit")
    source_hash = hashlib.sha256(
        SOURCE_PACK_PATH.read_bytes() if source_pack is None else pack.model_dump_json().encode("utf-8")
    ).hexdigest()
    return {
        "schema_version": INDEX_SCHEMA_VERSION,
        "index_version": pack.version,
        "embedding_version": EMBEDDING_VERSION,
        "embedding_dimension": EMBEDDING_DIMENSION,
        "source_pack_hash": source_hash,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "chunks": [chunk.model_dump(mode="json") for chunk in chunks],
    }


def rebuild_index(output_path: Path = INDEX_PATH) -> dict[str, Any]:
    """Explicitly build the persisted index; never call this from application startup."""
    index = build_index()
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
        "index_version": index["index_version"],
        "index_bytes": index_bytes,
    }


class KnowledgeService:
    _cached_mtime_ns: int | None = None
    _cached_index: dict[str, Any] | None = None

    @classmethod
    def clear_cache(cls) -> None:
        cls._cached_mtime_ns = None
        cls._cached_index = None

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
            current_source_hash = hashlib.sha256(SOURCE_PACK_PATH.read_bytes()).hexdigest()
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
        if (
            index.get("schema_version") != INDEX_SCHEMA_VERSION
            or index.get("embedding_version") != EMBEDDING_VERSION
            or index.get("embedding_dimension") != EMBEDDING_DIMENSION
            or not chunks
            or len(chunks) > MAX_INDEX_CHUNKS
            or index.get("source_pack_hash") != current_source_hash
            or not content_hashes_valid
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
        lowered = query.casefold()
        if any(term in lowered for term in ("invent", "fabricate", "make up")) and any(
            term in lowered for term in ("official", "government", "guarantee")
        ):
            return False
        query_tokens = _meaningful_tokens(query)
        if not query_tokens:
            return False
        source_tokens = _meaningful_tokens(
            " ".join((chunk.section_title, chunk.text, *chunk.retrieval_terms))
        )
        overlap = query_tokens.intersection(source_tokens)
        return len(overlap) >= 2 or bool(overlap.intersection(HIGH_SIGNAL_TERMS))

    @classmethod
    def search(cls, request: KnowledgeSearchRequest) -> KnowledgeSearchResponse:
        started = time.perf_counter()
        index = cls._load_index()
        query_embedding = embed_text(request.query)
        candidates: list[KnowledgeMatch] = []
        for raw_chunk in index["chunks"]:
            chunk = KnowledgeChunk.model_validate(raw_chunk)
            if request.domain is not None and request.domain not in chunk.domains:
                continue
            if not cls._has_lexical_grounding(request.query, chunk):
                continue
            relevance = cls._cosine(query_embedding, chunk.embedding)
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
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the Cyber Saathi authoritative knowledge index")
    parser.add_argument("--output", type=Path, default=INDEX_PATH)
    args = parser.parse_args()
    print(json.dumps(rebuild_index(args.output), ensure_ascii=False))


if __name__ == "__main__":
    main()
