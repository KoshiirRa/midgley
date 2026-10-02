# Release Notes - v0.8.4

Midgley **v0.8.4** is an econometric modeling and state-space estimation release, establishing asymmetric wholesale-to-retail error correction as the primary regional forecaster, delivering mixed-frequency Kalman filter metro nowcasting, embedding deterministic forward tax and regulatory calendars, and enforcing field-level spot price provenance.

---

## 🎯 Highlights & Improvements

### 1. Asymmetric Pass-Through ECM Core Forecaster (Issue #443)
- **Shared Econometric Core**: Wired [`AsymmetricECM`](src/asymmetric_ecm.py) as the foundational retail price estimator inside [`src/locations/runner.py`](src/locations/runner.py), replacing legacy synthetic return heuristics (`RBOB + current_margin`) across all 7 regional metro calibration hubs.
- **Two-Step Engle-Granger Cointegration**:
  $$\text{Long-Run Equilibrium: } r_t = c + \beta\, w_t + \tau_t + z_t$$
  $$\text{Dynamic Pass-Through: } r_{t+h} - r_t = a_h + \sum_{k=0}^K \left(g^+_{h,k}\Delta w^+_{t-k} + g^-_{h,k}\Delta w^-_{t-k}\right) + b_h z_t + \Delta \tau_{t \to t+h} + e_{t+h}$$
- **California Multiplicative Sales Tax Scaling**: Integrated statutory sales tax scaling $((r_t + \tau_{\text{excise}}) \cdot (1 + \tau_{\text{sales}}))$ for California metro pipelines (Oakland and SF Bay Area).
- **Direct Multi-Horizon Forecasting**: Added `forecast_horizon()` supporting direct $h \in [1..5]$ multi-day forward projections with asymmetric cost pass-through speeds ($g^+ > g^-$).

### 2. Mixed-Frequency Kalman Filter Metro 'True Price' Nowcast Engine (Issue #445)
- **Local-Level State-Space Modeling**: Added [`src/metro_nowcast.py`](src/metro_nowcast.py) implementing a pure NumPy/SciPy local-level Kalman filter and Rauch-Tung-Striebel (RTS) smoother:
  $$x_t = x_{t-1} + \eta_t, \quad \eta_t \sim \mathcal{N}(0, q)$$
  $$y_t^{(s)} = x_t + b_s + \varepsilon_t^{(s)}, \quad \varepsilon_t^{(s)} \sim \mathcal{N}(0, \sigma_s^2), \quad s \in \{\text{AAA}, \text{GasBuddy}, \text{EIA}\}$$
- **Bitemporal Nowcast vs. Evaluation Split**:
  - Point-in-time filtered state $\hat{x}_{t|t}$ serves as the authoritative live prospective base price.
  - Fixed-interval smoothed state $\hat{x}_{t|T}$ ($T > t+h$) provides matured evaluation ground truth.
- **Maximum Likelihood Calibration**: Fits source-specific biases ($b_s$) and measurement variances ($\sigma_s^2$), eliminating source mismatches between daily scrapers and weekly EIA surveys.

### 3. Forward Regulatory & Statutory Tax Covariates Registry (Issue #451)
- **Deterministic Forward Calendar (`data/known_future_events.json`)**: Tracks effective dates, regional target scopes, event classifications (excise tax rate indexing, summer RVP 7.4/6.99 psi compliance, winter transition, holiday settlement rolls), and dollar rate shifts ($\Delta \tau$).
- **Covariates Engine (`src/rvp_regulations.py`)**: Added `get_known_future_tax_deltas()` and `get_forward_regulatory_covariates()`, injecting forward statutory adjustments into multi-day horizon pipelines ($t \in [t, t+h]$).

### 4. Field-Level Wholesale Spot Price Provenance Engine (Issue #480)
- **Granular Data Provenance**: Enhanced `fetch_regional_wholesale_spot_matrix()` in [`src/data_ingestion.py`](src/data_ingestion.py) to tag every physical spot benchmark column with explicit field-level provenance metadata (`OBSERVED`, `ESTIMATED_PROXY`, `SYNTHETIC_FALLBACK`).
- **Lookahead & Leakage Safety**: Preserved strict publication lag enforcement ($T+1$ business days) across bitemporal vintage querying.

### 5. Wholesale RBOB Volatility Distribution & Predictive Density Engine (Issue #448)
- **GARCH(1,1) & GJR-GARCH Leverage Modeling**: Added [`src/volatility_engine.py`](src/volatility_engine.py) to forecast conditional variance paths and multi-step cumulative horizon volatility $\sigma_{t,h} = \sqrt{\sum_{k=1}^h \sigma^2_{t+k|t}}$ for wholesale RBOB futures.
- **HAR-RV Multi-Scale Realized Volatility**: Implemented Heterogeneous Autoregressive Realized Volatility model fusing Daily (1d), Weekly (5d), and Monthly (22d) variance components.
- **Fat-Tailed Student-$t_\nu$ Predictive Density**: Quantifies parametric return quantiles ($q_{0.01} \dots q_{0.99}$) with calibrated degrees of freedom $\nu$, Probability Integral Transform (PIT) uniformity validation, and Continuous Ranked Probability Score (CRPS) evaluation.

