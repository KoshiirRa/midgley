# Release Notes - v0.7.0

**Release Date:** September 21, 2026  
**Build Target:** `dev-vm` (`10.42.42.54`), GitHub Actions & Cloudflare Edge  
**Git Branch:** `dev` / `main`  
**Tracking Issues:** [Issue #343](https://github.com/KoshiirRa/midgley/issues/343), [Issue #354](https://github.com/KoshiirRa/midgley/issues/354), [Issue #344](https://github.com/KoshiirRa/midgley/issues/344), [Issue #341](https://github.com/KoshiirRa/midgley/issues/341), [Issue #327](https://github.com/KoshiirRa/midgley/issues/327), [Issue #372](https://github.com/KoshiirRa/midgley/issues/372), [Issue #363](https://github.com/KoshiirRa/midgley/issues/363), [Issue #365](https://github.com/KoshiirRa/midgley/issues/365), [Issue #364](https://github.com/KoshiirRa/midgley/issues/364), [Issue #366](https://github.com/KoshiirRa/midgley/issues/366), [Issue #368](https://github.com/KoshiirRa/midgley/issues/368), [Issue #418](https://github.com/KoshiirRa/midgley/issues/418), [Issue #408](https://github.com/KoshiirRa/midgley/issues/408), [Issue #400](https://github.com/KoshiirRa/midgley/issues/400), [Issue #403](https://github.com/KoshiirRa/midgley/issues/403), [Issue #404](https://github.com/KoshiirRa/midgley/issues/404), [Issue #393](https://github.com/KoshiirRa/midgley/issues/393), [Issue #391](https://github.com/KoshiirRa/midgley/issues/391), [Issue #392](https://github.com/KoshiirRa/midgley/issues/392), [Issue #399](https://github.com/KoshiirRa/midgley/issues/399)

---

## 🚀 Overview & Release Highlights

Midgley **v0.7.0** is a landmark reliability, security, econometric expansion, and benchmark integration release. It eliminates critical security vulnerabilities across reconcilers and API middleware, resolves lookahead temporal leakage in feature engineering, restores CoSPOT spectral context in intraday anomaly scoring, expands Weights & Biases telemetry to all active metropolitan hubs, introduces zero-cost daily EIA physical spot wholesale price and weekly EPA EMTS RIN credit ingestion, California Energy Commission (CEC) fuels watch ingestion, EPA statutory RVP blend transition schedules, NOAA CO-OPS marine terminal telemetry, decouples Headline Arena energy forecast generation and submission via a 24-hour pending cache and 30-minute sync workflow, supports EIA Weekly Retail Regular Gasoline Civic Challenges, reconciles CARB statutory tax itemization across all documentation and regional metadata, introduces point-in-time EIA Weekly Retail Gasoline price evaluation ground truth by PADD and state, adds NYMEX futures forward curve term structures, calendar spreads ($M_1 - M_2$), and 3-2-1 crack spreads, eliminates hardcoded dashboard accuracy hit rates and rolling performance arrays with dynamic calculations from real out-of-time prediction history, eliminates synthetic offset ladders and identity fallbacks in MLOps prediction logging, and purges test fixture artifacts from production history with runtime plausibility validation guards.

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

### 9. California Energy Commission (CEC) Weekly Fuels Watch (`src/data_ingestion.py` - Issue #364)
- **Zero-Cost PADD 5 Supply Balances:** Implemented `CECWeeklyFuelsConnector` fetching California refinery crude input, CARBOB production, NorCal vs. SoCal refinery utilization rates, and finished gasoline stocks.
- **Thursday Vintage Scheduling:** Tracks Thursday afternoon publication lag with bitemporal point-in-time snapshots in `data/cec_fuels_vintages.json`.

---

### 10. EPA Reid Vapor Pressure (RVP) Standards & Blend Transitions (`src/rvp_regulations.py` - Issue #366)
- **Statutory Volatility Limits (40 CFR Part 1090 & CARB):** Implemented `RVPRegulatoryEngine` modeling jurisdiction-specific RVP constraints (7.8 psi Non-Attainment, 9.0 psi Attainment, 7.4 psi RFG, 6.99 psi CARB CaRFG).
- **Seasonal Countdown & Compliance Premiums:** Computes exact countdown features for terminal delivery (May 1), retail compliance (June 1 - Sept 15), winter transitions (Sept 16), and spring transition ramp-ups with estimated summer compliance premiums ($+\$0.08$ to $+\$0.28$/gal). Supports emergency fuel waiver tracking.

---

### 11. NOAA CO-OPS Coastal Marine Disruption Telemetry (`src/data_ingestion.py` - Issue #368)
- **Marine Fuel Terminal Telemetry:** Implemented `NOAACOOPSConnector` fetching coastal water levels, draft anomalies, and storm surge residuals across key terminals (Station `8770613` Houston, `8557380` Delaware River, `9415144` Carquinez Strait, `8722237` Fort Pierce/Port St. Lucie).
- **Operational Risk Indices:** Converts tidal surge and shallow draft extremes to operational marine terminal disruption risk metrics with bitemporal persistence in `data/noaa_coops_vintages.json`.

---

### 12. EIA Weekly Retail Prices by PADD / State Ground Truth (`src/eia_retail_feed.py` & `src/prediction_logger.py` - Issue #403)
- **Point-in-Time Regional Retail Ground Truth:** Implemented `EIARetailFeed` mapping EIA weekly retail gasoline series by PADD and state:
  - U.S. National Regular (`GASREGW` / `TOTAL.EER_EPMRU_PFG_Y05R_DPG.W`)
  - PADD 2 Midwest & Oklahoma (`GASMIDW` / `TOTAL.EER_EPMRU_PFG_R20_DPG.W`)
  - PADD 1B Central Atlantic & New Jersey (`GASCAW` / `TOTAL.EER_EPMRU_PFG_R1Y_DPG.W`)
  - PADD 2 Ohio / Cincinnati (`TOTAL.EER_EPMRU_PFG_SOH_DPG.W`)
  - PADD 1C Lower Atlantic & North Carolina (`GASLAW` / `TOTAL.EER_EPMRU_PFG_SNC_DPG.W`)
  - PADD 1C Florida (`TOTAL.EER_EPMRU_PFG_SFL_DPG.W`)
  - PADD 5 West Coast & California (`GASCALW` / `TOTAL.EER_EPMRU_PFG_SCA_DPG.W`)
- **Automated Regional Backfill:** Upgraded `backfill_actual_prices_and_evaluate()` to dynamically retrieve regional ground truth retail prices using `EIARetailFeed.get_retail_price_for_date()`, persisting bitemporal vintages in `data/eia_retail_vintages.json`.

---

### 13. NYMEX Forward Curve, Calendar Spreads & 3-2-1 Crack Futures (`src/data_ingestion.py` & `src/feature_engineering.py` - Issue #404)
- **Term Structure & Calendar Spreads:** Implemented `NYMEXForwardCurveConnector` ingesting front-month ($M_1$) and second-month ($M_2$) futures for RBOB Gasoline (`RB=F`, `RB2=F`), WTI Crude (`CL=F`, `CL2=F`), and Heating Oil/Diesel (`HO=F`, `HO2=F`).
- **Engineered Econometric Features:** Computes prompt-to-second month calendar spreads ($M_1 - M_2$), backwardation flags ($M_1 > M_2$), 1:1 crack spread futures ($\text{Crack}_{1:1} = P_{\text{RBOB}} - P_{\text{WTI}} / 42$), and prompt 3-2-1 refinery crack margins ($\text{Crack}_{3:2:1} = \frac{2 \cdot P_{\text{RBOB}} \cdot 42 + 1 \cdot P_{\text{HO}} \cdot 42 - 3 \cdot P_{\text{WTI}}}{3}$).
- **Bitemporal Persistence:** Preserves point-in-time forward curve vintages in `data/nymex_forward_vintages.json`.

---

### 14. Dynamic Dashboard Accuracy Metrics & Rolling Performance Arrays (`src/dashboard_generator.py` - Issue #393)
- **Eliminated Static Hardcoded Metrics:** Replaced hardcoded literal directional hit rates (`76.8%`, `78.2%`, etc.) and static rolling array curves across all 9 dashboard HTML subpages (`national`, `tulsa`, `newark`, `cincinnati`, `greenville`, `charlotte`, `port_st_lucie`, `oakland`, `bayarea`).
- **Dynamic Chronological Computation:** Added `calculate_rolling_metrics()` and `compute_dynamic_accuracy_stats()` to dynamically compute overall and per-region MAE, RMSE, MAPE, sample sizes ($N$), and 7-day rolling performance metrics directly from `prediction_history.csv`.
- **Sparse Data Gating:** Enforces an explicit `Insufficient Data (N < 30)` fallback tag when evaluated samples are fewer than 30, preventing misleading confidence metrics during early deployment phases.

---

### 15. Headline Arena Pending Cache & Asynchronous Challenge Sync (`src/headline_arena_connector.py`, `scripts/sync_headline_arena.py`, `.github/workflows/headline_arena_sync.yml` - Issue #418)
- **Decoupled Forecast Generation & Challenge Availability:** Implemented a 24-hour pending forecast cache (`data/headline_arena_pending_forecasts.json`) that persists daily multi-agent commodity forecasts (RBOB, WTI, EIA Retail) across execution windows.
- **Challenge Idempotency Ledger:** Implemented `data/headline_arena_submitted_ledger.json` recording submitted challenge IDs and server responses to prevent duplicate submissions during periodic runs.
- **Automated 30-Minute Sync Runner:** Added `scripts/sync_headline_arena.py` and GitHub Actions workflow `.github/workflows/headline_arena_sync.yml` running every 30 minutes to match open Headline Arena challenges with cached forecasts.

---

### 16. EIA Weekly Retail Regular Gasoline Civic Challenge Submissions (`src/headline_arena_connector.py` - Issue #408)
- **Macro / Civic Numeric Distribution Scoring:** Implemented `format_eia_retail_civic_payload()` and `submit_macro_forecast()` supporting Headline Arena civic challenges.
- **Continuous Ranked Probability Score (CRPS) Calibration:** Computes closed-form Gaussian distributions with median target ($P_{50}$) and uncertainty standard deviation ($\sigma$) derived from multi-agent quantile spreads ($P_{90}-P_{10}$) or empirical residual variance.

---

### 17. Statutory CARB Environmental Tax & All-In Retail Math Reconciliation (`ARCHITECTURE.md`, `AGENTS.md`, `data/regional_metadata/oakland_ca.json` - Issue #400)
- **Reconciled California State Tax Burden:** Formulated exact statutory breakdown: $T_{\text{CARB}} = \tau_{\text{Excise}} + \tau_{\text{CapTrade}} + \tau_{\text{LCFS}} + \tau_{\text{UST/Env}} = \$0.596 + \$0.234 + \$0.088 + \$0.035 = \$0.953/\text{gal}$.
- **All-In Retail Pump Tax Total:** Reconciled total statutory burden: $T_{\text{All-In}} = T_{\text{CARB}} + \tau_{\text{Federal}} + \tau_{\text{Sales}} = \$0.953 + \$0.184 + \$0.270 = \$1.407/\text{gal}$ across all documentation and regional metadata files.

---

### 18. MLOps Ground Truth Integrity, Plausibility Guards & History Sanitation (`src/prediction_logger.py`, `data/prediction_history.csv` - Issues #391, #392, #399)
- **Eliminated Synthetic Offset Ladders (#391):** Removed artificial offset additions (`RB=F + $0.55`, `RB=F + $2.05`) in `backfill_actual_prices_and_evaluate()`. All regional actuals are now resolved strictly from real observed weekly EIA retail series via `EIARetailFeed`.
- **Eliminated Identity Fallback Biases (#392):** Removed `margin_offset = base_price - raw_actual if base_price > raw_actual else 0.55` fallback that synthetically forced `actual_direction = "UP"` on 100% of unmapped hub rows. Unobserved dates or unmapped hubs are now properly recorded as `np.nan` and excluded from directional hit rate calculations.
- **Plausibility Validation Guards (`validate_price_plausibility`, #399):** Added runtime bounds checking enforcing $\$1.00 \le P \le \$10.00/\text{gal}$ on retail observations and $\$0.50 \le P \le \$7.00/\text{gal}$ on wholesale futures.
- **Prediction History Sanitation (`cleanse_prediction_history`, #399):** Purged 100 `Test_Region` test fixture rows from `data/prediction_history.csv` and added automated history cleansing routines.
- **Disk-Backed Actuals Cache (`data/rbob_actuals_cache.json`, #399):** Added disk caching for national futures actuals to eliminate redundant full-series yfinance downloads during evaluation cycles.

---

### 19. Automated Verification & Regression Test Suite
- **`tests/test_check_updates.py`:** Validates RCE prevention, allowlisted action execution, legacy command translation, and insecure URL fallback rejection (4/4 passing).
- **`tests/test_temporal_leakage.py`:** Validates absence of backward filling, $h$-step split boundary purging, train-slice diagnostic computation, stacking CV purging, and chronological ordering (5/5 passing).
- **`tests/test_api_server.py`:** Verifies fail-closed admin secret verification and global API key middleware route enforcement (23/23 passing).
- **`tests/test_intraday_event_monitor.py`:** Validates CoSPOT spectral context generation in anomaly evaluator without exceptions (20/20 passing).
- **`tests/test_wandb_logger.py`:** Validates multi-region telemetry aggregation and performance table logging (8/8 passing).
- **`tests/test_eia_spot_connector.py`:** Validates daily regional spot price fetching, basis calculations, and vintage persistence (2/2 passing).
- **`tests/test_epa_rin_connector.py`:** Validates EPA EMTS RIN ingestion, dynamic RVO calculation, and biofuel connector integration (3/3 passing).
- **`tests/test_cec_fuels_connector.py`:** Validates California Energy Commission Weekly Fuels Watch ingestion and Thursday vintages (3/3 passing).
- **`tests/test_rvp_regulations.py`:** Validates statutory RVP limits, transition dates, and emergency waiver simulation (5/5 passing).
- **`tests/test_noaa_coops_connector.py`:** Validates NOAA CO-OPS coastal water level fetching and marine risk indices (3/3 passing).
- **`tests/test_headline_arena_connector.py`:** Validates pending forecast caching, 24h expiration, submitted ledger idempotency, EIA civic challenge payloads, and dispatching (27/27 passing).
- **`tests/test_eia_retail_feed.py`:** Validates EIA weekly retail ground truth series fetching, vintage persistence, regional price lookup, and fallback handling (5/5 passing).
- **`tests/test_nymex_forward_curve.py`:** Validates NYMEX forward curve connector, calendar spreads, 3-2-1 crack futures, backwardation flags, and feature matrix integration (3/3 passing).
- **`tests/test_dashboard_metrics.py`:** Validates dynamic dashboard metric computation, rolling arrays, sparse data gating, and template rendering without placeholders (5/5 passing).
- **`tests/test_prediction_logger_hardening.py`:** Validates price plausibility checking, Test_Region cleansing, unmapped hub handling without forced UP direction, and EIA ground truth integration (4/4 passing).
- **Total Test Results:** 100% pass rate across all 72 test suites with zero regressions.

