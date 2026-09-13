# AI 设备售后与运维助手 Implementation Plan

> **Status:** Completed on 2026-09-13. Implementation, tests, deterministic evaluation, Demo UI, screenshot, CI workflow, and GitHub release documentation are present and verified.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 构建一个可公开放入 GitHub 的 AI 设备售后与运维助手 MVP，演示设备状态查询、知识库检索、故障诊断、工单草稿和服务风险看板的完整闭环。

**Architecture:** 采用 Python FastAPI 单体后端、SQLite 结构化数据与 FTS5 文档检索、原生 HTML/CSS/JavaScript 前端。AI 编排层使用可替换的 OpenAI-compatible LLM 适配器；没有 API Key 时使用确定性的本地规则与模板回退，保证 Demo 可在无模型密钥环境启动。所有业务数据为模拟数据，知识文档为明确标注的演示资料。

**Tech Stack:** Python 3.11+、FastAPI、Uvicorn、Pydantic、SQLite/FTS5、pytest、原生 HTML/CSS/JavaScript、OpenAI-compatible HTTP API（可选）。

## Global Constraints

- 不使用真实企业、客户、设备或财务数据。
- 不把模拟结果描述为真实线上效果或真实客户案例。
- AI 只能生成诊断建议和工单草稿，高风险问题与工单提交必须人工确认。
- 数据库和规则层负责事实查询、阈值判断和指标计算；大模型负责理解、规划和表达。
- 知识库没有足够依据时，系统必须明确说明资料不足，不编造引用。
- API Key 只能通过环境变量读取，禁止提交 `.env`、密钥、Cookie 或个人信息。
- MVP 优先完成可体验闭环，不实现真实硬件控制、远程维修、移动端和复杂预测模型。

---

## Repository Structure

第一版创建以下文件和目录：

```text
.
├── app/
│   ├── main.py                 # FastAPI 应用入口和静态页面挂载
│   ├── config.py               # 环境变量和运行配置
│   ├── db.py                   # SQLite 连接、建表和初始化
│   ├── schemas.py              # API 请求/响应模型
│   ├── repositories.py         # 设备、告警、知识、工单查询和写入
│   ├── rules.py                # 阈值、故障等级和升级规则
│   ├── retrieval.py            # FTS5 知识检索和引用构造
│   ├── llm.py                  # OpenAI-compatible LLM 适配器与本地回退
│   ├── copilot.py              # 诊断 Agent 工作流编排
│   ├── routes.py               # REST API 路由
│   └── static/
│       ├── index.html          # 单页应用结构
│       ├── app.js              # 页面交互和 API 调用
│       └── styles.css          # 视觉样式
├── data/
│   ├── seed.py                 # 可重复执行的演示数据种子
│   └── knowledge/              # 演示版说明书、故障码和 SOP Markdown
├── evals/
│   ├── cases.json              # 30 条首版评测案例
│   ├── run_eval.py             # 评测执行脚本
│   └── README.md               # 指标口径和人工复核说明
├── tests/
│   ├── test_rules.py
│   ├── test_retrieval.py
│   ├── test_copilot.py
│   └── test_api.py
├── .env.example
├── .gitignore
├── README.md
├── requirements.txt
└── pyproject.toml
```

## Task 1: Repository Scaffold and Safe Configuration

**Files:**
- Create: `requirements.txt`
- Create: `pyproject.toml`
- Create: `.env.example`
- Create: `.gitignore`
- Create: `README.md`
- Create: `app/__init__.py`
- Create: `app/config.py`
- Test: `tests/test_config.py`

**Interfaces:**
- Produces `app.config.Settings` with `app_name`, `database_path`, `llm_api_key`, `llm_base_url`, `llm_model`, and `llm_enabled` fields.

- [ ] **Step 1: Write the failing configuration test**

```python
from app.config import Settings


def test_settings_disable_llm_without_api_key(monkeypatch):
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    settings = Settings()
    assert settings.llm_enabled is False
    assert settings.database_path.endswith("data/app.db")
```

- [ ] **Step 2: Run the focused test and verify it fails**

Run: `python -m pytest tests/test_config.py -q`

Expected: FAIL because `app.config.Settings` does not exist.

