import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.schemas.cyber_saathi import (
    ConfidenceBand,
    ConversationCreate,
    ConversationMessageRequest,
    CrimeDomain,
    EntityType,
    Intent,
    LanguageCode,
    Urgency,
)
from app.services.cyber_saathi_dataset import (
    generate_controlled_variants,
    load_inspection,
    load_sources,
    prepare_examples,
    validate_registry,
)
from app.services.cyber_saathi_evaluation import evaluate
from app.services.cyber_saathi_service import CyberSaathiService
from app.services.cyber_saathi_understanding import UnderstandingEngine


def test_understanding_api_returns_structured_result() -> None:
    response = TestClient(app).post(
        "/api/v1/cyber-saathi/understand",
        json={"message": "Mere bank se aaj Rs 10000 cut gaye"},
    )

    assert response.status_code == 200
    result = response.json()["data"]
    assert result["language"] == "HINGLISH"
    assert result["response_language"] == "HINGLISH"
    assert result["intent"] == "report_incident"
    assert result["crime_domain"] == "financial_fraud"
    assert result["urgency"] == "high"
    assert result["confidence_band"] == "high"
    assert result["needs_clarification"] is False


def test_equivalent_language_variants_preserve_meaning() -> None:
    utterances = [
        "I received a suspicious bank link. What should I do?",
        "मुझे संदिग्ध बैंक लिंक मिला है, क्या करूं?",
        "Mujhe suspicious bank link mila hai, kya karu?",
    ]
    results = [UnderstandingEngine.analyze(text) for text in utterances]

    assert [result.language for result in results] == [
        LanguageCode.EN,
        LanguageCode.HI,
        LanguageCode.HINGLISH,
    ]
    assert {result.intent for result in results} == {Intent.SEEK_GUIDANCE}
    assert {result.crime_domain for result in results} == {CrimeDomain.PHISHING_SCAM}


def test_critical_entities_require_confirmation_and_preserve_values() -> None:
    result = UnderstandingEngine.analyze(
        "Rs 12,500 went to fraudster@ybl, UTR ID 123456789012. "
        "Call +91 98765 43210 or victim@example.com on 18/05/2024 at 14:30."
    )
    entities = {entity.type: entity for entity in result.entities}

    for entity_type in {
        EntityType.AMOUNT,
        EntityType.UPI_ID,
        EntityType.TRANSACTION_ID,
        EntityType.PHONE_NUMBER,
        EntityType.EMAIL,
        EntityType.DATE,
        EntityType.TIME,
    }:
        assert entities[entity_type].requires_confirmation is True
    assert entities[EntityType.AMOUNT].normalized_value == "12500"
    assert entities[EntityType.UPI_ID].normalized_value == "fraudster@ybl"


def test_confidence_controls_clarification_behavior() -> None:
    high = UnderstandingEngine.analyze("My bank account was debited today by Rs 5000")
    medium = UnderstandingEngine.analyze("Please help me")
    low = UnderstandingEngine.analyze("Something odd happened online")

    assert high.confidence_band == ConfidenceBand.HIGH
    assert high.needs_clarification is False
    assert high.clarification_prompt is None
    assert medium.confidence_band == ConfidenceBand.MEDIUM
    assert medium.needs_clarification is True
    assert medium.clarification_prompt is not None
    assert low.confidence_band == ConfidenceBand.LOW
    assert low.needs_clarification is True
    assert "not fully certain" in (low.clarification_prompt or "")


def test_sentiment_changes_strategy_label_not_domain_truth() -> None:
    angry = UnderstandingEngine.analyze("I am furious about this suspicious link")
    neutral = UnderstandingEngine.analyze("I received this suspicious link")

    assert angry.sentiment.value == "angry"
    assert neutral.sentiment.value == "concerned"
    assert angry.crime_domain == neutral.crime_domain == CrimeDomain.PHISHING_SCAM


@pytest.mark.parametrize(
    ("message", "expected_prefix"),
    [
        ("I am furious about this suspicious link", "I understand this is frustrating."),
        ("I am confused about this suspicious link", "I will keep this simple."),
        ("I am scared because someone is threatening me online", "You are not alone."),
    ],
)
def test_sentiment_changes_conversation_response_strategy(
    message: str, expected_prefix: str
) -> None:
    state = CyberSaathiService.start(ConversationCreate(language=LanguageCode.EN)).state
    response = CyberSaathiService.reply(
        state.id,
        ConversationMessageRequest(message=message, state=state),
    )

    assert response.state.turns[-1].content.startswith(expected_prefix)


