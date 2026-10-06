# Release Notes - v0.8.5

Midgley **v0.8.5** is a comprehensive data integrity, econometric calibration, security hardening, and operational resilience release. It eliminates proxy fallbacks in regional evaluation ground truth, establishes authentic retail historical cointegration for the Asymmetric Error-Correction Model (ECM), unifies deterministic ledger primary keys across all storage engines, hardens Cloudflare edge security against token replay, reinforces CI/CD workflow synchronization, and restores Vectorize Hindsight hosted episodic memory ingestion across local dev runners.

---

## 🎯 Highlights & Improvements

### 1. Authentic Ground Truth Regional Price Series & National Fallback Elimination (Issue #608)
- **Authentic EIA Series Mapping**: Updated [`src/eia_retail_feed.py`](src/eia_retail_feed.py) to ingest dedicated official weekly retail gasoline price series from EIA API v2 and FRED:
  - `Tulsa_OK`: `GASREGWOK` (Oklahoma state retail actuals)
  - `Newark_DE`: `GASREGW01B` (Central Atlantic PADD 1B regional actuals)
  - `Cincinnati_OH`: `GASREGWOH` (Ohio state retail actuals)
  - `Cincinnati_KY`: `GASREGWKY` (Kentucky state retail actuals)
  - `Greenville_NC` & `Charlotte_NC`: `GASREGWNC` (North Carolina state retail actuals)
  - `Port_St_Lucie_FL`: `GASREGWFL` (Florida state retail actuals)
  - `Oakland_CA` & `BayArea_CA`: `GASREGWCA` (California state retail actuals)
  - `National`: `GASREGW` (U.S. National city average)
- **Elimination of Silent Fallbacks**: Refactored `evaluate_prediction_accuracy()` in [`src/prediction_logger.py`](src/prediction_logger.py) to strictly require the matched regional series, raising an explicit alerting warning/error when regional actuals are missing rather than quietly falling back to national prices.

### 2. Asymmetric ECM Refactor on Authentic Retail History & Dynamic Model Versioning (Issue #607)
- **Authentic Cointegration History**: Refactored `get_regional_retail_history()` in [`src/asymmetric_ecm.py`](src/asymmetric_ecm.py) to derive cointegrating price series directly from EIA weekly historical series via bitemporal point-in-time interpolation, eliminating artificial wholesale markup proxies.
- **Dynamic Semantic Model Versioning**: Replaced static model version identifiers with dynamic semantic version tags (`v2.1.0-asym-ecm`) resolved via [`src/version.py`](src/version.py).
- **Index-Safe Series Alignment**: Fixed DatetimeIndex vs. Int64Index alignment to ensure NaN-free feature construction during dynamic time-series regressions.

### 3. Unified Canonical Forecast IDs & Deterministic Ledger Deduplication (Issue #602)
- **Standardized Primary Key Formula**: Unified canonical forecast ID hashing across [`src/prediction_logger.py`](src/prediction_logger.py), [`scripts/clean_and_rekey_prediction_history.py`](scripts/clean_and_rekey_prediction_history.py), and [`scripts/migrate_csv_to_turso.py`](scripts/migrate_csv_to_turso.py):
  $$\text{forecast\_id} = \text{SHA256}(\text{target\_date} : \text{region} : \text{model\_version} : \text{horizon\_days}\text{d} : \text{run\_date})[:16]$$
- **Atomic Deduplication**: Added in-memory deduplication and atomic file swapping in `log_prediction()`, preventing duplicate rows across identical forecast targets.

### 4. Geopolitical Feed Archive Recovery & Union Merge Semantics (Issue #603)
- **Lossless Feed Union**: Implemented `merge_historical_geopolitical_records()` in [`src/geopolitical_feeds.py`](src/geopolitical_feeds.py), deduplicating records by deterministic content hashes (`title:published_date`).
- **Archive Restoration**: Rehydrated historical geopolitical context from `data/wayback_archive_cache.json` without introducing lookahead leakage.

