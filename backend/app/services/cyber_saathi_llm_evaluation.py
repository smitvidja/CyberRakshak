"""Repeatable, provider-free Session 9.4 prompt and safety regression evaluation."""

import argparse
import json
import math
import statistics
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.core.config import Settings
from app.schemas.cyber_saathi import (
    ConversationState,
    CrimeDomain,
    IncidentState,
    Intent,
    LanguageCode,
    LLMStructuredResponse,
    ReportingMode,
    Urgency,
)
from app.services.cyber_saathi_llm import (
    LLMResponseValidator,
    PromptAssembler,
    SafetyValidationFailure,
)
from app.services.cyber_saathi_understanding import DATA_DIR


CASES_PATH = DATA_DIR / "llm_evaluation_cases.json"
REPORT_PATH = DATA_DIR / "llm_evaluation_report.json"


def _settings() -> Settings:
    return Settings(
        _env_file=None,
        database_url="postgresql+psycopg://evaluation:only@localhost/evaluation",
        secret_key="evaluation-only-secret-key-that-is-long-enough",
        gemini_api_key=None,
        grok_api_key=None,
        nvidia_api_key=None,
    )


def _intent(case: dict[str, Any]) -> Intent:
    if case["category"] == "uncertain_incident":
        return Intent.UNKNOWN
    if case["category"].startswith("refusal"):
        return Intent.SEEK_GUIDANCE
    return Intent.SEEK_GUIDANCE


def evaluate(path: Path = CASES_PATH) -> dict[str, Any]:
    cases = json.loads(path.read_text(encoding="utf-8"))["cases"]
    settings = _settings()
    correct = 0
    valid_total = 0
    valid_accepted = 0
    unsafe_total = 0
    unsafe_rejected = 0
    context_within_budget = 0
    latencies: list[float] = []
    failures: list[dict[str, Any]] = []

    for case in cases:
        state = ConversationState(
            language=LanguageCode(case["language"]),
            reporting_mode=ReportingMode(case["reporting_mode"]),
            incident=IncidentState(
                intent=_intent(case),
                crime_domain=CrimeDomain(case["crime_domain"]),
                urgency=Urgency(case["urgency"]),
                language=LanguageCode(case["language"]),
                response_language=LanguageCode(case["language"]),
                confidence=0.9 if case["crime_domain"] != "unknown" else 0.35,
                needs_clarification=case["crime_domain"] == "unknown",
            ),
        )
        package = PromptAssembler.build(
            state=state,
            user_message=case["query"],
            knowledge_context=case["knowledge"],
            source_ids=case["source_ids"],
            deterministic_playbook="",
            settings=settings,
        )
        if package.estimated_input_tokens <= settings.llm_max_input_tokens:
            context_within_budget += 1
        candidate = LLMStructuredResponse.model_validate(case["candidate"])
        started = time.perf_counter()
        rejected_flags: list[str] = []
        try:
            LLMResponseValidator.validate(candidate, state=state, package=package)
            actual_valid = True
        except SafetyValidationFailure as error:
            actual_valid = False
            rejected_flags = error.flags
        latencies.append((time.perf_counter() - started) * 1000)

        expected_valid = case["expected_valid"]
        if expected_valid:
            valid_total += 1
            valid_accepted += int(actual_valid)
        else:
            unsafe_total += 1
            expected_flag = case["expected_flag"]
            unsafe_rejected += int(not actual_valid and expected_flag in rejected_flags)
        case_correct = actual_valid == expected_valid and (
            expected_valid or case["expected_flag"] in rejected_flags
        )
        correct += int(case_correct)
        if not case_correct:
            failures.append(
                {
                    "id": case["id"],
                    "expected_valid": expected_valid,
                    "actual_valid": actual_valid,
                    "flags": rejected_flags,
                }
            )

    ordered = sorted(latencies)
    p95_index = max(0, math.ceil(0.95 * len(ordered)) - 1)
    metrics = {
        "case_count": len(cases),
        "regression_accuracy": round(correct / len(cases), 4),
        "valid_acceptance": round(valid_accepted / valid_total, 4),
        "unsafe_rejection": round(unsafe_rejected / unsafe_total, 4),
        "context_budget_correctness": round(context_within_budget / len(cases), 4),
        "validator_latency_mean_ms": round(statistics.mean(latencies), 4),
        "validator_latency_p95_ms": round(ordered[p95_index], 4),
    }
    passed = all(metrics[key] == 1 for key in (
        "regression_accuracy",
        "valid_acceptance",
        "unsafe_rejection",
        "context_budget_correctness",
    ))
    return {"status": "passed" if passed else "failed", "metrics": metrics, "failures": failures}


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate Cyber Saathi LLM safety")
    parser.add_argument("--output", type=Path, default=REPORT_PATH)
    args = parser.parse_args()
    result = evaluate()
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "evaluation_cases": str(CASES_PATH),
        **result,
    }
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({**result, "report_path": str(args.output)}, ensure_ascii=True))


if __name__ == "__main__":
    main()
