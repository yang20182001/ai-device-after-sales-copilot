from app.rules import calculate_risk


def test_repeated_high_temperature_is_high_risk():
    result = calculate_risk(
        {"device_id": "DEV-001", "online": True},
        [{"type": "temperature", "value": 12.5, "severity": "high"}] * 3,
        {"fault_code": "E03", "severity": "high"},
    )
    assert result["level"] == "high"
    assert result["requires_human_review"] is True


def test_healthy_device_is_low_risk():
    result = calculate_risk(
        {"device_id": "DEV-002", "online": True},
        [],
        None,
    )
    assert result["level"] == "low"
    assert result["requires_human_review"] is False