### 5. Deterministic Tax Holiday Restoration & Business-Day Evaluation Windows (Issue #601)
- **Ohio HB 519 Sales Tax Holiday**: Corrected statutory tax schedules in [`src/rvp_regulations.py`](src/rvp_regulations.py) to model Ohio's temporary sales tax holiday (August 1–10, 2026), ensuring standard excise rates automatically restore on August 11, 2026.
- **Business-Day Horizon Realization**: Aligned maturity date calculations in [`src/prediction_logger.py`](src/prediction_logger.py) with standard business days (`pd.bdate_range(..., periods=5)`) matching NYMEX market settlement cycles.

### 6. Security Hardening, Token Replay Defense & Secret Hygiene (Issue #605)
- **Cloudflare D1 Replay Invalidation**: Enforced single-use link consumption in [`workers/intraday_monitor_worker.ts`](workers/intraday_monitor_worker.ts) with transactional SQL checks (`INSERT INTO intraday_flag_tokens`).
- **Safe Link Formatting & Webhook Payloads**: Ensured URL query parameters in Discord alert embeds are properly escaped and expanded headline truncation boundaries to preserve high-severity intelligence context.
- **NASA FIRMS Secret Rotation**: Rotated committed API keys and enforced runtime environment variable injection with non-empty validation in [`src/benchmark_updater.py`](src/benchmark_updater.py).

### 7. Workflow Dirty-Tree Guard & Fail-Closed Cloud Synchronization (Issue #606)
- **Safe Dirty-Tree Staging**: Updated `.github/workflows/gas_price_forecast.yml` and `.github/workflows/weekly_model_review.yml` to stage untracked files before running `git status --porcelain`, preventing uncommitted artifact loss.
- **Fail-Closed DB Synchronization**: Configured synchronization scripts to fail closed on database push errors, notifying maintainers via dead-man switch heartbeats (Healthchecks.io).
- **Isolated Headline Arena Jobs**: Decoupled Headline Arena sync into an isolated, non-blocking GitHub Actions workflow.

### 8. Dynamic Narrative Attribution Drivers & KaTeX SRI Hashes (Issue #604)
- **Proportional Model Driver Decomposition**: Refactored [`src/narrative_generator.py`](src/narrative_generator.py) to compute attribution drivers directly from the net forecast delta:
  $$\sum_{i=1}^3 d_i = \Delta_{\text{forecast}}, \quad \operatorname{sgn}(d_i) = \operatorname{sgn}(\Delta_{\text{forecast}})$$
- **Elimination of Static Literals**: Replaced hardcoded accuracy strings (`MAPE: 4.52% | RMSE: $0.1540`) in [`src/dashboard_generator.py`](src/dashboard_generator.py) with dynamic metrics computed from `prediction_history.csv`.
- **Verified Subresource Integrity (SRI)**: Updated KaTeX 0.16.8 CSS and JS hashes in [`src/sources_generator.py`](src/sources_generator.py) and verified against jsdelivr CDN digests.
 
### 9. Vectorize Hindsight Hosted SaaS Synchronization & Runner Resilience (Issue #557 / Operational Fix)
- **Vectorize Hosted SaaS Reconfiguration**: Resolved endpoint divergence where automated local runners on `dev-vm` (`midgley-daily-forecast.service` and `midgley-weekly-review.service`) attempted memory dispatch to a decommissioned Cloud Run endpoint (`https://midgley-hindsight-66up5e6b4a-uc.a.run.app`) returning `HTTP 503`, failing health probes and silently falling back to offline SQLite. Reconfigured `/home/marty/projects/midgley/.env` to point to Vectorize Hosted SaaS (`https://api.hindsight.vectorize.io`) with authenticated API token and `HINDSIGHT_BANK_ID="Midgley"`.
- **Workflow Environment Parity**: Updated [`.github/workflows/weekly_model_review.yml`](.github/workflows/weekly_model_review.yml) to inject missing `HINDSIGHT_API_KEY` and `HINDSIGHT_BANK_ID` secrets into the `Open Weekly GitHub Issue Report & Recommendations` step, ensuring parity across all production review steps.
- **Historical Prediction Anomaly Reconciliation**: Executed [`scripts/reconcile_hindsight_memory.py`](scripts/reconcile_hindsight_memory.py) across the October 1–5, 2026 window, successfully reconciling and dual-dispatching 16 previously un-synced prediction anomalies (`DIRECTIONAL_FLIP` and `LARGE_OVERESTIMATE` shocks) into the `Midgley` cloud memory bank, restoring continuous World Fact extraction.

