# Release Notes - v0.6.4

**Release Date:** September 17, 2026  
**Build Target:** \dev-vm\ (.42.42.54\) & Cloudflare Edge  
**Git Branch:** \dev\  

---

## 🚀 Overview & Release Highlights

Midgley **v0.6.4** introduces key edge infrastructure observability, multi-tier connectivity diagnostics, unified cloud batch synchronization, and dynamic model version decoupling:

1. **Active Multi-Tier Edge Cache Connectivity Probing & URL Scheme Normalization ([Issue #301](https://github.com/KoshiirRa/midgley/issues/301)):**
   - Implemented active multi-tier connectivity probing methods (\	est_edge_connectivity()\) in [\src/lookup_cache.py\](file:///src/lookup_cache.py) testing Turso Edge SQLite and Cloudflare D1/Worker gateways.
   - Added automated URL normalization for \	urso://\ and \libsql://\ schemes to \https://\ for HTTP REST \/v2/pipeline\ compatibility.
   - Added CLI diagnostic flags (\python3 -m src.lookup_cache --ping\, \--test-turso\, \--test-cloudflare\, \--test-all\, \--stats\).
   - Exposed live probe diagnostics via REST API endpoint \GET /api/v1/system/cache-status?probe=true\.

2. **Cloudflare D1 Batch Prediction Synchronization & Schema Migration ([Issue #302](https://github.com/KoshiirRa/midgley/issues/302)):**
   - Added dedicated \POST /api/v1/sync/predictions\ batch route in [\workers/cache_worker.ts\](file:///workers/cache_worker.ts) executing atomic \nv.DB.batch()\ statements with automated table provisioning.
   - Reconciled \POST /api/v1/cache\ and \DELETE /api/v1/cache\ routes in edge worker gateway.
   - Provisioned standalone D1 database schema migration script [\scripts/init_d1_schema.sql\](file:///scripts/init_d1_schema.sql).
   - Enhanced [\src/prediction_logger.py\](file:///src/prediction_logger.py) with HTTP error response body extraction and decoding on non-200 responses to streamline debugging.

3. **Dynamic Regional Model Version Tagging & Decoupling ([Issue #303](https://github.com/KoshiirRa/midgley/issues/303)):**
   - Eliminated brittle hardcoded \1.4\ and \1.5\ strings across all 8 regional runner modules (\	ulsa\, ewark\, \cincinnati\, \greenville\, \charlotte\, \oakland\, \port_st_lucie\, ational\), \src/dynamic_region.py\, \src/intraday_event_monitor.py\, \src/readme_updater.py\, and \src/api_server.py\.
   - Introduced [esolve_model_tag(region, model_type)\](file:///src/prediction_logger.py) dynamically binding to [\src.version.get_model_version()\](file:///src/version.py) (e.g. \1.6-Ipatieff-TulsaOK-Ridge\).

4. **Model Iteration Lineage Matrix & Comparison Table ([Issue #304](https://github.com/KoshiirRa/midgley/issues/304)):**
   - Added missing historical lineage entries for \1.4 Finlight-LLM\ and \1.5 Multi-Tier & Sensor MLOps\ to the Model Iteration table in [\src/dashboard_generator.py\](file:///src/dashboard_generator.py).
   - Updated \1.6 Ipatieff (Current)\ architecture description.
   - Added regression unit tests and regenerated all public dashboard web assets in \docs/\.

---

## 🧪 Verification & Test Suite Matrix

- **Execution Target:** Dedicated Linux VM (\dev-vm\ / .42.42.54\) & Cloudflare Edge Runtime.
- **Sprint Test Suite Results:**
  - \	ests/test_lookup_cache.py\ (9/9 tests passing)
  - \	ests/test_prediction_logger_cloud_sync.py\ (4/4 tests passing)
  - \	ests/test_mlops_prediction_schema.py\ (6/6 tests passing)
  - \	ests/test_dashboard_generator.py\ (22/22 tests passing)
  - \	ests/test_api_server.py\ (18/18 tests passing)
  - **Sprint Matrix:** **59/59 unit tests passing (100% pass rate)**.

---

## 📋 Upgrading

To update on the **dev** branch:

\\ash
git fetch origin
git checkout dev
git pull origin dev
pip install -e .
npx wrangler deploy
\