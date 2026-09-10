import re
from datetime import date, timedelta

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


def test_noisy_minor_morphed_image_message_reaches_women_child_domain() -> None:
    result = UnderstandingEngine.analyze(
        "Someone using my morfed img im mminor girl"
    )

    assert result.crime_domain == CrimeDomain.WOMEN_CHILD_ONLINE_SAFETY
    assert result.intent == Intent.SEEK_GUIDANCE
    assert result.needs_clarification is False


@pytest.mark.parametrize(
    ("message", "expected_domain"),
    [
        (
            "Meri 15 saal ki cousin ko online friend ne private photos bhejne ko "
            "convince kiya. Ab photos leak karne ki dhamki dekar paise maang raha hai.",
            CrimeDomain.CHILD_SAFETY,
        ),
        (
            "Mere ex ke paas meri private photos hain aur woh baat na karne par "
            "photos online upload karne ki threat de raha hai. Kisko report karu?",
            CrimeDomain.WOMEN_CHILD_ONLINE_SAFETY,
        ),
        (
            "A 16 year old is being blackmailed with intimate images for money",
            CrimeDomain.CHILD_SAFETY,
        ),
        (
            "Someone is threatening to leak my nude photos unless I pay",
            CrimeDomain.WOMEN_CHILD_ONLINE_SAFETY,
        ),
    ],
)
def test_intimate_image_abuse_outranks_money_and_report_words(
    message: str, expected_domain: CrimeDomain
) -> None:
    result = UnderstandingEngine.analyze(message)

    assert result.crime_domain == expected_domain
    assert result.crime_domain != CrimeDomain.FINANCIAL_FRAUD


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


@pytest.mark.parametrize(
    "message",
    [
        "Mere account se 2 lakh 30 hazar chale gaye",
        "Loss was 2 lakh 30 thousand rupees",
        "Mere account se 2.3 lakh gaye",
        "Loss was ₹2,30,000",
        "Total 230000 rupees tha",
    ],
)
def test_indian_amount_variants_normalise_to_one_total(message: str) -> None:
    result = UnderstandingEngine.analyze(message)
    amounts = [entity for entity in result.entities if entity.type == EntityType.AMOUNT]

    assert len(amounts) == 1
    assert amounts[0].normalized_value == "230000"


def test_normalized_amount_uses_indian_grouping_for_visible_confirmation() -> None:
    assert UnderstandingEngine.format_amount_for_display("230000") == "₹2,30,000"
    assert UnderstandingEngine.format_amount_for_display("10000000") == "₹1,00,00,000"


def test_relative_hinglish_date_and_time_are_combined_for_report_prefill() -> None:
    result = UnderstandingEngine.analyze("link kal 6 pm aaya tha")
    date_time = next(entity for entity in result.entities if entity.type == EntityType.DATE_TIME)

    assert date_time.normalized_value == f"{(date.today() - timedelta(days=1)).isoformat()}T18:00:00"


