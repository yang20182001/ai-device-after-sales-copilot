from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app import repositories
from app.copilot import diagnose_issue, generate_ticket_draft
from app.schemas import DiagnoseRequest, TicketDraftRequest


router = APIRouter(prefix="/api")


@router.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "ai-device-after-sales-copilot"}


@router.get("/devices")
def devices(status: str | None = None) -> list[dict]:
    return repositories.list_devices(status)


@router.get("/devices/{device_id}")
def device_status(device_id: str) -> dict:
    result = repositories.get_device_status(device_id)
    if not result:
        raise HTTPException(status_code=404, detail="设备不存在")
    return result


@router.get("/devices/{device_id}/alerts")
def device_alerts(device_id: str) -> list[dict]:
    if not repositories.get_device_status(device_id):
        raise HTTPException(status_code=404, detail="设备不存在")
    return repositories.get_device_alerts(device_id)


@router.post("/diagnose")
def diagnose(request: DiagnoseRequest) -> dict:
    try:
        return diagnose_issue(request.device_id, request.message)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/tickets/draft")
def ticket_draft(request: TicketDraftRequest) -> dict:
    device_id = request.diagnosis.get("device", {}).get("device_id")
    if not device_id or not repositories.get_device_status(device_id):
        raise HTTPException(status_code=404, detail="诊断结果中的设备不存在")
    return generate_ticket_draft(request.diagnosis)


@router.get("/tickets")
def tickets(status: str | None = None) -> list[dict]:
    return repositories.list_tickets(status)


@router.get("/dashboard/summary")
def dashboard_summary() -> dict:
    return repositories.get_dashboard_summary()
