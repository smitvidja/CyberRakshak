"""Bounded hosted multilingual semantic embeddings for Cyber Saathi retrieval.

This module is intentionally an ingestion/runtime adapter, not a local model
runtime. Source chunks are embedded only by the explicit knowledge build command;
query vectors are short-lived, redacted, and cached in process memory.
"""

from __future__ import annotations

import math
import re
from functools import lru_cache

import httpx

from app.core.config import Settings, get_settings


class SemanticEmbeddingError(RuntimeError):
    """Raised when an explicitly requested semantic embedding cannot be produced."""


_EMAIL = re.compile(r"(?<!\w)[\w.+-]+@[a-z0-9.-]+\.[a-z]{2,}(?!\w)", re.I)
_PHONE = re.compile(r"(?<!\d)(?:\+91[ -]?)?[6-9]\d{4}[ -]?\d{5}(?!\d)")
_LONG_IDENTIFIER = re.compile(r"(?<!\d)\d{12,16}(?!\d)")
_UPI = re.compile(r"(?<![\w.])[a-z0-9._-]{2,}@(upi|ybl|paytm|okaxis|okhdfcbank|oksbi|ibl|axl)(?![\w.])", re.I)


def redact_for_embedding(value: str) -> str:
    """Avoid sending common direct identifiers to a hosted embedding provider."""
    result = _EMAIL.sub("[EMAIL]", value)
    result = _PHONE.sub("[PHONE]", result)
    result = _LONG_IDENTIFIER.sub("[IDENTIFIER]", result)
    return _UPI.sub("[UPI]", result)


def _normalise(vector: list[float]) -> list[float]:
    magnitude = math.sqrt(sum(component * component for component in vector))
    if magnitude == 0:
        raise SemanticEmbeddingError("Semantic embedding returned a zero vector")
    return [round(component / magnitude, 8) for component in vector]


class GeminiSemanticEmbeddingProvider:
    """Minimal Gemini embedContent adapter using the existing server-side key."""

    provider = "gemini"

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    @property
    def configured(self) -> bool:
        key = self.settings.gemini_api_key
        return bool(self.settings.rag_semantic_embeddings_enabled and key and key.get_secret_value().strip())

    @property
    def model(self) -> str:
        return self.settings.rag_semantic_embedding_model

    @property
    def dimensions(self) -> int:
        return self.settings.rag_semantic_embedding_dimensions

    def embed(self, text: str, *, task_type: str) -> list[float]:
        if not self.configured:
            raise SemanticEmbeddingError("Gemini semantic embeddings are not configured")
        safe_text = redact_for_embedding(" ".join(text.split()))[:5000]
        if not safe_text:
            raise SemanticEmbeddingError("Cannot embed empty text")
        key = self.settings.gemini_api_key.get_secret_value()
        endpoint = f"{self.settings.gemini_base_url}/models/{self.model}:embedContent"
        payload = {
            "model": f"models/{self.model}",
            "content": {"parts": [{"text": safe_text}]},
            "taskType": task_type,
            "outputDimensionality": self.dimensions,
        }
        try:
            response = httpx.post(
                endpoint,
                params={"key": key},
                json=payload,
                timeout=self.settings.rag_semantic_embedding_timeout_seconds,
            )
            response.raise_for_status()
            values = response.json()["embedding"]["values"]
        except (httpx.HTTPError, KeyError, TypeError, ValueError) as error:
            raise SemanticEmbeddingError("Gemini semantic embedding request failed") from error
        if not isinstance(values, list) or len(values) != self.dimensions:
            raise SemanticEmbeddingError("Gemini returned an unexpected embedding dimension")
        try:
            return _normalise([float(value) for value in values])
        except (TypeError, ValueError) as error:
            raise SemanticEmbeddingError("Gemini returned an invalid embedding vector") from error

    @lru_cache(maxsize=256)
    def embed_query(self, redacted_query: str) -> tuple[float, ...]:
        return tuple(self.embed(redacted_query, task_type="RETRIEVAL_QUERY"))

    def query_embedding(self, text: str) -> list[float]:
        return list(self.embed_query(redact_for_embedding(text)))
