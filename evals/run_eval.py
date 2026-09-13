from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.copilot import diagnose_issue
from data.seed import seed_database


def _evaluate_case(case: dict) -> dict:
    result = diagnose_issue(case["device_id"], case["message"])
    expected = case["expected"]
    sources_hit = bool(result["sources"]) == (not expected["should_acknowledge_missing_evidence"])
    review_hit = result["risk"]["requires_human_review"] == expected["requires_human_review"]
    missing_hit = bool(result["missing_information"]) == expected["should_acknowledge_missing_evidence"]
    from app.copilot import generate_ticket_draft

    draft = generate_ticket_draft(result)
    required_fields = ("ticket_id", "device_id", "title", "symptom", "priority", "status")
    return {
        "id": case["id"],
        "citation_hit": sources_hit,
        "required_review_match": review_hit,
        "missing_evidence_match": missing_hit,
        "ticket_fields_complete": all(draft.get(field) for field in required_fields),
    }


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="ai-copilot-eval-") as directory:
        database_path = Path(directory) / "eval.db"
        seed_database(str(database_path))

        from app import repositories, retrieval
        from app.config import Settings

        config = Settings(database_path=str(database_path))
        repositories.settings = config
        retrieval.settings = config

        cases = json.loads((PROJECT_ROOT / "evals" / "cases.json").read_text(encoding="utf-8"))
        results = [_evaluate_case(case) for case in cases]
        expected_review_cases = [
            case for case in cases if case["expected"]["requires_human_review"]
        ]
        matched_review_ids = {
            item["id"] for item in results if item["required_review_match"]
        }
        review_recall = sum(
            case["id"] in matched_review_ids for case in expected_review_cases
        ) / max(len(expected_review_cases), 1)
        summary = {
            "case_count": len(results),
            "citation_hit_rate": round(sum(item["citation_hit"] for item in results) / len(results), 3),
            "required_review_recall": round(review_recall, 3),
            "missing_evidence_accuracy": round(sum(item["missing_evidence_match"] for item in results) / len(results), 3),
            "ticket_field_completeness": round(sum(item["ticket_fields_complete"] for item in results) / len(results), 3),
            "failed_case_ids": [
                item["id"]
                for item in results
                if not all(item[key] for key in (
                    "citation_hit", "required_review_match", "missing_evidence_match", "ticket_fields_complete"
                ))
            ],
        }
        print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