### 10. Econometric Model Hierarchy & Statistical Superiority Gating (Issue #609)
- **Rectangular Multi-Step Covariance in Clark-West**: Updated `clark_west_test()` in [`src/model_evaluation.py`](src/model_evaluation.py) to use unweighted rectangular covariance estimation across lags $k \in [1 .. h-1]$ for multi-step horizons, eliminating Bartlett window down-weighting on short lags and falling back to Bartlett only if positive semi-definiteness fails.
- **Strictly One-Sided Diebold-Mariano Testing**: Extended `diebold_mariano_test()` with `alternative="greater"` support to test for statistically significant superiority against naive baselines ($H_1: \text{loss}_{\text{naive}} > \text{loss}_{\text{candidate}}$).
- **Price Change Evaluation & Nested CW Scoping**: Refactored `evaluate_5tier_hierarchy()` to evaluate predicted price returns/changes ($\Delta y$) rather than raw price levels, restricted Clark-West testing strictly to nested tiers ($k$ vs $k-1$), and gated Tier promotion on positive persistence uplift and statistically significant one-sided Diebold-Mariano superiority ($p < 0.05$).
- **Multi-Horizon FWER / FDR Corrections**: Implemented `adjust_family_pvalues()` supporting Holm-Bonferroni (Family-Wise Error Rate) and Benjamini-Hochberg (False Discovery Rate) corrections across the full family of evaluated regions $\times$ horizons in [`scripts/evaluate_model_hierarchy.py`](scripts/evaluate_model_hierarchy.py).

### 11. Dynamic Kalman Filter Metro Nowcasting & Production Pipeline Anchoring (Issue #610)
- **Numerical MLE Parameter Estimation**: Implemented full prediction-error log-likelihood evaluation `compute_log_likelihood()` and numerical MLE optimization via `scipy.optimize.minimize(method="L-BFGS-B")` in [`src/metro_nowcast.py`](src/metro_nowcast.py).
- **Observable Reference Error Optimization**: Replaced hardcoded AAA reference noise variance ($\sigma^2_{\text{AAA}} = 0.0025$) with dynamic MLE estimation alongside GasBuddy and EIA measurement error variances and persistent systematic biases.
- **Production Pipeline Anchoring**: Wired `nowcast_metro_price()` into `run_regional_pipeline()` in [`src/locations/runner.py`](src/locations/runner.py), dynamically anchoring starting retail prices to the Kalman-filtered state prior to multi-step horizon forecasting.

### 12. Wholesale RBOB Volatility Engine & Predictive Density Distribution (Issue #611)
- **Analytic Closed-Form CRPS**: Replaced the truncated 200-point trapezoidal approximation in `StudentTPredictiveDistribution` with exact closed-form Continuous Ranked Probability Score (CRPS) for both Student-$t$ (via complete beta functions) and Gaussian distributions (Gneiting & Raftery 2007).
- **Dynamic Conditional Variance Standardization**: Refactored `RBOBVolatilityEngine` to standardize log returns by the time-varying GARCH conditional standard deviation path ($z_t = \varepsilon_t / \sigma_t$) before fitting Student-$t$ tail degrees of freedom ($\nu$).
- **Production Wiring into National Model**: Wired `WholesaleVolatilityEngine` into [`src/locations/national/main.py`](src/locations/national/main.py) and [`src/models.py`](src/models.py) to forecast multi-horizon wholesale predictive density cones (`q01` through `q99`).

