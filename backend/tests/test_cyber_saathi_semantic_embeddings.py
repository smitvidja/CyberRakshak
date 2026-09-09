import httpx

from app.core.config import Settings
from app.services.cyber_saathi_semantic_embeddings import (
    GeminiSemanticEmbeddingProvider,
    redact_for_embedding,
)


def _settings() -> Settings:
    return Settings(
        database_url="postgresql+psycopg://test:test@localhost/test",
        secret_key="semantic-embedding-test-secret-key-32chars",
        gemini_api_key="test-key",
        rag_semantic_embedding_dimensions=128,
    )


def test_hosted_embedding_request_is_bounded_and_redacts_direct_identifiers(monkeypatch) -> None:
    captured: dict[str, object] = {}

    class Response:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, object]:
            return {"embedding": {"values": [1.0] + [0.0] * 127}}

    def fake_post(url: str, *, params: dict[str, str], json: dict[str, object], timeout: float) -> Response:
        captured.update({"url": url, "params": params, "json": json, "timeout": timeout})
        return Response()

    monkeypatch.setattr(httpx, "post", fake_post)
    provider = GeminiSemanticEmbeddingProvider(_settings())
    vector = provider.embed(
        "Call +91 98765 43210 about scam@evil.example and name@upi",
        task_type="RETRIEVAL_QUERY",
    )

    text = captured["json"]["content"]["parts"][0]["text"]  # type: ignore[index]
    assert "98765" not in text
    assert "scam@evil.example" not in text
    assert "name@upi" not in text
    assert "[PHONE]" in text and "[EMAIL]" in text and "[UPI]" in text
    assert len(vector) == 128
    assert vector[0] == 1


def test_embedding_redaction_preserves_general_cyber_context() -> None:
    result = redact_for_embedding("UPI fraud after +91 98765 43210 shared scam@evil.example")

    assert "UPI fraud" in result
    assert "[PHONE]" in result
    assert "[EMAIL]" in result
