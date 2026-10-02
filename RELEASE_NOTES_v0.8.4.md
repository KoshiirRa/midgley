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

---

## 📦 Commits & Attribution
* **Tag**: `v0.8.4`
* **Resolved Issues**: #443, #445, #451, #480, #478, #448, #447, #442, #453, #483, #491, #493
