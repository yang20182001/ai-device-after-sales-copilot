from __future__ import annotations

import re
import uuid
from datetime import datetime, timedelta, timezone

from app.config import settings
from app.db import get_connection


def _row_to_dict(row):
    return dict(row) if row else None


def _connection():
    return get_connection(settings.database_path)


def list_devices(status: str | None = None) -> list[dict]:
    connection = _connection()
    try:
        if status:
            rows = connection.execute(
                "SELECT * FROM devices WHERE status = ? ORDER BY device_id", (status,)
            ).fetchall()
        else:
            rows = connection.execute("SELECT * FROM devices ORDER BY device_id").fetchall()
        return [_row_to_dict(row) for row in rows]
    finally:
        connection.close()


def get_device_status(device_id: str) -> dict | None:
    connection = _connection()
    try:
        device = connection.execute(
            "SELECT * FROM devices WHERE device_id = ?", (device_id,)
        ).fetchone()
        if not device:
            return None
        latest = connection.execute(
            "SELECT * FROM device_readings WHERE device_id = ? "
            "ORDER BY recorded_at DESC LIMIT 1",
            (device_id,),
        ).fetchone()
        active_ticket_count = connection.execute(
            "SELECT COUNT(*) FROM tickets WHERE device_id = ? "
            "AND status IN ('draft', 'open', 'in_progress')",
            (device_id,),
        ).fetchone()[0]
        result = _row_to_dict(device)
        result["online"] = result["status"] == "online"
        result["latest_reading"] = _row_to_dict(latest)
        result["active_ticket_count"] = active_ticket_count
        return result
    finally:
        connection.close()


def get_device_alerts(device_id: str, limit: int = 10) -> list[dict]:
    connection = _connection()
    try:
        rows = connection.execute(
            "SELECT * FROM alerts WHERE device_id = ? "
            "ORDER BY occurred_at DESC LIMIT ?",
            (device_id, limit),
        ).fetchall()
        return [_row_to_dict(row) for row in rows]
    finally:
        connection.close()


def get_fault_code(fault_code: str) -> dict | None:
    connection = _connection()
    try:
        row = connection.execute(
            "SELECT * FROM fault_codes WHERE fault_code = ?", (fault_code.upper(),)
        ).fetchone()
        result = _row_to_dict(row)
        if result:
            result["requires_field_service"] = bool(result["requires_field_service"])
        return result
    finally:
        connection.close()


def find_similar_tickets(
    device_id: str, symptom: str, limit: int = 5
) -> list[dict]:
    connection = _connection()
    try:
        tokens = [token for token in re.findall(r"[A-Za-z0-9-]+|[\u4e00-\u9fff]", symptom) if len(token) >= 2]
        conditions = ["device_id = ?"]
        params: list[str | int] = [device_id]
        if tokens:
            token_conditions = []
            for token in tokens[:5]:
                token_conditions.append("(title LIKE ? OR symptom LIKE ?)")
                params.extend([f"%{token}%", f"%{token}%"])
            conditions.append("(" + " OR ".join(token_conditions) + ")")
        params.append(limit)
        rows = connection.execute(
            "SELECT * FROM tickets WHERE " + " AND ".join(conditions) + " "
            "ORDER BY updated_at DESC LIMIT ?",
            params,
        ).fetchall()
        return [_row_to_dict(row) for row in rows]
    finally:
        connection.close()


def create_ticket_draft(payload: dict) -> dict:
    device_id = payload.get("device_id", "")
    now = datetime.now(timezone.utc).replace(microsecond=0)
    risk_level = payload.get("risk", {}).get("level", "medium")
    priority = {"high": "P1", "medium": "P2", "low": "P3"}.get(risk_level, "P2")
    draft = {
        "ticket_id": f"DRAFT-{uuid.uuid4().hex[:8].upper()}",
        "device_id": device_id,
        "title": payload.get("summary", "设备问题待处理"),
        "symptom": payload.get("symptom") or payload.get("summary", "待补充故障现象"),
        "priority": priority,
        "status": "draft",
        "assignee": None,
        "due_at": (now + timedelta(hours=2 if priority == "P1" else 8)).isoformat(),
        "created_at": now.isoformat(),
        "updated_at": now.isoformat(),
        "investigation_steps": payload.get("recommendations", []),
        "parts": payload.get("parts", []),
        "escalation_condition": "高风险问题需售后主管或授权工程师人工确认",
        "requires_human_confirmation": True,
    }
    connection = _connection()
    try:
        connection.execute(
            "INSERT INTO tickets "
            "(ticket_id, device_id, title, symptom, priority, status, assignee, due_at, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                draft["ticket_id"],
                draft["device_id"],
                draft["title"],
                draft["symptom"],
                draft["priority"],
                draft["status"],
                draft["assignee"],
                draft["due_at"],
                draft["created_at"],
                draft["updated_at"],
            ),
        )
        connection.commit()
    finally:
        connection.close()
    return draft


def list_tickets(status: str | None = None) -> list[dict]:
    connection = _connection()
    try:
        if status:
            rows = connection.execute(
                "SELECT * FROM tickets WHERE status = ? ORDER BY updated_at DESC", (status,)
            ).fetchall()
        else:
            rows = connection.execute("SELECT * FROM tickets ORDER BY updated_at DESC").fetchall()
        return [_row_to_dict(row) for row in rows]
    finally:
        connection.close()


def get_dashboard_summary() -> dict:
    connection = _connection()
    try:
        device_count = connection.execute("SELECT COUNT(*) FROM devices").fetchone()[0]
        offline_device_count = connection.execute(
            "SELECT COUNT(*) FROM devices WHERE status = 'offline'"
        ).fetchone()[0]
        high_risk_device_count = connection.execute(
            "SELECT COUNT(*) FROM devices WHERE status = 'offline' OR health_score < 70"
        ).fetchone()[0]
        open_ticket_count = connection.execute(
            "SELECT COUNT(*) FROM tickets WHERE status IN ('open', 'in_progress')"
        ).fetchone()[0]
        draft_ticket_count = connection.execute(
            "SELECT COUNT(*) FROM tickets WHERE status = 'draft'"
        ).fetchone()[0]
        unresolved_high_alert_count = connection.execute(
            "SELECT COUNT(*) FROM alerts WHERE severity = 'high' AND resolved = 0"
        ).fetchone()[0]
        return {
            "device_count": device_count,
            "offline_device_count": offline_device_count,
            "high_risk_device_count": high_risk_device_count,
            "open_ticket_count": open_ticket_count,
            "draft_ticket_count": draft_ticket_count,
            "unresolved_high_alert_count": unresolved_high_alert_count,
        }
    finally:
        connection.close()
