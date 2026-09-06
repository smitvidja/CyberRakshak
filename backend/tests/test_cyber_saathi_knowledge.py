from fastapi.testclient import TestClient

from app.main import app
from app.schemas.cyber_saathi import CrimeDomain, KnowledgeSearchRequest, LanguageCode
from app.services.cyber_saathi_knowledge import INDEX_PATH, KnowledgeService, rebuild_index
from app.services.cyber_saathi_knowledge_evaluation import evaluate


def setup_module() -> None:
    rebuild_index()


def test_explicit_ingestion_creates_a_persistent_traceable_index() -> None:
    result = rebuild_index()

    assert result["status"] == "passed"
    assert result["source_count"] == 13
    assert result["chunk_count"] == 30
    assert result["embedding_dimension"] == 384
    assert INDEX_PATH.exists()

    KnowledgeService.clear_cache()
    response = KnowledgeService.search(
        KnowledgeSearchRequest(
            query="My UPI payment was unauthorized and money was debited",
            domain=CrimeDomain.FINANCIAL_FRAUD,
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
            domain=CrimeDomain.ONLINE_HARASSMENT,
            language=LanguageCode.HINGLISH,
        )
    )
    assert harassment.no_result is False
    assert all(CrimeDomain.ONLINE_HARASSMENT in match.domains for match in harassment.matches)

    unrelated = KnowledgeService.search(
        KnowledgeSearchRequest(query="Please give me a dinner recipe", minimum_relevance=0.25)
    )
    assert unrelated.no_result is True
    assert unrelated.matches == []
    assert unrelated.bounded_context == ""


def test_knowledge_search_api_has_bounded_results_and_source_metadata() -> None:
    response = TestClient(app).post(
        "/api/v1/cyber-saathi/knowledge/search",
        json={
            "query": "बच्चे की ऑनलाइन सुरक्षा और शिकायत",
            "domain": "child_safety",
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
    assert result["metrics"]["case_count"] == 21
    assert result["metrics"]["retrieval_relevance"] == 1
    assert result["metrics"]["source_correctness"] == 1
    assert result["metrics"]["no_result_correctness"] == 1