### 13. Data Feed Remediation & Midwest Edgeworth Cycle Restoration (Issue #612)
- **Strict Midwestern Edgeworth Cycle Diagnostics**: Refactored `EdgeworthCycleDetector.is_cycling` in [`src/edgeworth_cycle.py`](src/edgeworth_cycle.py) to require strict asymmetry criteria ($\ge 60\%$ negative returns, positive skewness $\ge 0.80$, run length $\ge 2.0$, and $\ge 2$ discrete restoration jumps), preventing false positives on drifting random walks.
- **Restoration Hazard Regularization**: Added feature standardization and L2 regularization to `RestorationHazardModel.fit()`, and wired hazard jump trajectories into [`src/locations/cincinnati/regional.py`](src/locations/cincinnati/regional.py) and [`src/locations/runner.py`](src/locations/runner.py) for hubs with `has_edgeworth_cycles=True`.
- **NASA FIRMS Flaring Telemetry Repair**: Corrected zero detections to mean zero flaring activity (not API errors), computed 7d vs 30d Fire Radiative Power (FRP) anomaly z-scores, and eliminated unkeyed mock records.
- **NOAA Coordinate Hub Routing**: Correctly routed all 10 metro keys to specific refinery/pipeline hub coordinates in `get_hub_coordinates()` in [`src/noaa_weather.py`](src/noaa_weather.py).

### 14. Point-in-Time Cutoff Row Invariance & Test Sandbox Isolation (Issue #613)
- **Cutoff-Row Invariance Remediation**: Audited all live connectors in [`src/feature_engineering.py`](src/feature_engineering.py) (FERC, USGS water/seismic, AQI, CEC, EIA, USDA, NOAA CO-OPS, USACE) and gated `.loc[df.index[-1], ...]` overwrites with `if is_live_inference:`, guaranteeing strict point-in-time invariance between truncated datasets and historical datasets.
- **BSEE Vintage Alignment**: Fixed BSEE offshore shut-in vintage loading to map from `data/bsee_vintages.json`.
- **Production Data Integrity Verification**: Added `verify_data_directory_unpolluted` session fixture in [`tests/conftest.py`](tests/conftest.py) to verify via SHA256 checksums that no tracked files in `data/` or `docs/` are modified during test runs.
- **Value-Level Analytical Math Tests**: Created [`tests/test_value_math.py`](tests/test_value_math.py) covering GARCH variance recursion, closed-form CRPS, Kalman log-likelihood curvature, Clark-West statistics, and FWER/FDR p-value adjustments.

### 15. REST API Security Hardening & Client Resilience (Issue #614)
- **Sliding-Window Rate Limiting**: Added strict sliding-window rate limiters (60s window) across all 49 API routes, 120 RPM unauthenticated IP limiter, and 15 RPM authentication failure brute-force throttle in [`src/api_server.py`](src/api_server.py) and [`src/key_manager.py`](src/key_manager.py).
- **PBKDF2 Verification Caching & Secret Masking**: Added thread-safe PBKDF2 hash cache with LRU eviction and integrated `RedactingLoggingFilter` to redact API keys and bearer tokens from logs.
- **Database Circuit Breaker**: Added consecutive failure tracking and automatic circuit tripping in [`src/db/client.py`](src/db/client.py).
- **Batch Insertion Resilience**: Hardened prediction evaluation batch inserts in [`src/prediction_logger.py`](src/prediction_logger.py) with `WHERE EXISTS (...)` and individual statement fallbacks.

### 16. Component Wiring Audit & Architecture Alignment (Issue #615)
- **Comprehensive Production Caller Audit**: Established active non-test production callers for `metro_nowcast`, `volatility_engine`, `locations/specs`, `edgeworth_cycle`, and `firms_satellite_feed`, verified via automated AST test [`tests/test_caller_audit.py`](tests/test_caller_audit.py).
- **Repo-Wide Version Harmonization**: Aligned version numbers across `pyproject.toml`, `src/__init__.py`, `src/version.py`, `src/http_client.py`, and `RELEASE_MANIFEST.json` to `0.8.5`.

