from __future__ import annotations

import json
import re
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

from app.db import get_connection, init_db


ROOT = Path(__file__).resolve().parent
KNOWLEDGE_DIR = ROOT / "knowledge"


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def _chunks(text: str) -> list[tuple[str, str, str]]:
    sections = re.split(r"(?=^##?\s+)", text, flags=re.MULTILINE)
    chunks = []
    for index, section in enumerate(sections):
        content = section.strip()
        if not content:
            continue
        heading = content.splitlines()[0].lstrip("# ").strip()
        chunk_id = f"chunk-{index + 1:03d}"
        chunks.append((chunk_id, heading or "通用说明", content))
    return chunks


def _insert_knowledge(connection: sqlite3.Connection) -> None:
    for document_path in sorted(KNOWLEDGE_DIR.glob("*.md")):
        document_id = f"doc-{document_path.stem}"
        source_name = document_path.name
        connection.execute(
            "INSERT OR IGNORE INTO knowledge_documents "
            "(document_id, source_name, source_type, is_demo_data) VALUES (?, ?, ?, 1)",
            (document_id, source_name, "markdown_demo"),
        )
        for index, (_, section, content) in enumerate(
            _chunks(document_path.read_text(encoding="utf-8")), start=1
        ):
            chunk_id = f"{document_id}-{index:03d}"
            connection.execute(
                "INSERT OR IGNORE INTO knowledge_chunks "
                "(chunk_id, document_id, content, source_section, source_page, is_demo_data) "
                "VALUES (?, ?, ?, ?, ?, 1)",
                (chunk_id, document_id, content, section, str(index)),
            )
            document_row = connection.execute(
                "SELECT source_name FROM knowledge_documents WHERE document_id = ?",
                (document_id,),
            ).fetchone()
            connection.execute(
                "INSERT OR IGNORE INTO knowledge_fts "
                "(chunk_id, content, source_name, source_section) VALUES (?, ?, ?, ?)",
                (chunk_id, content, document_row[0], section),
            )