### 6. Edgeworth Price Cycle Diagnostics & Restoration-Hazard Model (Issue #447)
- **Microstructure Asymmetry Diagnostics**: Added [`src/edgeworth_cycle.py`](src/edgeworth_cycle.py) detecting Midwestern cycling regimes using negative price change fractions ($\rho_{\text{neg}} > 0.60$), strong positive skewness ($\gamma_1 > 1.0$), and consecutive undercutting run lengths.
- **Logistic Restoration Hazard Modeling**: Computes cumulative spike probability $P_{t,h} = \operatorname{logit}^{-1}(a + b\, m_t + c\, d_t)$ driven by margin compression $m_t$ and elapsed days $d_t$.
- **Cincinnati Regional Integration**: Integrated restoration-hazard forecasting into [`src/locations/cincinnati/regional.py`](src/locations/cincinnati/regional.py) to model sharp coordinated price jumps and daily undercutting trajectories.

### 7. Pirate Weather API Historical Reanalysis Connector (Issue #442)
- **Point-in-Time NOAA HRRR / ERA5 Reanalysis**: Implemented `PirateWeatherConnector` in [`src/noaa_weather.py`](src/noaa_weather.py) querying Dark Sky-compatible hourly/daily reanalysis across exact refinery and pipeline logistics hub coordinates.
- **Multi-Year Weather Shock Calibration**: Computes freeze-off duration hours ($T \le 32^\circ\text{F}$) and extreme heat stress hours ($T \ge 95^\circ\text{F}$) for retrospective econometric backtesting, with bitemporal persistence in `data/pirateweather_vintages.json` and 3-tier lookup caching.

### 8. Unified EIA Retail Diesel Series Key Mappings (Issue #478)
- **Canonical Diesel Series Registry**: Added dual-key mappings for `_ULSD` and `_Diesel` aliases in [`src/eia_retail_feed.py`](src/eia_retail_feed.py) across all 8 regional diesel markets (`National`, `Tulsa`, `Newark`, `Cincinnati`, `Greenville`, `Charlotte`, `Oakland`, `Port_St_Lucie`).
- **Automated Actuals Backfill**: Aligned Monday survey observation dates to eliminate unmapped series and ensure seamless point-in-time actuals matching in [`src/prediction_logger.py`](src/prediction_logger.py).

### 9. Automated Narrative Synthesis & Dynamic Model Explanation (Issue #493)
- **Plain-English Multi-Market Prose**: Created [`src/narrative_generator.py`](src/narrative_generator.py) synthesizing natural language market explanations across Main (`index.html`), National (`national.html`), and all 8 regional metro pages (`tulsa.html`, `newark.html`, `cincinnati.html`, `greenville.html`, `charlotte.html`, `port_st_lucie.html`, `oakland.html`, `bayarea.html`).
- **Tri-Factor Decomposition**: Deconstructs 5-day price projections into:
  1. *Quantitative Baseline Mechanics* (AR momentum, crack margin mean-reversion, calendar spreads).
  2. *Qualitative & Midstream Logistics* (river barge tow drafts, pipeline batch allocations, waterborne freight).
  3. *Regional Regulatory & Infrastructure Context* (CARB LCFS/Cap-Trade, RVP summer blend countdowns, Edgeworth restoration hazard).
- **Responsive Dark-Themed UI Cards**: Rendered standardized Tailwind CSS visual summary cards with direction badges, catalyst tags, and key attribution breakdowns embedded across public dashboard templates.

### 10. NASA FIRMS Active Fire Satellite Telemetry & Topological Outage Exposure (Issue #453)
- **NASA FIRMS Active Fire Satellite Connector**: Created [`src/firms_satellite_feed.py`](src/firms_satellite_feed.py) querying the NASA Fire Information for Resource Management System (FIRMS) API across MODIS (`MODIS_NRT`) and VIIRS (`VIIRS_NOAA20_NRT`, `VIIRS_SNPP_NRT`) thermal anomaly products over major refining clusters (Gulf Coast, Bay Area, Philadelphia/Delaware, Mid-Continent, Midwest).
- **Thermal Anomaly Rolling Z-Score**: Computes normalized 7-day vs 30-day thermal brightness anomalies ($\Delta_{\text{thermal}} = (F_{7\text{d}} - \mu_{30\text{d}}) / \sigma_{30\text{d}}$) with bitemporal persistence in `data/firms_satellite_vintages.json`.
- **Topological Supply Network Outage Exposure**: Added `compute_metro_outage_exposure_index()` to `KnowledgeGraphEngine` in [`src/knowledge_graph.py`](src/knowledge_graph.py) computing exact topological supply exposure $X_{r,t} = \sum_{k \in \mathcal{K}} s_{r,k} \cdot \frac{\text{offline\_cap}_{k,t}}{\text{nameplate\_cap}_k}$, routing multi-source pipeline and waterborne outage shocks into localized retail estimators.

