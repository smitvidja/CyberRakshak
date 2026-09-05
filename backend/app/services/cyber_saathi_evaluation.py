import json
from collections import Counter

from app.schemas.cyber_saathi import EntityType, Urgency
from app.services.cyber_saathi_dataset import prepare_examples, validate_registry
from app.services.cyber_saathi_understanding import UnderstandingEngine


ENTITY_FIXTURES = [
    (
        "Rs 12,500 went to fraudster@ybl, UTR ID 123456789012 on 18/05/2024 at 14:30.",
        {EntityType.AMOUNT, EntityType.UPI_ID, EntityType.TRANSACTION_ID, EntityType.DATE, EntityType.TIME},
    ),
    (
        "Contact +91 98765 43210 or victim@example.com and check https://example.com/a.",
        {EntityType.PHONE_NUMBER, EntityType.EMAIL, EntityType.URL},
    ),
    (
        "My HDFC bank account and Instagram profile were affected in Mumbai.",
        {EntityType.PROVIDER, EntityType.ACCOUNT_SERVICE, EntityType.SOCIAL_PLATFORM, EntityType.LOCATION},
    ),
]
FALSE_POSITIVE_FIXTURES = ["Hello, how are you?", "Tell me something interesting."]


def macro_f1(expected: list[str], predicted: list[str]) -> float:
    labels = set(expected) | set(predicted)
    scores = []
    for label in labels:
        true_positive = sum(e == label and p == label for e, p in zip(expected, predicted))
        false_positive = sum(e != label and p == label for e, p in zip(expected, predicted))
        false_negative = sum(e == label and p != label for e, p in zip(expected, predicted))
        precision = true_positive / (true_positive + false_positive) if true_positive + false_positive else 0
        recall = true_positive / (true_positive + false_negative) if true_positive + false_negative else 0
        scores.append(2 * precision * recall / (precision + recall) if precision + recall else 0)
    return round(sum(scores) / len(scores), 3) if scores else 0


def evaluate() -> dict[str, object]:
    validate_registry()
    fixtures = prepare_examples()["evaluation"]
    results = [UnderstandingEngine.analyze(row.variant_text) for row in fixtures]

    expected_intents = [row.intent.value for row in fixtures]
    predicted_intents = [result.intent.value for result in results]
    expected_domains = [row.crime_domain.value for row in fixtures]
    predicted_domains = [result.crime_domain.value for result in results]
    expected_languages = [row.language.value for row in fixtures]
    predicted_languages = [result.language.value for result in results]
    expected_sentiments = [row.sentiment.value for row in fixtures]
    predicted_sentiments = [result.sentiment.value for result in results]

    expected_urgent = [row.urgency in {Urgency.HIGH, Urgency.CRITICAL} for row in fixtures]
    predicted_urgent = [result.urgency in {Urgency.HIGH, Urgency.CRITICAL} for result in results]
    urgent_tp = sum(expected and predicted for expected, predicted in zip(expected_urgent, predicted_urgent))
    urgent_fp = sum(not expected and predicted for expected, predicted in zip(expected_urgent, predicted_urgent))
    urgent_fn = sum(expected and not predicted for expected, predicted in zip(expected_urgent, predicted_urgent))

    entity_passes = 0
    for message, expected_types in ENTITY_FIXTURES:
        extracted = {entity.type for entity in UnderstandingEngine.analyze(message).entities}
        entity_passes += expected_types.issubset(extracted)

    false_positive_passes = 0
    for message in FALSE_POSITIVE_FIXTURES:
        result = UnderstandingEngine.analyze(message)
        false_positive_passes += result.crime_domain.value == "unknown" and not result.entities

    ambiguous = UnderstandingEngine.analyze("Something odd happened online.")
    metrics = {
        "fixture_count": len(fixtures),
        "intent_accuracy": round(sum(e == p for e, p in zip(expected_intents, predicted_intents)) / len(fixtures), 3),
        "intent_macro_f1": macro_f1(expected_intents, predicted_intents),
        "crime_domain_accuracy": round(sum(e == p for e, p in zip(expected_domains, predicted_domains)) / len(fixtures), 3),
        "crime_domain_macro_f1": macro_f1(expected_domains, predicted_domains),
        "language_accuracy": round(sum(e == p for e, p in zip(expected_languages, predicted_languages)) / len(fixtures), 3),
        "sentiment_accuracy": round(sum(e == p for e, p in zip(expected_sentiments, predicted_sentiments)) / len(fixtures), 3),
        "entity_fixture_accuracy": round(entity_passes / len(ENTITY_FIXTURES), 3),
        "urgent_precision": round(urgent_tp / (urgent_tp + urgent_fp), 3) if urgent_tp + urgent_fp else 0,
        "urgent_recall": round(urgent_tp / (urgent_tp + urgent_fn), 3) if urgent_tp + urgent_fn else 0,
        "false_positive_pass_rate": round(false_positive_passes / len(FALSE_POSITIVE_FIXTURES), 3),
        "ambiguous_input_requests_clarification": ambiguous.needs_clarification,
        "intent_confusion": dict(Counter(f"{e}->{p}" for e, p in zip(expected_intents, predicted_intents) if e != p)),
        "domain_confusion": dict(Counter(f"{e}->{p}" for e, p in zip(expected_domains, predicted_domains) if e != p)),
    }
    thresholds_pass = (
        metrics["intent_accuracy"] >= 0.8
        and metrics["crime_domain_accuracy"] >= 0.8
        and metrics["language_accuracy"] >= 0.8
        and metrics["sentiment_accuracy"] >= 0.8
        and metrics["entity_fixture_accuracy"] == 1
        and metrics["urgent_precision"] >= 0.8
        and metrics["urgent_recall"] >= 0.8
        and metrics["false_positive_pass_rate"] == 1
        and metrics["ambiguous_input_requests_clarification"] is True
    )
    return {"status": "passed" if thresholds_pass else "failed", "metrics": metrics}


def main() -> None:
    result = evaluate()
    print(json.dumps(result, indent=2))
    if result["status"] != "passed":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