### 17. Official EIA API v2 Weekly Ground Truth & WPSR Supply Fundamentals (Finding 3.1 & 3.2, E-2)
- **EIA API v2 Client Engine**: Built [`src/eia_api_client.py`](src/eia_api_client.py) querying official endpoints (`api.eia.gov/v2/petroleum/pri/gnd/data/` for weekly retail pump prices and `api.eia.gov/v2/seriesid/PET.{id}.W` for Weekly Petroleum Status Report fundamentals).
- **Honest Provenance Tiering**: Ingests official weekly ground truth with transparent geographical tier tags (`EIA_CITY_SanFrancisco` for `EMM_EPMR_PTE_Y05SF_DPG`, `EIA_STATE_OH` for `EMM_EPMR_PTE_SOH_DPG`, `EIA_PADD_1B`, `EIA_PADD_1C`, `EIA_PADD_2`, `EIA_COUNTRY_US`). Non-city targets (`Tulsa_OK`, `Cincinnati_KY`, `Newark_DE`, `Charlotte_NC`, `Greenville_NC`) are honestly labeled at true PADD tier.
- **WPSR Supply Fundamentals Ingestion**: Wired weekly inventory and refinery inputs into [`src/data_ingestion.py`](src/data_ingestion.py): Gulf Coast total gasoline (`WGTSTP31`), PADD 2 inventory (`WGTSTP21`), East Coast inventory (`WGTSTP11`), refinery utilization rates (`W_NA_YUP_R20_PER`, `W_NA_YUP_R30_PER`), and refinery production runs (`WGFUPUS2`).
- **Lookahead-Safe Bitemporal Persistence**: Persists release vintages in `VintageStore` (`data/eia_retail_vintages.json`) with release timing bounds (Tuesdays 15:00 UTC for retail, Wednesdays 15:30 UTC for WPSR).

### 18. USGS River Water Telemetry Migration to OGC API Collection (Finding 3.2)
- **Modern OGC API Collection Endpoint**: Migrated [`src/usgs_water_feed.py`](src/usgs_water_feed.py) and [`src/usace_locks.py`](src/usace_locks.py) to query modern OGC API (`https://api.waterdata.usgs.gov/ogcapi/v1/collections/continuous/items?monitoring_location_number=...&parameter_code=00065&f=json`), completely insulating Midgley from the legacy `waterservices.usgs.gov` sunset and throttling cutoff scheduled for November 16, 2026.
- **Robust GeoJSON Parsing & Fallback**: Added `_parse_usgs_ogc_json()` with automated fallback to legacy JSON during the transition period.
- **Test Sandbox Isolation**: Guarded vintage and benchmark writes with `TESTING == 1` checks to prevent checksum mutation errors in test suites.

### 19. Regional Hub Consolidation: Oakland & SF Bay Area Unified Architecture (Finding 3.7)
- **Canonical Hub Unification**: Unified `REGIONAL_SPECS["bay_area"]` as canonical `BayArea_CA` targeting slug `bay_area` and EIA series `EMM_EPMR_PTE_Y05SF_DPG` in [`src/locations/specs.py`](src/locations/specs.py).
- **Transparent Alias Routing**: Aliased `REGIONAL_SPECS["oakland"] = REGIONAL_SPECS["bay_area"]`, and exported `run_bay_area_pipeline = run_oakland_pipeline` in [`src/locations/__init__.py`](src/locations/__init__.py) and [`src/locations/runner.py`](src/locations/runner.py).
- **Public Dashboard Redirection**: Consolidated Card 5 on index to *"SF Bay Area, CA (incl. Oakland)"*, and refactored `build_oakland_html()` in [`src/dashboard_generator.py`](src/dashboard_generator.py) to generate an instant HTTP refresh/canonical redirect stub at `docs/oakland.html` pointing to `bayarea.html`.