### 11. Pipeline Failure Gating & Non-Zero Exit Code Propagation (Issue #483)
- **Strict Pre-Artifact Failure Gate**: Refactored [`run_all.py`](run_all.py) to halt pipeline execution *before* updating `README.md` or generating public GitHub Pages dashboard artifacts if any location forecast model fails, preventing corrupted or stale artifacts from being published.
- **Fail-Fast CLI Override**: Added `--allow-partial` flag for localized debugging and testing, while enforcing strict fail-fast non-zero exit code (`sys.exit(1)`) in production CI/CD workflows.
- **Exporter Error Propagation**: Wrapped README updating, dashboard compilation, Cloud DB sync, and Headline Arena export in try/except blocks to record and propagate downstream non-zero exit codes.

### 12. Wayback Machine SPN2 Auth & HTTP 429 Pre-Flight Circuit Breaker (Issue #491)
- **Availability Pre-Flight Check**: Refactored [`src/wayback_archiver.py`](src/wayback_archiver.py) to query the Wayback Availability API (`archive.org/wayback/available?url=...`) before attempting snapshot writes, eliminating unnecessary SPN write requests for already-archived URLs.
- **Save Page Now 2 (SPN2) S3 Auth**: Added support for authenticated SPN2 requests via `WAYBACK_ACCESS_KEY` and `WAYBACK_SECRET_KEY` headers, unlocking higher rate limits and priority archiving queues.
- **15-Minute Adaptive Circuit Breaker & Retry Cooldown**: Enforces strict 3.0s minimum spacing between writes, trips a 15-minute circuit breaker on HTTP 429 rate limit responses, and enforces a 1-hour self-healing cache TTL on failed attempts.

### 13. Unified HTTP Client & Resilient Session Factory (Issue #564)
- **Standardized Session Factory**: Implemented [`src/http_client.py`](src/http_client.py) configuring `requests.Session` with `urllib3.util.Retry` exponential backoff across HTTP 429, 500, 502, 503, and 504 status codes.
- **Connection Pooling & Timeout Enforcement**: Enforces default connection (3.05s) and read (20.0s) timeouts via `TimeoutHTTPAdapter` and standardized User-Agent (`Midgley-Energy-Analytics/0.8.4`).

### 14. Syndicated Headline Deduplication & Idempotent Archiving (Issue #566)
- **Canonical Normalization & Token Jaccard Filter**: Added URL tracking parameter stripping (`normalize_url`) and headline token Jaccard similarity filtering ($\ge 0.85$) in [`src/geopolitical_feeds.py`](src/geopolitical_feeds.py).
- **Idempotent Historical Persistence**: Prevents duplicate syndicated wire stories from saturating event memory and stops self-appending growth in `data/geopolitical_historical.json`.

### 15. Multi-Tiered Baker Hughes Rig Count Connector & Centralized DB Storage (Issue #555)
- **Multi-Tiered Ingestion**: Refactored `BakerHughesDataConnector` in [`src/alternative_data_feeds.py`](src/alternative_data_feeds.py) supporting:
  1. *Tier 1 (Official Primary):* Direct weekly table scraping from `https://rigcount.bakerhughes.com/` and `/na-rig-count` via `FirecrawlConnector`.
  2. *Tier 2 (Secondary Web):* Barchart cmdty fundamental overview extraction from `https://www.barchart.com/cmdty/data/fundamental/explore/BH` via `FirecrawlConnector`.
  3. *Tier 3 (Open Machine-Readable):* Active St. Louis Fed FRED rotary rig series (`OGUSROTRIG` - Total US Rotary Rigs, `OILRIGS` - Oil Rigs) for zero-cost, API-key-free CSV ingestion.
- **Centralized Database Storage (`data_vintages` table)**: Persists all observations to SQLite/Turso via `VintageStore.record_observation(feed="baker_hughes", entity="us_rotary_rigs", ...)` with quality classification (`LIVE`, `CACHED`, `BENCHMARK`) and bitemporal file mirroring.
- **Feature Momentum**: Computes rolling 1-week and 4-week rig deltas ($\Delta_{1\text{w}}, \Delta_{4\text{w}}$) and Permian basin concentration metrics.