@pytest.mark.parametrize(
    ("domain", "messages"),
    [
        (CrimeDomain.FINANCIAL_FRAUD, ("Money was debited from my bank account", "मेरे बैंक से पैसे कट गए", "I lost money from my bnak acount")),
        (CrimeDomain.PHISHING_SCAM, ("I opened a fake link", "मैंने नकली लिंक खोला", "I opened a phising lnik")),
        (CrimeDomain.ACCOUNT_COMPROMISE, ("My account was hacked and I cannot log in", "मेरा अकाउंट एक्सेस किसी और ने ले लिया", "My acount was haced")),
        (CrimeDomain.IMPERSONATION, ("A fake cyber police officer called me", "नकली पुलिस अधिकारी ने कॉल किया", "A fake syber polce officer called")),
        (CrimeDomain.IDENTITY_THEFT, ("My documents were misused for identity theft", "मेरी पहचान चोरी हुई", "My adahr misuse hua")),
        (CrimeDomain.ECOMMERCE_FRAUD, ("My online order was not delivered", "ऑनलाइन ऑर्डर का सामान नहीं मिला", "Online order delevery nahi hui")),
        (CrimeDomain.MALWARE, ("I installed an APK and gave remote access", "फोन में वायरस आ गया", "APK ko remot access diya")),
        (CrimeDomain.ONLINE_HARASSMENT, ("I am receiving online harassment and abuse", "इंस्टाग्राम पर मुझे धमकी मिल रही है", "Someone is harrasing me online")),
        (CrimeDomain.CYBERSTALKING, ("Someone is stalking online and tracking my location", "कोई मेरी लोकेशन ट्रैक कर रहा है", "Someone is stoking online")),
        (CrimeDomain.WOMEN_CHILD_ONLINE_SAFETY, ("A woman's morphed image is being shared", "महिला की अश्लील फोटो साझा हो रही है", "Woman morfd image shared")),
        (CrimeDomain.CHILD_SAFETY, ("An adult is grooming a child online", "बच्चे को ऑनलाइन grooming messages आ रहे हैं", "Adult is gruming a child")),
        (CrimeDomain.MISINFORMATION, ("A deepfake video is spreading misinformation", "फर्जी खबर वायरल हो रही है", "A deepfek video is viral")),
        (CrimeDomain.CYBER_TERRORISM, ("A cyber terrorism threat targeted a hospital", "साइबर आतंकवाद की धमकी मिली", "A terror thret targeted a hospital")),
        (CrimeDomain.OTHER, ("I need help with another cyber issue", "मुझे अन्य साइबर समस्या में मदद चाहिए", "I need help with an othr cyber isue")),
        (CrimeDomain.UNKNOWN, ("Something unusual happened online", "ऑनलाइन कुछ अजीब हुआ", "Somthing odd hapend onlne")),
    ],
)
def test_all_domain_routes_cover_english_hindi_and_typo_stt_variants(
    domain: CrimeDomain,
    messages: tuple[str, str, str],
) -> None:
    assert [UnderstandingEngine.analyze(message).crime_domain for message in messages] == [
        domain,
        domain,
        domain,
    ]


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
    assert len(inspection["datasets"]) == 10
    assert {row["id"] for row in inspection["datasets"]} >= {
        "bitext_27k",
        "cyber_chat_history_sqlite",
    }
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
        (
            "I paid for an online t-shirt but the order was not delivered",
            Intent.SEEK_GUIDANCE,
            CrimeDomain.ECOMMERCE_FRAUD,
        ),
        (
            "KYC update nahi kiya toh account block bola aur link open kar diya",
            Intent.SEEK_GUIDANCE,
            CrimeDomain.PHISHING_SCAM,
        ),
        (
            "A fake officer put my father under digital arrest",
            Intent.SEEK_GUIDANCE,
            CrimeDomain.IMPERSONATION,
        ),
        (
            "Someone is tracking my location and cyberstalking me",
            Intent.SEEK_GUIDANCE,
            CrimeDomain.CYBERSTALKING,
        ),
        (
            "A woman's morphed image is being used for blackmail",
            Intent.SEEK_GUIDANCE,
            CrimeDomain.WOMEN_CHILD_ONLINE_SAFETY,
        ),
    ],
)
def test_required_taxonomy_routes_are_explicit(
    message: str, expected_intent: Intent, expected_domain: CrimeDomain
) -> None:
    result = UnderstandingEngine.analyze(message)

    assert result.intent == expected_intent
    assert result.crime_domain == expected_domain


def test_explicit_language_selection_is_not_overridden_by_message_style() -> None:
    """A citizen who selects हिन्दी keeps getting Hindi even if they type romanised.

    Detection used to win outright, so one Hinglish-looking line silently
    switched the conversation away from the language the citizen had chosen.
    English is still treated as the interface default, so an English
    conversation continues to adopt a citizen writing in Hindi or Hinglish.
    """
    hi = LanguageCode.HI
    hinglish = LanguageCode.HINGLISH
    en = LanguageCode.EN

    # explicit selections stick
    assert UnderstandingEngine.response_language(hinglish, hi) is hi
    assert UnderstandingEngine.response_language(en, hi) is hi
    assert UnderstandingEngine.response_language(hi, hinglish) is hinglish

    # the English default still adapts to the citizen
    assert UnderstandingEngine.response_language(hinglish, en) is hinglish
    assert UnderstandingEngine.response_language(hi, en) is hi

    # no stated preference falls back to what was detected
    assert UnderstandingEngine.response_language(hinglish, None) is hinglish


def test_hindi_conversation_answers_in_devanagari_after_a_romanised_message() -> None:
    client = TestClient(app)
    started = client.post(
        "/api/v1/cyber-saathi/conversations",
        json={"language": "HI", "storage_consent": False, "reporting_mode": "undecided"},
    )
    assert started.status_code == 201, started.text
    state = started.json()["data"]["state"]
    assert re.search(r"[ऀ-ॿ]", state["turns"][0]["content"]), "welcome must be Hindi"

    replied = client.post(
        f"/api/v1/cyber-saathi/conversations/{state['id']}/messages",
        json={"state": state, "message": "mere sath kya hua pata hai"},
    )
    assert replied.status_code == 200, replied.text
    next_state = replied.json()["data"]["state"]
    assert next_state["language"] == "HI"
    answer = [turn for turn in next_state["turns"] if turn["role"] == "assistant"][-1]["content"]
    assert re.search(r"[ऀ-ॿ]", answer), f"expected Hindi, got: {answer}"
