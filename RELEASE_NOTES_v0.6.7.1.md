# Release Notes - v0.6.7.1

**Release Date:** September 22, 2026  
**Build Target:** `dev-vm` (`10.42.42.54`), GitHub Actions & Cloudflare Edge  
**Git Branch:** `main`  
**Tracking Issue:** [Issue #421](https://github.com/KoshiirRa/midgley/issues/421)

---

## 🚀 Overview & Release Highlights

Midgley **v0.6.7.1** is a targeted infrastructure hotfix release that transitions the Vectorize Hindsight episodic agent memory engine from self-managed Google Cloud Run scale-to-zero containers to **Vectorize Hindsight-Hosted SaaS** (`https://api.hindsight.vectorize.io`, bank `Midgley`). 

This hotfix eliminates unexpected serverless compute billing overruns (~$17.14–$35.66/month in GCP Cloud Run charges) and replaces 75-second cold-start initialization delays with an always-warm, token-efficient SaaS architecture (~$3.50/month operating cost).

---

### 1. Vectorize Hindsight-Hosted SaaS Migration ([`src/hindsight_client.py`](src/hindsight_client.py) - Issue #421)
- **Hosted Cloud Endpoint:** Migrated the primary episodic memory engine to `https://api.hindsight.vectorize.io` with Bearer token authentication.
- **Dynamic Bank Configuration:** Upgraded `HindsightClient` to dynamically resolve target bank IDs from `HINDSIGHT_BANK_ID` (defaulting to `Midgley`).
- **Telemetry & Stats Parser:** Updated `HindsightClient.get_bank_stats()` to dynamically parse `total_nodes`, `total_documents`, `total_observations`, and `fact_count` from remote `/v1/default/banks/{bank_id}/stats` endpoints.
- **Zero Cold-Start Latency:** Eliminates container boot handshakes and timeout retries across daily forecasting and Saturday weekly review executions.

---

### 2. CI/CD Pipeline & Workflow Secret Hardening ([`.github/workflows/*.yml`](.github/workflows/))
- **Daily Forecasting Pipeline:** Updated [`.github/workflows/gas_price_forecast.yml`](.github/workflows/gas_price_forecast.yml) to pass `HINDSIGHT_API_KEY` and `HINDSIGHT_BANK_ID: "Midgley"` into the execution step.
- **Weekly Model Review Pipeline:** Updated [`.github/workflows/weekly_model_review.yml`](.github/workflows/weekly_model_review.yml) to pass `HINDSIGHT_API_KEY` and `HINDSIGHT_BANK_ID: "Midgley"` into the review step.
- **Fail-Safe Offline Continuity:** Retains seamless failover to local SQLite FTS5 store (`data/agent_memory.sqlite`) whenever remote network calls are unavailable or suppressed under `TESTING=1`.

---

### 3. Automated Verification & Test Coverage
- Executed unit and integration test suites:
  - `tests/test_agent_memory.py` (9/9 tests passing)
  - `tests/test_memory_telemetry_sync.py` (4/4 tests passing)
- Verified Retain, Recall, and Reflect operations against live hosted bank `Midgley`.