### 16. Point-in-Time Truncation-Invariance Regression Test Harness (Issue #568)
- **Zero-Lookahead Leakage Verification**: Implemented [`tests/test_truncation_invariance.py`](tests/test_truncation_invariance.py) proving mathematically that feature matrices computed on truncated historical timelines ($t \le T_0$) vs full timelines ($t \le T_0 + k$) are byte-identical for all common observation dates across technical, physical, and qualitative event channels.

### 17. Self-Hosted Deployment Concurrency Locking & API Reader Hardening (Issue #425)
- **Advisory File Locking Barrier**: Serialized self-hosted runners (`scripts/run_local_daily_forecast.sh`, `scripts/run_local_intraday_polling.sh`, and `scripts/run_local_weekly_review.sh`) via `flock -w 900 /tmp/midgley-data.lock` barriers, eliminating multi-process lost-update collisions on `data/`.
- **API Reader Fault Tolerance**: Hardened `src/api_server.py` against empty/missing history files with graceful structured fallback handling and designated root `api_server.py` as an entrypoint proxy.

### 18. Declarative RegionSpec Registry & Universal Runner (Issue #561)
- **Strongly-Typed RegionSpec Dataclass**: Added [`src/locations/specs.py`](src/locations/specs.py) defining a unified dataclass capturing all regional metadata, EIA ground truth series mappings, wholesale spot benchmark columns, baseline tax burdens, and microstructure flags (`has_edgeworth_cycles`, `has_carb_compliance`) across all 8 metro hubs.
- **Universal Regional Dispatcher**: Enhanced [`src/locations/runner.py`](src/locations/runner.py) to resolve regional execution dynamically from declarative specs while preserving 100% backward compatibility for per-metro entrypoints.

### 19. Dynamic Sliding-Window Rate Limiting & Bounded Query Validation (Issue #571)
- **Dynamic Rate Limit Middleware**: Injected HTTP middleware in [`src/api_server.py`](src/api_server.py) dynamically returning `X-RateLimit-Limit`, `X-RateLimit-Remaining`, and `X-RateLimit-Reset` response headers on authenticated calls.
- **Strict Query Bounds**: Enforced bounded query validation (`days` 1..30, `window` 1..365, `locales` $\le 10$, `hops` 1..5) with HTTP 422 Unprocessable Entity error handling.

### 20. Subresource Integrity (SRI), Strict CSP & Secret Redaction (Issue #570)
- **Subresource Integrity Hashes**: Added cryptographic SRI hashes (`integrity="sha384-..."`, `crossorigin="anonymous"`) across KaTeX math rendering, Leaflet maps, and FontAwesome icons in [`src/dashboard_generator.py`](src/dashboard_generator.py) and [`src/sources_generator.py`](src/sources_generator.py).
- **Strict Content-Security-Policy**: Enforced standardized `<meta http-equiv="Content-Security-Policy">` protection across public dashboard pages.
- **Automated Secret Redaction**: Added `redact_secrets()` in [`src/key_manager.py`](src/key_manager.py) to prevent unintentional credential leakage in logs and telemetry.

### 21. Automated 5-Tier Nested Model Evaluation & Clark-West Tests (Issue #567)
- **Clark-West (2007) Hypothesis Testing**: Implemented `clark_west_test()` in [`src/model_evaluation.py`](src/model_evaluation.py) adjusting for parameter noise in nested model comparisons.
- **Multiplicity Control**: Added step-down Holm-Bonferroni Family-Wise Error Rate (FWER) and step-up Benjamini-Hochberg False Discovery Rate (FDR) multiplicity adjustments across hierarchical tiers.
- **Automated Promotion Gates**: Integrated sequential Clark-West test statistics and multiplicity-adjusted p-values into `ModelHierarchyEvaluator.evaluate_5tier_hierarchy()`.

### 22. Fundamental External Connector Wiring into Feature Matrix (Issue #565)
- **USACE Lock Delays**: Ingested Ohio River lock delay hours and queue vessels from [`src/usace_locks.py`](src/usace_locks.py) into `create_feature_matrix()`.
- **PHMSA Pipeline Incident Benchmarks**: Ingested midstream pipeline outage and disruption severity benchmarks from [`src/phmsa_pipeline.py`](src/phmsa_pipeline.py).
- **BSEE Offshore Shut-Ins**: Ingested Gulf of Mexico production shut-in percentages and platform evacuation metrics.

---

## 📦 Commits & Attribution
* **Tag**: `v0.8.4`
* **Resolved Issues**: #443, #445, #451, #480, #478, #448, #447, #442, #453, #483, #491, #493, #564, #566, #555, #568, #425, #561, #571, #570, #567, #565

