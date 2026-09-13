const state = { devices: [], selectedDevice: null, diagnosis: null };

const $ = (selector) => document.querySelector(selector);
const escapeHtml = (value) => String(value ?? "")
  .replaceAll("&", "&amp;")
  .replaceAll("<", "&lt;")
  .replaceAll(">", "&gt;")
  .replaceAll('"', "&quot;")
  .replaceAll("'", "&#039;");

async function api(path, options = {}) {
  const response = await fetch(path, { headers: { "Content-Type": "application/json" }, ...options });
  if (!response.ok) {
    let detail = `请求失败（${response.status}）`;
    try { detail = (await response.json()).detail || detail; } catch (_) {}
    throw new Error(detail);
  }
  return response.json();
}

function showToast(message, isError = false) {
  const toast = $("#toast");
  toast.textContent = message;
  toast.className = `toast visible ${isError ? "error" : ""}`;
  window.setTimeout(() => toast.className = "toast", 3200);
}

function riskLabel(level) {
  return ({ high: "高风险", medium: "中风险", low: "低风险" })[level] || "待判断";
}

function renderSummary(summary) {
  const cards = [
    ["设备总数", summary.device_count, "全部接入设备"],
    ["高风险设备", summary.high_risk_device_count, "离线或健康分偏低"],
    ["未关闭工单", summary.open_ticket_count, "open / in progress"],
    ["高风险告警", summary.unresolved_high_alert_count, "等待处理"],
  ];
  $("#summary-cards").innerHTML = cards.map(([label, value, hint]) => `
    <div class="metric-card"><span>${label}</span><strong>${escapeHtml(value)}</strong><small>${hint}</small></div>
  `).join("");
}

function renderDevices() {
  $("#device-list").innerHTML = state.devices.map((device) => `
    <button class="device-item ${state.selectedDevice?.device_id === device.device_id ? "selected" : ""}" data-device-id="${escapeHtml(device.device_id)}">
      <span class="device-status ${device.status}"></span>
      <span class="device-main"><strong>${escapeHtml(device.device_id)}</strong><small>${escapeHtml(device.store_name)} · ${escapeHtml(device.device_type)}</small></span>
      <span class="health-score">${escapeHtml(device.health_score)}</span>
    </button>
  `).join("");
  document.querySelectorAll(".device-item").forEach((button) => button.addEventListener("click", () => selectDevice(button.dataset.deviceId)));
}

function renderDevice(device, alerts) {
  $("#selected-device-title").textContent = `${device.device_id} · ${device.store_name}`;
  $("#device-overview").className = "device-overview";
  $("#device-overview").innerHTML = `
    <div class="overview-grid"><div><span>设备型号</span><strong>${escapeHtml(device.model)}</strong></div><div><span>当前状态</span><strong class="${device.online ? "online" : "offline"}">${device.online ? "在线" : "离线"}</strong></div><div><span>健康分</span><strong>${escapeHtml(device.health_score)}</strong></div><div><span>活跃工单</span><strong>${escapeHtml(device.active_ticket_count)}</strong></div></div>
    <div class="alert-strip"><span>最新告警</span>${alerts.length ? alerts.slice(0, 3).map((alert) => `<em class="severity-${alert.severity}">${escapeHtml(alert.message)}</em>`).join("") : "<em>暂无未处理告警</em>"}</div>
  `;
}

function renderDiagnosis(result) {
  state.diagnosis = result;
  const risk = result.risk || {};
  const pill = $("#risk-pill");
  pill.textContent = riskLabel(risk.level);
  pill.className = `risk-pill ${risk.level || "neutral"}`;
  $("#conversation").innerHTML = `
    <div class="user-message"><span class="message-label">现场描述</span><p>${escapeHtml(result.user_message)}</p></div>
    <div class="assistant-message"><span class="message-label">AI 建议</span><p>${escapeHtml(result.recommendations?.join("；") || "暂无建议")}</p></div>
    <div class="result-block"><h3>已确认事实</h3>${(result.facts || []).map((fact) => `<p>✓ ${escapeHtml(fact)}</p>`).join("")}</div>
    <div class="result-block"><h3>风险判断</h3><p>${escapeHtml((risk.reasons || []).join("；"))}</p>${risk.requires_human_review ? '<div class="review-alert">高风险事项：请人工复核后再执行</div>' : ""}</div>
    ${result.missing_information?.length ? `<div class="missing-block"><h3>资料边界</h3>${result.missing_information.map((item) => `<p>! ${escapeHtml(item)}</p>`).join("")}</div>` : ""}
  `;
  $("#evidence-count").textContent = `${result.sources?.length || 0} 条`;
  $("#evidence-list").className = result.sources?.length ? "evidence-list" : "evidence-list empty-state";
  $("#evidence-list").innerHTML = result.sources?.length ? result.sources.map((source) => `
    <article class="evidence-card"><div><strong>${escapeHtml(source.source_name)}</strong><span>${escapeHtml(source.source_section)}</span></div><p>${escapeHtml(source.content)}</p></article>
  `).join("") : "没有足够匹配的知识库证据，系统不会伪造引用。";
  $("#ticket-content").className = "ticket-content ready";
  $("#ticket-content").innerHTML = `<strong>可根据当前诊断生成草稿</strong><span>优先级将按风险规则计算，提交前必须人工确认。</span>`;
  $("#draft-button").disabled = false;
}

async function selectDevice(deviceId) {
  try {
    const [device, alerts] = await Promise.all([api(`/api/devices/${deviceId}`), api(`/api/devices/${deviceId}/alerts`)]);
    state.selectedDevice = device;
    renderDevices();
    renderDevice(device, alerts);
  } catch (error) { showToast(error.message, true); }
}

async function load() {
  try {
    const [devices, summary] = await Promise.all([api("/api/devices"), api("/api/dashboard/summary")]);
    state.devices = devices;
    renderDevices();
    renderSummary(summary);
    $("#api-status").textContent = "系统在线";
    $("#api-status").className = "status-dot online";
    if (devices.length) await selectDevice(devices[0].device_id);
  } catch (error) {
    $("#api-status").textContent = "连接失败";
    $("#api-status").className = "status-dot offline";
    showToast(error.message, true);
  }
}

$("#diagnosis-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  if (!state.selectedDevice) return showToast("请先选择设备", true);
  const button = event.target.querySelector("button");
  button.disabled = true;
  button.textContent = "分析中...";
  try {
    const result = await api("/api/diagnose", { method: "POST", body: JSON.stringify({ device_id: state.selectedDevice.device_id, message: $("#question").value }) });
    renderDiagnosis(result);
  } catch (error) { showToast(error.message, true); }
  button.disabled = false;
  button.textContent = "开始诊断";
});

$("#draft-button").addEventListener("click", async () => {
  if (!state.diagnosis) return;
  const button = $("#draft-button");
  button.disabled = true;
  try {
    const draft = await api("/api/tickets/draft", { method: "POST", body: JSON.stringify({ diagnosis: state.diagnosis }) });
    $("#ticket-content").innerHTML = `<strong>${escapeHtml(draft.ticket_id)} · ${escapeHtml(draft.priority)}</strong><span>${escapeHtml(draft.title)}</span><span>状态：草稿 · ${escapeHtml(draft.escalation_condition)}</span>`;
    showToast("工单草稿已生成，尚未提交");
  } catch (error) { showToast(error.message, true); button.disabled = false; }
});

$("#refresh-button").addEventListener("click", load);
load();
