import json
from collections import Counter

from app.schemas.cyber_saathi import Urgency
from app.services.cyber_saathi_dataset import (
    DATA_DIR,
    prepare_examples,
    validate_registry,
)
from app.services.cyber_saathi_understanding import UnderstandingEngine


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


def _load_cases() -> dict[str, list[object]]:
    return json.loads((DATA_DIR / "evaluation_cases.json").read_text(encoding="utf-8"))


def _classification_cases() -> list[dict[str, str]]:
    generated = [
        {
            "text": row.variant_text,
            "language": row.language.value,
            "intent": row.intent.value,
            "crime_domain": row.crime_domain.value,
            "urgency": row.urgency.value,
            "sentiment": row.sentiment.value,
        }
        for row in prepare_examples()["evaluation"]
    ]
    return generated + _load_cases()["classification_cases"]


def _entity_signature(result: object) -> list[tuple[str, str]]:
    return sorted(
        (entity.type.value, entity.normalized_value or entity.value)
        for entity in result.entities
    )


def evaluate() -> dict[str, object]:
    validate_registry()
    cases = _load_cases()
    fixtures = _classification_cases()
    results = [UnderstandingEngine.analyze(row["text"]) for row in fixtures]

    expected_intents = [row["intent"] for row in fixtures]
    predicted_intents = [result.intent.value for result in results]
    expected_domains = [row["crime_domain"] for row in fixtures]
    predicted_domains = [result.crime_domain.value for result in results]
    expected_languages = [row["language"] for row in fixtures]
    predicted_languages = [result.language.value for result in results]
    expected_sentiments = [row["sentiment"] for row in fixtures]
    predicted_sentiments = [result.sentiment.value for result in results]
    expected_urgency = [row["urgency"] for row in fixtures]
    predicted_urgency = [result.urgency.value for result in results]

    expected_urgent = [value in {Urgency.HIGH.value, Urgency.CRITICAL.value} for value in expected_urgency]
    predicted_urgent = [value in {Urgency.HIGH.value, Urgency.CRITICAL.value} for value in predicted_urgency]
    urgent_tp = sum(expected and predicted for expected, predicted in zip(expected_urgent, predicted_urgent))
    urgent_fp = sum(not expected and predicted for expected, predicted in zip(expected_urgent, predicted_urgent))
    urgent_fn = sum(expected and not predicted for expected, predicted in zip(expected_urgent, predicted_urgent))

    entity_passes = 0
    entity_failures: list[dict[str, object]] = []
    for fixture in cases["entity_cases"]:
        result = UnderstandingEngine.analyze(fixture["text"])
        actual = _entity_signature(result)
        expected = sorted(
            (entity["type"], entity["normalized_value"])
            for entity in fixture["entities"]
        )
        if actual == expected:
            entity_passes += 1
        else:
            entity_failures.append({"text": fixture["text"], "expected": expected, "actual": actual})

    false_positive_passes = 0
    for message in cases["false_positive_cases"]:
        result = UnderstandingEngine.analyze(message)
        false_positive_passes += (
            result.intent.value == "unknown"
            and result.crime_domain.value == "unknown"
            and result.urgency == Urgency.LOW
        )

    ambiguous_passes = 0
    for message in cases["ambiguous_cases"]:
        result = UnderstandingEngine.analyze(message)
        ambiguous_passes += result.needs_clarification and result.clarification_prompt is not None

    metrics = {
        "classification_fixture_count": len(fixtures),
        "entity_fixture_count": len(cases["entity_cases"]),
        "false_positive_fixture_count": len(cases["false_positive_cases"]),
        "ambiguous_fixture_count": len(cases["ambiguous_cases"]),
        "total_fixture_count": len(fixtures) + len(cases["entity_cases"]) + len(cases["false_positive_cases"]) + len(cases["ambiguous_cases"]),
        "intent_accuracy": round(sum(e == p for e, p in zip(expected_intents, predicted_intents)) / len(fixtures), 3),
        "intent_macro_f1": macro_f1(expected_intents, predicted_intents),
        "crime_domain_accuracy": round(sum(e == p for e, p in zip(expected_domains, predicted_domains)) / len(fixtures), 3),
        "crime_domain_macro_f1": macro_f1(expected_domains, predicted_domains),
        "language_accuracy": round(sum(e == p for e, p in zip(expected_languages, predicted_languages)) / len(fixtures), 3),
        "sentiment_accuracy": round(sum(e == p for e, p in zip(expected_sentiments, predicted_sentiments)) / len(fixtures), 3),
        "urgency_accuracy": round(sum(e == p for e, p in zip(expected_urgency, predicted_urgency)) / len(fixtures), 3),
        "entity_exact_match": round(entity_passes / len(cases["entity_cases"]), 3),
        "urgent_precision": round(urgent_tp / (urgent_tp + urgent_fp), 3) if urgent_tp + urgent_fp else 0,
        "urgent_recall": round(urgent_tp / (urgent_tp + urgent_fn), 3) if urgent_tp + urgent_fn else 0,
        "false_positive_pass_rate": round(false_positive_passes / len(cases["false_positive_cases"]), 3),
        "ambiguous_clarification_rate": round(ambiguous_passes / len(cases["ambiguous_cases"]), 3),
        "intent_confusion": dict(Counter(f"{e}->{p}" for e, p in zip(expected_intents, predicted_intents) if e != p)),
        "domain_confusion": dict(Counter(f"{e}->{p}" for e, p in zip(expected_domains, predicted_domains) if e != p)),
        "entity_failures": entity_failures,
    }
    thresholds_pass = (
        metrics["intent_accuracy"] >= 0.85
        and metrics["crime_domain_accuracy"] >= 0.85
        and metrics["language_accuracy"] >= 0.85
        and metrics["sentiment_accuracy"] >= 0.85
        and metrics["urgency_accuracy"] >= 0.85
        and metrics["entity_exact_match"] == 1
        and metrics["urgent_precision"] >= 0.85
        and metrics["urgent_recall"] >= 0.85
        and metrics["false_positive_pass_rate"] >= 0.9
        and metrics["ambiguous_clarification_rate"] == 1
    )
    return {"status": "passed" if thresholds_pass else "failed", "metrics": metrics}


def main() -> None:
    result = evaluate()
    print(json.dumps(result, indent=2))
    if result["status"] != "passed":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