- [ ] **Step 3: Implement configuration and repository metadata**

`Settings` reads only environment variables, defaults the database to `data/app.db`, and treats a missing or blank `LLM_API_KEY` as disabled. `.env.example` contains placeholder values only. `README.md` explains that the project is a simulated portfolio MVP and includes the local run command.

- [ ] **Step 4: Run the focused test and verify it passes**

Run: `python -m pytest tests/test_config.py -q`

Expected: PASS.

## Task 2: SQLite Schema and Synthetic Domain Data

**Files:**
- Create: `app/db.py`
- Create: `app/schemas.py`
- Create: `data/seed.py`
- Create: `data/knowledge/device-manual.md`
- Create: `data/knowledge/fault-codes.md`
- Create: `data/knowledge/service-sop.md`
- Create: `data/knowledge/safety-guide.md`
- Test: `tests/test_db.py`

**Interfaces:**
- `app.db.init_db(path: str) -> None`
- `app.db.get_connection(path: str) -> sqlite3.Connection`
- `data.seed.seed_database(path: str) -> None`
- Tables: `devices`, `device_readings`, `alerts`, `fault_codes`, `tickets`, `knowledge_documents`, `knowledge_chunks`.

- [ ] **Step 1: Write tests for schema and repeatable seed data**

```python
from app.db import get_connection, init_db
from data.seed import seed_database


def test_seed_creates_repeatable_demo_data(tmp_path):
    database = tmp_path / "app.db"
    init_db(str(database))
    seed_database(str(database))
    first = get_connection(str(database)).execute(
        "SELECT COUNT(*) FROM devices"
    ).fetchone()[0]
    seed_database(str(database))
    second = get_connection(str(database)).execute(
        "SELECT COUNT(*) FROM devices"
    ).fetchone()[0]
    assert first >= 6
    assert second == first
```

- [ ] **Step 2: Run the focused test and verify it fails**

Run: `python -m pytest tests/test_db.py -q`

Expected: FAIL because database initialization and seed functions do not exist.

- [ ] **Step 3: Implement schema and synthetic fixtures**

Create at least six devices across three stores, readings covering normal and abnormal temperatures, offline periods, at least six fault codes, ten tickets in different statuses, and four knowledge documents. Add `source_name`, `source_section`, and `is_demo_data` metadata to knowledge chunks so citations are visibly traceable.

- [ ] **Step 4: Run the focused test and verify it passes**

Run: `python -m pytest tests/test_db.py -q`

Expected: PASS.

## Task 3: Repository Queries and Deterministic Rules

**Files:**
- Modify: `app/repositories.py`
- Modify: `app/rules.py`
- Test: `tests/test_rules.py`
- Test: `tests/test_repositories.py`

**Interfaces:**
- `list_devices(status: str | None = None) -> list[dict]`
- `get_device_status(device_id: str) -> dict | None`
- `get_device_alerts(device_id: str, limit: int = 10) -> list[dict]`
- `get_fault_code(fault_code: str) -> dict | None`
- `find_similar_tickets(device_id: str, symptom: str, limit: int = 5) -> list[dict]`
- `create_ticket_draft(payload: dict) -> dict`
- `calculate_risk(device: dict, alerts: list[dict], fault: dict | None) -> dict`

- [ ] **Step 1: Write failing tests for rule boundaries and repository outputs**

```python
from app.rules import calculate_risk


def test_repeated_high_temperature_is_high_risk():
    result = calculate_risk(
        {"device_id": "DEV-001", "online": True},
        [{"type": "temperature", "value": 12.5, "severity": "high"}] * 3,
        {"fault_code": "E03", "severity": "high"},
    )
    assert result["level"] == "high"
    assert result["requires_human_review"] is True
```

- [ ] **Step 2: Run tests and verify they fail**

Run: `python -m pytest tests/test_rules.py tests/test_repositories.py -q`

Expected: FAIL because repository functions and rules are not implemented.

- [ ] **Step 3: Implement query functions and rules**

Rules must distinguish `low`, `medium`, and `high`; mark high severity, repeated alerts, stale readings, and prolonged offline states for human review. All calculated facts must be returned with timestamps or source fields where available.

