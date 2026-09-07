# Midgley Release Notes

## 🚀 Release v0.5.0 — Milestone 10: Weekly Review v1.0 \ Audit\ (In-Progress)

**Target Branch:** \dev\ $\\rightarrow$ \main\  
**Milestone:** [Weekly Review v1.0 \Audit\](https://github.com/KoshiirRa/midgley/milestone/10) (**21/21 issues completed, 100%**)

---

### 🌟 Executive Summary

Release \0.5.0\ completes the **Weekly Review v1.0 \Audit\** milestone, delivering automated pipeline heartbeat observability, self-hosted web archive preservation, open-weights LLM capability tracking, and autonomous programmatic energy research evaluation.

---

### 📦 Key Features & Component Upgrades

#### 1. ⏱️ Healthchecks.io Pipeline Heartbeat & Dead-Man's Snitch Monitoring (Issue #98)
* **Module:** [\src/healthcheck_monitor.py\](src/healthcheck_monitor.py)
* **Description:** Integrates Healthchecks.io heartbeat monitoring across daily forecasting (\src/prediction_logger.py\) and Saturday weekly review audits (\src/weekly_issue_reporter.py\).
* **Heartbeat Lifecycle:** Dispatches \/start\ on execution begin, \/0\ or \POST /\ on success with execution duration and logs in the payload, and \/fail\ on uncaught errors.
* **Workflows:** Supported in \.github/workflows/gas_price_forecast.yml\ and \.github/workflows/weekly_model_review.yml\.
* **Resiliency:** 100% fail-open, 10s timeout, isolated during test suites (\TESTING=1\).

#### 2. 📡 Open Source AI Radar Automated Model Discovery & Benchmarks (Issue #187)
* **Module:** \OpenSourceAIRadarConnector\ in [\src/data_ingestion.py\](src/data_ingestion.py)
* **REST API:** \GET /api/v1/system/radar\ in [\src/api_server.py\](src/api_server.py)
* **Description:** Monitors live releases of open-weights LLMs/SLMs, parameter sizes, licenses, quantization benchmarks, and capability metrics from Open Source AI Radar REST endpoints.
* **Caching & Reporting:** 24-hour disk cache (\data/radar_cache.json\) and automated model discovery tables in Saturday weekly model review reports.

#### 3. 🗄️ Self-Hosted ArchiveBox Historical News Preservation & Snapshot Ledger (Issue #97)
* **Module:** \ArchiveBoxClient\ in [\src/archive_service.py\](src/archive_service.py)
* **Description:** Submits qualitative news and event URLs to self-hosted ArchiveBox instances (\POST /api/v1/core/add/\) asynchronously via background thread pools.
* **Fallback Ledger:** Falls back seamlessly to local markdown snapshots in \data/archives/\ and ledger tracking in \data/archived_events_ledger.json\.
* **Zero Overhead:** Integrated into \xtract_event_features_from_url()\ in [\src/event_analyzer.py\](src/event_analyzer.py) with 0ms latency impact on LLM scoring.

#### 4. 🧠 Sapient PRAXIST Autonomous Energy Research Engine (Issue #188)
* **Module:** \PraxistResearchHarness\ in [\src/praxist_engine.py\](src/praxist_engine.py)
* **Description:** Programmatic research harness enabling LLM agents to formulate empirical feature engineering hypotheses, run out-of-sample backtests, compute paired \\$-tests and \\$-values, and execute parameter sweeps (Ridge \$\\alpha\$, decay half-life \{1/2}\$).
* **Weekly Integration:** Research findings and factor candidate validation tables are formatted into Saturday weekly review issues (\src/weekly_issue_reporter.py\).

---

### 📡 New & Updated API Endpoints

| Endpoint | Method | Description |
| :--- | :---: | :--- |
| \/api/v1/system/radar\ | \GET\ | Open Source AI Radar model discovery, benchmarks, and capabilities |
| \/api/v1/forecast/scoreboard\ | \GET\ | Rolling 30/60/90-day MAE, RMSE, Directional Hit Rate, and Model Uplift |
| \/api/v1/forecast/cloud-status\ | \GET\ | Relational cloud database sync status and record counts |
| \/api/v1/forecast/cloud-sync\ | \POST\ | Triggers manual prediction history sync to Turso / D1 / Postgres |

---

### 🧪 Test Suite & Validation Summary

* **New Sprint Unit Tests:**
  - \	ests/test_healthcheck_monitor.py\ (10 passed)
  - \	ests/test_open_source_ai_radar.py\ (6 passed)
  - \	ests/test_archive_service.py\ (4 passed)
  - \	ests/test_praxist_research.py\ (7 passed)
* **Full Codebase Regression Suite:** **446 passed, 3 skipped, 0 failures** in \214.39s\ on Ubuntu 26.04 LTS (\dev-vm\).

---

### 📚 Documentation & Guides Updated

* [\AGENTS.md\](AGENTS.md) — Multi-agent specifications for Healthchecks, AI Radar, ArchiveBox, and PRAXIST.
* [\README.md\](README.md) — Key Features #24–#27 added.
* [\SELF_HOSTING.md\](SELF_HOSTING.md) & [\docs/SELF_HOSTING.md\](docs/SELF_HOSTING.md) — Environment variables and setup instructions.
* [\docs/API.md\](docs/API.md) — REST endpoint schemas.
* [\docs/ARCHITECTURE.md\](docs/ARCHITECTURE.md) — Sections 12–15 technical specifications.
* **GitHub Wiki (\KoshiirRa/midgley.wiki\)** — Synchronized across all corresponding wiki topics.
