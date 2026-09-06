"""Repeatable offline evaluation for the authoritative knowledge retriever."""

import json
import statistics
from pathlib import Path
from typing import Any

from app.schemas.cyber_saathi import CrimeDomain, KnowledgeSearchRequest
from app.services.cyber_saathi_knowledge import EVALUATION_CASES_PATH, KnowledgeService


def load_cases(path: Path = EVALUATION_CASES_PATH) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    cases = payload.get("cases", [])
    if not cases:
        raise ValueError("Knowledge evaluation requires at least one case")
    return cases


def evaluate() -> dict[str, Any]:
    cases = load_cases()
    positive_cases = 0
    relevant_hits = 0
    source_correct = 0
    expected_no_result = 0
    correct_no_result = 0
    latencies: list[float] = []
    failures: list[dict[str, Any]] = []

    for case in cases:
        expected_source = case["expected_source_id"]
        domain = case.get("domain")
        response = KnowledgeService.search(
            KnowledgeSearchRequest(
                query=case["query"],
                domain=CrimeDomain(domain) if domain is not None else None,
            )
        )
        latencies.append(response.retrieval_latency_ms)
        actual_source = response.matches[0].source_id if response.matches else None
        if expected_source is None:
            expected_no_result += 1
            if response.no_result:
                correct_no_result += 1
            else:
                failures.append({"query": case["query"], "expected": None, "actual": actual_source})
            continue
        positive_cases += 1
        if not response.no_result:
            relevant_hits += 1
        if actual_source == expected_source:
            source_correct += 1
        else:
            failures.append(
                {"query": case["query"], "expected": expected_source, "actual": actual_source}
            )

    metrics = {
        "case_count": len(cases),
        "positive_case_count": positive_cases,
        "retrieval_relevance": round(relevant_hits / positive_cases, 4),
        "source_correctness": round(source_correct / positive_cases, 4),
        "no_result_rate": round(expected_no_result / len(cases), 4),
        "no_result_correctness": round(correct_no_result / expected_no_result, 4),
        "latency_mean_ms": round(statistics.mean(latencies), 3),
        "latency_p95_ms": round(max(latencies), 3),
    }
    status = "passed" if (
        metrics["retrieval_relevance"] == 1
        and metrics["source_correctness"] == 1
        and metrics["no_result_correctness"] == 1
    ) else "failed"
    return {"status": status, "metrics": metrics, "failures": failures}


def main() -> None:
    # PowerShell may still expose a legacy code page; escaped output preserves
    # repeatable CLI evaluation instead of failing after a valid Hindi case.
    print(json.dumps(evaluate(), ensure_ascii=True))


if __name__ == "__main__":
    main()
