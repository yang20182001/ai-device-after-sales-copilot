from __future__ import annotations


def calculate_risk(
    device: dict,
    alerts: list[dict],
    fault: dict | None,
) -> dict:
    reasons: list[str] = []
    level = "low"
    requires_human_review = False

    if device.get("status") == "offline" or device.get("online") is False:
        level = "high"
        requires_human_review = True
        reasons.append("设备当前离线")

    if fault and fault.get("severity") == "high":
        level = "high"
        requires_human_review = True
        reasons.append(f"故障码 {fault.get('fault_code', '')} 标记为高风险")
    elif fault and fault.get("severity") == "medium" and level == "low":
        level = "medium"
        reasons.append(f"故障码 {fault.get('fault_code', '')} 需要关注")

    high_alerts = [alert for alert in alerts if alert.get("severity") == "high"]
    if high_alerts:
        level = "high"
        requires_human_review = True
        reasons.append(f"存在 {len(high_alerts)} 条高风险告警")

    temperature_alerts = [
        alert for alert in alerts if alert.get("alert_type") == "temperature"
    ]
    if len(temperature_alerts) >= 3:
        level = "high"
        requires_human_review = True
        reasons.append("温度告警重复出现")

    return {
        "level": level,
        "requires_human_review": requires_human_review,
        "reasons": reasons or ["当前没有发现明显高风险信号"],
    }
