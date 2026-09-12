"""Repeatable evaluation for "which crime is this?".

This exists because the answer was 25% and nobody knew. The lexicon looked fine -
it is never loudly wrong, it just silently returns unknown - and an unknown domain
means no question flow, no retrieval filter, and a citizen told "मुझे स्पष्ट नहीं
है कि क्या हुआ" on every turn. There was no number anywhere that would have shown
that, so it survived until someone read a transcript.

Three sets, reported separately because they answer different questions:

``seed``
    Phrasings that were in mind while the domain exemplars were authored. Their
    score is contaminated and is kept only to catch an outright break.
``holdout``
    Written afterwards, same domains, deliberately different wording. This is the
    honest accuracy number.
``off_topic``
    Must return no domain at all. Without these, "improving recall" is
    indistinguishable from classifying everything as something.

Run with a provider configured to exercise the semantic path:

    ./.venv/Scripts/python.exe -m app.services.cyber_saathi_classification_evaluation

With no provider it still runs and reports the lexicon alone, which is the
configuration the test suite uses.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.schemas.cyber_saathi import CrimeDomain
from app.services.cyber_saathi_domain_classifier import classify_semantically
from app.services.cyber_saathi_understanding import UnderstandingEngine

DATA_DIR = Path(__file__).resolve().parents[1] / "data" / "cyber_saathi"
EVALUATION_CASES_PATH = DATA_DIR / "classification_evaluation_cases.json"
EVALUATION_REPORT_PATH = DATA_DIR / "classification_evaluation_report.json"

UNRESOLVED = {CrimeDomain.UNKNOWN.value, CrimeDomain.OTHER.value}


def load_cases(path: Path = EVALUATION_CASES_PATH) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    cases = payload.get("cases", [])
    if not cases:
        raise ValueError("Classification evaluation requires at least one case")
    return cases


def classify(query: str) -> tuple[str, str]:
    """Return (domain, which path decided it) exactly as the service does."""
    lexicon = UnderstandingEngine.analyze(query).crime_domain
    confident = lexicon.value not in UNRESOLVED
    resolved = classify_semantically(query, lexicon_confident=confident)
    if resolved is not None:
        return resolved.value, "override" if confident else "semantic"
    if confident:
        return lexicon.value, "lexicon"
    return CrimeDomain.UNKNOWN.value, "none"


def evaluate() -> dict[str, Any]:
    cases = load_cases()
    buckets: dict[str, dict[str, int]] = {}
    failures: list[dict[str, Any]] = []
    paths: dict[str, int] = {}

    for case in cases:
        expected = case["expected_domain"]
        got, path = classify(case["query"])
        paths[path] = paths.get(path, 0) + 1
        bucket = buckets.setdefault(
            case["set"], {"total": 0, "correct": 0, "unresolved": 0, "wrong": 0}
        )
        bucket["total"] += 1

        if expected is None:
            # Off-topic: the only correct answer is no domain at all.
            if got in UNRESOLVED:
                bucket["correct"] += 1
            else:
                bucket["wrong"] += 1
                failures.append({"set": case["set"], "query": case["query"], "expected": None, "actual": got})
            continue

        if got == expected:
            bucket["correct"] += 1
        elif got in UNRESOLVED:
            bucket["unresolved"] += 1
            failures.append({"set": case["set"], "query": case["query"], "expected": expected, "actual": "unknown"})
        else:
            bucket["wrong"] += 1
            failures.append({"set": case["set"], "query": case["query"], "expected": expected, "actual": got})

    def rate(bucket: dict[str, int], key: str) -> float:
        return round(bucket[key] / bucket["total"], 4) if bucket["total"] else 0.0

    metrics = {
        "case_count": len(cases),
        "decided_by": paths,
        **{
            f"{name}_{key}": rate(bucket, key)
            for name, bucket in buckets.items()
            for key in ("correct", "unresolved", "wrong")
        },
    }
    holdout = buckets.get("holdout", {"total": 0, "correct": 0, "wrong": 0})
    off_topic = buckets.get("off_topic", {"total": 0, "correct": 0, "wrong": 0})

    # Thresholds are floors, not targets. holdout_correct was 0.25 before the
    # semantic pass and 0.875 after; off_topic_wrong must stay at zero, because a
    # confidently wrong playbook is worse than admitting the domain is unclear.
    status = (
        "passed"
        if rate(holdout, "correct") >= 0.75 and off_topic.get("wrong", 0) == 0
        else "failed"
    )
    return {"status": status, "metrics": metrics, "failures": failures}


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate Cyber Saathi crime-domain classification")
    parser.add_argument("--output", type=Path, default=EVALUATION_REPORT_PATH)
    args = parser.parse_args()
    result = evaluate()
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "evaluation_cases": str(EVALUATION_CASES_PATH),
        **result,
    }
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], **result["metrics"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