- [ ] **Step 4: Run tests and verify they pass**

Run: `python -m pytest tests/test_rules.py tests/test_repositories.py -q`

Expected: PASS.

## Task 4: Knowledge Retrieval and Citation Grounding

**Files:**
- Create: `app/retrieval.py`
- Test: `tests/test_retrieval.py`

**Interfaces:**
- `index_knowledge_documents(database_path: str, directory: str) -> int`
- `search_service_knowledge(query: str, limit: int = 5) -> list[dict]`
- Each result contains `chunk_id`, `content`, `source_name`, `source_section`, and `score`.

- [ ] **Step 1: Write failing tests for relevant retrieval and no-evidence behavior**

```python
from app.retrieval import search_service_knowledge


def test_fault_code_query_returns_source_metadata(seed_db):
    results = search_service_knowledge("E03 温度传感器", limit=3)
    assert results
    assert results[0]["source_name"]
    assert results[0]["source_section"]


def test_unknown_query_returns_empty_or_low_confidence_results():
    results = search_service_knowledge("不存在的紫色推进器", limit=3)
    assert all(item["score"] < 0.5 for item in results)
```

- [ ] **Step 2: Run tests and verify they fail**

Run: `python -m pytest tests/test_retrieval.py -q`

Expected: FAIL because the FTS5 index and retrieval function do not exist.

- [ ] **Step 3: Implement FTS5 indexing and retrieval**

Split Markdown documents by headings and paragraphs, preserve source metadata, normalize Chinese and English search terms, and return a score. Retrieval must not fabricate a source for an empty result.

- [ ] **Step 4: Run tests and verify they pass**

Run: `python -m pytest tests/test_retrieval.py -q`

Expected: PASS.

## Task 5: LLM Adapter and Copilot Workflow

**Files:**
- Create: `app/llm.py`
- Create: `app/copilot.py`
- Test: `tests/test_copilot.py`

**Interfaces:**
- `class LLMClient: generate_json(system_prompt: str, user_prompt: str, schema: dict) -> dict`
- `class LocalFallbackLLM(LLMClient)`
- `class OpenAICompatibleLLM(LLMClient)`
- `diagnose_issue(device_id: str, user_message: str) -> dict`
- `generate_ticket_draft(diagnosis: dict) -> dict`

- [ ] **Step 1: Write failing tests for the complete deterministic workflow**

```python
from app.copilot import diagnose_issue


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
```

- [ ] **Step 2: Run the focused test and verify it fails**

Run: `python -m pytest tests/test_copilot.py -q`

Expected: FAIL because the workflow and LLM adapters do not exist.

- [ ] **Step 3: Implement provider-neutral orchestration**

The workflow must call device status, alerts, fault-code lookup, similar-ticket lookup, knowledge retrieval, and risk rules in a visible sequence. `OpenAICompatibleLLM` is optional and reads configuration only from `Settings`; `LocalFallbackLLM` creates a structured response from retrieved facts and templates. The output must separate confirmed facts, inference, recommendations, sources, missing information, and human review requirements.

- [ ] **Step 4: Run the focused test and verify it passes**

Run: `python -m pytest tests/test_copilot.py -q`

Expected: PASS without an API key.

## Task 6: FastAPI API Surface

**Files:**
- Create: `app/routes.py`
- Create: `app/main.py`
- Test: `tests/test_api.py`

**Interfaces:**
- `GET /api/health`
- `GET /api/devices`
- `GET /api/devices/{device_id}`
- `GET /api/devices/{device_id}/alerts`
- `POST /api/diagnose`
- `POST /api/tickets/draft`
- `GET /api/tickets`
- `GET /api/dashboard/summary`

- [ ] **Step 1: Write failing API tests**

```python
def test_diagnose_endpoint_returns_structured_result(client):
    response = client.post(
        "/api/diagnose",
        json={"device_id": "DEV-001", "message": "故障码 E03 怎么处理？"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["risk"]["level"]
    assert payload["sources"]
```

- [ ] **Step 2: Run API tests and verify they fail**

Run: `python -m pytest tests/test_api.py -q`

Expected: FAIL because the FastAPI app and routes do not exist.

