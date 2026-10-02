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

---

## 📦 Commits & Attribution
* **Tag**: `v0.8.4`
* **Resolved Issues**: #443, #445, #451, #480, #478, #448, #447, #442
