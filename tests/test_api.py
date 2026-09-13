import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import app


@pytest.fixture
def client(seed_db, monkeypatch):
    from app import main

    monkeypatch.setattr(main, "settings", Settings(database_path=str(seed_db)))
    with TestClient(app) as test_client:
        yield test_client


def test_health_and_devices_endpoints(client):
    assert client.get("/api/health").json()["status"] == "ok"

    response = client.get("/api/devices")

    assert response.status_code == 200
    assert len(response.json()) >= 6


def test_diagnose_endpoint_returns_structured_result(client):
    response = client.post(
        "/api/diagnose",
        json={"device_id": "DEV-001", "message": "故障码 E03 怎么处理？"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["risk"]["level"] == "high"
    assert payload["sources"]


def test_ticket_draft_endpoint_only_creates_draft(client):
    diagnosis = client.post(
        "/api/diagnose",
        json={"device_id": "DEV-001", "message": "故障码 E03 怎么处理？"},
    ).json()

    response = client.post("/api/tickets/draft", json={"diagnosis": diagnosis})

    assert response.status_code == 200
    assert response.json()["status"] == "draft"
    assert response.json()["requires_human_confirmation"] is True


def test_api_rejects_unknown_device_and_empty_message(client):
    unknown = client.post(
        "/api/diagnose",
        json={"device_id": "DEV-999", "message": "请检查"},
    )
    invalid = client.post(
        "/api/diagnose",
        json={"device_id": "DEV-001", "message": ""},
    )

    assert unknown.status_code == 404
    assert invalid.status_code == 422


def test_dashboard_summary_contains_operational_metrics(client):
    response = client.get("/api/dashboard/summary")

    assert response.status_code == 200
    payload = response.json()
    assert payload["device_count"] >= 6
    assert "high_risk_device_count" in payload
    assert "open_ticket_count" in payload
