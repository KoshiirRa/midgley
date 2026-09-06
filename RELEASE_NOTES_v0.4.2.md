# Release Notes - v0.4.2

**Release Date:** September 5, 2026  
**Build Target:** `dev-vm` (`10.42.42.54`)  
**Git Branch:** `dev`  

---

## 🚀 Key Features, Bug Fixes & Architectural Enhancements

### 1. Tulsa AAA Scraper Bug Fix & `py-gasbuddy` Integration (Issue #206)
- **GraphQL Fuel Data Ingestion:** Integrated `py-gasbuddy` GraphQL client (`py-gasbuddy>=0.7.1`) in [`src/live_fuel_feed.py`](file:///c:/Users/concentus/Documents/Random%20Ideas%20-%20LLM%20Unleaded%20Gas%20Price%20Prediction%20Modelling/src/live_fuel_feed.py) to resolve HTML structure changes in AAA state average scrapers.
- **Robust Fallback Chain:** Establishes resilient live pump pricing lookups for Tulsa metro and state-level averages with seamless GasBuddy station telemetry fallbacks.

### 2. Baker Hughes Ingestion & Feature Matrix Fix (Issue #203)
- **NameError Resolution:** Fixed `UnboundLocalError`/`NameError` in [`src/alternative_data_feeds.py`](file:///c:/Users/concentus/Documents/Random%20Ideas%20-%20LLM%20Unleaded%20Gas%20Price%20Prediction%20Modelling/src/alternative_data_feeds.py) during Baker Hughes rig count processing.
- **Feature Matrix Alignment:** Preserves drilling rig count features (`baker_hughes_total_rigs`, `baker_hughes_oil_rigs`) in [`src/feature_engineering.py`](file:///c:/Users/concentus/Documents/Random%20Ideas%20-%20LLM%20Unleaded%20Gas%20Price%20Prediction%20Modelling/src/feature_engineering.py), preventing feature drops during baseline quantitative model execution.

### 3. GitHub Actions CI Runner & Node Deprecation Upgrades (Issue #202)
- **Workflow Modernization:** Upgraded Node.js runner environments across all GitHub Actions workflows (`deploy_cloudflare_worker.yml`, `docker_publish.yml`, `gas_price_forecast.yml`, `intraday_event_monitor.yml`, `nightly_dev_release.yml`, `sync_self_hosted.yml`, `weekly_model_review.yml`).
- **Runner Warning Elimination:** Resolves Node 20 runner deprecation warnings, aligning CI automation with supported Node 22/24 execution standards.

### 4. Dynamic Region Runner & Regional Metro Calibration Engine
- **Flexible Metro Profiles ([`src/dynamic_region.py`](file:///c:/Users/concentus/Documents/Random%20Ideas%20-%20LLM%20Unleaded%20Gas%20Price%20Prediction%20Modelling/src/dynamic_region.py)):** Implemented `DynamicRegionRunner` class enabling programmatic instantiation and execution of custom regional metro forecasting pipelines.
- **CLI Region Management ([`scripts/manage_regions.py`](file:///c:/Users/concentus/Documents/Random%20Ideas%20-%20LLM%20Unleaded%20Gas%20Price%20Prediction%20Modelling/scripts/manage_regions.py)):** Created CLI tool to list, add, and evaluate dynamic metro profiles with custom PADD allocations, ZIP anchors, and local tax policies.

### 5. Dynamic Release Banner Version Binding
- **Version Parity ([`src/dashboard_generator.py`](file:///c:/Users/concentus/Documents/Random%20Ideas%20-%20LLM%20Unleaded%20Gas%20Price%20Prediction%20Modelling/src/dashboard_generator.py)):** Bound public web dashboard release headers dynamically to package version (`midgley.__version__`) and environment overrides (`MIDGLEY_BRANCH` / `MIDGLEY_VERSION`), eliminating hardcoded version text drift.

### 6. Automated Model Degradation & Baseline Underperformance Alerting (Issue #210)
- **MLOps Degradation Threshold Check ([`src/weekly_issue_reporter.py`](file:///c:/Users/concentus/Documents/Random%20Ideas%20-%20LLM%20Unleaded%20Gas%20Price%20Prediction%20Modelling/src/weekly_issue_reporter.py)):** Implemented `evaluate_model_degradation_alerts()` to check rolling MAE uplift across all active regions against naive persistence baseline (`model_uplift_mae_pct < 0.0`).
- **Telemetry Alerts Ledger ([`data/telemetry_alerts.json`](file:///c:/Users/concentus/Documents/Random%20Ideas%20-%20LLM%20Unleaded%20Gas%20Price%20Prediction%20Modelling/data/telemetry_alerts.json)):** Logs persistent alert records, active degraded region lists, and timestamps.
- **Webhook & GitHub Issue Alerts:** Dispatches HTTP POST webhook payloads to `MODEL_DEGRADATION_WEBHOOK_URL` and opens GitHub Issues tagged `degradation-alert,modeling,mlops,bug` when model underperformance is detected.
- **Saturday Cloud Review Workflow ([`.github/workflows/weekly_model_review.yml`](file:///c:/Users/concentus/Documents/Random%20Ideas%20-%20LLM%20Unleaded%20Gas%20Price%20Prediction%20Modelling/.github/workflows/weekly_model_review.yml)):** Surfacing alert status in weekly Saturday review reports and committing telemetry alert logs.

### 7. Refine Execution Audit Naming & Headline Sanitization (Issue #204)
- **Dynamic Batch Execution Audit Pipeline Naming:** Updated the audit pipeline header in [`src/dashboard_generator.py`](file:///c:/Users/concentus/Documents/Random%20Ideas%20-%20LLM%20Unleaded%20Gas%20Price%20Prediction%20Modelling/src/dashboard_generator.py) and [`src/weekly_issue_reporter.py`](file:///c:/Users/concentus/Documents/Random%20Ideas%20-%20LLM%20Unleaded%20Gas%20Price%20Prediction%20Modelling/src/weekly_issue_reporter.py) to output dynamic ISO 8601 UTC execution timestamps (`Daily Forecast Batch Execution ({timestamp_utc}) | Weekly Model Review Report`).
- **Strict Headline Prose Sanitization (`is_valid_headline()`):** Implemented strict validation filters in [`src/dashboard_generator.py`](file:///c:/Users/concentus/Documents/Random%20Ideas%20-%20LLM%20Unleaded%20Gas%20Price%20Prediction%20Modelling/src/dashboard_generator.py) and [`src/intraday_event_monitor.py`](file:///c:/Users/concentus/Documents/Random%20Ideas%20-%20LLM%20Unleaded%20Gas%20Price%20Prediction%20Modelling/src/intraday_event_monitor.py) to reject raw REST API endpoints, raw JSON strings, system logs, code snippets, and short non-headline text from entering the intelligence event matrix and public UI dashboard.
- **Human-Readable Feed Source Formatting (`format_human_source()`):** Replaced technical feed identifiers with polished human-readable labels (*Reuters Energy*, *Bloomberg Market Wire*, *NOAA NWS Storm Alert*, *CME Group / NYMEX*, *Google News Energy Feed*) across audit cards and web app components.

### 8. CORE Open-Access Research Paper Monitoring (Issue #53)
- **CORE API V3 Integration (`src/core_monitor.py`):** Integrated the [CORE API](https://core.ac.uk/services/api) (`https://api.core.ac.uk/v3/search/works`) to monitor open-access research papers on energy commodity forecasting, refining rack margins, oil market volatility, and machine learning time-series literature.
- **Weekly Self-Review Reporter Integration (`src/weekly_issue_reporter.py`):** Appends `## 🔬 Relevant CORE Open-Access Research Papers` alongside arXiv research preprints in the Saturday weekly model performance review report.
- **GitHub Workflow Integration (`.github/workflows/weekly_model_review.yml`):** Added `CORE_API_KEY` secret environment variable for execution on GitHub Actions cloud runners.

### 9. GeoPandas Spatial Refinery Distance Buffering Engine for Metro Agents (Issue #95)
- **Core Spatial Buffering Engine (`src/spatial_refinery.py`):** Built `SpatialRefineryEngine` containing WGS84 (`EPSG:4326`) point locations, capacities, PADD regions, and primary locales for 11 key refining hubs, pipelines, and marine terminals.
- **Web Mercator Projection & Multi-Ring Buffer Polygons (`EPSG:3857`):** Generates spatial buffer polygon rings across 5 radii (`25mi`, `50mi`, `100mi`, `250mi`, `500mi`) around refining infrastructure and computes projected spatial distances in miles.
- **Exponential Spatial Attenuation & Shock Multipliers:** Computes exponential spatial decay weight $w(d) = \exp(-d / 150.0)$, attenuating refinery outage shock impacts as distance increases from fence-line rack proximity out to inter-state pipeline boundaries.
- **Spherical Haversine Fallback Engine:** Automatic fallback to mathematical spherical Haversine distance calculations when GeoPandas is uninstalled in lightweight container environments.

### 10. Google TimesFM Foundation Model Integration & Zero-Shot Forecasting Engine (Issues #185 & #112)
- **Core TimesFM Forecaster (`src/timesfm_forecaster.py`):** Built `TimesFMForecaster` class implementing Google Research's decoder-only time-series foundation model supporting `google/timesfm-1.0-200m-pytorch` and `google/timesfm-2.0-500m-pytorch` pretrained checkpoints.
- **Scikit-Learn Estimator & Zero-Shot API:** Features standard `fit(X, y)` and `predict(X)` methods alongside `forecast_zero_shot(history, horizon_len=5)` returning point predictions and P10, P50, P90 quantile uncertainty prediction intervals.
- **Zero-Dependency Analytical Fallback (`AnalyticalZeroShotFallback`):** Built an analytical zero-shot trend-decay and residual variance estimator when PyTorch or `timesfm` packages are omitted in lightweight environments.
- **Zero-Shot Benchmarking Harness:** Systematic zero-shot ablation evaluations comparing TimesFM against Naive Persistence, 5-Day Moving Average, Ridge Regression ($\alpha=10.0$), XGBoost, and Stacking Ensembles across out-of-time test splits.

### 11. Qualitative Intelligence Knowledge Graph & Agent Memory Layer (Issue #116)
- **Zero-Cost Embedded Graph Engine (`src/knowledge_graph.py`):** Built `KnowledgeGraphEngine` using pure Python `NetworkX` graph core with `SQLite` persistent storage (`data/knowledge_graph.db`), ensuring **$0 infrastructure cost**.
- **Automated Petroleum Topology Seeding:** Seeds all 9 refining assets, 4 marine chokepoints, 5 PADD regions, and 6 regional metro hubs on initial startup from `src/spatial_refinery.py`.
- **GraphRAG Subgraph Context Injection (`src/event_analyzer.py`):** Resolves entity nodes from breaking headlines, extracts 2-hop neighborhood subgraphs, and formats standardized `GraphContextSchema` contexts into LLM prompts (`LLM_SINGLE_PROMPT`).
- **Episodic Shock Memory & Precedent Retrieval Engine:** Ingests high-impact event shocks into `kg_memory_shocks`, supporting TF-IDF + graph distance precedent retrieval.
- **REST API & MCP Tooling:** Exposed endpoints (`/api/v1/graph/*`, `/api/v1/memory/*`) and registered MCP tools (`query_knowledge_graph`, `retrieve_event_precedents`).

### 12. Bitemporal Vintage Tracking (`as_of`) for EIA Data Ingestion (Issue #121)
- **Bitemporal EIA Data Architecture (`src/data_ingestion.py` & `src/alternative_data_feeds.py`):** Extended `EIADataConnector` and `EIAStateMetroRetailConnector` methods (`fetch_padd_inventory_and_refinery_data`, `fetch_state_retail_price`, `fetch_metro_retail_price`) to attach explicit publication release timestamps (`as_of`), observation period dates (`valid_date`), and honesty flags (`is_vintage_reconstructed: False` for live queries, `True` for historical backfills).
- **Persistent Vintage Storage (`data/eia_vintages.json`):** Implemented `save_eia_vintage_record()` and `get_eia_vintages_as_of()` static helpers on `EIADataConnector` to save live observation snapshots and enable point-in-time point queries.
- **Point-in-Time Feature Engineering (`src/feature_engineering.py`):** Updated `create_feature_matrix()` to accept an `as_of_cutoff` parameter (`as_of <= target_run_date`), ensuring zero lookahead leakage from restated EIA figures during model retraining and historical backtests.
- **Unit Test Suite (`tests/test_eia_bitemporal_vintages.py`):** Added comprehensive unit test suite covering bitemporal metadata fields, JSON vintage persistence, point-in-time lookup queries, and cutoff feature matrix generation (`4/4 passed`).

### 13. Microsoft Qlib & RD-Agent Architecture Integration (Issue #127)
- **Qlib Symbolic Domain Expression Engine ([`src/qlib_symbolic_engine.py`](file:///c:/Users/concentus/Documents/Random%20Ideas%20-%20LLM%20Unleaded%20Gas%20Price%20Prediction%20Modelling/src/qlib_symbolic_engine.py)):** Implemented AST-parsed safe expression evaluator supporting rolling operators (`Ref`, `Mean`, `Std`, `Delta`, `Roc`, `ZScore`, `Slope`, `Corr`, `Rank`) with point-in-time calculation rules ($d \ge 0$).
- **Autonomous RD-Agent LLM Alpha Factor Miner ([`src/alpha_factor_miner.py`](file:///c:/Users/concentus/Documents/Random%20Ideas%20-%20LLM%20Unleaded%20Gas%20Price%20Prediction%20Modelling/src/alpha_factor_miner.py)):** Gemini 2.5 Flash sub-agent loop for economic hypothesis formulation, symbolic factor formula generation, Information Coefficient ($IC$, Rank $IC$, $IC_{IR}$) evaluation, and redundancy pruning ($|r| > 0.70$), persisting active factors to `data/alpha_factors.json`.
- **Dynamic Data Grouping Domain Adaptation ([`src/ddg_da_adapter.py`](file:///c:/Users/concentus/Documents/Random%20Ideas%20-%20LLM%20Unleaded%20Gas%20Price%20Prediction%20Modelling/src/ddg_da_adapter.py)):** Implemented Qlib DDG-DA framework to cluster non-stationary market regimes via Gaussian Mixture Models (GMM) and compute Gaussian RBF kernel similarity weights to combat concept drift during structural market shifts.
- **Benchmarking & Documentation:** Comprehensive unit tests in [`tests/test_qlib_rd_agent.py`](file:///c:/Users/concentus/Documents/Random%20Ideas%20-%20LLM%20Unleaded%20Gas%20Price%20Prediction%20Modelling/tests/test_qlib_rd_agent.py), evaluation benchmark in [`scripts/benchmark_qlib_rd_agent.py`](file:///c:/Users/concentus/Documents/Random%20Ideas%20-%20LLM%20Unleaded%20Gas%20Price%20Prediction%20Modelling/scripts/benchmark_qlib_rd_agent.py), and technical reference guide in [`docs/qlib_rd_agent_integration.md`](file:///c:/Users/concentus/Documents/Random%20Ideas%20-%20LLM%20Unleaded%20Gas%20Price%20Prediction%20Modelling/docs/qlib_rd_agent_integration.md).

### 14. USGS Water Data API Telemetry & Multi-Regional Hydrological Modeling (Issue #56)
- **Zero-Cost Telemetry Connector ([`src/usgs_water_feed.py`](file:///c:/Users/concentus/Documents/Random%20Ideas%20-%20LLM%20Unleaded%20Gas%20Price%20Prediction%20Modelling/src/usgs_water_feed.py)):** Built `USGSWaterFeedConnector` integrating instantaneous values from the USGS Water Data API (`waterservices.usgs.gov`) across 13 key stations in 6 hydrological clusters (Inland Barge Corridor, Gulf Coast Refining Origin, Bay Area Carquinez Strait, Delaware River/Bay, Tulsa MKARNS, and South Florida Coastal Drainage).
- **Physical Risk Indices:** Extracts streamflow (`00060`), gage height (`00065`), water temperature (`00010`), and specific conductance (`00095`) to compute normalized metrics:
  - `hydrological_barge_bottleneck_index` (Memphis & Cairo low-water draft limits throttle barge capacity by 40%)
  - `gulf_marine_departure_risk_index` (Houston Ship Channel deluge closures & Lower Mississippi salt-wedge intrusion)
  - `carquinez_berthing_risk_index` (Sacramento River atmospheric river runoff & Suisun Bay cooling water salinity)
  - `delaware_refinery_thermal_index` (Summer Delaware River water temps $>28^\circ\text{C}$ degrading cooling tower efficiency)
- **Multi-Regional Calibration:** Fuses live telemetry into regional metro models (`cincinnati`, `newark`, `tulsa`, `oakland`, `port_st_lucie`) and macro feature engineering (`src/feature_engineering.py`).
- **API & MCP Tooling:** Added `GET /api/v1/usgs/water_levels` REST endpoint (`src/api_server.py`), counterfactual simulator scenarios (`houston_ship_channel_closure`, `carquinez_atmospheric_river`, `summer_refinery_thermal_cutback`), and registered MCP tool `get_usgs_water_telemetry` (`src/mcp_server.py`).
- **Comprehensive Verification ([`tests/test_usgs_water_feed.py`](file:///c:/Users/concentus/Documents/Random%20Ideas%20-%20LLM%20Unleaded%20Gas%20Price%20Prediction%20Modelling/tests/test_usgs_water_feed.py)):** 100% test pass rate covering API parsing, risk index calculations, cluster filtering, 15-minute lookup caching, fallback baseline, REST API, and MCP tool execution.

### 15. USGS Earthquake API Telemetry & Multi-Regional Seismic Fuel Market Risk Scoring (Issue #55)
- **Zero-Cost GeoJSON Seismic Connector ([`src/usgs_seismic.py`](file:///c:/Users/concentus/Documents/Random%20Ideas%20-%20LLM%20Unleaded%20Gas%20Price%20Prediction%20Modelling/src/usgs_seismic.py)):** Built `USGSSeismicConnector` querying the USGS Earthquake Web Service (`earthquake.usgs.gov/fdsnws/event/1/query?format=geojson`) across 5 critical refining, pipeline, and storage corridors (`bay_area`, `cushing_ok`, `socal`, `mid_atlantic`, `new_madrid`) within rolling 7-day windows with a 15-minute global TTL cache.
- **3D Hypocentral Attenuation & Peak Ground Acceleration (PGA) Proxy:** Models focal depth $h$ and epicentral distance $d$ to compute hypocentral distance $R = \sqrt{d^2 + h^2}$, geometric attenuation $w(R) = \frac{1}{1 + (R/35)^2}$, and normalized ground shaking intensity $I = 10^{M - M_{\text{base}}} \times w(R)$.
- **Multi-Regional Physical Risk Indices:** Calculates continuous risk scores $\in [0, 1]$ and generates qualitative intelligence shock headlines:
  - `usgs_bay_area_seismic_risk_index`: Monitors Richmond, Martinez, Benicia refineries and SFPP pipeline near Hayward and San Andreas faults.
  - `usgs_cushing_seismic_risk_index`: Monitors Cushing WTI crude storage tank farms, Tulsa, and Ponca City refineries against wastewater injection induced seismicity ($M_{\text{base}}=3.6$).
  - `usgs_socal_seismic_risk_index`: Monitors Torrance, Wilmington, El Segundo, Carson refineries and Carson terminal along Newport-Inglewood fault.
  - `usgs_mid_atlantic_seismic_risk_index`: Monitors Delaware City, Bayway, and Buckeye pipeline along Ramapo seismic zone.
  - `usgs_new_madrid_seismic_risk_index`: Monitors critical mid-continent and cross-Mississippi crude and product pipelines along New Madrid seismic zone.
  - `usgs_composite_seismic_risk_index`: Weighted macro risk index across all monitored corridors.
- **Regional Agent Calibration & Feature Matrix:** Ingests live telemetry into `oakland`, `tulsa`, and `newark` regional models, appending breaking shock headlines when corridor risk $\ge 0.20$, dynamically weighting counterfactual baseline simulations, and integrating macro indices into [`src/feature_engineering.py`](file:///c:/Users/concentus/Documents/Random%20Ideas%20-%20LLM%20Unleaded%20Gas%20Price%20Prediction%20Modelling/src/feature_engineering.py).
- **API & MCP Tooling:** Added `GET /api/v1/usgs/seismic` endpoint ([`src/api_server.py`](file:///c:/Users/concentus/Documents/Random%20Ideas%20-%20LLM%20Unleaded%20Gas%20Price%20Prediction%20Modelling/src/api_server.py)), calibrated `hayward_quake` counterfactual scenario ($+18.5\text{ c/gal}$ wholesale spike), and registered MCP tool `get_usgs_seismic_telemetry` ([`src/mcp_server.py`](file:///c:/Users/concentus/Documents/Random%20Ideas%20-%20LLM%20Unleaded%20Gas%20Price%20Prediction%20Modelling/src/mcp_server.py)).
- **Web App Dashboard Binding:** Bound Physical Hazard Risk Matrix in `docs/oakland.html` to live USGS seismic telemetry status.
- **Comprehensive Verification ([`tests/test_usgs_seismic.py`](file:///c:/Users/concentus/Documents/Random%20Ideas%20-%20LLM%20Unleaded%20Gas%20Price%20Prediction%20Modelling/tests/test_usgs_seismic.py)):** 100% test pass rate across 9 unit and integration tests (distance math, 3D attenuation, GeoJSON parsing, caching, Cushing induced quakes, REST endpoint, and MCP tool execution).

---

## 🧪 Verification & Test Suite Results

- **Full Test Suite Execution on `dev-vm` (`10.42.42.54`):**
  ```bash
  PYTHONPATH=. pytest
  ```
  **Result:** `357 passed` (100% pass rate across all test modules including USGS Earthquake and USGS Water Data telemetry suites).

---

## 📋 Closed & Superseded GitHub Issues
- **Issue #53**: `feat(core-api): Monitor open-access research papers via CORE API during weekly self-review` (Closed as completed)
- **Issue #55**: `[Feature Request] Ingest live USGS Earthquake API feeds for real-time seismic fuel market risk scoring` (Closed as completed)
- **Issue #56**: `feat: Integrate USGS Water Data API Telemetry (api.waterdata.usgs.gov) for Inland Waterway & Refinery Bottleneck Forecasting` (Closed as completed)
- **Issue #95**: `[Feature Request] Implement GeoPandas Spatial Refinery Distance Buffering for Metro Agents` (Closed as completed)
- **Issue #112**: `[Feature Request] Evaluate Google TimesFM Foundation Model for Zero-Shot Gas Price Forecasting` (Closed as completed)
- **Issue #116**: `[Feature Request] Implement Knowledge Graph & Agent Memory Layer for Qualitative Intelligence (Cognee, GraphRAG, Graphiti, Mem0 & Neo4j)` (Closed as completed)
- **Issue #121**: `[Feature Request] Implement Bitemporal Vintage Tracking (as_of) for EIA Data Ingestion` (Closed as completed)
- **Issue #127**: `[Feature Request] Evaluate Microsoft Qlib & RD-Agent Architecture for Automated Alpha Factor Discovery & Dynamic Domain Adaptation` (Closed as completed)
- **Issue #185**: `[Feature Request] Ingest Google TimesFM Foundation Model for Zero-Shot Gas Price Forecasting` (Closed as completed)
- **Issue #202**: `fix(ci): Upgrade Node environment settings & resolve Node 20 runner deprecation warnings` (Closed as completed)
- **Issue #203**: `fix(ingestion): Resolve Baker Hughes NameError and feature matrix drop` (Closed as completed)
- **Issue #204**: `feat(mlops): Refine execution audit naming & sanitize news feed headlines` (Closed as completed)
- **Issue #206**: `fix(scraping): Resolve Tulsa AAA state average scraper bug & integrate py_gasbuddy GraphQL feeds` (Closed as completed)
- **Issue #210**: `feat(mlops): Implement Automated Model Degradation & Baseline Underperformance Alerting` (Closed as completed)
