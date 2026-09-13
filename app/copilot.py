from __future__ import annotations

import re

from app import repositories
from app.retrieval import search_service_knowledge
from app.rules import calculate_risk


def _extract_fault_codes(message: str) -> list[str]:
    return sorted(set(code.upper() for code in re.findall(r"\bE\d{2}\b", message.upper())))


def _fact_from_reading(reading: dict | None) -> list[str]:
    if not reading:
        return ["暂无最新设备读数"]
    facts = []
    if reading.get("temperature") is not None:
        facts.append(f"最新温度读数为 {reading['temperature']}°C")
    if reading.get("network_strength") is not None:
        facts.append(f"网络信号为 {reading['network_strength']} dBm")
    if reading.get("battery_percent") is not None:
        facts.append(f"电量为 {reading['battery_percent']}%")
    return facts


def diagnose_issue(device_id: str, user_message: str) -> dict:
    device = repositories.get_device_status(device_id)
    if not device:
        raise LookupError(f"设备不存在: {device_id}")

    alerts = repositories.get_device_alerts(device_id)
    fault_codes = _extract_fault_codes(user_message)
    faults = [
        fault
        for fault_code in fault_codes
        if (fault := repositories.get_fault_code(fault_code)) is not None
    ]
    primary_fault = faults[0] if faults else None
    raw_sources = search_service_knowledge(user_message, limit=5)
    sources = [source for source in raw_sources if source["score"] >= 0.5]

    facts = [
        f"设备 {device['device_id']} 当前状态为 {'在线' if device['online'] else '离线'}",
        f"设备健康分为 {device['health_score']}",
        *_fact_from_reading(device.get("latest_reading")),
    ]
    facts.extend(
        f"告警：{alert['message']}（{alert['severity']}）"
        for alert in alerts[:5]
    )
    facts.extend(
        f"故障码 {fault['fault_code']}：{fault['title']}（{fault['severity']}）"
        for fault in faults
    )

    risk = calculate_risk(device, alerts, primary_fault)
    recommendations: list[str] = []
    if primary_fault:
        recommendations.append(primary_fault["recommended_action"])
        if primary_fault["requires_field_service"]:
            recommendations.append("如现场确认传感器或制冷系统异常，安排授权工程师到场检修")
    elif sources:
        recommendations.append("按照引用资料逐项确认设备状态、告警和现场环境")
    else:
        recommendations.append("当前资料不足，先补充设备型号、告警时间和现场现象，再给出处理建议")
    if risk["requires_human_review"]:
        recommendations.append("该问题需售后主管或授权工程师人工复核后再执行")

    similar_tickets = repositories.find_similar_tickets(device_id, user_message)
    missing_information = []
    if not sources:
        missing_information.append("知识库没有找到足够匹配的资料，以上不是基于引用资料生成的结论")
    if not fault_codes and not sources:
        missing_information.append("用户描述中未识别到标准故障码")
    if fault_codes and not faults:
        missing_information.append("输入中的故障码不在当前演示故障码表中")

    return {
        "device": device,
        "user_message": user_message,
        "facts": facts,
        "inference": [
            "风险等级由设备状态、告警严重度和故障码规则计算，未使用虚构置信度"
        ],
        "recommendations": recommendations,
        "sources": sources,
        "missing_information": missing_information,
        "risk": risk,
        "faults": faults,
        "similar_tickets": similar_tickets,
    }


def generate_ticket_draft(diagnosis: dict) -> dict:
    return repositories.create_ticket_draft(
        {
            "device_id": diagnosis["device"]["device_id"],
            "summary": diagnosis["recommendations"][0]
            if diagnosis.get("recommendations")
            else "设备问题待处理",
            "symptom": diagnosis.get("user_message", "待补充故障现象"),
            "risk": diagnosis.get("risk", {"level": "medium"}),
            "recommendations": diagnosis.get("recommendations", []),
            "parts": [],
        }
    )
