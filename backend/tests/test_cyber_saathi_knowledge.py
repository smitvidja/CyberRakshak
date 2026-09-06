import json
import subprocess
import sys

from fastapi.testclient import TestClient

from app.core.errors import APIError
from app.main import app
from app.schemas.cyber_saathi import KnowledgeDomain, KnowledgeSearchRequest, LanguageCode
from app.services import cyber_saathi_knowledge as knowledge_module
from app.services.cyber_saathi_knowledge import (
    INDEX_PATH,
    MAX_INDEX_BYTES,
    SOURCE_PACK_PATH,
    KnowledgeService,
    build_index,
    load_source_pack,
    rebuild_index,
)
from app.services.cyber_saathi_knowledge_evaluation import evaluate


def setup_module() -> None:
    rebuild_index()


def test_explicit_ingestion_creates_a_persistent_traceable_index() -> None:
    result = rebuild_index()

    assert result["status"] == "passed"
    assert result["source_count"] == 13
    assert result["chunk_count"] == 30
    assert result["embedding_dimension"] == 384
    assert result["index_bytes"] < MAX_INDEX_BYTES
    assert INDEX_PATH.exists()

    KnowledgeService.clear_cache()
    response = KnowledgeService.search(
        KnowledgeSearchRequest(
            query="My UPI payment was unauthorized and money was debited",
            domain=KnowledgeDomain.UPI_PAYMENT_FRAUD,
        )
    )
    assert response.no_result is False
    assert response.matches[0].source_id == "ncrp_financial_fraud"
    assert response.matches[0].source_url.startswith("https://cybercrime.gov.in/")
    assert "1930" in response.bounded_context


def test_domain_filter_and_low_confidence_no_result_are_enforced() -> None:
    harassment = KnowledgeService.search(
        KnowledgeSearchRequest(
            query="Instagram abusive messages and stalking",
            domain=KnowledgeDomain.CYBERSTALKING,
            language=LanguageCode.HINGLISH,
        )
    )
    assert harassment.no_result is False
    assert all(KnowledgeDomain.CYBERSTALKING in match.domains for match in harassment.matches)

    unrelated = KnowledgeService.search(
        KnowledgeSearchRequest(query="Please give me a dinner recipe", minimum_relevance=0.25)
    )
    assert unrelated.no_result is True
    assert unrelated.matches == []
    assert unrelated.bounded_context == ""


def test_every_priority_domain_has_chunk_level_coverage() -> None:
    chunks = build_index(load_source_pack())["chunks"]
    covered = {
        KnowledgeDomain(domain)
        for chunk in chunks
        for domain in chunk["domains"]
    }

    assert covered == set(KnowledgeDomain)


def test_persisted_index_is_read_by_a_fresh_python_process() -> None:
    command = (
        "from app.schemas.cyber_saathi import KnowledgeSearchRequest; "
        "from app.services.cyber_saathi_knowledge import KnowledgeService; "
        "r=KnowledgeService.search(KnowledgeSearchRequest(query='phishing fake link safety')); "
        "print(r.index_version, r.no_result)"
    )
    completed = subprocess.run(
        [sys.executable, "-c", command],
        cwd=INDEX_PATH.parents[4],
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    assert completed.stdout.strip().endswith("2026.09.3.2 False")


def test_stale_or_tampered_index_fails_closed(tmp_path, monkeypatch) -> None:
    source_copy = tmp_path / "sources.json"
    source_copy.write_bytes(SOURCE_PACK_PATH.read_bytes())
    index_copy = tmp_path / "knowledge_index.json"
    monkeypatch.setattr(knowledge_module, "SOURCE_PACK_PATH", source_copy)
    monkeypatch.setattr(knowledge_module, "INDEX_PATH", index_copy)
    rebuild_index(index_copy)

    source_copy.write_text(source_copy.read_text(encoding="utf-8") + "\n", encoding="utf-8")
    KnowledgeService.clear_cache()
    try:
        KnowledgeService.search(KnowledgeSearchRequest(query="phishing fake link safety"))
    except APIError as error:
        assert error.code == "KNOWLEDGE_INDEX_INVALID"
    else:
        raise AssertionError("A stale source-pack hash must fail closed")

    source_copy.write_bytes(SOURCE_PACK_PATH.read_bytes())
    rebuild_index(index_copy)
    payload = json.loads(index_copy.read_text(encoding="utf-8"))
    payload["chunks"][0]["text"] += " tampered"
    index_copy.write_text(json.dumps(payload), encoding="utf-8")
    KnowledgeService.clear_cache()
    try:
        KnowledgeService.search(KnowledgeSearchRequest(query="UPI unauthorized payment"))
    except APIError as error:
        assert error.code == "KNOWLEDGE_INDEX_INVALID"
    else:
        raise AssertionError("A tampered chunk hash must fail closed")


def test_knowledge_search_api_has_bounded_results_and_source_metadata() -> None:
    response = TestClient(app).post(
        "/api/v1/cyber-saathi/knowledge/search",
        json={
            "query": "बच्चे की ऑनलाइन सुरक्षा और शिकायत",
            "domain": "women_child_online_safety",
            "language": "HI",
            "top_k": 3,
        },
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["no_result"] is False
    assert len(data["matches"]) <= 3
    assert data["matches"][0]["source_id"] == "ncrp_hindi_faq"
    assert data["matches"][0]["section_title"]
    assert data["retrieval_latency_ms"] >= 0


def test_knowledge_gold_set_meets_relevance_source_and_no_result_gates() -> None:
    result = evaluate()

    assert result["status"] == "passed"
    assert result["metrics"]["case_count"] == 30
    assert result["metrics"]["retrieval_relevance"] == 1
    assert result["metrics"]["source_correctness"] == 1
    assert result["metrics"]["no_result_correctness"] == 1
    assert result["metrics"]["domain_filter_correctness"] == 1
    assert result["metrics"]["chunk_correctness"] == 1
    assert result["metrics"]["false_positive_count"] == 0
    assert result["metrics"]["false_negative_count"] == 0