def seed_database(path: str) -> None:
    init_db(path)
    connection = get_connection(path)
    now = _now()
    devices = [
        ("DEV-001", "STORE-101", "淮海路门店", "智能冷藏柜", "SC-200", "online", 62, now - timedelta(minutes=3)),
        ("DEV-002", "STORE-101", "淮海路门店", "智能咖啡机", "CM-100", "online", 96, now - timedelta(minutes=1)),
        ("DEV-003", "STORE-102", "徐家汇门店", "智能冷藏柜", "SC-200", "offline", 41, now - timedelta(hours=2, minutes=12)),
        ("DEV-004", "STORE-102", "徐家汇门店", "智能咖啡机", "CM-100", "online", 88, now - timedelta(minutes=4)),
        ("DEV-005", "STORE-103", "五角场门店", "智能冷藏柜", "SC-210", "online", 74, now - timedelta(minutes=7)),
        ("DEV-006", "STORE-103", "五角场门店", "智能咖啡机", "CM-110", "online", 99, now - timedelta(minutes=2)),
    ]
    for device_id, store_id, store_name, device_type, model, status, health, last_seen in devices:
        connection.execute(
            "INSERT OR IGNORE INTO devices "
            "(device_id, store_id, store_name, device_type, model, status, health_score, last_seen_at, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (device_id, store_id, store_name, device_type, model, status, health, last_seen.isoformat(), now.isoformat()),
        )

    fault_codes = [
        ("E01", "网络连接异常", "设备无法保持与平台的稳定连接。", "medium", "检查门店网络和设备通信模块。", 0),
        ("E02", "门体状态异常", "门体传感器连续上报异常状态。", "medium", "检查门体、磁簧开关和传感器线缆。", 1),
        ("E03", "温度传感器异常", "温度读数连续超出设备正常工作范围。", "high", "先确认环境温度和传感器连接，必要时安排现场检修。", 1),
        ("E04", "制冷效率下降", "设备降温速度低于基准，可能影响储存安全。", "high", "确认散热空间、冷凝器和制冷系统状态。", 1),
        ("E05", "电量不足", "备用电池电量低于安全阈值。", "low", "安排充电或检查供电线路。", 0),
        ("E06", "数据上报延迟", "设备数据上报延迟超过监控阈值。", "medium", "检查网络质量和设备缓存状态。", 0),
    ]
    for fault in fault_codes:
        connection.execute(
            "INSERT OR IGNORE INTO fault_codes "
            "(fault_code, title, description, severity, recommended_action, requires_field_service) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            fault,
        )

    readings = [
        ("DEV-001", 12.8, -61, 88, now - timedelta(minutes=4)),
        ("DEV-001", 13.4, -65, 88, now - timedelta(minutes=9)),
        ("DEV-001", 12.6, -63, 87, now - timedelta(minutes=14)),
        ("DEV-002", 4.2, -50, 100, now - timedelta(minutes=2)),
        ("DEV-003", 15.1, None, 76, now - timedelta(hours=2, minutes=13)),
        ("DEV-004", 4.8, -49, 100, now - timedelta(minutes=5)),
        ("DEV-005", 8.7, -57, 93, now - timedelta(minutes=8)),
        ("DEV-006", 3.9, -45, 100, now - timedelta(minutes=3)),
    ]
    for device_id, temperature, network, battery, recorded_at in readings:
        exists = connection.execute(
            "SELECT 1 FROM device_readings WHERE device_id = ? AND recorded_at = ?",
            (device_id, recorded_at.isoformat()),
        ).fetchone()
        if not exists:
            connection.execute(
                "INSERT INTO device_readings "
                "(device_id, temperature, network_strength, battery_percent, recorded_at) VALUES (?, ?, ?, ?, ?)",
                (device_id, temperature, network, battery, recorded_at.isoformat()),
            )

    alerts = [
        ("DEV-001", "temperature", "温度高于门店设备建议上限", "12.8", "high", now - timedelta(minutes=4), 0),
        ("DEV-001", "temperature", "温度连续三次超限", "13.4", "high", now - timedelta(minutes=9), 0),
        ("DEV-001", "fault_code", "检测到故障码 E03", "E03", "high", now - timedelta(minutes=5), 0),
        ("DEV-003", "offline", "设备已离线超过 2 小时", "132", "high", now - timedelta(hours=2), 0),
        ("DEV-005", "temperature", "温度接近告警阈值", "8.7", "medium", now - timedelta(minutes=8), 0),
    ]
    for device_id, alert_type, message, value, severity, occurred_at, resolved in alerts:
        exists = connection.execute(
            "SELECT 1 FROM alerts WHERE device_id = ? AND message = ? AND occurred_at = ?",
            (device_id, message, occurred_at.isoformat()),
        ).fetchone()
        if not exists:
            connection.execute(
                "INSERT INTO alerts "
                "(device_id, alert_type, message, value, severity, occurred_at, resolved) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (device_id, alert_type, message, value, severity, occurred_at.isoformat(), resolved),
            )

    tickets = [
        ("TKT-1001", "DEV-001", "冷藏柜温度连续超限", "温度多次超过建议范围，故障码 E03", "P1", "open", "张工", (now + timedelta(hours=2)).isoformat()),
        ("TKT-1002", "DEV-003", "设备离线排查", "设备连续离线超过 2 小时", "P1", "in_progress", "李工", (now + timedelta(hours=1)).isoformat()),
        ("TKT-1003", "DEV-005", "温度接近阈值", "温度接近预警线，需要观察", "P2", "open", "王工", (now + timedelta(hours=8)).isoformat()),
    ]
    for ticket_id, device_id, title, symptom, priority, status, assignee, due_at in tickets:
        connection.execute(
            "INSERT OR IGNORE INTO tickets "
            "(ticket_id, device_id, title, symptom, priority, status, assignee, due_at, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (ticket_id, device_id, title, symptom, priority, status, assignee, due_at, now.isoformat(), now.isoformat()),
        )

    _insert_knowledge(connection)
    connection.commit()
    connection.close()


if __name__ == "__main__":
    from app.config import settings

    seed_database(settings.database_path)
    print(json.dumps({"database": settings.database_path, "status": "seeded"}, ensure_ascii=False))
