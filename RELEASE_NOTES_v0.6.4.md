# Release Notes - v0.6.4

**Release Date:** September 17, 2026  
**Build Target:** `dev-vm` (`10.42.42.54`) & Cloudflare Edge  
**Git Branch:** `dev`  

---

## 🚀 Overview & Release Highlights

Midgley **v0.6.4** introduces key edge infrastructure observability, multi-tier connectivity diagnostics, unified cloud batch synchronization, dynamic model version decoupling, and Headline Arena energy benchmark integration:

1. **Active Multi-Tier Edge Cache Connectivity Probing & URL Scheme Normalization ([Issue #301](https://github.com/KoshiirRa/midgley/issues/301)):**
   - Implemented active multi-tier connectivity probing methods (`test_edge_connectivity()`) in [`src/lookup_cache.py`](src/lookup_cache.py) testing Turso Edge SQLite and Cloudflare D1/Worker gateways.
   - Added automated URL normalization for `turso://` and `libsql://` schemes to `https://` for HTTP REST `/v2/pipeline` compatibility.
   - Added CLI diagnostic flags (`python3 -m src.lookup_cache --ping`, `--test-turso`, `--test-cloudflare`, `--test-all`, `--stats`).
   - Exposed live probe diagnostics via REST API endpoint `GET /api/v1/system/cache-status?probe=true`.

2. **Cloudflare D1 Batch Prediction Synchronization & Schema Migration ([Issue #302](https://github.com/KoshiirRa/midgley/issues/302)):**
   - Added dedicated `POST /api/v1/sync/predictions` batch route in [`workers/cache_worker.ts`](workers/cache_worker.ts) executing atomic `env.DB.batch()` statements with automated table provisioning.
   - Reconciled `POST /api/v1/cache` and `DELETE /api/v1/cache` routes in edge worker gateway.
   - Provisioned standalone D1 database schema migration script [`scripts/init_d1_schema.sql`](scripts/init_d1_schema.sql).
   - Enhanced [`src/prediction_logger.py`](src/prediction_logger.py) with HTTP error response body extraction and decoding on non-200 responses to streamline debugging.

3. **Dynamic Regional Model Version Tagging & Decoupling ([Issue #303](https://github.com/KoshiirRa/midgley/issues/303)):**
   - Eliminated brittle hardcoded `v1.4` and `v1.5` strings across all 8 regional runner modules (`tulsa`, `newark`, `cincinnati`, `greenville`, `charlotte`, `oakland`, `port_st_lucie`, `national`), `src/dynamic_region.py`, `src/intraday_event_monitor.py`, `src/readme_updater.py`, and `src/api_server.py`.
   - Introduced [`resolve_model_tag(region, model_type)`](src/prediction_logger.py) dynamically binding to [`src.version.get_model_version()`](src/version.py) (e.g. `v1.6-Ipatieff-TulsaOK-Ridge`).

4. **Model Iteration Lineage Matrix & Comparison Table ([Issue #304](https://github.com/KoshiirRa/midgley/issues/304)):**
   - Added missing historical lineage entries for `v1.4 Finlight-LLM` and `v1.5 Multi-Tier & Sensor MLOps` to the Model Iteration table in [`src/dashboard_generator.py`](src/dashboard_generator.py).
   - Updated `v1.6 Ipatieff (Current)` architecture description.
   - Added regression unit tests and regenerated all public dashboard web assets in `docs/`.

5. **Headline Arena Energy Benchmark Protocol Alignment & Active Challenge Discovery ([Issue #182](https://github.com/KoshiirRa/midgley/issues/182)):**
   - Aligned [`src/headline_arena_connector.py`](src/headline_arena_connector.py) with Headline Arena's official REST API specifications (`POST /api/v1/agent/auth/token` with `client_credentials`, `POST /api/v1/agent/prediction-scope/{scope_key}` for scope subscription, `GET /api/v1/eval/challenges/active` for dynamic daily challenge discovery, and `POST /api/v1/eval/challenges/{challenge_id}/predict` for forecast submission).
   - Resolved `HTTP 404 Not Found` errors caused by legacy non-existent `/predictions/submit` endpoint.
   - Added dynamic active challenge resolution for **`CL` (WTI Crude Oil)** daily directional challenges and graceful `SKIPPED_NO_ACTIVE_CHALLENGE` status handling for unlisted assets like `RB`.
   - Updated official `CL` settlement dead-zone rule default to ±0.30% (`neutral_pct: 0.3`).
   - Added full mock and live protocol unit tests in [`tests/test_headline_arena_connector.py`](tests/test_headline_arena_connector.py).

---

## 🧪 Verification & Test Suite Matrix

- **Execution Target:** Dedicated Linux VM (`dev-vm` / `10.42.42.54`) & Cloudflare Edge Runtime.
- **Sprint Test Suite Results:**
  - `tests/test_headline_arena_connector.py` (19/19 tests passing)
  - `tests/test_lookup_cache.py` (9/9 tests passing)
  - `tests/test_prediction_logger_cloud_sync.py` (4/4 tests passing)
  - `tests/test_mlops_prediction_schema.py` (6/6 tests passing)
  - `tests/test_dashboard_generator.py` (22/22 tests passing)
  - `tests/test_api_server.py` (18/18 tests passing)
  - **Sprint Matrix:** **78/78 unit tests passing (100% pass rate)**.

---

## 📋 Upgrading

To update on the **dev** branch:

```bash
git fetch origin
git checkout dev
git pull origin dev
pip install -e .
npx wrangler deploy
```
