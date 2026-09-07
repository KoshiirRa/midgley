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

### 16. Multi-Feed Air Quality Ingestion & Industrial Emissions Early Outage Detection (Issue #54)
- **Zero-Cost Multi-Feed AQI Connector ([`src/aqi_feed.py`](file:///c:/Users/concentus/Documents/Random%20Ideas%20-%20LLM%20Unleaded%20Gas%20Price%20Prediction%20Modelling/src/aqi_feed.py)):** Built `AQIFeedConnector` ingesting real-time fine particulate ($\text{PM}_{2.5}, \text{PM}_{10}$) and chemical gas ($\text{SO}_2, \text{NO}_2, \text{O}_3$) metrics from PurpleAir, OpenAQ, EPA AirNow, and WAQI across 15 km fence-line polygons downwind of major refining hubs (`bay_area`, `tulsa`, `delaware_valley`, `tri_state`) with a 15-minute global TTL cache.
- **Statistical Flaring Outage Detection & Wildfire Discrimination:** Computes standardized rolling 30-day $Z$-scores ($Z = (X - \mu) / \sigma$). Flags emergency refinery flaring and FCC unit shutdown events when $Z_{\text{PM2.5}} \ge 3.5$ AND $Z_{\text{SO2}} \ge 2.5$, achieving a 12–24 hour lead time over commercial news, while discriminating against ambient wildfire/wood smoke ($Z_{\text{PM2.5}} \ge 3.5, Z_{\text{SO2}} < 1.5$).
- **Multi-Regional Physical Outage Risk Indices:** Computes continuous normalized outage risk indices $\in [0, 1]$ and estimated rack margin shock impacts ($+\$0.15\text{ to }+\$0.35/\text{gal}$):
  - `aqi_bay_area_outage_risk_index`: Monitors Richmond, Martinez, and Benicia refineries in Contra Costa County.
  - `aqi_tulsa_outage_risk_index`: Monitors West Tulsa HF Sinclair and Ponca City refineries.
  - `aqi_delaware_outage_risk_index`: Monitors Delaware City and Bayway refineries.
  - `aqi_catlettsburg_outage_risk_index`: Monitors Marathon Catlettsburg refinery in Ohio River Valley.
  - `aqi_composite_outage_risk_index`: Weighted macro flaring outage shock index.
- **Regional Agent Calibration & Feature Matrix:** Ingests live telemetry into `oakland`, `tulsa`, `newark`, and `cincinnati` regional models, generating breaking shock headlines when corridor risk $\ge 0.40$, and integrates macro indices into [`src/feature_engineering.py`](file:///c:/Users/concentus/Documents/Random%20Ideas%20-%20LLM%20Unleaded%20Gas%20Price%20Prediction%20Modelling/src/feature_engineering.py).
- **API & MCP Tooling:** Added `GET /api/v1/aqi/live` endpoint ([`src/api_server.py`](file:///c:/Users/concentus/Documents/Random%20Ideas%20-%20LLM%20Unleaded%20Gas%20Price%20Prediction%20Modelling/src/api_server.py)) and registered MCP tool `get_refinery_aqi_anomalies` ([`src/mcp_server.py`](file:///c:/Users/concentus/Documents/Random%20Ideas%20-%20LLM%20Unleaded%20Gas%20Price%20Prediction%20Modelling/src/mcp_server.py)).
- **Comprehensive Verification ([`tests/test_aqi_feed.py`](file:///c:/Users/concentus/Documents/Random%20Ideas%20-%20LLM%20Unleaded%20Gas%20Price%20Prediction%20Modelling/tests/test_aqi_feed.py)):** 100% test pass rate across 14 unit and integration tests (distance math, Z-scores, flaring vs. wildfire discrimination, caching, REST endpoint, and MCP tool execution).
### 17. SEC EDGAR 8-K Refinery Operator Monitor (Issues #69 & #129)
- **Zero-Cost EDGAR Feed (`src/edgar_8k_monitor.py`, `src/sec_edgar_feed.py` & `workers/intraday_monitor_worker.ts`):** Implemented edge-first EDGAR 8-K filing monitor using the SEC EDGAR ATOM RSS API (`cgi-bin/browse-edgar?output=atom`). In production, the Cloudflare Worker (`workers/intraday_monitor_worker.ts`) handles polling and deduplication at the edge via a new `pollEdgar8KFeeds()` function wired into the existing 15-minute cron trigger. The Python module (`src/edgar_8k_monitor.py` / `src/sec_edgar_feed.py`, `EDGAR8KMonitor` class) serves as the origin queue-consumer handler and local dev/fallback harness. Zero new Python dependencies — stdlib only (`urllib`, `xml.etree.ElementTree`, `html.parser`).
- **Target Operators:** `PBF` (PBF Energy — Delaware City, PADD 1B), `DINO` (HF Sinclair — El Dorado/Tulsa, PADD 2), `MPC` (Marathon Petroleum — Catlettsburg, PADD 3/2), `VLO` (Valero — multi-PADD), `PSX` (Phillips 66 — multi-PADD). Configurable via `EDGAR_8K_TICKERS` environment variable / `wrangler.toml` var.
- **22-Keyword Operational Relevance Gate:** Filters ~85% of 8-K filings (earnings, executive appointments, debt issuances) using a keyword gate covering: outage, force majeure, fire, explosion, unplanned shutdown, capacity reduction, turnaround, FCC unit, crude distillation unit, hydrocracker, coker, pipeline, leak, spill, environmental, flaring, evacuation, accident, incident, disruption.
- **Event Pipeline Integration:** Relevant 8-Ks are routed through `process_incoming_headline(source="EDGAR_8K")` into the existing event scoring pipeline, producing `supply_disruption` and `overall_price_pressure` shock vectors. `TRIGGER_KEYWORDS` extended with 5 operator names and 6 operational terms. `resolve_target_locales()` extended with PBF→Newark, HF Sinclair→Tulsa, Marathon→Cincinnati, Valero/PSX→National mappings.
- **Edge Deduplication:** Cloudflare D1 `edgar_8k_seen` table (accession-number keyed, permanent, no TTL) prevents duplicate pipeline ingestion. Local dev path uses `data/edgar_8k_cache.json`.
- **Cloudflare Worker Telemetry:** `edgar_8k_enqueued` events logged to Axiom; per-ticker Sentry error capture; zero latency impact via `ctx.waitUntil()` flush.
- **Credentials:** `SEC_USER_AGENT` (name + email; per EDGAR robots.txt policy; set as `wrangler secret put SEC_USER_AGENT`). No API key, no account, $0.00/mo.
- **Documentation:** `SELF_HOSTING.md` §2 env block + §7 Prompt 3 item 7 (new-region ticker discovery guidance). `AGENTS.md` Agent 1 module list updated.
- **Verification (`tests/test_edgar_8k_monitor.py`):** 7/7 tests passing — relevance gate positive (FCC outage, refinery fire, capacity reduction), relevance gate negative (earnings release, debt issuance), integration pipeline routing gate (`supply_disruption >= 0.40`), and cache persistence deduplication.

### 18. Firecrawl Web Scraping API & Web-to-Markdown Ingestion (Issue #83)
- **Web-to-Markdown Scraper Connector (`src/firecrawl_scraper.py`):** Integrated the Firecrawl API (`https://api.firecrawl.dev/v1/scrape`) to ingest full-text articles from breaking energy media, refinery press releases, and state motor fuel tax portals into clean, structured Markdown with JavaScript rendering support.
- **Hard Quota Safety Valve:** Enforces an **800 call/month safety cap** (and 30 call/day burst limit) on `data/firecrawl_quota.json` out of the 1,000 free tier allowance, safeguarding free credits and routing gracefully to local extraction when caps are reached.
- **24-Hour Multi-Tier Caching:** Persists scraped markdown to `data/firecrawl_cache.json` and in-memory cache keyed by SHA-256 hash of normalized URLs with a 24-hour TTL (86,400s).
- **Deterministic Offline HTML Fallback:** Built-in `SimpleHTMLTextExtractor` ($0 cost, 100% offline) using standard library `urllib` and `html.parser` to strip scripts, styles, navigation, and headers into clean Markdown when API keys are omitted or offline.
- **URL Event Feature Extraction (`src/event_analyzer.py`):** Added `extract_event_features_from_url()` with automatic content truncation (~1,500 words) to protect Gemini Flash token context budgets while enabling full qualitative impact scoring on web articles.
- **Verification (`tests/test_firecrawl_scraper.py`):** 7/7 unit tests passing covering API response parsing, quota safety valve enforcement, cache hit persistence, offline HTML fallback extraction, HTTP error resiliency (429/500), and telemetry accounting.

### 19. U.S. Census Bureau Metro Commuter & Vehicle Availability Ingestion (Issue #75)
- **Zero-Cost Public ACS Connector (`src/census_demographics.py`):** Built `CensusDemographicsConnector` ingesting American Community Survey (ACS 1-Year & 5-Year) tables (`B08201` vehicle availability, `B08301` commute mode split, `B08013` aggregate travel time) across all regional benchmark MSAs (Tulsa, Newark, Cincinnati, Greenville, Oakland, Charlotte, Port St. Lucie).
- **Econometric Derived Metrics:** Computes `vehicle_dependency_ratio`, `vehicles_per_household`, `mean_commute_minutes`, `transit_alternative_index`, and composite `inelastic_demand_score` ($0.0$ elastic to $1.0$ completely captive driving demand) to calibrate retail price pass-through speed and baseline rack margin spreads.
- **Adaptive Annual Release Window Caching:** Features a window-aware caching engine that actively polls daily during the annual September release window (Sept 1–30) for new ACS-1 vintages and locks long-term cache forward (~335+ days until next August 31st) once the new vintage is confirmed ($0 compute/network overhead during standard operation).
- **Regional Profile & Dynamic Calibration Integration:** Enriched all 8 regional JSON profiles in `data/regional_metadata/` and integrated commuter factors directly into `DynamicRegionRunner` (`src/dynamic_region.py`).
- **Comprehensive Verification (`tests/test_census_demographics.py`):** 7/7 unit tests passing covering release window lifecycle, derived econometric metric formulas, live response parsing, deterministic offline fallbacks, and multi-metro resolution.

### 20. EPA AirNow Ground-Level Ozone Alerts & Statutory Summer-Blend RVP Compliance Engine (Issue #73)
- **Zero-Cost EPA AirNow Connector ([`src/aqi_feed.py`](file:///c:/Users/concentus/Documents/Random%20Ideas%20-%20LLM%20Unleaded%20Gas%20Price%20Prediction%20Modelling/src/aqi_feed.py)):** Enhanced `AQIFeedConnector` with full HTTP integration to the official U.S. EPA AirNow API (`airnowapi.org/aq/observation/zipCode/current/`) supporting `AIRNOW_API_KEY`, 1-hour lookup caching (`global_cache`), and deterministic geographic/seasonal offline fallbacks.
- **7-Metro Calibration Coverage:** Mapped official monitoring sites and primary ZIP codes for all 7 regional benchmark hubs (`bay_area` 94612, `tulsa` 74101, `delaware_valley` 19711, `tri_state` 45202, `carolinas_coastal` 27834, `carolinas_piedmont` 28202, `south_florida` 34984).
- **Ozone Action Day Anomaly Gate:** Automatically flags statutory Ozone Action Days when ground-level ozone $\text{AQI}_{\text{O3}} \ge 101$ (Category 3+ "Unhealthy for Sensitive Groups"), adding localized compliance surcharges ($+\$0.040/\text{gal}$) for acute anti-smog and VOC blendstock restrictions.
- **Seasonal Reid Vapor Pressure (RVP) Step Function:** Dynamically computes statutory seasonal RVP specifications and base summer-blend margin surcharges:
  - **CARB Phase 3 (Oakland / Bay Area):** 7.0 psi statutory RVP limit ($+\$0.180/\text{gal}$ baseline summer spread).
  - **EPA Ozone Non-Attainment (Cincinnati / Tri-State):** 7.8 psi statutory RVP limit ($+\$0.085/\text{gal}$ baseline summer spread).
  - **Conventional Baseline (Tulsa, Newark, Greenville, Charlotte, PSL):** 9.0 psi statutory RVP limit ($+\$0.045\text{ to }+\$0.060/\text{gal}$ baseline summer spread).
  - **Seasonal Cutover Calendar:** Summer Blend (May 1 to Sept 15), Spring Butane Drawdown Shoulder (April), Fall Transition Shoulder (Sept 16 to Oct 15), and Winter Blend (Oct 16 to March 31, \$0.00 surcharge).
- **API & MCP Tooling:** Added `GET /api/v1/aqi/ozone-alerts` endpoint in [`src/api_server.py`](file:///c:/Users/concentus/Documents/Random%20Ideas%20-%20LLM%20Unleaded%20Gas%20Price%20Prediction%20Modelling/src/api_server.py) supporting direct ZIP code and regional corridor filters, and registered `get_regional_ozone_alerts` MCP tool in [`src/mcp_server.py`](file:///c:/Users/concentus/Documents/Random%20Ideas%20-%20LLM%20Unleaded%20Gas%20Price%20Prediction%20Modelling/src/mcp_server.py).
- **Feature Matrix & Regional Fusion:** Exposed `aqi_ozone_action_day_count` and `aqi_max_rvp_surcharge_per_gal` in [`src/feature_engineering.py`](file:///c:/Users/concentus/Documents/Random%20Ideas%20-%20LLM%20Unleaded%20Gas%20Price%20Prediction%20Modelling/src/feature_engineering.py).
- **Comprehensive Verification ([`tests/test_aqi_feed.py`](file:///c:/Users/concentus/Documents/Random%20Ideas%20-%20LLM%20Unleaded%20Gas%20Price%20Prediction%20Modelling/tests/test_aqi_feed.py)):** 100% test pass rate across 16 unit and integration tests (mocked live API, 7-metro ZIP resolution, seasonal step function, Ozone Action Day trigger, REST endpoints, and MCP tool execution).

### 21. U.S. Treasury Yield Curve & TIPS Inflation Metrics Ingestion (Issue #66)
- **Zero-Cost U.S. Treasury Fiscal Data API Connector ([`src/treasury_yield_feed.py`](file:///c:/Users/concentus/Documents/Random%20Ideas%20-%20LLM%20Unleaded%20Gas%20Price%20Prediction%20Modelling/src/treasury_yield_feed.py)):** Built `TreasuryYieldConnector` ingests daily nominal Treasury yields (10Y, 2Y) and 10-Year TIPS real yields from the keyless U.S. Treasury Fiscal Data API (`fiscaldata.treasury.gov`), FRED Treasury series, and market proxies ($0 API cost, 24-hour multi-tier caching via `data/treasury_cache.json`).
- **Macroeconomic Yield Spread Dynamics:** Derives the benchmark 10Y-2Y yield curve spread $\text{Spread}_{10\text{Y}-2\text{Y}} = Y_{10\text{Y}} - Y_{2\text{Y}}$ and 5-day spread momentum delta (`treasury_spread_delta_5d`) to model leading recessionary demand contraction and expansionary signals.
- **TIPS Real Rate Financing Proxy:** Captures 10-Year TIPS real rates (`tips_10y_real_yield`) to quantify real cost of physical commodity inventory carry and real USD purchasing power movements.
- **Feature Matrix & Quantitative Splits Fusion:** Integrated into [`src/feature_engineering.py`](file:///c:/Users/concentus/Documents/Random%20Ideas%20-%20LLM%20Unleaded%20Gas%20Price%20Prediction%20Modelling/src/feature_engineering.py) with point-in-time forward-filling and registered under `quant_features` in `prepare_chronological_splits()`.
- **Automated Test Suite ([`tests/test_treasury_yield_feed.py`](file:///c:/Users/concentus/Documents/Random%20Ideas%20-%20LLM%20Unleaded%20Gas%20Price%20Prediction%20Modelling/tests/test_treasury_yield_feed.py)):** 100% test pass rate verifying connector attributes, live and synthetic dataset generation, spread calculations, and feature matrix integration.

### 22. Quantitative Feature Leakage & Factor Decay Auditor (Issue #146)
- **Point-in-Time Temporal Leakage Auditor ([`src/feature_auditor.py`](file:///c:/Users/concentus/Documents/Random%20Ideas%20-%20LLM%20Unleaded%20Gas%20Price%20Prediction%20Modelling/src/feature_auditor.py)):** Built `PointInTimeLeakageAuditor` calculating lead-lag cross-correlations across predictive and lookahead shifts to detect unphysical future returns leakage ($|r| > 0.50$) or inverted lead anomalies across multi-frequency EIA, FRED, NOAA, USDA, and futures series.
- **Multi-Horizon Factor IC & Decay Half-Life Analysis:** Implemented `FactorDecayAuditor` to compute Pearson IC, Spearman Rank IC, and IC Information Ratio ($IC_{IR}$) across forward price horizons $H \in \{1, 3, 5, 10, 14, 20\}$ days, fitting empirical exponential decay half-lives ($t_{1/2} = -\frac{\ln 2}{\lambda}$) to validate qualitative event shock decay priors.
- **Combinatorial Symmetric Cross-Validation & Overfitting Inference:** Implemented `BacktestOverfittingAuditor` computing Probability of Backtest Overfitting (PBO) via CSCV and Deflated Sharpe Ratio (DSR / PSR) adjusting for multiple testing.
- **Standalone CLI Audit Tool ([`scripts/audit_feature_leakage.py`](file:///c:/Users/concentus/Documents/Random%20Ideas%20-%20LLM%20Unleaded%20Gas%20Price%20Prediction%20Modelling/scripts/audit_feature_leakage.py)):** Created executable utility to audit unified feature matrices and output structured summaries (`data/feature_audit_report.json` and Markdown tables).
- **MLOps Weekly Review Integration ([`src/weekly_issue_reporter.py`](file:///c:/Users/concentus/Documents/Random%20Ideas%20-%20LLM%20Unleaded%20Gas%20Price%20Prediction%20Modelling/src/weekly_issue_reporter.py)):** Added automated feature leakage pass rates, PBO percentages, and qualitative factor decay metrics to Saturday weekly performance review issue reports.
- **Automated Test Suite ([`tests/test_feature_auditor.py`](file:///c:/Users/concentus/Documents/Random%20Ideas%20-%20LLM%20Unleaded%20Gas%20Price%20Prediction%20Modelling/tests/test_feature_auditor.py)):** 100% test pass rate across unit tests for synthetic leakage detection, factor decay curve fitting, CSCV PBO estimation, Deflated Sharpe, and full matrix execution.

---

## 🧪 Verification & Test Suite Results

- **Full Test Suite Execution on `dev-vm` (`10.42.42.54`):**
  ```bash
  PYTHONPATH=. pytest
  ```
  **Result:** `395 passed` (100% pass rate across all test modules including Feature Leakage & Factor Decay Auditor, Treasury Yield Curve, Census Demographics, Multi-Feed AQI, USGS Earthquake, USGS Water Data, and EDGAR 8-K test suites).

---

## 📋 Closed & Superseded GitHub Issues
- **Issue #146**: `[Feature Request] Evaluate Lacuna for Quantitative Feature Leakage & Factor Decay Auditing` (Closed as completed)
- **Issue #66**: `[Feature Request] Ingest U.S. Treasury Yield Curve & TIPS Inflation Metrics (Fiscal Data API)` (Closed as completed)
- **Issue #73**: `[Feature Request] Ingest EPA AirNow Ozone Alerts for Summer-Blend Gas Compliance` (Closed as completed)
- **Issue #75**: `[Feature Request] Ingest U.S. Census Bureau Metro Commuter & Vehicle Ownership Metrics` (Closed as completed)
- **Issue #53**: `feat(core-api): Monitor open-access research papers via CORE API during weekly self-review` (Closed as completed)
- **Issue #54**: `feat(aqi): Integrate Independent & Multi-Feed Air Quality Ingestion (PurpleAir, OpenAQ, AirNow) for Refinery Outage Early Detection` (Closed as completed)
- **Issue #55**: `[Feature Request] Ingest live USGS Earthquake API feeds for real-time seismic fuel market risk scoring` (Closed as completed)
- **Issue #56**: `feat: Integrate USGS Water Data API Telemetry (api.waterdata.usgs.gov) for Inland Waterway & Refinery Bottleneck Forecasting` (Closed as completed)
- **Issue #83**: `[Feature Request] Ingest Firecrawl Web-to-Markdown API for LLM Event Extraction` (Closed as completed)
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
- **Issue #129**: `[Feature Request] EDGAR 8-K Refinery Operator Monitor (Operational Disruption Feed)` (Closed as completed)
- **Issue #69**: `[Feature Request] Ingest SEC EDGAR Official Refinery 8-K Outage Filings (sec.gov API)` (Closed as completed)