### 20. Statutory Tax Rates, Provenance Attribution & Event Transparency (Findings T-1, T-4)
- **Provenance-Enriched Events**: Enriched all statutory rows in [`data/known_future_events.json`](data/known_future_events.json) with verified `source_url` and `announced_on` provenance metadata.
- **Verified Statutory Actions**:
  - Ohio HB 519 statutory motor fuel tax holiday ($-0.385$/gal effective 12:01 a.m. 4 Oct 2026 through 11:59 p.m. 2 Jan 2027; restoration effective 3 Jan 2027; source: Ohio Dept of Taxation).
  - California SB 1 annual statutory inflation reset (+2.2¢/gal effective 1 Jul 2026; CDTFA L-1025).
  - North Carolina formula adjustment (+0.7¢/gal effective 1 Jan 2026; NCDOR).

### 21. Exchange Trading Calendar & NYMEX RBOB Contract Roll Boundary Detection (Findings A-5, A-8)
- **Deterministic NYMEX Trading Calendar**: Implemented [`NYMEXTradingCalendar`](src/market_calendar.py) in [`src/market_calendar.py`](src/market_calendar.py) with CME Globex holiday schedules (New Year's, MLK, Presidents' Day, Good Friday, Memorial Day, Juneteenth, July 4, Labor Day, Thanksgiving, Christmas) and Gregorian Easter computation.
- **RBOB Contract Roll Boundary Detection**: Implemented `get_rbob_contract_expiry()` calculating exact NYMEX contract termination dates (last business day of month preceding delivery month) and `is_roll_straddling()` detecting forecast windows straddling contract roll boundaries.
- **Production Forecasting & Logger Integration**: Replaced naive `bdate_range` in [`src/models.py`](src/models.py) and [`src/prediction_logger.py`](src/prediction_logger.py) with `get_trading_calendar().get_target_date_for_horizon(...)`, logging explicit warnings and setting `is_roll_straddling` flags when multi-day forecast horizons cross monthly roll expirations.

### 22. Preservation of Live Scraping Channels (AAA & GasBuddy)
- **Commercial Boundary Respect**: In accordance with project instructions, kept live retail fuel scraping channels in [`src/live_fuel_feed.py`](src/live_fuel_feed.py) operational without premature deprecation, while maintainers coordinate directly with OPIS.

### 23. Production Wiring of Pirate Weather Telemetry & Reanalysis Engine (Issue #442)
- **Dual-Endpoint Routing Architecture**: Resolved Pirate Weather API past vs current routing in [`src/noaa_weather.py`](src/noaa_weather.py) by routing timestamps in the past (>2 hours ago) to `https://timemachine.pirateweather.net/forecast/...` while current/forecast queries use `https://api.pirateweather.net/forecast/...`, eliminating HTTP 400 rejection on historical queries.
- **Production Feature Engineering Ingestion**: Wired `PirateWeatherConnector` into `create_feature_matrix()` in [`src/feature_engineering.py`](src/feature_engineering.py) across all 8 refining hub coordinates, injecting live heating degree days (`hdd_daily`), cooling degree days (`cdd_daily`), and freeze warning flags (`freeze_warning_flag`) with automated fallback to `OpenMeteoDegreeDaysConnector`.
- **Scenario Simulation Polar Freeze Hook**: Integrated live telemetry into `_evaluate_live_telemetry_trigger()` in [`src/scenario_engine.py`](src/scenario_engine.py) to evaluate refinery freeze-off risk (`freeze_off_risk_index`) and sub-freezing temperatures for `polar_vortex_freeze` scenario gating.
- **MCP & REST API Exposure**: Added MCP tool `get_pirate_weather_telemetry` in [`src/mcp_server.py`](src/mcp_server.py) and REST route `GET /api/v1/weather/pirate` in [`src/api_server.py`](src/api_server.py).
- **Test Sandbox Integrity**: Guarded all vintage writes with `TESTING=1` checks and isolated fixtures in `tests/conftest.py`, ensuring zero file mutation in tracked repositories.