def test_medium_and_low_confidence_use_distinct_clarification_strategies() -> None:
    medium_state = CyberSaathiService.start(ConversationCreate(language=LanguageCode.EN)).state
    medium = CyberSaathiService.reply(
        medium_state.id,
        ConversationMessageRequest(message="Please help me", state=medium_state),
    )
    low_state = CyberSaathiService.start(ConversationCreate(language=LanguageCode.EN)).state
    low = CyberSaathiService.reply(
        low_state.id,
        ConversationMessageRequest(message="Something odd happened online", state=low_state),
    )

    medium_copy = medium.state.turns[-1].content
    low_copy = low.state.turns[-1].content
    assert "Was this about money" in medium_copy
    assert "not fully certain" in low_copy
    assert medium_copy != low_copy


def test_dataset_registry_and_split_are_controlled() -> None:
    validate_registry()
    inspection = load_inspection()
    sources = load_sources()
    generated = generate_controlled_variants(sources)
    prepared = prepare_examples()
    support_ids = {row.source_example_id for row in prepared["support"]}
    evaluation_ids = {row.source_example_id for row in prepared["evaluation"]}

    assert support_ids.isdisjoint(evaluation_ids)
    assert len(inspection["datasets"]) == 9
    assert all(row["rows"] > 0 and row["schema"] for row in inspection["datasets"])
    assert len(generated) == len(sources) * 3
    assert all(row.original_text and row.source_dataset for row in generated)
    assert {
        row.language for row in generated
    } == {LanguageCode.EN, LanguageCode.HI, LanguageCode.HINGLISH}
    assert {row.language for row in prepared["evaluation"]} >= {
        LanguageCode.EN,
        LanguageCode.HI,
        LanguageCode.HINGLISH,
    }


def test_repeatable_evaluation_meets_session_thresholds() -> None:
    result = evaluate()

    assert result["status"] == "passed"
    metrics = result["metrics"]
    assert metrics["total_fixture_count"] >= 69
    assert metrics["classification_fixture_count"] >= 39
    assert metrics["entity_fixture_count"] >= 10
    assert metrics["false_positive_fixture_count"] >= 12
    assert metrics["ambiguous_fixture_count"] >= 8
    assert metrics["intent_accuracy"] >= 0.85
    assert metrics["crime_domain_accuracy"] >= 0.85
    assert metrics["entity_exact_match"] == 1
    assert metrics["urgent_precision"] >= 0.85
    assert metrics["urgent_recall"] >= 0.85
    assert metrics["false_positive_pass_rate"] == 1
    assert metrics["ambiguous_clarification_rate"] == 1


def test_child_safety_urgent_language_is_explicit_without_fabricated_coverage() -> None:
    result = UnderstandingEngine.analyze(
        "Ek minor ko online grooming messages aa rahe hain, urgent help chahiye"
    )

    assert result.crime_domain == CrimeDomain.CHILD_SAFETY
    assert result.urgency == Urgency.CRITICAL
    assert result.language == LanguageCode.HINGLISH


@pytest.mark.parametrize(
    ("message", "expected_intent", "expected_domain"),
    [
        ("Please verify link https://example.com", Intent.CHECK_IDENTIFIER, CrimeDomain.UNKNOWN),
        ("How can I become a cyber warrior volunteer?", Intent.CYBER_WARRIOR, CrimeDomain.UNKNOWN),
        ("Share online safety tips", Intent.GENERAL_AWARENESS, CrimeDomain.UNKNOWN),
        ("My files are locked by ransomware", Intent.SEEK_GUIDANCE, CrimeDomain.MALWARE),
        ("Someone stole my identity", Intent.SEEK_GUIDANCE, CrimeDomain.IDENTITY_THEFT),
        ("This post contains fake news", Intent.SEEK_GUIDANCE, CrimeDomain.MISINFORMATION),
        ("I received a cyber terrorism threat", Intent.SEEK_GUIDANCE, CrimeDomain.CYBER_TERRORISM),
    ],
)
def test_required_taxonomy_routes_are_explicit(
    message: str, expected_intent: Intent, expected_domain: CrimeDomain
) -> None:
    result = UnderstandingEngine.analyze(message)

    assert result.intent == expected_intent
    assert result.crime_domain == expected_domain