- [ ] **Step 3: Implement routes, validation, and error responses**

Use Pydantic request models. Unknown devices return `404`; invalid empty messages return `422`; model/tool failures return a structured `503` only when no local fallback is possible. Initialize the demo database on startup and mount `app/static` at `/`.

- [ ] **Step 4: Run API tests and verify they pass**

Run: `python -m pytest tests/test_api.py -q`

Expected: PASS.

## Task 7: Portfolio-Quality Frontend

**Files:**
- Create: `app/static/index.html`
- Create: `app/static/app.js`
- Create: `app/static/styles.css`
- Modify: `README.md`

**Interfaces:**
- The frontend consumes only the routes defined in Task 6.
- Main views: device overview, diagnosis workspace, evidence panel, ticket draft panel, risk summary.

- [ ] **Step 1: Implement the static page structure**

Create a responsive two-column workspace with a device list on the left, diagnosis conversation in the center, and evidence/ticket details on the right. Provide clear labels for “模拟数据”, “AI 建议”, “事实依据”, and “需人工确认”.

- [ ] **Step 2: Implement API-backed interactions**

Load devices and summary on startup; selecting a device loads status and alerts; submitting a question calls `/api/diagnose`; clicking “生成工单草稿” calls `/api/tickets/draft`; no action may silently submit a ticket.

- [ ] **Step 3: Add empty, loading, error, and no-evidence states**

The UI must show a useful message for unknown devices, empty evidence, API errors, and high-risk review blocks. Do not display fabricated confidence percentages.

- [ ] **Step 4: Run the app manually and verify the five-minute demo path**

Run: `python -m uvicorn app.main:app --reload`

Verify: select `DEV-001` → view abnormal status → ask about `E03` → inspect sources → generate ticket draft → see human confirmation warning → view dashboard summary.

## Task 8: Evaluation, Documentation, and GitHub Readiness

**Files:**
- Create: `evals/cases.json`
- Create: `evals/run_eval.py`
- Create: `evals/README.md`
- Modify: `README.md`
- Modify: `.gitignore`
- Test: `tests/test_eval.py`

**Interfaces:**
- `evals/run_eval.py` reads `evals/cases.json` and prints JSON summary with `case_count`, `citation_hit_rate`, `required_review_recall`, and `ticket_field_completeness`.

- [ ] **Step 1: Write failing evaluation test**

```python
def test_eval_cases_cover_unknown_and_high_risk_scenarios():
    import json
    from pathlib import Path

    cases = json.loads(Path("evals/cases.json").read_text(encoding="utf-8"))
    assert len(cases) >= 30
    assert any(case["expected"]["requires_human_review"] for case in cases)
    assert any(case["expected"]["should_acknowledge_missing_evidence"] for case in cases)
```

- [ ] **Step 2: Run the focused test and verify it fails**

Run: `python -m pytest tests/test_eval.py -q`

Expected: FAIL because the evaluation set does not exist.

- [ ] **Step 3: Add evaluation cases, runner, and GitHub documentation**

Create at least 30 cases covering normal diagnosis, ambiguous descriptions, unknown codes, stale data, conflicting documents, missing evidence, repeated alerts, and high-risk conditions. README must include setup, local run, optional LLM configuration, architecture, screenshots placeholder section, limitations, simulated-data disclaimer, and a roadmap. `.gitignore` must exclude `.env`, `data/app.db`, caches, and local output files.

- [ ] **Step 4: Run the evaluation and full test suite**

Run: `python evals/run_eval.py`

Expected: JSON summary printed without secrets.

Run: `python -m pytest -q`

Expected: all tests pass.

## Final Verification Checklist (Completed)

- [x] Run `python -m pytest -q`.
- [x] Run `python evals/run_eval.py` and save the summary in the portfolio notes.
- [x] Start `python -m uvicorn app.main:app --reload` and complete the five-minute demo path.
- [x] Confirm `.env`, database files, personal data, and API keys are ignored.
- [x] Confirm every AI conclusion displays facts, sources, missing evidence, and human-review state where applicable.
- [x] Confirm README accurately labels all data and results as simulated.
- [x] Capture screenshots or a short demo recording for the GitHub README.
