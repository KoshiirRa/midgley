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

---

## 🧪 Verification & Test Suite Results

- **Full Test Suite Execution on `dev-vm` (`10.42.42.54`):**
  ```bash
  PYTHONPATH=. pytest
  ```
  **Result:** `334 passed` (100% pass rate across all 334 test modules).

---

## 📋 Closed & Superseded GitHub Issues
- **Issue #53**: `feat(core-api): Monitor open-access research papers via CORE API during weekly self-review` (Closed as completed)
- **Issue #95**: `[Feature Request] Implement GeoPandas Spatial Refinery Distance Buffering for Metro Agents` (Closed as completed)
- **Issue #112**: `[Feature Request] Evaluate Google TimesFM Foundation Model for Zero-Shot Gas Price Forecasting` (Closed as completed)
- **Issue #116**: `[Feature Request] Implement Knowledge Graph & Agent Memory Layer for Qualitative Intelligence (Cognee, GraphRAG, Graphiti, Mem0 & Neo4j)` (Closed as completed)
- **Issue #121**: `[Feature Request] Implement Bitemporal Vintage Tracking (as_of) for EIA Data Ingestion` (Closed as completed)
- **Issue #185**: `[Feature Request] Ingest Google TimesFM Foundation Model for Zero-Shot Gas Price Forecasting` (Closed as completed)
- **Issue #202**: `fix(ci): Upgrade Node environment settings & resolve Node 20 runner deprecation warnings` (Closed as completed)
- **Issue #203**: `fix(ingestion): Resolve Baker Hughes NameError and feature matrix drop` (Closed as completed)
- **Issue #204**: `feat(mlops): Refine execution audit naming & sanitize news feed headlines` (Closed as completed)
- **Issue #206**: `fix(scraping): Resolve Tulsa AAA state average scraper bug & integrate py_gasbuddy GraphQL feeds` (Closed as completed)
- **Issue #210**: `feat(mlops): Implement Automated Model Degradation & Baseline Underperformance Alerting` (Closed as completed)
