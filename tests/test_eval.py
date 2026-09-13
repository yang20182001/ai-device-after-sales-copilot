import json
from pathlib import Path


def test_eval_cases_cover_unknown_and_high_risk_scenarios():
    cases = json.loads(Path("evals/cases.json").read_text(encoding="utf-8"))

    assert len(cases) >= 30
    assert any(case["expected"]["requires_human_review"] for case in cases)
    assert any(
        case["expected"]["should_acknowledge_missing_evidence"]
        for case in cases
    )


def test_eval_cases_have_stable_required_fields():
    cases = json.loads(Path("evals/cases.json").read_text(encoding="utf-8"))

    for case in cases:
        assert {"id", "device_id", "message", "expected"} <= set(case)
        assert {"requires_human_review", "should_acknowledge_missing_evidence"} <= set(
            case["expected"]
        )
