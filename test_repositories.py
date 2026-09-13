from app.repositories import (
    create_ticket_draft,
    find_similar_tickets,
    get_device_alerts,
    get_device_status,
    get_fault_code,
    list_devices,
)


def test_repository_returns_device_and_fault_facts(seed_db):
    devices = list_devices()
    assert len(devices) >= 6
    device = get_device_status("DEV-001")
    assert device["device_id"] == "DEV-001"
    assert device["latest_reading"]["temperature"] > 10
    assert get_device_alerts("DEV-001")
    assert get_fault_code("E03")["severity"] == "high"


def test_repository_finds_similar_tickets_and_creates_draft(seed_db):
    matches = find_similar_tickets("DEV-001", "温度 故障码 E03")
    assert matches
    draft = create_ticket_draft(
        {
            "device_id": "DEV-001",
            "summary": "温度持续超限",
            "risk": {"level": "high"},
            "recommendations": ["确认传感器连接"],
        }
    )
    assert draft["ticket_id"].startswith("DRAFT-")
    assert draft["status"] == "draft"
