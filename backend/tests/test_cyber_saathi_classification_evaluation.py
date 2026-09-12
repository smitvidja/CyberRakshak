"""The gate that stops classification quietly going back to 25%.

The suite runs offline, so it cannot reproduce the semantic accuracy itself. What
it can do is check the things that hold without a provider, and hold the committed
report to its floor - which means anyone changing the classifier has to re-run the
evaluation and commit the new numbers, the same contract the knowledge index has.
"""

from __future__ import annotations

import json

import pytest

from app.schemas.cyber_saathi import CrimeDomain
from app.services import cyber_saathi_classification_evaluation as evaluation


def _report() -> dict:
    return json.loads(evaluation.EVALUATION_REPORT_PATH.read_text(encoding="utf-8"))


# ------------------------------------------------------------------ the cases

def test_every_domain_is_represented_in_the_holdout_or_seed_sets() -> None:
    """A domain with no case can regress to zero without any number moving."""
    cases = evaluation.load_cases()
    covered = {case["expected_domain"] for case in cases if case["expected_domain"]}
    expected = {
        domain.value
        for domain in CrimeDomain
        if domain not in {CrimeDomain.UNKNOWN, CrimeDomain.OTHER}
    }
    missing = expected - covered
    assert not missing, f"no evaluation case for: {sorted(missing)}"


def test_the_holdout_set_is_kept_separate_and_is_not_empty() -> None:
    """Accuracy measured on the phrasings the exemplars were written from is not
    accuracy. The honest number needs its own set."""
    cases = evaluation.load_cases()
    holdout = [case for case in cases if case["set"] == "holdout"]
    seed = [case for case in cases if case["set"] == "seed"]
    assert len(holdout) >= 12
    assert not ({case["query"] for case in holdout} & {case["query"] for case in seed})


def test_off_topic_cases_exist() -> None:
    """Without these, classifying everything as something scores perfectly."""
    cases = evaluation.load_cases()
    assert [case for case in cases if case["set"] == "off_topic"]


# ------------------------------------------------------- holds without a provider

def test_off_topic_text_is_never_given_a_crime_domain() -> None:
    """True offline as well: the lexicon must not fire on a recipe either."""
    result = evaluation.evaluate()
    assert result["metrics"]["off_topic_wrong"] == 0.0


def test_the_evaluation_runs_without_a_provider() -> None:
    """It has to be runnable in CI and on a machine with no key, or it will not be
    run at all."""
    result = evaluation.evaluate()
    assert result["metrics"]["case_count"] == len(evaluation.load_cases())
    assert "holdout_correct" in result["metrics"]


# ------------------------------------------------------- the committed report

def test_the_committed_report_meets_its_floor() -> None:
    """Held-out accuracy was 0.25 before the semantic pass. This is the number that
    would have caught it, and it fails if someone regresses the classifier and
    commits a worse report - or forgets to re-run it."""
    report = _report()
    assert report["status"] == "passed", report.get("failures")
    assert report["metrics"]["holdout_correct"] >= 0.75
    assert report["metrics"]["off_topic_wrong"] == 0.0


def test_the_committed_report_was_produced_with_the_semantic_path_live() -> None:
    """A report generated with no provider would show a passing lexicon and hide
    everything this evaluation exists to measure."""
    report = _report()
    decided = report["metrics"]["decided_by"]
    assert decided.get("semantic", 0) > 0, (
        "the committed report was generated without a provider; re-run "
        "python -m app.services.cyber_saathi_classification_evaluation"
    )


def test_the_committed_report_covers_the_current_case_file() -> None:
    report = _report()
    assert report["metrics"]["case_count"] == len(evaluation.load_cases()), (
        "cases were added or removed without re-running the evaluation"
    )