---

## 📦 Closed Issues & Findings

| Issue / Finding | Title | Component |
| :--- | :--- | :--- |
| **#442** | `feat(weather): Wire Pirate Weather connector into feature engineering, scenario simulation, and MCP/REST API` | Weather / Feature Engineering |
| **#601** | `fix(regulations): Correct tax calendar for Ohio holiday & statutory rates, and align calendar vs business-day evaluation window` | Regulations / MLOps |
| **#602** | `fix(data-integrity): Unify forecast ID generation across logger, re-keying, and Turso migration to prevent ledger duplication` | Data Integrity / Ledger |
| **#603** | `fix(data-ingestion): Fix geopolitical feed refresh data truncation and repair headline deduplication logic` | Data Ingestion / NLP |
| **#604** | `fix(dashboard): Ground narrative card attribution drivers in computed model SHAP/linear impacts and verify KaTeX SRI hashes` | Dashboard / Presentation |
| **#605** | `fix(security): Harden intraday flag links, enforce D1 replay table, fix headline truncation, and rotate committed FIRMS key` | Security / Edge |
| **#606** | `fix(workflows): Fix dirty-tree guard, isolate Headline Arena sync, and ensure resilient forecast ledger commits` | CI/CD / Workflows |
| **#607** | `fix(modeling): Reconcile asymmetric ECM retail forecasting with genuine retail price history and distinct model versioning` | Econometrics / Modeling |
| **#608** | `fix(ground-truth): Ingest authentic regional retail gasoline price series and eliminate cross-geography fallbacks` | Ground Truth / EIA |
| **#609** | `fix(econometrics): Standardize Clark-West covariance, one-sided Diebold-Mariano testing, and multi-horizon FWER/FDR adjustments` | Econometrics / Evaluation |
| **#610** | `fix(nowcast): Standardize state-space nowcast likelihood, reference observation variance estimation, and production wiring` | Nowcasting / State-Space |
| **#611** | `fix(volatility): Standardize RBOB volatility distribution engine, closed-form CRPS, and production density cone forecasting` | Volatility / Predictive Density |
| **#612** | `fix(data-feeds): Repair FIRMS flaring anomaly telemetry, coordinate hub routing in weather, and Midwestern cycle modeling` | Data Ingestion / Feeds |
| **#613** | `fix(testing): Ensure cutoff-row point-in-time invariance, isolate test environment sandbox, and add value-level math tests` | Testing / Quality Assurance |
| **#614** | `fix(api): Harden API server rate limiting, PBKDF2 auth cache, SQLite circuit breaker, and evaluation batch inserts` | API / Security / Database |
| **#615** | `docs(alignment): Audit component production callers, harmonize versioning to v0.8.5, and update multi-agent specifications` | Architecture / Documentation |
| **Finding 3.1 / 3.2** | `feat(eia): Implement official EIA API v2 client and weekly retail ground truth with WPSR supply fundamentals` | Data Ingestion / EIA Client |
| **Finding 3.2** | `feat(usgs): Migrate USGS water telemetry to OGC API continuous items endpoint ahead of sunset deadline` | Hydrology / Navigation |
| **Finding 3.7** | `refactor(locations): Merge Oakland and Bay Area into canonical BayArea_CA hub with oakland.html redirect` | Locations / Dashboard |
| **Finding T-1 / T-4** | `docs(taxes): Enrich statutory tax events in known_future_events.json with source URLs and announcement dates` | Regulations / Provenance |
| **Finding A-5 / A-8** | `feat(calendar): Implement NYMEXTradingCalendar with CME holiday schedules and RBOB contract roll boundary detection` | Market Calendar / Models |
| **Finding E-2** | `docs(governance): Document strict non-commercial policy and honest labeling of macro PADD regional actuals` | Governance / Documentation |
