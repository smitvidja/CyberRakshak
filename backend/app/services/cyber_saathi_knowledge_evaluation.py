"""Repeatable offline evaluation for the authoritative knowledge retriever."""

import argparse
import json
import math
import statistics
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.schemas.cyber_saathi import KnowledgeDomain, KnowledgeSearchRequest
from app.services.cyber_saathi_knowledge import EVALUATION_CASES_PATH, KnowledgeService


EVALUATION_REPORT_PATH = EVALUATION_CASES_PATH.with_name("knowledge_evaluation_report.json")


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
    actual_no_result = 0
    domain_cases = 0
    domain_correct = 0
    chunk_cases = 0
    chunk_correct = 0
    latencies: list[float] = []
    failures: list[dict[str, Any]] = []

    for case in cases:
        # A case may name several acceptable sources. As the corpus grows, more
        # than one document legitimately answers the same question - a morphing
        # query is answered correctly by the general image-misuse guidance and by
        # the dedicated Morphing section - and pinning one exact source turns every
        # genuine addition into a failure that says nothing about retrieval quality.
        expected_source = case["expected_source_id"]
        acceptable = (
            set()
            if expected_source is None
            else set(expected_source)
            if isinstance(expected_source, list)
            else {expected_source}
        )
        domain = case.get("domain")
        response = KnowledgeService.search(
            KnowledgeSearchRequest(
                query=case["query"],
                domain=KnowledgeDomain(domain) if domain is not None else None,
            )
        )
        latencies.append(response.retrieval_latency_ms)
        actual_source = response.matches[0].source_id if response.matches else None
        actual_chunk = response.matches[0].chunk_id if response.matches else None
        if response.no_result:
            actual_no_result += 1
        if expected_source is None:
            expected_no_result += 1
            if response.no_result:
                correct_no_result += 1
            else:
                failures.append({"query": case["query"], "expected": None, "actual": actual_source})
            continue
        positive_cases += 1
        if domain is not None:
            domain_cases += 1
            if response.matches and all(
                KnowledgeDomain(domain) in match.domains for match in response.matches
            ):
                domain_correct += 1
        if not response.no_result:
            relevant_hits += 1
        if actual_source in acceptable:
            source_correct += 1
        else:
            failures.append(
                {"query": case["query"], "expected": sorted(acceptable), "actual": actual_source}
            )
        expected_chunk = case.get("expected_chunk_id")
        if expected_chunk is not None:
            chunk_cases += 1
            if actual_chunk == expected_chunk:
                chunk_correct += 1
            else:
                failures.append(
                    {
                        "query": case["query"],
                        "expected_chunk": expected_chunk,
                        "actual_chunk": actual_chunk,
                    }
                )

    ordered_latencies = sorted(latencies)
    p95_index = max(0, math.ceil(0.95 * len(ordered_latencies)) - 1)

    metrics = {
        "case_count": len(cases),
        "positive_case_count": positive_cases,
        "retrieval_relevance": round(relevant_hits / positive_cases, 4),
        "source_correctness": round(source_correct / positive_cases, 4),
        "no_result_rate": round(actual_no_result / len(cases), 4),
        "expected_no_result_rate": round(expected_no_result / len(cases), 4),
        "no_result_correctness": round(correct_no_result / expected_no_result, 4)
        if expected_no_result else 1.0,
        "domain_filter_correctness": round(domain_correct / domain_cases, 4)
        if domain_cases else 1.0,
        "chunk_correctness": round(chunk_correct / chunk_cases, 4)
        if chunk_cases else 1.0,
        "false_positive_count": expected_no_result - correct_no_result,
        "false_negative_count": positive_cases - relevant_hits,
        "latency_mean_ms": round(statistics.mean(latencies), 3),
        "latency_p95_ms": round(ordered_latencies[p95_index], 3),
    }
    status = "passed" if (
        metrics["retrieval_relevance"] == 1
        and metrics["source_correctness"] == 1
        and metrics["no_result_correctness"] == 1
        and metrics["domain_filter_correctness"] == 1
        and metrics["chunk_correctness"] == 1
    ) else "failed"
    return {"status": status, "metrics": metrics, "failures": failures}


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate Cyber Saathi knowledge retrieval")
    parser.add_argument("--output", type=Path, default=EVALUATION_REPORT_PATH)
    args = parser.parse_args()
    result = evaluate()
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "evaluation_cases": str(EVALUATION_CASES_PATH),
        **result,
    }
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    # PowerShell may still expose a legacy code page; escaped output preserves
    # repeatable CLI evaluation instead of failing after a valid Hindi case.
    print(json.dumps({**result, "report_path": str(args.output)}, ensure_ascii=True))


if __name__ == "__main__":
    main()
