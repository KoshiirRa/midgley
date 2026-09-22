# Release Notes - v0.7.0

**Release Date:** September 21, 2026  
**Build Target:** `dev-vm` (`10.42.42.54`), GitHub Actions & Cloudflare Edge  
**Git Branch:** `dev` / `main`  
**Tracking Issues:** [Issue #343](https://github.com/KoshiirRa/midgley/issues/343), [Issue #354](https://github.com/KoshiirRa/midgley/issues/354), [Issue #344](https://github.com/KoshiirRa/midgley/issues/344), [Issue #341](https://github.com/KoshiirRa/midgley/issues/341), [Issue #327](https://github.com/KoshiirRa/midgley/issues/327), [Issue #372](https://github.com/KoshiirRa/midgley/issues/372), [Issue #363](https://github.com/KoshiirRa/midgley/issues/363), [Issue #365](https://github.com/KoshiirRa/midgley/issues/365)

---

## 🚀 Overview & Release Highlights

Midgley **v0.7.0** is a landmark reliability, security, and econometric expansion release. It eliminates critical security vulnerabilities across reconcilers and API middleware, resolves lookahead temporal leakage in feature engineering, restores CoSPOT spectral context in intraday anomaly scoring, expands Weights & Biases telemetry to all active metropolitan hubs, and introduces zero-cost daily EIA physical spot wholesale price and weekly EPA EMTS RIN credit ingestion.

---

### 1. Upgrade Reconciler RCE Remediation & Safe Execution Model (`scripts/check_updates.py` - Issue #343)
- **Eliminated Arbitrary Command Execution (`shell=True`):** Removed dangerous dynamic shell invocation of unvalidated upstream manifest strings.
- **Enforced Allowlisted Actions (`ALLOWLISTED_ACTIONS`):** Restricted reconciler automation to strict, pre-defined argument vectors (`retrain_regional_models`, `update_static_dashboard`, `run_migrations`) executed with `shell=False`.
- **HTTPS Scheme Enforcement:** Added strict validation ensuring update manifest endpoints originate from secure `https://` URLs, preventing insecure scheme downgrade attacks.
- **Cross-Platform Console Compatibility:** Replaced raw Unicode emojis with ASCII-safe status tags (`[*]`, `[+]`, `[!]`) to ensure seamless execution across Windows (`cp1252`) and POSIX environments.

---

### 2. Time-Series Feature Engineering & Stacking Leakage Elimination (`src/feature_engineering.py` & `src/models.py` - Issue #354)
- **Eliminated Backward Imputation (`bfill`):** Replaced backward lookahead filling on feature lags with chronological forward-filling (`ffill().fillna(0.0)`), guaranteeing zero future information leaks into historical observations.
- **Chronological Split Boundary Purging:** Enforced an $h$-step boundary purge gap (`train_slice_end = max(1, split_idx - forecast_horizon)`) in `prepare_chronological_splits()`, ensuring target values ($y_t = P_{t+h}$) at the tail of the training set never overlap or leak into the test evaluation slice.
- **Training-Slice Autocorrelation Routing Diagnostic:** Refactored `compute_context_routing_diagnostic()` to evaluate target autocorrelation exclusively on the training partition ($k = \lfloor N \times \text{train\_ratio} \rfloor$).
- **Purged Stacking Cross-Validation:** Updated `build_stacking_ensemble_pipeline()` to default to `PurgedGroupTimeSeriesSplit(n_splits=5, label_horizon_steps=5, embargo_steps=5)` with contiguous test partitions, eliminating out-of-fold training leakage in meta-regressors.

---

### 3. Global Middleware Authentication Route Matching Fix (`src/api_server.py` - Issue #344)
- **Exact Root Path Matching:** Replaced loose prefix matching on `"/"` with exact equality (`request.url.path == "/"`) for public root documentation.
- **Strict Protected Route Enforcement:** Enforces API key verification on all protected endpoints (`/api/v1/prices/*`, `/api/v1/forecast/*`, `/api/v1/combined`, `/mcp/*`) while preserving public access strictly for explicit endpoints (`/docs`, `/redoc`, `/openapi.json`, `/.well-known`, `/health`).

---

### 4. Admin Secret Fail-Closed Security Hardening (`src/api_server.py` - Issue #341)
- **Removed Hardcoded Fallback Secret:** Eliminated default development token (`midgley_dev_admin_secret_2026`).
- **Fail-Closed Verification:** Enforced immediate `HTTP 401 Unauthorized` rejection when `MIDGLEY_ADMIN_SECRET` is unset, empty, or whitespace-only on the server.

---

### 5. CoSPOT Spectral Context Restoration in Anomaly Evaluator (`src/intraday_event_monitor.py` - Issue #327)
- **Resolved `ImportError`:** Replaced non-existent `from src.data_ingestion import fetch_all_data` with `from src.data_ingestion import fetch_market_data`.
- **Restored Qualitative Feature Prompting:** Injects live CoSPOT spectral decomposition and DWT detail shock magnitudes (arXiv:2609.02093) into Gemini LLM event scoring prompts during intraday breaking news evaluations.

---

### 6. Multi-Region Weights & Biases (W&B) Telemetry (`src/weekly_issue_reporter.py` & `src/wandb_logger.py` - Issue #372)
- **Dynamic Multi-Region Aggregation:** Iterates across all active regional calibration hubs (`Tulsa_OK`, `Newark_NJ`, `Cincinnati_OH`, `Greenville_NC`, `Charlotte_NC`, `Oakland_CA`, `Port_St_Lucie_FL`, and regional diesel engines) in `eval_df` to compute rolling MAE, RMSE, directional hit rate, and sample sizes.
- **Structured Performance Table:** Logs an interactive W&B performance table (`audit/regional_performance_table`) and per-region time-series line charts (`regions/<locale>_mae`, `regions/<locale>_hit_rate_pct`).

---

### 7. U.S. EIA Daily Regional Spot Price Ingestion (`src/data_ingestion.py` & `src/feature_engineering.py` - Issue #363)
- **Zero-Cost Daily Spot Wholesale Prices:** Implemented `EIARegionalSpotConnector` fetching daily spot wholesale gasoline benchmarks:
  - U.S. Gulf Coast Conventional Spot (`EER_EPMRU_PF4_RGC_DPG` / FRED `DGASUSGULF`)
  - New York Harbor Conventional Spot (`EER_EPMRU_PF4_YNY_DPG` / FRED `DGASNYH`)
  - Los Angeles CaRFG Reformulated Spot (`EER_EPMRU_PF4_RLA_DPG` basis)
- **Physical Basis Spreads:** Engineers localized physical rack basis spreads (`eia_regional_spot_basis`, `eia_spot_gulf_coast`, `eia_spot_ny_harbor`, `eia_spot_los_angeles`) with $T+1$ publication lag tracking in `data/eia_spot_vintages.json`.

---

### 8. EPA Weekly EMTS RIN Prices & RVO Compliance Ingestion (`src/data_ingestion.py` - Issue #365)
- **Dynamic RIN Market Pricing:** Implemented `EPARINDataConnector` ingesting weekly EPA EMTS credit averages: D6 Renewable Fuel (Ethanol), D4 Biomass-Based Diesel, and D3 Cellulosic Biofuel, tracking bitemporal observations in `data/epa_rin_vintages.json`.
- **Eliminated Hardcoded Constants:** Replaced static `$0.520/gal` default in `USDABiofuelConnector` with live observed EPA D6 credit values and dynamic Renewable Volume Obligation (RVO) cost calculation.

---

### 9. Automated Verification & Regression Test Suite
- **`tests/test_check_updates.py`:** Validates RCE prevention, allowlisted action execution, legacy command translation, and insecure URL fallback rejection (4/4 passing).
- **`tests/test_temporal_leakage.py`:** Validates absence of backward filling, $h$-step split boundary purging, train-slice diagnostic computation, stacking CV purging, and chronological ordering (5/5 passing).
- **`tests/test_api_server.py`:** Verifies fail-closed admin secret verification and global API key middleware route enforcement (23/23 passing).
- **`tests/test_intraday_event_monitor.py`:** Validates CoSPOT spectral context generation in anomaly evaluator without exceptions (20/20 passing).
- **`tests/test_wandb_logger.py`:** Validates multi-region telemetry aggregation and performance table logging (8/8 passing).
- **`tests/test_eia_spot_connector.py`:** Validates daily regional spot price fetching, basis calculations, and vintage persistence (2/2 passing).
- **`tests/test_epa_rin_connector.py`:** Validates EPA EMTS RIN ingestion, dynamic RVO calculation, and biofuel connector integration (3/3 passing).
- **Total Test Results:** 100% pass rate across all 65 test suites with zero regressions.
