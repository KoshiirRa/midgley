# Release Notes - v0.7.0

**Release Date:** September 21, 2026  
**Build Target:** `dev-vm` (`10.42.42.54`), GitHub Actions & Cloudflare Edge  
**Git Branch:** `dev` / `main`  
**Tracking Issues:** [Issue #329](https://github.com/KoshiirRa/midgley/issues/329), [Issue #331](https://github.com/KoshiirRa/midgley/issues/331), [Issue #334](https://github.com/KoshiirRa/midgley/issues/334), [Issue #335](https://github.com/KoshiirRa/midgley/issues/335), [Issue #342](https://github.com/KoshiirRa/midgley/issues/342), [Issue #343](https://github.com/KoshiirRa/midgley/issues/343), [Issue #347](https://github.com/KoshiirRa/midgley/issues/347), [Issue #354](https://github.com/KoshiirRa/midgley/issues/354), [Issue #344](https://github.com/KoshiirRa/midgley/issues/344), [Issue #341](https://github.com/KoshiirRa/midgley/issues/341), [Issue #327](https://github.com/KoshiirRa/midgley/issues/327), [Issue #372](https://github.com/KoshiirRa/midgley/issues/372), [Issue #363](https://github.com/KoshiirRa/midgley/issues/363), [Issue #365](https://github.com/KoshiirRa/midgley/issues/365), [Issue #364](https://github.com/KoshiirRa/midgley/issues/364), [Issue #366](https://github.com/KoshiirRa/midgley/issues/366), [Issue #368](https://github.com/KoshiirRa/midgley/issues/368), [Issue #418](https://github.com/KoshiirRa/midgley/issues/418), [Issue #408](https://github.com/KoshiirRa/midgley/issues/408), [Issue #410](https://github.com/KoshiirRa/midgley/issues/410), [Issue #420](https://github.com/KoshiirRa/midgley/issues/420), [Issue #370](https://github.com/KoshiirRa/midgley/issues/370), [Issue #422](https://github.com/KoshiirRa/midgley/issues/422), [Issue #400](https://github.com/KoshiirRa/midgley/issues/400), [Issue #403](https://github.com/KoshiirRa/midgley/issues/403), [Issue #404](https://github.com/KoshiirRa/midgley/issues/404), [Issue #393](https://github.com/KoshiirRa/midgley/issues/393), [Issue #391](https://github.com/KoshiirRa/midgley/issues/391), [Issue #392](https://github.com/KoshiirRa/midgley/issues/392), [Issue #399](https://github.com/KoshiirRa/midgley/issues/399), [Issue #401](https://github.com/KoshiirRa/midgley/issues/401), [Issue #397](https://github.com/KoshiirRa/midgley/issues/397), [Issue #396](https://github.com/KoshiirRa/midgley/issues/396), [Issue #395](https://github.com/KoshiirRa/midgley/issues/395), [Issue #394](https://github.com/KoshiirRa/midgley/issues/394), [Issue #398](https://github.com/KoshiirRa/midgley/issues/398), [Issue #390](https://github.com/KoshiirRa/midgley/issues/390), [Issue #355](https://github.com/KoshiirRa/midgley/issues/355), [Issue #389](https://github.com/KoshiirRa/midgley/issues/389), [Issue #351](https://github.com/KoshiirRa/midgley/issues/351), [Issue #353](https://github.com/KoshiirRa/midgley/issues/353), [Issue #350](https://github.com/KoshiirRa/midgley/issues/350), [Issue #421](https://github.com/KoshiirRa/midgley/issues/421), [PR #320](https://github.com/KoshiirRa/midgley/pull/320), [PR #321](https://github.com/KoshiirRa/midgley/pull/321)

---

## 🚀 Overview & Release Highlights

Midgley **v0.7.0** is a landmark reliability, security, econometric expansion, and benchmark integration release. It eliminates critical security vulnerabilities across reconcilers and API middleware, resolves lookahead temporal leakage in feature engineering, restores CoSPOT spectral context in intraday anomaly scoring, expands Weights & Biases telemetry to all active metropolitan hubs, introduces zero-cost daily EIA physical spot wholesale price and weekly EPA EMTS RIN credit ingestion, California Energy Commission (CEC) fuels watch ingestion, EPA statutory RVP blend transition schedules, NOAA CO-OPS marine terminal telemetry, integrates NASA POWER Point Daily Climatology for distillate heating/cooling degree days and Midwest biofuel agroclimatology, expands Headline Arena daily challenge continuous probability forecasting across RBOB Gasoline, Cushing WTI, Henry Hub Natural Gas (NG), and US Dollar Index (DXY), exposes granular Hindsight Hosted episodic memory telemetry (durable observations, cloud reconciliation queue, and connector event health), decouples Headline Arena energy forecast generation and submission via a 24-hour pending cache and 30-minute sync workflow, supports EIA Weekly Retail Regular Gasoline Civic Challenges, reconciles CARB statutory tax itemization across all documentation and regional metadata, introduces point-in-time EIA Weekly Retail Gasoline price evaluation ground truth by PADD and state, adds NYMEX futures forward curve term structures, calendar spreads ($M_1 - M_2$), and 3-2-1 crack spreads, eliminates hardcoded dashboard accuracy hit rates and rolling performance arrays with dynamic calculations from real out-of-time prediction history, eliminates synthetic offset ladders and identity fallbacks in MLOps prediction logging, purges test fixture artifacts from production history with runtime plausibility validation guards, modernizes CI/CD GitHub Actions workflows with major `actions-workflows` version bumps (`actions/checkout@v7`, `actions/setup-python@v7`), and updates ASGI server dependencies (`uvicorn>=0.53.0`).

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

### 19. Quantitative Econometrics Hardening, 3-2-1 Crack Formulation & Return Target Modeling (`src/feature_engineering.py`, `src/models.py`, `docs/math.html` - Issues #401, #397, #396)
- **Standardized 3-2-1 Crack Spread Formulation (#401):** Implemented multi-product 3-2-1 refining crack spread in both $\$ / \text{bbl}$ ($\text{Crack}_{321}^{\text{bbl}} = \frac{2 \cdot (P_{\text{RBOB}} \cdot 42) + 1 \cdot (P_{\text{HO}} \cdot 42) - 3 \cdot P_{\text{WTI}}}{3}$) and $\$ / \text{gal}$ ($\text{Crack}_{321}^{\text{gal}} = \frac{2 \cdot P_{\text{RBOB}} + 1 \cdot P_{\text{HO}} - 3 \cdot (P_{\text{WTI}}/42)}{3}$), retaining 1:1 single-product crack ($\text{CrackSpread} = P_{\text{RBOB}} - P_{\text{WTI}}/42$) as an independent quantitative feature. Synchronized equations in `docs/math.html` (Equation 1.2).
- **Return-Based Target Modeling & Level Reconstruction (#397):** Standardized model targets on $h$-day percentage returns ($\hat{r}_{t+h} = (P_{t+h} - P_t) / P_t$) with level reconstruction ($\hat{P}_{t+h} = P_t \cdot (1 + \hat{r}_{t+h})$). Eliminates spurious persistence autocorrelation while improving directional hit rate and out-of-time stability.
- **Chronological Embargo Buffer & Purged Cross-Validation (#396):** Enforced an embargo gap equal to $\text{forecast\_horizon} + \text{embargo\_steps}$ in `prepare_chronological_splits()`, ensuring training target intervals never touch the test slice. Upgraded Ridge regression pipelines in `train_and_compare_models()` to optimize hyperparameter $\alpha \in [0.01, 0.1, 1.0, 10.0, 50.0, 100.0, 500.0]$ dynamically across purged walk-forward cross-validation folds via `PurgedGroupTimeSeriesSplit(chronological_only=True)`.
- **Vectorized Exact Business Day Inference:** Replaced approximate integer day scaling in `_infer_horizon_days()` with `np.busday_count()` for nanosecond-speed exact business day calculation.

### 20. Injectable Evaluation Architecture & Offline Unit Test Coverage (`src/prediction_logger.py` - Issue #395)
- **Dependency Injected Evaluation Overrides:** Added `actuals_map_override`, `eia_feed_override`, `csv_path`, and `force_eval` parameters to `backfill_actual_prices_and_evaluate()`.
- **Enabled Comprehensive Evaluation Under `TESTING=1`:** Enabled testing of directional accuracy, error calculation, actual price assignments, and confidence interval bounds in continuous integration without requiring external network access, paid API tokens, or yfinance requests.

---

### 21. Calibrated 95% Confidence Interval Coverage & Dynamic Standard Error Scaling (`src/prediction_logger.py` - Issue #394)
- **Eliminated Conflicting Arbitrary Fallback:** Removed the conflicting `abs(actual_price - pred_price) <= 0.12` fallback rule in `src/prediction_logger.py` that caused empirical coverage to diverge from nominal confidence levels.
- **Dynamic Residual Standard Error Scaling:** Upgraded `compute_regional_residual_std()` to support multi-horizon square-root scaling ($\sigma_{\text{residual}} \times \sqrt{h/5}$), dynamically reconstructing calibrated 95% CI bands ($[\hat{P} - 1.96\sigma, \hat{P} + 1.96\sigma]$) when explicit bounds are absent.
- **Scoreboard Coverage Telemetry:** Added `empirical_95ci_coverage_pct` tracking across rolling scoreboards, regional matrix breakdowns, forecast horizon tables, and public dashboard KPI cards.

---

### 22. README Live Summary Automation, Workflow DST Alignment & Freshness Gating (`scripts/readme_updater.py`, `.github/workflows/gas_price_forecast.yml` - Issue #398)
- **Standalone README Live Summary CLI:** Created `scripts/readme_updater.py` (and enhanced `src/readme_updater.py`) to inject live 5-day forecast tables across all 10 active regional locales into `README.md`.
- **Automated Workflow Execution Step:** Added explicit `python scripts/readme_updater.py` step in `.github/workflows/gas_price_forecast.yml` guaranteeing summary table freshness on every daily batch execution.
- **UTC vs Central DST Schedule Drift Documentation:** Documented GitHub Actions cron UTC scheduling (`17 7 * * *`) and seasonal Daylight Saving Time transitions (02:17 AM CDT vs 01:17 AM CST).
- **Dashboard Forecast Staleness Gate:** Added an automated forecast age check in `src/dashboard_generator.py` rendering a visual warning badge (`Forecast Stale (>36h)`) whenever the latest prediction record exceeds 36 hours of age.

---

### 23. Vectorize Hindsight Agent Memory Migration to Hosted SaaS & Cloud Run Cost Remediation (`src/hindsight_client.py`, `scripts/migrate_memory_to_hosted.py` - Issue #421)
- **Cloud Run Scale-to-Zero Cost Overrun Remediation:** Diagnosed and mitigated unexpected Google Cloud Run serverless compute costs (~$17.14–$35.66/month) caused by 2 vCPU / 2GiB container cold boots and frequent wake-ups across daily forecasting, weekly reviews, and telemetry syncs.
- **Direct Hosted SaaS Cutover:** Migrated the primary agent memory engine to Vectorize Hindsight Hosted SaaS (`https://api.hindsight.vectorize.io`, bank `Midgley`), reducing recurring memory infrastructure costs to ~**$3.50/month** (a 90% reduction) with zero cold-start latency.
- **Standardized Energy Commodity Bank Mission Directives (`Midgley`):**
  - **Retain Extraction Rules:** Ingests quantitative price anomalies, localized basis spread shifts, and physical supply shock catalysts (refinery outages, pipeline shut-ins, river navigation constraints, EPA/CARB RVP blend countdowns) using chunk size `1500` and `Concise` extraction mode.
  - **Observations Consolidation Policy:** Synthesizes durable macroeconomic beliefs across wholesale RBOB, WTI crude, regional metro basis spreads (Tulsa, Newark, Cincinnati, Carolinas, Oakland, Port St. Lucie), regulatory blend transitions, and weekly model recalibration lessons while filtering out transient daily noise (<$0.02/gal).
  - **Reflect Reasoning Parameters:** Configures Hindsight reflection reasoning as an expert quantitative energy economist and commodity forecasting analyst, tuned with **Skepticism: 4/5** (guards against unverified macro narratives), **Literalism: 4/5** (enforces exact dollar errors and regulatory dates), and **Empathy: 1/5** (Detached quantitative error analysis).
- **Automated Memory Migration Pipeline:** Implemented `scripts/migrate_memory_to_hosted.py` which successfully batch-transferred all **512 historical episodic memories** and **18 reflections** from `data/agent_memory.sqlite` to the remote hosted bank.
- **Client & CI/CD Hardening:** Updated `HindsightClient` to dynamically support `HINDSIGHT_BANK_ID` and parse remote fact/node metrics from `/v1/default/banks/{bank_id}/stats`. Configured `HINDSIGHT_API_KEY` and `HINDSIGHT_BANK_ID` across `.github/workflows/gas_price_forecast.yml` and `weekly_model_review.yml`.

---

### 24. Dependency Maintenance & CI Workflow Modernization (`requirements.txt`, `.github/workflows/false_positive_reviewer.yml` - PR #320, PR #321)
- **ASGI Server Dependency Upgrade (PR #320):** Updated `uvicorn` requirement from `>=0.52.4` to `>=0.53.0` in the `python-packages` group in `requirements.txt`.
- **GitHub Actions Workflow Modernization (PR #321):** Bumped `actions-workflows` group dependencies in `.github/workflows/false_positive_reviewer.yml`:
  - Upgraded `actions/checkout` from `v4` to `v7`
  - Upgraded `actions/setup-python` from `v5` to `v7` (Node.js 24 compatibility, RHEL support, and enhanced Windows pip cache error handling).

---

### 25. Baseline Quantitative Model Isolation, LLM Augmentation Delta Derivation & Dual Scoreboard Win Rates (`src/models.py`, `src/prediction_logger.py`, `src/locations/` - Issue #390)
- **Baseline Quantitative Forecast Isolation (`quant_baseline_5d_price`):** Upgraded `train_multi_horizon_models()` and all regional forecasters (`national`, `tulsa`, `newark`, `cincinnati`, `greenville`, `charlotte`, `oakland`, `port_st_lucie`, `dynamic_region`, `intraday_event_monitor`) to evaluate and record the pure quantitative baseline forecast alongside the hybrid LLM-augmented forecast.
- **Canonical LLM Augmentation Delta Derivation:** Derived `llm_augmentation_delta = round(pred_price - quant_base, 4)` isolating the explicit dollar price contribution added strictly by qualitative event intelligence and exponential memory shocks.
- **Dual Win Rate Metrics on Rolling Scoreboard:** Upgraded `/api/v1/forecast/scoreboard` and MLOps observability calculations (`compute_mlops_observability_summary()`, `compute_rolling_scoreboard_metrics()`) to report distinct:
  - `llm_vs_quant_win_rate_pct` (LLM-augmented hybrid model vs. pure quantitative baseline without event shocks)
  - `model_vs_persistence_win_rate_pct` (LLM-augmented hybrid model vs. naive persistence baseline)
- **Backfill Integration (`backfill_new_region_history()`):** Extended backfill helpers to accept and persist `quant_baseline_prices`, `llm_price_pressures`, and `llm_supply_disruptions` vectors across historical test evaluations.

### 26. Multi-Event Row Duplication Prevention, Weekend Shock Forward Mapping & Continuous Calendar Exponential Decay (`src/feature_engineering.py` - Issue #355)
- **Eliminated Multi-Event Row Duplication:** Replaced unaggregated left join with session-level shock aggregation, guaranteeing strict 1-to-1 merges without row inflation (`len(merged) == len(df)`).
- **Weekend / Holiday Forward Mapping:** Implemented `np.searchsorted()` forward-mapping of non-trading weekend (Saturday/Sunday) and exchange holiday qualitative shocks to the next active Monday market session.
- **Shock Domain Clamping:** Grouped and summed multiple shocks per trading day with bounded saturation constraints ($[-1.0, 1.0]$ for signed price pressure / demand sentiment; $[0.0, 1.0]$ for unidirectional supply disruption / geopolitical risk / OPEC actions).
- **Continuous Calendar-Elapsed Exponential Decay:** Parameterized dynamic memory decay by elapsed calendar days ($\Delta t_i = \max(1, (\text{date}_i - \text{date}_{i-1}).\text{days})$), ensuring multi-day weekend gaps (Friday $\to$ Monday, $\Delta t = 3$) decay memory continuously ($e^{-3\lambda}$) rather than artificially treating them as a 1-day step.

### 27. Retroactive Backtest Segregation & Write-Time Prediction Validation (`src/prediction_logger.py`, `src/api_server.py` - Issue #389)
- **Extended Schema with `is_retroactive_backtest`:** Added explicit boolean column `is_retroactive_backtest` to `prediction_history.csv` schema, automatically migrating existing prediction logs and tagging retroactive test records.
- **Write-Time Target Date Validation:** `log_predictions()` now automatically evaluates `pd.to_datetime(log_timestamp).date() >= pd.to_datetime(forecast_target_date).date()`, tagging past target dates as `is_retroactive_backtest = True` and forward out-of-time predictions as `False`.
- **Public Scoreboard Out-of-Time Track Record Segregation:** Upgraded `compute_rolling_scoreboard_metrics()`, `compute_regional_scoreboard_breakdown()`, `compute_horizon_scoreboard_breakdown()`, and REST API `/api/v1/forecast/scoreboard` with `include_retroactive` filtering (defaulting to `false`) to ensure public scoreboard metrics reflect strictly genuine, forward-only out-of-time forecasts.
- **Historical Backfill Tagging:** Configured `backfill_new_region_history()` to explicitly tag backfilled historical test slices with `is_retroactive_backtest = True`.

### 28. Defused XML Feed Parsing & Ingestion Security Hardening across Remote Connectors (`defusedxml` - Issue #351)
- **Eliminated XML Entity Expansion Vulnerabilities:** Replaced standard library `xml.etree.ElementTree.fromstring()` with `defusedxml.ElementTree.fromstring()` across all 7 unauthenticated remote XML ingestion modules:
  - `src/arxiv_monitor.py` (arXiv research preprint API feeds)
  - `src/bsee_shutins.py` (BSEE offshore Gulf production shut-in bulletins)
  - `src/edgar_8k_monitor.py` (SEC EDGAR 8-K refinery outage Atom feeds)
  - `src/fireworks_tech_graph.py` (Fireworks architecture SVG diagram validator)
  - `src/geopolitical_feeds.py` (Maritime chokepoint and geopolitical RSS streams)
  - `src/nhc_hurricane.py` (NOAA NHC tropical cyclone advisory feeds)
  - `src/reachability_adapters.py` (Agent-reach RSS syndication adapters)
- **Denial-of-Service & Parser Disruption Protection:** Defuses Billion Laughs attacks, quadratic blowup payloads, and DTD entity exploits from compromised, intercepted, or adversarial upstream XML feeds.
- **Fail-Safe Exception Handling:** Ensures all connector parsers defensively catch `DefusedXmlException` and XML syntax errors, cleanly falling back to cached observations or zero-cost deterministic models without interrupting pipeline execution.
- **Dependency Integration:** Added `defusedxml>=0.7.1` to `requirements.txt` and `pyproject.toml`.

---

### 29. Multi-Horizon Inference Freshness & Unlabelled Frame Preservation (`src/feature_engineering.py`, `src/models.py`, `src/locations/` - Issue #353)
- **Decoupled Training Maturity from Live Inference:** Eliminated stale feature inputs in multi-horizon live predictions ($h \in [1..5]$) where models previously evaluated lagged inputs from $t - h$ instead of contemporary today ($t = 0$).
- **Unlabelled Inference Frame Preservation:** `create_feature_matrix()` computes continuous rolling indicators, event decay memory, and Qlib alpha factors across the entire series, preserving the final $h$ unlabelled rows in `labelled_df.attrs["unlabelled_inference_frame"]` along with `forecast_origin_date` and `feature_cutoff_date`.
- **Contemporary $t=0$ Ingestion in Forecasting Pipelines:** `prepare_chronological_splits()` and `train_multi_horizon_models()` extract `X_live_hybrid`, `X_live_quant`, and `live_current_price` from the contemporary $t=0$ observation, ensuring identical feature origin dates across all discrete step-ahead horizons.
- **Regional Forecaster Realignment:** Updated all regional pipelines (`national`, `tulsa`, `newark`, `cincinnati`, `greenville`, `charlotte`, `oakland`, `port_st_lucie`) to evaluate contemporary live inference features for shock scenario simulations.

---

### 30. Ruff Fatal-Error & Syntax Static Analysis Gate (`pyproject.toml`, `.github/workflows/` - Issue #350)
- **High-Signal Static Analysis Gate:** Configured `[tool.ruff]` and `[tool.ruff.lint]` in `pyproject.toml` selecting fatal syntax errors (`E9`) and Pyflakes violations (`F`), focusing on undefined variable references (`F821`), scope leaks (`F822`, `F823`), and duplicate symbol definitions (`F811`).
- **Defect Remediation:** Resolved latent undefined variable bugs (`prompt` in `src/alpha_factor_miner.py`, `DATA_DIR` in `src/dashboard_generator.py`, `challenge_id` in `src/headline_arena_connector.py`, `re` in `src/intraday_event_monitor.py`) and cleaned up duplicate symbol imports across the codebase.
- **CI/CD Quality Gate:** Added mandatory `ruff check src/ scripts/ tests/` static analysis steps to `.github/workflows/gas_price_forecast.yml` and `.github/workflows/weekly_model_review.yml`.
- **Dependency Integration:** Added `ruff>=0.9.0` to `requirements.txt` and `pyproject.toml`.

---

### 31. IPASIS Default API Credential Revocation & Strict Environment Ingestion (`src/ipasis_security.py` - Issue #342)
- **Revoked Hardcoded Default API Credential:** Eliminated committed active API key (`ipasis_c92c...`) from `src/ipasis_security.py`, strictly binding credential resolution to `os.environ.get("IPASIS_API_KEY")`.
- **Graceful Unconfigured Allowlist Provider:** When `IPASIS_API_KEY` is unset or empty, incoming traffic is allowlisted cleanly under provider `IPASIS_Unconfigured` (`reason="Unconfigured IPASIS (Allowlisted)"`) without issuing invalid outbound API calls or emitting false provider outage warnings.
- **Telemetry Accounting & Unconfigured Status:** Telemetry tracking at `data/ipasis_telemetry.json` records `unconfigured_checks` and reports system status as `UNCONFIGURED` rather than `CAP_EXCEEDED` or error when running without optional third-party IP reputation keys.
- **Documentation & Self-Hosting Guide Hardening:** Updated `SELF_HOSTING.md` and `docs/SELF_HOSTING.md` with sanitized environment configuration guidance.

---

### 32. Leading-Zero ZIP Code Geocoding & PADD Resolution Hardening (`src/zip_geocoding.py` - Issue #335)
- **Preserved Leading Zeros (`.zfill(5)`):** Zero-pads numeric integer and short string ZIP code inputs (e.g. `7001` / `"7001"` -> `"07001"`, `2138` -> `"02138"`), ensuring 3-digit prefixes (`"070"`, `"021"`) correctly map to East Coast states (`NJ`, `MA`) and PADD 1B/1A models rather than being truncated and misrouted to PADD 3 Gulf Coast (`"700"` Louisiana).
- **Sanitized ZIP+4 Parsing:** Handles hyphenated ZIP+4 inputs (`07001-1234` -> `"07001"`) and validates input digit length.
- **Test Suite Hardening:** Added `test_leading_zero_zip_resolution` to `tests/test_zip_geocoding.py` covering integer, string, and ZIP+4 cases across PADD 1A/1B (6/6 passing).

---

### 33. SQLite FTS5 Special Punctuation & Operator Sanitization (`src/agent_memory.py` - Issue #331)
- **Eliminated FTS5 Syntax Exceptions:** Sanitized raw search queries in `SQLiteMemoryStore.recall()` by replacing non-alphanumeric punctuation (`+`, `-`, `*`, `:`, `^`) with whitespace (`re.sub(r'[^\w\s]', ' ', raw_query)`) and enclosing individual token terms in double quotes (`"token"`).
- **Prevented Boolean Collision & Silent Failures:** Eliminates `sqlite3.OperationalError: fts5: syntax error near "+"` when querying complex energy terms (e.g. `"OPEC+ cut"`, `"crack-spread delta"`, `"PADD-1B"`).
- **Defensive FTS5 Exception Handling & Fallback:** Added inner try-except handling around FTS5 MATCH execution so any syntax anomalies gracefully fall back to chronological recent memory retrieval rather than returning empty result sets.
- **Test Suite Hardening:** Added `test_recall_with_special_punctuation_and_operators` to `tests/test_agent_memory.py` verifying queries with `+`, `-`, `*`, `:`, `^`, `AND`, `OR`, `NOT`, and pure punctuation strings (10/10 passing).

---

### 34. SQLite Concurrency Rate Limiter Atomic UPSERT (`src/key_manager.py` - Issue #329)
- **Eliminated `UNIQUE constraint failed` Race Conditions:** Replaced non-atomic `SELECT` $\to$ `INSERT`/`UPDATE` sequence in `KeyManager.check_rate_limit()` with atomic SQLite `INSERT INTO rate_limits ... ON CONFLICT(key_prefix, minute_timestamp) DO UPDATE SET request_count = request_count + 1`.
- **Concurrent Request Resilience:** Guarantees zero `sqlite3.IntegrityError` collisions when multiple asynchronous requests with identical API keys arrive in the same minute window.
- **Multi-Threaded Test Suite Hardening:** Added `test_concurrent_rate_limiting` to `tests/test_key_manager.py` executing 25 concurrent threads simultaneously without errors (8/8 passing).

---

### 35. Batch LLM Extraction Size Mismatch Itemized Fallback (`src/event_analyzer.py` - Issue #334)
- **Itemized Per-Headline LLM Extraction Fallback:** When batch LLM extraction (`extract_batch_event_features_llm()`) returns a length mismatch (`len(parsed_list) != len(uncached)`) or encounters JSON parsing exceptions, it iterates over each uncached headline and attempts individual LLM extraction (`extract_event_features_llm()`) across the primary/secondary provider tiers before falling back to the zero-cost rule-based lexicon.
- **Cache Persistence & Multi-Tier Cascade:** Individual itemized calls populate both `_LLM_SCORE_CACHE` and `global_cache`, preventing unnecessary repeated API queries and maximizing quantitative feature fidelity.
- **Test Suite Hardening:** Added `test_batch_size_mismatch_itemized_fallback` to `tests/test_event_analyzer.py` simulating truncated batch JSON responses and verifying all items trigger itemized extraction (4/4 passing).

---

### 36. RSS & Atom Diagnostic Health Check Fallback Hardening (`src/intraday_event_monitor.py` - Issue #347)
- **Eliminated `NameError` in Diagnostic Feeds Fallback:** Ensured top-level import of the standard library `re` module in `src/intraday_event_monitor.py` so that `check_feed_health()` regex parsing (`len(re.findall(r'<item>|<entry>', content, re.I))`) executes without throwing exceptions in environments where `feedparser` is not installed.
- **Accurate Diagnostic Classification:** Prevents healthy external RSS (`<item>`) and Atom (`<entry>`) feeds from being erroneously flagged as `FAILED` during diagnostic health probes when running with minimal dependencies.
- **Test Suite Hardening:** Added `test_check_feed_health_rss_fallback_without_feedparser` and `test_check_feed_health_atom_fallback_without_feedparser` in `tests/test_intraday_event_monitor.py` verifying fallback item extraction and `HEALTHY` status classification when `feedparser` is `None` (22/22 passing).

---

### 37. Hindsight Hosted Memory Metrics & Reconciliation Queue Telemetry (`src/hindsight_client.py`, `src/agent_memory.py`, `src/dashboard_generator.py` - Issue #422)
- **Granular Bank Statistics API:** Updated `HindsightClient.get_bank_stats()` to parse `total_observations` and `observations` alongside `memories` and `reflections`, returning standardized metric dictionary `{"memories": int, "observations": int, "reflections": int}`.
- **Connector Event Telemetry Logging:** Integrated `log_connector_event("HindsightHosted", ...)` for all hosted operations (`ping`, `warmup`, `get_bank_stats`), tracking upstream latency, HTTP status codes, and endpoint availability in `data/connector_telemetry.json`.
- **Local Reconciliation Queue Tracking:** Upgraded `SQLiteMemoryStore.get_bank_inventory()` to query `SELECT COUNT(*) FROM memories WHERE cloud_synced = 0`, exposing `pending_reconciliation_count` alongside active observation counts.
- **Telemetry UI Surface:** Enhanced `dashboard_generator.py` to render a 3-badge memory metric grid (Experiences, Observations, Reflections) and a dynamic `Cloud Sync Queue` badge displaying sync status and pending record counts.

---

### 38. Headline Arena Natural Gas (NG) & US Dollar Index (DXY) Daily Challenges (`src/headline_arena_connector.py` - Issue #410)
- **Multi-Asset Continuous Settlement Rules:** Expanded `DEFAULT_SETTLEMENT_RULES` to include `NG` (Henry Hub Natural Gas Futures, dead_zone=0.0050, unit="$/MMBtu") and `DXY` (US Dollar Index, dead_zone=0.0020, unit="pts") alongside `RB` and `CL`.
- **Domain Rationale Synthesis:** Extended `synthesize_forecasting_rationale()` with quantitative and fundamental drivers for Natural Gas (HDD/CDD deviations, EIA working gas storage draws/injections, LNG feedgas flows, Gulf production freeze-offs) and US Dollar Index (Fed interest rate differentials, Treasury yield curves, macro risk-off flows, commodity purchasing power headwinds).
- **Multi-Asset Submission Pipeline:** Updated `submit_midgley_energy_forecasts()` to discover, evaluate, cache, and dispatch continuous probability forecasts for NG and DXY challenges during daily pipeline runs and 30-minute sync loops.

---

### 39. NASA POWER Distillate Climatology & Ethanol Agroclimatology Engine (`src/nasa_power.py` & `src/data_ingestion.py` - Issues #370, #420)
- **NASA POWER Point Daily Client:** Implemented `NASAPowerClient` querying NASA Langley POWER Daily Point API (`https://power.larc.nasa.gov/api/temporal/daily/point`) with zero API key dependencies and automatic 24-hour disk caching at `data/nasa_power_cache.json`.
- **PADD 1 Distillate Heating/Cooling Degree Days:** Ingests daily surface temperatures (`T2M`, `T2M_MAX`, `T2M_MIN`), precipitation (`PRECTOTCORR`), and relative humidity (`RH2M`) across primary Atlantic refining and import terminals (Station `NY_HARBOR`, `DELAWARE_CITY`, `BOSTON`) to compute cumulative Heating Degree Days ($HDD = \max(0, 65 - T_{\text{mean}})$) and Cooling Degree Days ($CDD = \max(0, T_{\text{mean}} - 65)$) for heating oil and ULSD demand modeling.
- **PADD 2 Biofuel Agroclimatology & Corn GDD:** Ingests surface solar irradiance (`ALLSKY_SFC_SW_DWN`), precipitation, and temperature across major Midwest corn/ethanol belts (Station `DES_MOINES_IA`, `PEORIA_IL`, `OMAHA_NE`) to compute Corn Growing Degree Days ($GDD = \max(0, \frac{\min(86, T_{\text{max}}) + \max(50, T_{\text{min}})}{2} - 50)$) and 30-day precipitation anomalies for ethanol feedstock availability and RIN pricing models.

---

### 40. Automated Verification & Regression Test Suite
- **`tests/test_nasa_power.py`:** Validates NASA POWER temperature conversions, degree day formulas (HDD/CDD/GDD), mock API retrieval, disk caching, and PADD 1/PADD 2 feature extraction (8/8 passing).
- **`tests/test_headline_arena_connector.py`:** Validates pending forecast caching, 24h expiration, submitted ledger idempotency, EIA civic challenge payloads, NG/DXY dead-zones, rationale synthesis, and multi-asset dispatching (32/32 passing).
- **`tests/test_agent_memory.py` & `tests/test_memory_telemetry_sync.py`:** Validates Hindsight-Hosted API integration, durable observations parsing, reconciliation queue counting, SQLite FTS5 punctuation sanitization, Retain-Recall-Reflect workflows, and bank inventory telemetry (14/14 passing).
- **`tests/test_intraday_event_monitor.py`:** Validates RSS `<item>` and Atom `<entry>` health check fallbacks without `feedparser`, CoSPOT spectral context generation, multi-provider failovers, publisher suffix normalization, 24h headline deduplication, and locale routing (22/22 passing).
- **`tests/test_event_analyzer.py`:** Validates batch extraction length mismatch itemized fallbacks, single-item parsing, zero-cost lexicon cascade, and spectral context prompt integration (4/4 passing).
- **`tests/test_key_manager.py`:** Validates key creation, PBKDF2 verification, basic/privileged tier permissions, revocation, sliding-window rate limiting, and multi-threaded atomic UPSERT concurrency (8/8 passing).
- **`tests/test_zip_geocoding.py`:** Validates metro cluster hit resolution, state/PADD fallback resolution, unmapped telemetry logging, invalid input fallback, REST API integration, and leading-zero integer zero-padding (6/6 passing).
- **`tests/test_ipasis_security.py`:** Validates private IP bypassing, unconfigured API key allowlisting, clean public IP verification, Tor origin blocking, fail-open resiliency, and telemetry reporting (9/9 passing).
- **`tests/test_static_analysis_gate.py`:** Validates `pyproject.toml` Ruff lint configuration, zero-error codebase check, and intentional undefined variable catch (3/3 passing).
- **`tests/test_multi_horizon_inference_freshness.py`:** Validates unlabelled frame preservation in DataFrame attrs, contemporary $t=0$ live feature extraction in chronological splits, and origin alignment across discrete horizons 1D to 5D (3/3 passing).
- **`tests/test_defusedxml_security.py`:** Validates defusedxml import across all 7 connectors, entity expansion / Billion Laughs payload blocking, and graceful rejection without exceptions (10/10 passing).
- **`tests/test_mlops_prediction_schema.py`:** Validates prediction history schema vectors, baseline quant logging, LLM augmentation deltas, dual win rate reporting, `is_retroactive_backtest` write-time derivation, scoreboard segregation, and model version tagging (10/10 passing).
- **`tests/test_feature_engineering_fusion.py`:** Validates 1-to-1 merge length preservation across multi-event dates, weekend shock forward mapping and aggregation, and continuous calendar decay ratios over 3-day weekends (3/3 passing).
- **`tests/test_check_updates.py`:** Validates RCE prevention, allowlisted action execution, legacy command translation, and insecure URL fallback rejection (4/4 passing).
- **`tests/test_temporal_leakage.py`:** Validates absence of backward filling, $h$-step split boundary purging, train-slice diagnostic computation, stacking CV purging, and chronological ordering (5/5 passing).
- **`tests/test_api_server.py`:** Verifies fail-closed admin secret verification, global API key middleware route enforcement, and scoreboard filtering (23/23 passing).
- **`tests/test_wandb_logger.py`:** Validates multi-region telemetry aggregation and performance table logging (8/8 passing).
- **`tests/test_eia_spot_connector.py`:** Validates daily regional spot price fetching, basis calculations, and vintage persistence (2/2 passing).
- **`tests/test_epa_rin_connector.py`:** Validates EPA EMTS RIN ingestion, dynamic RVO calculation, and biofuel connector integration (3/3 passing).
- **`tests/test_cec_fuels_connector.py`:** Validates California Energy Commission Weekly Fuels Watch ingestion and Thursday vintages (3/3 passing).
- **`tests/test_rvp_regulations.py`:** Validates statutory RVP limits, transition dates, and emergency waiver simulation (5/5 passing).
- **`tests/test_noaa_coops_connector.py`:** Validates NOAA CO-OPS coastal water level fetching and marine risk indices (3/3 passing).
- **`tests/test_eia_retail_feed.py`:** Validates EIA weekly retail ground truth series fetching, vintage persistence, regional price lookup, and fallback handling (5/5 passing).
- **`tests/test_nymex_forward_curve.py`:** Validates NYMEX forward curve connector, calendar spreads, 3-2-1 crack futures, backwardation flags, and feature matrix integration (3/3 passing).
- **`tests/test_dashboard_metrics.py`:** Validates dynamic dashboard metric computation, rolling arrays, sparse data gating, and template rendering without placeholders (5/5 passing).
- **`tests/test_prediction_logger_hardening.py`:** Validates price plausibility checking, Test_Region cleansing, unmapped hub handling without forced UP direction, and EIA ground truth integration (4/4 passing).
- **`tests/test_crack_spread_321.py`:** Validates 3-2-1 crack spread calculation against manual mathematical benchmark ($32.80/bbl, $0.78095/gal) (3/3 passing).
- **`tests/test_model_returns_and_embargo.py`:** Validates return target modeling, price level reconstruction, chronological split embargo gaps, and purged walk-forward RidgeCV hyperparameter tuning (5/5 passing).
- **`tests/test_ci_and_evaluation_coverage.py`:** Validates injectable evaluation under TESTING=1, strict calibrated 95% CI coverage without fallback, residual std horizon scaling, scoreboard empirical coverage metrics, and README updater execution (5/5 passing).
- **`tests/test_prediction_scoreboard.py`:** Validates rolling scoreboard metrics, window filtering, regional breakdowns, discrete horizon breakdowns, and recent evaluated record retrieval (7/7 passing).
- **Total Test Results:** 100% pass rate across all 788 test suites with zero regressions.

