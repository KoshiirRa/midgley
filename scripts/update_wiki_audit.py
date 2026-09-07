"""
Update Wiki Documentation for Milestone 10 Audit Sprint
(Issues #97 ArchiveBox, #98 Healthchecks, #187 AI Radar, #188 Sapient PRAXIST)
"""

import os
import sys

def update_wiki(wiki_dir: str):
    if not os.path.exists(wiki_dir):
        print(f"Wiki directory '{wiki_dir}' does not exist.")
        return

    # 1. Update Agent-Architecture.md
    aa_path = os.path.join(wiki_dir, "Agent-Architecture.md")
    if os.path.exists(aa_path):
        with open(aa_path, "r", encoding="utf-8") as f:
            aa_text = f.read()

        archive_snippet = "* **Self-Hosted ArchiveBox Client (`src/archive_service.py`, Issue #97):** Dispatches asynchronous web page snapshot captures to self-hosted ArchiveBox instances (`POST /api/v1/core/add/`) via non-blocking thread pools, with local markdown snapshot fallback (`data/archived_events_ledger.json` + `data/archives/`).\n"
        if "src/archive_service.py" not in aa_text:
            aa_text = aa_text.replace("---\n\n## 2.", archive_snippet + "\n---\n\n## 2.")

        agent7_snippet = """* **Healthchecks.io Pipeline Heartbeats (`src/healthcheck_monitor.py`, Issue #98):** Dispatches start, success, duration, and failure pings to dead-man's snitch endpoints across daily forecasting and Saturday review runs.
* **Open Source AI Radar Model Discovery (`src/data_ingestion.py`, Issue #187):** Ingests open-weights LLM/SLM releases, quantization benchmarks, and capability metrics via `GET /api/v1/system/radar`.
* **Sapient PRAXIST Research Harness (`src/praxist_engine.py`, Issue #188):** Programmatic research harness for formulating, backtesting, and statistically validating empirical feature hypotheses ($p < 0.05$).
"""
        if "src/healthcheck_monitor.py" not in aa_text:
            target_7 = "## 8. Public Web Dashboard"
            aa_text = aa_text.replace(target_7, agent7_snippet + "\n---\n\n" + target_7)

        with open(aa_path, "w", encoding="utf-8") as f:
            f.write(aa_text)
        print("Updated Agent-Architecture.md in wiki")

    # 2. Update Data-Ingestion-and-APIs.md
    dia_path = os.path.join(wiki_dir, "Data-Ingestion-and-APIs.md")
    if os.path.exists(dia_path):
        with open(dia_path, "r", encoding="utf-8") as f:
            dia_text = f.read()

        dia_addition = """

---

## 31. Open Source AI Radar REST API & Model Capability Ingestion (`src/data_ingestion.py`, Issue #187)
* **Module:** `OpenSourceAIRadarConnector` | **REST API:** `GET /api/v1/system/radar`
* **API Providers:** Open Source AI Radar REST endpoints (`api.opensourceai.io/v1/radar/models`).
* **Ingested Features:** Open-weights LLMs/SLMs, parameter sizes (`7B`, `70B`, etc.), quantization profiles (`Q4_K_M`, `FP8`, `AWQ`), benchmark scores, and licenses.
* **Caching & Resilience:** 24-hour disk cache (`data/radar_cache.json`) with deterministic fallback model registry.

---

## 32. Self-Hosted ArchiveBox Historical Article Preservation Engine (`src/archive_service.py`, Issue #97)
* **Module:** `ArchiveBoxClient` in `src/archive_service.py`
* **Primary Role:** Submits qualitative news, OPEC bulletins, and refinery outage URLs to self-hosted ArchiveBox instances (`POST /api/v1/core/add/`) asynchronously via background thread pools.
* **Dual-Tier Snapshot Ledger:** If ArchiveBox instance is unreachable or disabled, saves local markdown snapshots to `data/archives/` and records entries in `data/archived_events_ledger.json`.

---

## 33. Healthchecks.io Pipeline Heartbeat & Dead-Man's Snitch Monitoring (`src/healthcheck_monitor.py`, Issue #98)
* **Module:** `HealthcheckMonitor` in `src/healthcheck_monitor.py`
* **Dispatch Endpoints:** Supports `/start`, `/0` (or `POST /` with execution logs/duration), and `/fail`.
* **Integrated Workflows:** Daily 02:00 AM Central forecast runs (`src/prediction_logger.py`) and Saturday 08:00 AM Central weekly review audits (`src/weekly_issue_reporter.py`).

---

## 34. Sapient PRAXIST Autonomous Energy Research Engine (`src/praxist_engine.py`, Issue #188)
* **Module:** `PraxistResearchHarness` in `src/praxist_engine.py`
* **Primary Role:** Programmatic evaluation harness enabling LLM agents to formulate empirical feature engineering hypotheses, run out-of-sample backtests, compute paired $t$-tests and $p$-values, and execute parameter sweeps (Ridge $\\alpha$, decay half-life $t_{1/2}$).
"""
        if "## 31. Open Source AI Radar" not in dia_text:
            dia_text += dia_addition
            with open(dia_path, "w", encoding="utf-8") as f:
                f.write(dia_text)
            print("Updated Data-Ingestion-and-APIs.md in wiki")

    # 3. Update MLOps-and-Continuous-Feedback.md
    mlops_path = os.path.join(wiki_dir, "MLOps-and-Continuous-Feedback.md")
    if os.path.exists(mlops_path):
        with open(mlops_path, "r", encoding="utf-8") as f:
            mlops_text = f.read()

        mlops_addition = """

---

## 9. Healthchecks.io Pipeline Heartbeats & Dead-Man's Snitch Monitoring (Issue #98)
* **Module:** `src/healthcheck_monitor.py`
* **Primary Role:** Monitors scheduled daily forecasting and Saturday weekly review executions, dispatching `/start`, `/0` (with execution duration/logs), and `/fail` pings to Healthchecks.io endpoints.

---

## 10. Open Source AI Radar Automated Model Discovery (Issue #187)
* **Module:** `src/data_ingestion.py` & `src/api_server.py`
* **Primary Role:** Ingests state-of-the-art open-weights LLMs/SLMs and benchmark capability scores via `GET /api/v1/system/radar` and embeds capability tracking sections in Saturday weekly review issues.

---

## 11. Sapient PRAXIST Autonomous Energy Research Engine (Issue #188)
* **Module:** `src/praxist_engine.py`
* **Primary Role:** Enables autonomous formulation, backtesting, and statistical validation of empirical feature hypotheses ($p < 0.05$) and hyperparameter sweeps, synthesizing research findings into Saturday weekly model reviews.
"""
        if "## 9. Healthchecks.io Pipeline Heartbeats" not in mlops_text:
            mlops_text += mlops_addition
            with open(mlops_path, "w", encoding="utf-8") as f:
                f.write(mlops_text)
            print("Updated MLOps-and-Continuous-Feedback.md in wiki")

    # 4. Update Project-History-and-Roadmap.md
    road_path = os.path.join(wiki_dir, "Project-History-and-Roadmap.md")
    if os.path.exists(road_path):
        with open(road_path, "r", encoding="utf-8") as f:
            road_text = f.read()

        phase10 = """
### Phase 10: System Release v0.5.0 — Milestone 10: Weekly Review v1.0 "Audit" (#97, #98, #187, #188 - Current)
* **Healthchecks.io Pipeline Heartbeat Monitoring (Issue #98):** Built `HealthcheckMonitor` (`src/healthcheck_monitor.py`) with start, success, duration, and failure pings integrated into daily forecasting and Saturday weekly review workflows.
* **Open Source AI Radar Model Discovery (Issue #187):** Built `OpenSourceAIRadarConnector` (`src/data_ingestion.py`), `GET /api/v1/system/radar` (`src/api_server.py`), and automated model capability tracking in Saturday review reports.
* **Self-Hosted ArchiveBox Historical Article Preservation (Issue #97):** Built `ArchiveBoxClient` (`src/archive_service.py`) with asynchronous thread pool dispatch, local markdown snapshot ledger fallback (`data/archived_events_ledger.json` + `data/archives/`), and zero-latency event scoring hooks.
* **Sapient PRAXIST Autonomous Energy Research Engine (Issue #188):** Built `PraxistResearchHarness` (`src/praxist_engine.py`) with programmatic hypothesis testing, statistical $t$-test scoring, multi-parameter sweeps, and automated weekly review research sections.
* **Milestone 10 Completion:** 100% of all 21 component issues closed.
"""
        if "Phase 10: System Release v0.5.0" not in road_text:
            target_road = "## 🎯 Future Development & Long-Term Roadmap"
            road_text = road_text.replace(target_road, phase10 + "\n\n" + target_road)
            with open(road_path, "w", encoding="utf-8") as f:
                f.write(road_text)
            print("Updated Project-History-and-Roadmap.md in wiki")

    # 5. Update Home.md
    home_path = os.path.join(wiki_dir, "Home.md")
    if os.path.exists(home_path):
        with open(home_path, "r", encoding="utf-8") as f:
            home_text = f.read()

        home_text = home_text.replace("v0.4.2", "v0.5.0").replace("v0.4.1", "v0.5.0").replace("v0.4.0", "v0.5.0")
        with open(home_path, "w", encoding="utf-8") as f:
            f.write(home_text)
        print("Updated Home.md in wiki")

    # 6. Update Self-Hosting.md
    sh_path = os.path.join(wiki_dir, "Self-Hosting.md")
    if os.path.exists(sh_path):
        with open(sh_path, "r", encoding="utf-8") as f:
            sh_text = f.read()

        if "HEALTHCHECKS_PING_URL" not in sh_text:
            sh_env_addition = """
# Healthchecks Cron & Execution Heartbeat Monitoring (healthchecks.io, Issue #98)
HEALTHCHECKS_PING_URL="https://hc-ping.com/12ab7587-e0ed-40ac-83ad-822f9eb56a3b"

# Self-Hosted ArchiveBox Historical Preservation Server (github.com/ArchiveBox/ArchiveBox, Issue #97)
ARCHIVEBOX_URL="http://10.42.42.54:8000"
ARCHIVEBOX_API_KEY=""
"""
            sh_text = sh_text.replace('EDGAR_8K_TICKERS="PBF,DINO,MPC,VLO,PSX"', 'EDGAR_8K_TICKERS="PBF,DINO,MPC,VLO,PSX"' + sh_env_addition)
            with open(sh_path, "w", encoding="utf-8") as f:
                f.write(sh_text)
            print("Updated Self-Hosting.md in wiki")

if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "/home/marty/projects/midgley_wiki"
    update_wiki(target)
