from app.copilot import diagnose_issue, generate_ticket_draft


def test_diagnosis_contains_facts_recommendations_sources_and_review_flag(seed_db):
    result = diagnose_issue(
        "DEV-001",
        "设备多次温度超限，故障码 E03，应该怎么处理？",
    )

    assert result["facts"]
    assert result["recommendations"]
    assert result["sources"]
    assert result["risk"]["level"] in {"low", "medium", "high"}
    assert "requires_human_review" in result["risk"]
    assert result["device"]["device_id"] == "DEV-001"


def test_diagnosis_acknowledges_missing_evidence_for_unknown_question(seed_db):
    result = diagnose_issue("DEV-002", "紫色推进器应该怎样维修？")

    assert result["missing_information"]
    assert result["sources"] == []


def test_diagnosis_does_not_call_known_evidence_missing_only_for_no_fault_code(seed_db):
    result = diagnose_issue("DEV-001", "温度传感器异常")

    assert result["sources"]
    assert not result["missing_information"]


def test_ticket_draft_keeps_human_confirmation_and_draft_status(seed_db):
    diagnosis = diagnose_issue("DEV-001", "故障码 E03 怎么处理？")

    draft = generate_ticket_draft(diagnosis)

    assert draft["status"] == "draft"
    assert draft["priority"] == "P1"
    assert draft["requires_human_confirmation"] is True
    assert draft["ticket_id"].startswith("DRAFT-")
