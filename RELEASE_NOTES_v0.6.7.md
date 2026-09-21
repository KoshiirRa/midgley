# Release Notes - v0.6.7

**Release Date:** September 21, 2026  
**Build Target:** `dev-vm` (`10.42.42.54`), GitHub Actions & Cloudflare Edge  
**Git Branch:** `dev` / `main`  
**Tracking Issue:** [Issue #324](https://github.com/KoshiirRa/midgley/issues/324)

---

## 🚀 Overview & Release Highlights

Midgley **v0.6.7** resolves episodic memory state persistence on ephemeral CI/CD runners, introduces a lightweight `--dashboard-only` regeneration mode in `run_all.py`, and wires automated post-review dashboard compilation into the Saturday weekly review workflow to guarantee that synthesized qualitative reflections and memory inventories are rendered live on GitHub Pages.

---

### 1. Persistent CI Runner Memory Caching (`.github/workflows/*.yml` - Issue #324)
- Added `data/agent_memory.sqlite` to `actions/cache` across both primary workflow pipelines:
  - **Weekly Model Review Pipeline:** [`.github/workflows/weekly_model_review.yml`](.github/workflows/weekly_model_review.yml)
  - **Daily Forecasting Pipeline:** [`.github/workflows/gas_price_forecast.yml`](.github/workflows/gas_price_forecast.yml)
- Prevents database resets on ephemeral GitHub Actions runners, preserving historical experience shocks ($|\text{error}| \ge \$0.25/\text{gal}$) and synthesized reflections across daily and weekly automated executions.

---

### 2. Fast Dashboard Regeneration Mode (`run_all.py`)
- Implemented the `--dashboard-only` CLI flag in [`run_all.py`](run_all.py):
  - Skips individual regional model training pipelines and long backtest loops.
  - Updates live README forecast tables ([`src/readme_updater.py`](src/readme_updater.py)).
  - Compiles the entire public web application under `docs/` ([`src/dashboard_generator.py`](src/dashboard_generator.py)).
  - Synchronizes static REST API endpoints under `docs/api/v1/` ([`src/static_api_exporter.py`](src/static_api_exporter.py)).
- Enables rapid UI and telemetry refreshes in < 15 seconds.

---

### 3. Post-Review Dashboard Compilation Step (`.github/workflows/weekly_model_review.yml`)
- Added a dedicated `Regenerate Public Dashboard with Updated Reflections` step to the Saturday weekly review workflow immediately following `python -m src.weekly_issue_reporter`.
- Ensures newly synthesized qualitative anomaly post-mortems and mental models are baked directly into [`docs/telemetry.html`](docs/telemetry.html) prior to `git-auto-commit` and GitHub Pages deployment.

---

### 4. Multi-Tier Memory Resilience & Hindsight Integration
- Preserves the 3-tier memory execution hierarchy:
  1. **Tier 1 (Remote Cloud):** Vectorize Hindsight on Google Cloud Run backed by Supabase `pgvector` (`midgley-gas-forecasting`).
  2. **Tier 2 (Cloud LLM):** Gemini 2.5 Flash qualitative post-mortem synthesis.
  3. **Tier 3 (Zero-Cost Offline):** Deterministic rule-based reflection engine + Local SQLite FTS5 store.
- Gracefully handles cold-start timeouts and unconfigured cloud credentials by maintaining unbroken continuity via cached SQLite stores.

---

### 5. Automated Verification & Test Coverage
- Executed unit and integration test suites:
  - `tests/test_agent_memory.py` (9/9 tests passing)
  - `tests/test_memory_telemetry_sync.py` (4/4 tests passing)
- Verified `python run_all.py --dashboard-only` execution locally and on `dev-vm` (`10.42.42.54`).
