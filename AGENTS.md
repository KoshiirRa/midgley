# Agent System Specification (AGENTS.md)

This project utilizes an **LLM Multi-Agent Framework** to forecast wholesale and retail unleaded gasoline prices by integrating qualitative real-world event intelligence, **NOAA Weather Models**, **Global Maritime Chokepoints (Hormuz/Suez/Venezuela)**, **Executive Social Media (Trump Posts & Weekend Gap Analysis)**, **Alternative Physical Data (Cboe OVX Volatility & Baker Hughes Rig Counts)**, and **Tulsa Regional Refining Dynamics** into quantitative time-series estimators.

---

## Multi-Agent Architecture Overview

```
               ┌─────────────────────────────────────────────────────────────┐
               │    UNSTRUCTURED NEWS, NOAA WEATHER & PHYSICAL DATA FEEDS    │
               │  • Geopolitical Headlines & OPEC Press Releases             │
               │  • NOAA NWS API (api.weather.gov) - Multi-Basin & Regional Alerts │
               │  • Maritime Chokepoints (Hormuz 21M bpd, Suez, Venezuela)   │
               │  • Executive Social Feed (Trump Twitter / Truth Social)     │
               │  • Physical Alternative Feeds (Cboe OVX & Baker Hughes)     │
               └──────────────────────────────┬──────────────────────────────┘
                                              │
                                              ▼
               ┌─────────────────────────────────────────────────────────────┐
               │     1. EVENT, WEATHER & PHYSICAL EXTRACTION AGENT           │
               │        (Google Gemini 2.5 Flash / Domain NLP Lexicon)       │
               │ • Geopolitical Risk  • Supply Disruption  • OPEC Action     │
               │ • NOAA Tornado Risk  • NOAA Polar Vortex  • Hurricane Track │
               │ • Weekend Gap Multiplier (1.42x Monday Open Volatility)     │
               │ • Cboe OVX Tail Risk • Baker Hughes Drilling Rig Pipeline   │
               └──────────────────────────────┬──────────────────────────────┘
                                              │ Structured Bounded Vector
                                              ▼
               ┌─────────────────────────────────────────────────────────────┐
               │             2. EXPONENTIAL MEMORY FUSION AGENT              │
               │       (Decays Shocks with Half-Life t1/2 = 4.0 to 5.0 Days) │
               └──────────────────────────────┬──────────────────────────────┘
                                              │ Unified Feature Matrix
                                              ▼
               ┌─────────────────────────────────────────────────────────────┐
               │             3. QUANTITATIVE FORECASTING AGENT               │◄──────────────────┐
               │           (Standardized Ridge / XGBoost Estimator)          │                   │
               │           Main Model: National Wholesale RBOB Futures       │                   │
               └──────────────────────────────┬──────────────────────────────┘                   │
                                              │ Base Commodity Forecast                          │
                                              ▼                                                  │
               ┌─────────────────────────────────────────────────────────────┐                   │
               │         4. LOCALIZED METRO AREA CALIBRATION AGENTS          │                   │
               │  • Tulsa Metro Model (Cushing WTI & West Tulsa Refinery)    │                   │
               │  • Newark Metro Model (PADD 1B & C&D Canal Detour)          │                   │
               │  • Cincinnati Tri-State (Dual-State Tax & Ohio/Miss River) │                   │
               └──────────────────────────────┬──────────────────────────────┘                   │
                                              │ Localized Metro Forecasts                        │
                                              ▼                                                  │
               ┌─────────────────────────────────────────────────────────────┐                   │
               │             5. SYNTHESIS & SHOCK SIMULATOR AGENT            │                   │
               │ Simulates Refinery Outages, Hormuz Blockades & Weekend Posts │                   │
               └──────────────────────────────┬──────────────────────────────┘                   │
                                              │ Real-Time Adjusted Forecast                      │
                                              ▼                                                  │
               ┌─────────────────────────────────────────────────────────────┐                   │
               │             6. MLOps PREDICTION LOGGING AGENT               │                   │
               │        (src/prediction_logger.py -> prediction_history.csv) │                   │
               │  Logs Out-of-Time Forecasts & Backfills Actual Market Prices│                   │
               └──────────────────────────────┬──────────────────────────────┘                   │
                                              │ Persistent Prediction History                    │
                                              ▼                                                  │
               ┌─────────────────────────────────────────────────────────────┐                   │
               │      7. MODEL PERFORMANCE REVIEW & FEEDBACK LOOP AGENT      │                   │
               │         (.github/workflows/weekly_model_review.yml)         │                   │
               │  Evaluates Rolling Error Metrics & Computes Validation Loss │                   │
               │  Automated Saturday (08:00 AM Central / 13:00 UTC) Runner   │                   │
               └──────────────────────────────┬──────────────────────────────┘                   │
                                              │ Empirical Feedback Signal ───────────────────────┘
                                              ▼
               ┌─────────────────────────────────────────────────────────────┐
               │     8. PUBLIC WEB DASHBOARD & PRESENTATION AGENT            │
               │     (src/dashboard_generator.py -> docs/ GitHub Pages)      │
               └─────────────────────────────────────────────────────────────┘
```

---

## Agent Specifications

### 1. Event, Weather & Social Media Extraction Agent (`src/event_analyzer.py`, `src/finlight_feed.py`, `src/noaa_weather.py`, `src/geopolitical_feeds.py`, `src/executive_social_feed.py`, & `src/alternative_data_feeds.py`)

* **Role:** Ingests live financial media headlines (`finlight.me`), raw news bulletins, NOAA alerts, maritime chokepoints, executive social media posts, Cboe OVX options volatility, and Baker Hughes drilling rig counts into structured numerical impact score vectors.
* **Model Engine:** Google Gemini (`gemini-2.5-flash` / `gemini-1.5-flash`) via `google-genai` SDK with deterministic NLP lexicon fallback.
* **Real-Time Financial News Stream & Quota Safety Valve (`src/finlight_feed.py`):**
  - **Live Coverage:** Ingests real-time financial energy headlines from tier-1 media (Reuters, Bloomberg, Seeking Alpha, Investing.com) via `finlight.me` REST API.
  - **Hard Quota Safety Valve:** Persistent ledger at `data/finlight_quota.json` enforcing a **150 call/month safety cap** (and 10 call/day burst limit) out of the 250 free tier allowance. Automatically blocks outgoing API calls when cap is reached, falling back seamlessly to cached news or the Tier 3 Offline Lexicon. Quota status exposed via `GET /api/v1/system/quota`.
* **Unified Intraday Event Monitor & Webhook Gateway (`src/intraday_event_monitor.py`):**
  - **Strategy 2 (Free RSS Polling & Time-Constrained Filtering):** Zero-cost 15-minute polling across free energy RSS streams (Google News, NYT, CNBC). Enforces `when:1d` Google News query constraint and timestamp age filtering (`max_age_hours=24.0`) in `fetch_rss_headlines()`, automatically discarding stale historical articles.
  - **Strategy 1 (Cascading Anomaly Gate):** Regex/keyword trigger gate (`tariff`, `retaliat`, `trade war`, `opec emergency`, `pipeline halt`, `explosion`, `tornado`) evaluating fast-path impact scores. Tripping threshold: \(|\text{overall\_price\_pressure}| \ge 0.40\) or \(\text{supply\_disruption} \ge 0.50\).
  - **Strategy 3 (Trading Hours Adaptive Ingestion):** `is_trading_hours()` helper restricts `finlight.me` fetches to active US commodity trading hours (08:00 AM – 05:00 PM EST, Mon–Fri).
  - **Strategy 4 (Incoming Webhook Gateway & HMAC Security):** `POST /api/v1/events/webhook` endpoint on `src/api_server.py` for direct push ingestion from external alerts (Zapier, IFTTT, Google Alerts). Mandatory payload schema requires `headline` text and `url` article link, with optional `source` origin. Enforces HMAC-SHA256 signature validation via `X-Midgley-Signature` header when `MIDGLEY_WEBHOOK_SECRET` is set in the environment, rejecting unauthorized payload tampering with HTTP 401.
  - **24-Hour Headline & URL Deduplication Engine:** `is_headline_already_processed()` deduplicates incoming headlines and article URLs against `data/intraday_events.json` within a rolling 24-hour window, skipping redundant LLM scoring calls, avoiding duplicate prediction revision logs, and preventing unnecessary dashboard regenerations.
  - **Test Suite Execution Isolation & Defensive Dashboard Filtering:** Isolates unit test executions by checking `source.startswith("Test_")` or `TESTING=1` environment variable in `process_incoming_headline()`, automatically suppressing persistent disk writes (`_save_anomaly_record`, `log_predictions`) and skipping `generate_public_dashboard()` calls. Defensively filters test event sources (`Test_Suite`, `Test_Runner`, `Test_*`) in `src/dashboard_generator.py` when building public web app card feeds to guarantee production state cleanliness.
  - **Cloudflare Edge Workers & Option A2 Observability Architecture (`workers/intraday_monitor_worker.ts`, `workers/cache_worker.ts`, `wrangler.toml`, & `wrangler.cache.toml`):**
    - **`midgley-intraday-monitor` (`workers/intraday_monitor_worker.ts`):** 15-minute cron trigger worker scanning energy RSS feeds, evaluating regex anomaly triggers, deduplicating via edge cache, and firing GitHub Repository Dispatch events.
    - **`midgley-cache-worker` (`workers/cache_worker.ts`):** Tier 2 Edge Cache Gateway exposing `/api/v1/cache/:key` GET/POST and `/status` REST endpoints over Cloudflare D1.
    - **Option A2 Telemetry Engine:** Both workers integrate **Cloudflare Native Observability** (100% trace/log sampling rate), **Axiom Log Analytics** (`logToAxiom()` streaming top-level event logs to dataset `midgley-workers` via `AXIOM_TOKEN`), **Sentry Error Tracking** (`captureSentryException()` exporting stack traces via `SENTRY_DSN`), and **Sentry Cron Heartbeats** (`sendSentryCronCheckIn()` sending `in_progress` start and `ok`/`error` completion pings with matching `check_in_id` for execution duration tracking and timeout protection). Telemetry flushes execute asynchronously via `ctx.waitUntil()`, ensuring 0 latency overhead and $0 infrastructure cost.

* **NOAA Weather Models & Lightweight `wxs.us` Ingestion (`src/noaa_weather.py`):**
  - **Token-Efficient Ingestion Engine:** Integrates `t.wxs.us` lightweight terminal REST endpoints (`/location?format=json`) to fetch NWS alerts and SPC (Storm Prediction Center) convective outlooks for specific zipcodes (`74101` Tulsa, `19711` Newark, `45202` Cincinnati, `27834` Greenville, `28202` Charlotte, `94612` Oakland).
  - **90%–95% Token Savings:** Pre-filters location weather data down to ~150–300 tokens (vs 2,500–4,500 tokens for raw NOAA text bulletins/GeoJSON feature maps).
  - **0-Token Deterministic SPC Risk Mapping:** Maps categorical convective risks (`HIGH`: 1.0, `MDT`: 0.8, `ENH`: 0.6, `SLGT`: 0.4, `MRGL`: 0.2, `NONE`: 0.0) and sub-risks (Tornado, Hail, Wind) directly in Python without requiring LLM prompt calls.

* **Tiered Multi-Provider LLM Failover Engine (`src/event_analyzer.py`):**
  - **Tier 1 (Primary):** Google **Gemini 2.5 Flash** (`GEMINI_API_KEY`).
  - **Tier 2 (Secondary - Optional):** OpenAI `gpt-4o-mini` (`OPENAI_API_KEY`) / Anthropic `claude-3-5-haiku` (`ANTHROPIC_API_KEY`). Soft-checked if keys exist; safely skipped if absent.
  - **Tier 3 (Safety Net - 100% Guaranteed):** **Offline Rule-Based Lexicon Extractor**. 100% offline, $0 cost, 0 API keys required, zero downtime guarantee.
* **Executive Social Media & Weekend Gap Engine:**
  - **Empirical Correlation:** Econometric analysis confirms $p < 0.01$ correlation between executive social media posts (e.g., Trump OPEC pressure & tariff declarations) and immediate short-term futures return shocks.
  - **Dovish OPEC Pressure:** Posts urging OPEC to lower prices cause immediate average $-1.85\%$ single-day RBOB price drops.
  - **Hawkish Tariff Shocks:** Energy import tariff threats produce $+2.10\%$ 24-hour price surges.
  - **Weekend Market Gap Multiplier:** Saturday/Sunday posts published while commodity markets are closed produce **$1.42\times$ higher Monday morning open price gap volatility**.

* **Zero-Cost Open-Access Energy Data Suite & Universal 50-State Connector (`src/data_ingestion.py`, `src/state_open_data.py`, & `src/noaa_weather.py`) (Issue #141):**
  - **Universal 50-State Open Data Portals Connector (`src/state_open_data.py`):** `UniversalStateOpenDataConnector` provides dynamic resolution across all 50 US States + DC (51 total locales). Queries Socrata domains (`data.<state>.gov` / `data.gov`), U.S. Census State Tax Collections API, and FTA motor fuel indices for official state excise tax rates ($/gal), UST fees, and motor fuel sales volume proxies.
  - **FRED (St. Louis Fed) Energy Series (`src/data_ingestion.py`):** `FREDDataConnector` ingests weekly national and PADD retail gasoline/diesel series (`GASREGW`, `GASDESW`, `GASREGWCW`, `GASREGWGULF`) and CPI gasoline index (`CUUR0000SETB01`).
  - **U.S. EIA API v2 Open Data (`src/data_ingestion.py`):** `EIADataConnector` ingests weekly retail price series, PADD refinery percent utilization, and regional motor gasoline/crude stock inventories (`/petroleum/pri/gnd/data/`, `/petroleum/pnp/pct/data/`, `/petroleum/stoc/wstk/data/`).
  - **USDA Biofuel & Ethanol Market Reports (`src/data_ingestion.py`):** `USDABiofuelConnector` ingests spot Midwest ethanol (E100) rack prices ($/gal) and RIN D6 Ethanol Credit spot values (`marsapi.ams.usda.gov`) for E10 unleaded blendstock cost modeling ($0.10 \times \text{E100} + 0.90 \times \text{RBOB} + \text{RIN Overhead}$).
  - **3-2-1 Refining Crack Spread Engine (`src/data_ingestion.py` & `src/feature_engineering.py`) (Issue #169):** Queries NYMEX Heating Oil futures (`HO=F`) alongside RBOB Gasoline (`RB=F`) and WTI Crude (`CL=F`) to compute the industry-standard 3-2-1 refining crack margin ($\text{Crack}_{321} = \frac{2 \times \text{RBOB} \times 42 + 1 \times \text{HO} \times 42 - 3 \times \text{WTI}}{3}$) and 5-day margin momentum (`crack_spread_321_delta_5d`) to model refinery yield switching and run cut dynamics.
  - **Open-Meteo & NOAA High-Resolution Degree Days (`src/noaa_weather.py`):** `OpenMeteoDegreeDaysConnector` computes daily Heating Degree Days ($\text{HDD}$), Cooling Degree Days ($\text{CDD}$), and freeze/heat stress risk warnings across 6 primary refining hubs (West Tulsa, Delaware City, Catlettsburg, Richmond/Martinez, Selma, Paw Creek).
  - **NOAA NHC Tropical Cyclone Advisories (`src/nhc_hurricane.py`) (Issue #177):** `NHCHurricaneConnector` ingests NOAA NHC active tropical cyclone RSS/GIS advisories to model Gulf Coast refining hub threat scores (`nhc_gulf_refinery_exposure_score`) and Colonial Pipeline Line 1/2 intake risk flags.
  - **BSEE Offshore Gulf Production Shut-Ins (`src/bsee_shutins.py`) (Issue #178):** `BSEEShutInConnector` parses daily Bureau of Safety and Environmental Enforcement reports during tropical storm evacuations to track offshore crude oil shut-in percentages (`bsee_gulf_oil_shutin_pct`) and platform evacuation counts.
  - **EIA-930 Hourly Electric Grid Stress Monitor (`src/data_ingestion.py`) (Issue #179):** `EIA930GridMonitorConnector` monitors ERCOT, MISO, PJM, and CAISO balancing authority load anomalies near refining hubs (`grid_stress_load_anomaly_zscore`).
  - **Expanded EIA Weekly Petroleum Balance (`src/data_ingestion.py`) (Issue #180):** Expands `EIADataConnector` to ingest weekly motor gasoline product supplied (implied demand), refiner net production by PADD, and inter-PADD pipeline movements.
  - **USACE LPMS Ohio River Lock Delays (`src/usace_locks.py`) (Issue #181):** `USACELockConnector` monitors commercial barge queue times and delay hours at Markland and McAlpine locks on the Ohio River (`usace_ohio_river_lock_delay_hours`) for Cincinnati regional logistics calibration.



---

### 2. Exponential Memory Fusion Agent (`src/feature_engineering.py`)

* **Role:** Solves point-shock persistence by modeling event decay over 2–3 weeks using dynamic taxonomy-based half-life decay curves (`CATEGORY_HALF_LIVES_DAYS`).
* **Mathematical Decay:**
  \[
  \text{Memory}_{t} = \text{Memory}_{t-1} \times e^{-\frac{\ln(2)}{t_{1/2}(\text{category})}} + \text{NewShock}_t
  \]
  where dynamic half-lives $t_{1/2}(\text{category})$ are mapped by shock taxonomy:
  - **`supply_disruption`** (structural physical outages, refinery fires, pipeline shut-ins, hurricane damage): **$t_{1/2} = 14.0\text{ days}$**
  - **`geopolitical_risk`** (Hormuz/Suez chokepoint blockades, military escalation, sanctions): **$t_{1/2} = 7.0\text{ days}$**
  - **`opec_action`** (OPEC+ production quota policy shifts): **$t_{1/2} = 5.0\text{ days}$**
  - **`demand_sentiment`** (macroeconomic indicators, recession fears, driving season demand): **$t_{1/2} = 4.0\text{ days}$**
  - **`overall_price_pressure`** (executive social media posts, short-term news sentiment headlines): **$t_{1/2} = 2.5\text{ days}$** (retaining $1.42\times$ weekend open gap volatility multiplier)
* **Pre-Training Context Routing Diagnostic (Paper 2608.25128v1):** Modulates effective half-life ($t_{1/2} \times 0.20$ for `SKIP_FUSION` vs $1.0\times t_{1/2}$ for `TRY_FUSION`) based on temporal autocorrelation $\rho_h$.

---

### 3. Quantitative Forecasting Agent (`src/models.py`)

* **Role:** Fits regularized linear pipelines (StandardScaler + Ridge Regression α=10.0), XGBoost regressors, and multi-model Stacking Ensemble Regressors on 80/20 chronological train/test splits. Main model generates base wholesale RBOB commodity price forecasts.
* **Multi-Model Stacking Ensemble Regressor & Quantile Uncertainty Bands (`build_stacking_ensemble_pipeline()`, `compute_quantile_uncertainty_bands()`) (Issue #170):** Combines Ridge ($\alpha=10.0$), ElasticNet ($\alpha=0.1$, $l_1=0.5$), RandomForest, and XGBoost with a `RidgeCV` meta-learner. Computes probabilistic $P_{10}$ (downside), $P_{50}$ (median), and $P_{90}$ (upside) quantile prediction bands ($\text{P}_{10} = \text{P}_{50} - 1.2815 \sigma, \text{P}_{90} = \text{P}_{50} + 1.2815 \sigma$).
* **Naive Persistence & Benchmark Comparisons (`evaluate_baseline_comparisons()`) (Issue #43):** Computes out-of-time benchmark metrics for Naive Persistence ($\hat{y}_{t+5} = y_t$) and 5-Day Moving Average ($\hat{y}_{t+5} = \text{MA}_{5d}(y_t)$), quantifying model MAE uplift over trivial guesses ($\text{Uplift}_{\text{MAE}} = \frac{\text{MAE}_{\text{Persistence}} - \text{MAE}_{\text{Model}}}{\text{MAE}_{\text{Persistence}}} \times 100\%$).
* **Out-of-Time Test Performance (Regular Model v1.4 "Dubbs" Finlight-LLM Engine):**
  - **National Model:** **60.79% Directional Accuracy** ($0.1069 MAE).
  - **Tulsa Model:** **58.15% Directional Accuracy** ($0.1331 MAE).
  - **Cincinnati Model:** **58.85% Directional Accuracy** ($0.1245 MAE).

---

### 4. Localized Metro Area Calibration Agents (`src/locations/<location>/regional.py`)

* **Role:** Ingest the base commodity forecast from the Main Quantitative Model and calibrate to local retail pump prices, dynamic regional rack margins, refinery dynamics, delivery hub logistics, and localized infrastructure shocks. Organized as modular subpackages within `src/locations/`.
* **Tulsa Regional Calibration Agent (`src/locations/tulsa/`):**
  - Tailors market time series to the Tulsa, OK metropolitan area calibrated to live pump prices ($3.89/gal base) & Cushing WTI delivery hub dynamics.
  - Rack margin: $P_{\text{Tulsa Retail}} = P_{\text{Wholesale RBOB}} + \text{Dynamic Rack Margin}$.
* **Newark Regional Calibration Agent (`src/locations/newark/`):**
  - Tailors market time series to the Newark, DE metropolitan area (PADD 1B Central Atlantic) calibrated to live pump prices ($3.35/gal base) & PBF Delaware City Refinery (180,000 bpd capacity).
  - Integrates **Delaware Bay deepwater lightering alerts (Big Stone Anchorage)** and **Chesapeake & Delaware (C&D) Canal barge detour events** (300 nm detour around Delmarva, $+\$0.097/\text{gal}$ rack margin expansion, $p = 0.00191$).
* **Cincinnati Regional Calibration Agent (`src/locations/cincinnati/`):**
  - Tailors market time series to the Cincinnati, OH & Northern Kentucky tri-state metropolitan area, modeling the dual-state fuel tax differential (Ohio state fuel tax $0.385/\text{gal}$ vs Kentucky state fuel tax $0.260/\text{gal}$, creating a persistent $\approx \$0.125/\text{gal}$ cross-river retail price gap).
  - Integrates Marathon Catlettsburg KY Refinery dynamics (291,000 bpd capacity), Ohio River marine terminal barge deliveries, and **Lower Mississippi River downriver low-water barge bottlenecks (Cairo, IL confluence & Memphis draft restrictions)**.
* **Greenville Regional Calibration Agent (`src/locations/greenville/`):**
  - Tailors market time series to the Greenville, NC metropolitan area (PADD 1C South Atlantic) calibrated to live pump prices ($3.25/gal base).
  - Integrates **Colonial Pipeline Line 1/2 breakout hubs at Selma NC & Apex NC**, Port of Wilmington marine oil terminals, North Carolina State Motor Fuel Tax ($0.404/gal variable formula), and **NOAA Pitt County (NCZ081) Tar River flooding & Atlantic hurricane alerts**.
* **Charlotte Regional Calibration Agent (`src/locations/charlotte/`):**
  - Tailors market time series to the Charlotte, NC metropolitan area (PADD 1C South Atlantic) calibrated to live pump prices ($3.28/gal base).
  - Integrates **Colonial Pipeline Line 1 & Line 2 Paw Creek Petroleum Distribution Hub**, Plantation Pipeline interconnects, NC state fuel tax ($0.404/gal) vs South Carolina cross-border tax differential ($0.288/gal, persistent ~$0.116/gal gap), and **NOAA Mecklenburg County (NCZ071) Catawba River flooding & winter ice storm alerts**.
* **Port St. Lucie Regional Calibration Agent (`src/locations/port_st_lucie/`):**
  - Tailors market time series to the Port St. Lucie, FL metropolitan area (St. Lucie County / Treasure Coast, PADD 1C South Atlantic) calibrated to live pump prices ($3.38/gal base).
  - Models Florida's unique **>95% waterborne marine tank barge/vessel offloading dependency** (0 crude oil refineries and 0 interstate refined product pipelines entering South Florida), waterborne marine freight tariffs, Port Everglades (Fort Lauderdale) & Port Canaveral petroleum terminals, Florida State Motor Fuel Tax + St. Lucie County local option tax ($0.384/gal), I-95 & Florida Turnpike tank-truck corridors, and **NOAA St. Lucie County (FLZ147 / Zip 34952) Atlantic hurricane, marine gale & flash deluge flood alerts**.
* **Oakland & SF Bay Area Regional Calibration Agent (`src/locations/oakland/`):**
  - Tailors market time series to Oakland, CA ($4.950/gal base) and the 9-County SF Bay Area Region ($5.050/gal base), establishing high-cost PADD 5 West Coast benchmarks ("scare factor").
  - Models statutory **CARB & CA state tax burden ($0.953/gal total)**: 63.4¢ state excise tax, ~25¢ Cap-and-Trade carbon fees, ~18.5¢ LCFS credit overhead, and ~15¢ local sales tax/UST fees.
  - Integrates Chevron Richmond Refinery dynamics (245,000 bpd capacity), PBF Martinez, Valero Benicia, Kinder Morgan SFPP pipeline corridors, **USGS Hayward/San Andreas Fault seismic risks**, **CAL FIRE & PG&E Public Safety Power Shutoff (PSPS) refinery blackout risks**, **NOAA PTWC Tsunami advisories**, and **NHC EPAC Tropical Storm Remnants**.

* **Mandatory Regional Dashboard Visual Card Standard & Metadata Storage Specification (Issue #35 & Decoupled Storage Architecture):**
  - ALL localized regional public web dashboard pages (`/tulsa`, `/newark`, `/cincinnati`, `/greenville`, `/charlotte`, `/oakland`, `/bayarea`) MUST display dedicated visual cards detailing their unique regional econometric drivers, refining logistics, tax structures, and physical delivery hub dynamics.
  - **Decoupled JSON Storage Specification:** Regional econometric descriptions, refinery capacities, tax structures, delivery hub dynamics, and shock scenarios MUST NOT be hardcoded directly into HTML template strings inside `src/dashboard_generator.py`. Instead, all regional metadata profiles MUST be maintained as structured JSON files under `data/regional_metadata/<region_id>.json` (e.g., `tulsa_ok.json`, `newark_de.json`, `cincinnati_oh.json`, `greenville_nc.json`, `charlotte_nc.json`, `oakland_ca.json`, `bayarea_ca.json`).
  - **Mandatory Guidance when New Regions are Added:** Whenever a new regional calibration agent / metro locale is added to Midgley (e.g., in `src/locations/<new_location>/`):
    1. Create a JSON profile file at `data/regional_metadata/<region_id>.json` following the schema defined in `src/regional_metadata.py` covering all 4 core dimensions (`econometric_drivers`, `refining_logistics`, `tax_structure`, `infrastructure_delivery`) and `shock_scenarios`.
    2. Import `render_regional_driver_cards_html` from `src.regional_metadata` inside `src/dashboard_generator.py` and replace `{{REGIONAL_CARDS}}` in the HTML template string to dynamically render the visual cards onto the regional dashboard page.

---

### 5. Synthesis & Scenario Simulator Agent (`src/locations/<location>/main.py`)

* **Role:** Enables counterfactual "What-If" scenario simulation.
* **Scenarios Evaluated:**
  - *West Tulsa HF Sinclair Refinery EF-3 Tornado Shock:* +$0.173/gal (+4.58%)
  - *Cushing Keystone Pipeline Spill:* +$0.173/gal (+4.58%)
  - *Strait of Hormuz Tanker Blockade (21M bpd):* +$0.109/gal (+2.88%)
  - *Red Sea / Suez Rerouting Crisis:* +$0.201/gal (+5.32%)
  - *Marathon Catlettsburg KY Refinery Unplanned Outage:* +$0.165/gal (+4.78%)
  - *Lower Mississippi & Ohio River Low-Water Barge Bottleneck:* +$0.145/gal (+4.20%)
  - *USGS Hayward Fault M>=6.0 Seismic Quake & Pipeline Shutoff:* +$0.420/gal (+8.48%)
  - *PG&E PSPS Red Flag Wildfire Power Shutoff & Refinery Blackout:* +$0.350/gal (+7.07%)
  - *Chevron Richmond Refinery Unplanned Hydrocracker Outage:* +$0.285/gal (+5.76%)
  - *CARB CaRFG Summer-Blend Transition Compliance Surge:* +$0.220/gal (+4.44%)
  - *NOAA PTWC Pacific Tsunami Berth Closure:* +$0.165/gal (+3.33%)
  - *Weekend Executive OPEC Talkdown Post:* $3.780/gal (Monday Open Re-anchoring)
  - *Weekend Foreign Energy Tariff Declaration:* $3.780/gal (Supply Shock Re-anchoring)


---

### 6. MLOps Prediction Logging Agent (`src/prediction_logger.py`)

* **Role:** Manages persistent prediction tracking by writing 5-day out-of-time forecasts to `data/prediction_history.csv`, backfilling actual historical market prices as target dates arrive, and exposing continuous rolling performance metrics via API & web dashboard.
* **Automated Daily Schedule & Target Calculation:** Executes automatically during daily forecast runs (02:00 AM Central). For every daily run, the 5-day out-of-time target date is automatically computed as `run_date + 5 days` (e.g. run date `2026-08-24` -> target date `2026-08-29`), maintaining clean out-of-time prediction records.
* **Realized-vs-Predicted Rolling Scoreboard Engine:**
  - `compute_rolling_scoreboard_metrics(window_days=30, region=None)`: Calculates rolling 30/60/90-day MAE, RMSE, MAPE, Directional Hit Rate %, Naive Persistence Baseline MAE, and Model MAE Uplift % vs. ground-truth market prices.
  - `compute_regional_scoreboard_breakdown(window_days=30)`: Computes per-region accuracy breakdowns across all 8 active regional markets.
  - `get_recent_evaluated_records(region=None, limit=50)`: Returns chronologically sorted evaluated forecast records.
  - Exposed publicly via REST API gateway `GET /api/v1/forecast/scoreboard` and embedded in `docs/index.html`.
* **Functions:**
  - `log_predictions()`: Logs 5-day out-of-time forecasts with dynamically calculated target dates.
  - `backfill_actual_prices_and_evaluate()`: Queries ground-truth market prices from `yfinance` as target dates mature and backfills actual prices in `prediction_history.csv`.

---

### 7. Model Performance Review & Continuous Feedback Loop Agent (`.github/workflows/weekly_model_review.yml`, `src/weekly_issue_reporter.py`, `src/catalog_monitor.py` & `src/arxiv_monitor.py`)

* **Role:** Operates automated weekly model performance evaluations, self-reviews open GitHub repository issues, monitors public developer catalog lists for newly added tools, monitors arXiv.org for relevant quantitative research preprints, and maintains a continuous feedback loop into the quantitative forecasting engine to drive accuracy improvements over time.
* **Automated Cloud Schedule:** Executes automatically every **Saturday morning at 08:00 AM Central / 13:00 UTC** on GitHub Actions cloud runners.
* **Continuous Feedback Loop & Self-Review Mechanism:**
  - **Rolling Error Metrics:** Evaluates rolling MAE, RMSE, and Directional Hit Rate metrics across 30-day, 60-day, and 90-day historical evaluation windows.
  - **Open GitHub Issue Self-Review:** Fetches all open repository issues on `KoshiirRa/midgley` via `gh` CLI or GitHub REST API, evaluates each issue's potential modeling impact using Gemini 2.5 Flash (with a domain-specific heuristic fallback), ranks issues, and selects the top issue expected to yield the largest accuracy/MAE improvement.
  - **Automated Developer Catalog Monitor (`src/catalog_monitor.py`, `data/catalog_monitors_state.json` & [`docs/research_sources.md`](file:///c:/Users/concentus/Documents/Random%20Ideas%20-%20LLM%20Unleaded%20Gas%20Price%20Prediction%20Modelling/docs/research_sources.md)):** Continuously tracks 10 major developer catalog indexes (`public-apis`, `free-for-dev`, `freestuff.dev`, `free-for-life`, `awesome`, `awesome-selfhosted`, `awesome-quant`, `awesome-python`, `awesome-nodejs`, `api-mega-list`), detailed in [`docs/research_sources.md`](file:///c:/Users/concentus/Documents/Random%20Ideas%20-%20LLM%20Unleaded%20Gas%20Price%20Prediction%20Modelling/docs/research_sources.md). On weekly runs, evaluates newly added catalog items with Gemini 2.5 Flash and automatically files GitHub Feature Request issues for items scoring $\ge 7.0/10.0$.
  - **Apify Tools Barred Policy:** All AI agents, catalog monitors, issue self-reviewers, and LLM evaluation prompts MUST explicitly ignore, reject, and exclude any tools, scrapers, actors, or services hosted on or referencing Apify (`apify.com`) due to paid subscription and compute unit cost constraints. All ingested tools and scrapers must be 100% zero-cost.
  - **Automated arXiv Research Paper Monitor (`src/arxiv_monitor.py`):** Queries `export.arxiv.org/api/query` for recent preprints in quantitative finance, econometrics, and machine learning matching energy market and commodity forecasting queries within the 7-day review window, formatting abstracts and download links into weekly review reports.
  - **Empirical Feedback Loop:** Feeds diagnostic loss signals back into estimator re-calibration, adjusting regularized Ridge regression hyperparameters ($\alpha$), updating LLM feature decay half-lives ($t_{1/2}$), and fine-tuning prompt scoring weights to continuously refine model accuracy.


---

### 8. Public Web Dashboard & Multi-Locale Presentation Agent (`src/dashboard_generator.py`, `src/regional_metadata.py` & `src/social_embed_generator.py`)

* **Role:** Builds and updates the responsive, multi-page public web application deployed to GitHub Pages (`docs/`), loads decoupled regional metadata profiles from `data/regional_metadata/` via `src/regional_metadata.py`, renders dark-mode social preview cards (`1200x630px`), and injects Open Graph and Twitter Card metadata.
* **Dynamic Overview Card Engine:** Dynamically queries real-time live retail pump prices via `fetch_live_metro_retail_price()` for all regional metro cards (`Tulsa_OK`, `Newark_DE`, `Cincinnati_OH`, `Oakland_CA`, `BayArea_CA`), while preserving NYMEX RBOB commodity futures benchmark pricing ($3.184/gal - $3.270/gal) for the **National Wholesale** contract card.
* **Automated Social Preview Image Generator (`src/social_embed_generator.py`):**
  - Uses Matplotlib (`Agg` backend) to generate 10 dark-mode social preview cards (`1200x630px` PNG) in `docs/assets/embeds/` (`national.png`, `tulsa.png`, `newark.png`, `cincinnati.png`, `greenville.png`, `charlotte.png`, `oakland.png`, `bayarea.png`, `overview.png`, `math.png`).
  - Left panel displays current base price, 5-day projected price, expected delta badge (`+$0.173 (+4.45%)` or `-$0.127 (-3.39%)`), directional color styling (`#10b981` green for drop, `#ef4444` red for surge, `#0ea5e9` sky blue for stable), model directional accuracy, rack margin / tax overhead, and top market driver tagline.
  - Right panel displays 15-day historical sparkline transitioning into 5-day forecast trajectory with confidence interval shading.
* **Open Graph & Twitter Card Metadata Tag Injection (`get_head_meta_tags()`):**
  - Injects Open Graph (`og:site_name`, `og:type`, `og:title`, `og:description`, `og:url`, `og:image`, `og:image:width="1200"`, `og:image:height="630"`, `og:image:type="image/png"`), Twitter Card (`twitter:card="summary_large_image"`), and Discord accent color (`<meta name="theme-color">`) tags into `<head>` across all 11 HTML dashboard pages.
* **Dev Environment vs. Production Social Preview Behavior:**
  - **Production-Only Image Resolution:** All Open Graph (`og:image`) and Twitter Card (`twitter:image`) metadata tags injected into `docs/*.html` resolve to absolute production URLs (`https://koshiirra.github.io/midgley/assets/embeds/<locale>.png`).
  - **Dev Environment Limitation:** When testing or previewing pages locally in development environments (`dev-vm` on port 8080, `file://`, or local web servers), social link preview cards will point to production-hosted assets on GitHub Pages and will **not** preview local uncommitted dev changes unless deployed to production.
* **Route Structure & Hierarchy:**
  - **Overview Landing Page (`/` / `docs/index.html`):** Executive overview of the Midgley engine, featuring the dynamic **Last Run Intelligence & Impact Audit Component** (GitHub Issue #105) positioned between the Hero Banner and Active Forecast Locales. Parses `prediction_history.csv` and `intraday_events.json` to display Trigger Context (with linked headline feeds), Mathematical Impact (score bars, half-life $t_{1/2}=5.0\text{d}$, and plain English impact analysis), and Prediction Revisions Delta across all 8 modeled regions with trend direction arrows (`↑`, `↓`, `→`). Includes clickable **Technical Analysis** header routing directly to `technical_breakdown.html`.
  - **Technical Analysis & Specific-Run Math Audit Engine (`/technical_breakdown` / `docs/technical_breakdown.html` & `.md`):** Generates full step-by-step mathematical audits with exact substituted numerical values for every run ($M_0 \dots M_5$, Ridge parameters, 8 regional metro equations, and CARB excise tax notes). Features **Section 5: NOAA SPC-Style Quantitative & Narrative Synopsis** providing run-specific executive summaries, technical market discussion, and catalyst uncertainty scenarios, alongside a **Historical Run Selector Dropdown** and machine-readable JSON exports (`docs/runs/latest.json`, `docs/runs/<run_id>.json`, `docs/runs/index.json`).
  - **National Wholesale RBOB Page (`/national` / `docs/national.html` & `docs/national/index.html`):** Dedicated commodity futures page with NYMEX RBOB predictions chart, out-of-time error metrics, global maritime & geopolitical shock scenarios (Hormuz/Suez), and technical driver breakdowns. Accessible via **`National Wholesale`** in the top navbar.
  - **Tulsa Metro Retail Gas Page (`/tulsa` / `docs/tulsa.html` & `docs/tulsa/index.html`):** Dedicated regional retail page calibrated to live pump prices ($3.89/gal), Cushing WTI delivery hub dynamics, West Tulsa HF Sinclair refinery tornado/freeze shock scenarios, and dynamic rack margins ($0.706/gal). Accessible via the top nav **`Metro Areas`** dropdown menu.
  - **Educational Math Guide (`/math` / `docs/math.html`):** Educational reference detailing equations and vector spaces across all 10 feature layers rendered via KaTeX (including Section 10 multiline `aligned` CARB tax breakdown).
  - **Fill-Up Timing & Estimated Savings Advisor (`/savings` / `docs/savings.html` & `docs/savings/index.html`) (Issue #91):** Interactive tank fill savings calculator and recommendation engine (`🔴 FILL UP TODAY` vs `🟢 WAIT TO FILL UP`), vehicle presets (Compact 12g, Sedan 15g, Pickup 24g, Fleet 100g), 5-day trajectory table, and LubeLogger (Issue #22) / Android Auto (Issue #21) cross-link integrations.

---

### 9. Dev Environment & Permanent Server Agent (`dev-vm` Port 8080 & Systemd Local Workflow Timers)

* **Role:** Manages the persistent local development environment on `dev-vm`, keeping the permanent `dev` branch active, serving the web dashboard live on port 8080, and running local scheduled workflow equivalents (daily forecasting & weekly model issue self-reviews).
* **Key Specifications:**
  - **Dedicated Dev Branch:** Tracks the permanent `dev` branch (`origin/dev`) in the project directory.
  - **Systemd Web & API Services:** Managed by `midgley-dev.service` (dashboard web server on port 8080) and `midgley-api.service` (FastAPI / MCP gateway on port 8000).
  - **Systemd Scheduled Local Workflow Timers:**
    - `midgley-daily-forecast.timer`: Executes `scripts/run_local_daily_forecast.sh` daily at **02:00 AM Central / 07:00 UTC**.
    - `midgley-intraday-polling.timer`: Executes `scripts/run_local_intraday_polling.sh` **every 15 minutes** 24/7 (running zero-cost RSS energy news polling, evaluating shock thresholds, and auto-revising forecasts/dashboard on anomalies).
    - `midgley-weekly-review.timer`: Executes `scripts/run_local_weekly_review.sh` every **Saturday at 08:00 AM Central / 13:00 UTC** (running model backtests, GitHub open issue self-reviews via Gemini, and public dashboard updates).
  - **User Linger:** User linger enabled (`loginctl enable-linger`) to ensure background web services and scheduled timers run 24/7 across host reboots.

---

### 10. Nightly Dev Release Automation Agent (`.github/workflows/nightly_dev_release.yml`)

* **Role:** Executes automated nightly pre-releases tracking whatever is committed on the permanent `dev` branch.
* **Automated Cloud Schedule:** Executes daily at **03:00 AM Central / 08:00 UTC** on GitHub Actions.
* **Key Specifications:**
  - **Tagging Strategy:** Tagged as `dev-YYYY-MM-DD` and published as a GitHub Pre-Release.
  - **Automated Changelog Generation:** Parses git commit history since the preceding nightly release, formatting structured release notes with commit messages, commit hashes, and author attributions.

---

### 11. MCP & REST API Gateway Agent (`src/api_server.py`, `src/mcp_server.py`, `src/live_fuel_feed.py`, & `src/lookup_cache.py`)

* **Role:** Exposes real-time unleaded gasoline price ingestion, 5-day out-of-time quantitative forecasting, counterfactual physical/geopolitical shock simulations, and Model Context Protocol (MCP) integrations for external LLMs, AI agents, and chatbots.
* **Service Orchestration:** Managed by `midgley-api.service` running continuously on `dev-vm` (`http://localhost:8000`).
* **Scraper Fallback Sequence (`src/live_fuel_feed.py`):**
  - **Step 1 (GasBuddy GraphQL):** Real-time station queries by zip code.
  - **Step 2 (AAA Metro BS4 Scraper):** Targeted BeautifulSoup metro table parsing by region keywords (e.g. `Oakland`, `San Francisco`, `Tulsa`, `Wilmington`, `Cincinnati`, `Covington`). Rejects unparseable headers to return `None` rather than matching global top-nav header text.
  - **Step 3 (EIA / yfinance RBOB Futures Benchmark):** RBOB futures contract close plus regional rack margin offset.
  - **Step 4 (prediction_history.csv Clean History):** Prior validated regional base price (sanitized against anomalies $< \$4.50$ for CA regions).
  - **Step 5 (Static Regional Fallback Anchor):** Locale-specific base anchors ($5.550 Oakland, $5.650 Bay Area, $3.890 Tulsa, $3.350 Newark, $3.450 Cincinnati).
* **Key Components:**
  - **Stale-While-Revalidate (SWR) Response Cache & Provenance Chains (`src/lookup_cache.py`) (Issue #45):** 3-tier cache gateway implementing `LookupCache.get_swr()` with non-blocking async background revalidation threads (`HIT_FRESH`, `HIT_STALE`, `MISS`) and `build_provenance_chain()` metadata serialization to flag state vs. metro fallback granularity mismatches (`is_fallback_granularity`).
  - **System Telemetry & Grafana Observability Engine (`src/telemetry.py` & `docs/TELEMETRY_HANDOFF.md`) (Issues #107 & #108):** Central observability engine tracking LLM token metrics, estimated USD costs, tier fallback activations, API quota safety valves, and Prometheus text exporter stream (`GET /metrics`). Supports `MIDGLEY_ENV` environment isolation (`dev` vs `prod`), `GET /api/v1/system/quota` endpoint, and 1-click Grafana dashboard template ([`grafana/dashboard_observability.json`](file:///c:/Users/concentus/Documents/Random%20Ideas%20-%20LLM%20Unleaded%20Gas%20Price%20Prediction%20Modelling/grafana/dashboard_observability.json)).

---

### 12. GitHub Wiki & Documentation Maintenance Directives (`https://github.com/KoshiirRa/midgley.wiki.git`)

* **Role:** Ensures that the repository documentation ([`docs/SELF_HOSTING.md`](docs/SELF_HOSTING.md), [`README.md`](README.md), [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)) and official GitHub Wiki (`https://github.com/KoshiirRa/midgley.wiki.git`) are continuously updated and kept in full synchronization with the codebase whenever features, system architecture, data feeds, regional models, or environment states change.
* **Core Documentation Maintenance Rules:**
  1. **Mandatory Documentation & Self-Hosting Sync:** Any agent or process modifying system architecture, data ingestion streams, API gateways, MLOps processes, cache gateways, systemd services, or scenario simulators MUST update both the main repository documentation ([`docs/SELF_HOSTING.md`](docs/SELF_HOSTING.md), [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)) and the corresponding Markdown documentation page in the GitHub Wiki (`Agent-Architecture.md`, `Data-Ingestion-and-APIs.md`, `Scenario-Simulator.md`, `MLOps-and-Continuous-Feedback.md`, `Self-Hosting.md`).
  2. **Mandatory Self-Hosting Guide Maintenance (`docs/SELF_HOSTING.md` & Wiki `Self-Hosting.md`):** Whenever a new feature, API connector, cache tier, systemd service/timer, CLI parameter, environment variable, or regional calibration agent is introduced, agents MUST verify and update `docs/SELF_HOSTING.md` and the Wiki `Self-Hosting.md` page covering:
     - New environment variables and API key requirements in the environment configuration table.
     - New or updated `systemd` user service unit files and timer schedules.
     - 3-tier cache gateway configuration steps (Turso, Cloudflare D1/Worker, Local SQLite).
     - Standardized LLM guidance discovery prompts and the 7-step regional extension tutorial whenever regional metadata schemas (`data/regional_metadata/`) or location registries (`src/locations/`) are modified.
  3. **New Regional Model Calibration Specs:** Whenever a new regional metro model or locale subpackage is introduced to `src/locations/`, its complete calibration specifications (PADD region, base pump price, rack margin equation, delivery hub dynamics, state tax burden, refining capacity, and local hazard alert vectors) MUST be documented in `Regional-Metro-Models.md` in the GitHub Wiki and registered in `docs/SELF_HOSTING.md`.
  4. **Dev vs. Prod Environment Synchronization:** The environment status and comparative matrix in `Environment-State-and-Dev-vs-Prod.md` and `Home.md` MUST be kept up to date to clearly reflect operational differences between **Production** (`main` branch / GitHub Actions / GitHub Pages) and **Development** (`dev` branch / `dev-vm`).
  5. **Security & Data Privacy:** Public repository documentation and Wiki pages MUST NEVER contain internal IP addresses, local network topology, internal domain names, or private server login credentials.
  6. **Project History & Roadmap Updates:** Major release milestones, new feature additions, and roadmap target updates MUST be logged in `Project-History-and-Roadmap.md`.

---

### 13. GitHub Credential Health & Rate Limit Directives

* **Role:** Ensures agents and development tools maintain GitHub credential health during issue management, milestone tracking, and repository operations.
* **Diagnostic & Self-Healing Protocol:**
  - **Rate Limit Detection:** If any `gh` CLI command or GitHub REST API call returns `HTTP 403 API rate limit exceeded` or `status: 403`, the agent MUST immediately inspect `gh auth status` on the execution target (host or `dev-vm` via `ssh marty@10.42.42.54 "gh auth status"`).
  - **Re-Authentication Prompt:** If the stored credentials are invalid or expired (`The token in keyring/hosts.yml is invalid`), the agent MUST pause API calls and prompt the user to refresh authentication:
    - **Local Host:** `gh auth refresh -h github.com` (or `gh auth login`)
    - **Dev VM (`10.42.42.54`):** `ssh marty@10.42.42.54 "gh auth login"`
  - **Strict Anti-Revocation Rule (No Plaintext Tokens)**: Agents MUST NEVER pass raw GitHub tokens (e.g. `gho_...`, `ghp_...`, `github_pat_...`) inline in CLI commands or single-line env overrides (e.g. `GH_TOKEN=gho_... gh api ...`). Plaintext tokens in shell execution strings or command logs trigger GitHub Secret Scanning, causing instant token revocation. Agents MUST rely strictly on `gh auth` keyring credentials or environment variables set outside command execution strings.
  - **No Unauthenticated Polling Loops:** Agents MUST NOT retry failing GitHub API calls in a loop when IP rate limits are exhausted.

---

### 14. GitHub Issue Triage & Three-Track Milestone Taxonomy Directives

* **Role:** Establishes strict rules for assigning GitHub issues to three dedicated, parallel milestone release tracks across the project lifecycle.
* **Three Parallel Release Tracks:**
  1. **Track 1: Software & UI Release Track (Titled `v0.X`, `v1.X`):** Reserved for general software releases, public web dashboard UI rendering (`docs/`), 1920s gas pump design system, REST API gateway routing, geocoding lookups, security/authentication, mobile/home assistant integrations (Home Assistant, Android Auto, LubeLogger), and dev VM hosting infrastructure (Metabase, Dagu, Cloudflare Tunnels).
  2. **Track 2: Quantitative Model Engine Track (Titled `Regular Model vX.Y "Codename"` / `Diesel Model vX.Y "Codename"`):** Reserved STRICTLY for quantitative model estimation, econometric estimators, feature engineering, physical/weather data ingestion vectors, crack spread formulas, decay half-life tuning, TimesFM foundation models, SHAP attributions, and ML forecasting algorithms.
  3. **Track 3: Weekly Self-Review & MLOps Feedback Track (Titled `Weekly Review vX.Y "Codename"`):** Dedicated to the automated Saturday morning review runner (`weekly_model_review.yml`), issue self-review evaluation engine (`weekly_issue_reporter.py`), developer catalog monitoring (`catalog_monitor.py`), arXiv research paper tracking (`arxiv_monitor.py`), CORE API paper ingestion (#53), W&B model drift tracking (#80), ArchiveBox preservation (#97), Healthchecks cron heartbeats (#98), Grafana system telemetry (#107), and prediction history schema expansion (#124).
* **Strict Separation:** Issues MUST NOT cross release tracks. Non-model UI/API issues belong in the Software/UI Track; forecasting/math issues belong in the Model Engine Track; and automated review/telemetry/meta-agent issues belong in the Weekly Self-Review Track.
* **Automated Agent Issue Creation & Milestone Triage Protocol:**
  - **Mandatory Domain Labeling:** ALL issues created or triaged by any AI agent (including `catalog_monitor.py`, `weekly_issue_reporter.py`, `arxiv_monitor.py`, or interactive assistant sessions) MUST be assigned appropriate domain taxonomy labels (`data-ingestion`, `infrastructure`, `modeling`, `dashboard`, `integration`, `api`, `security`, `token-efficiency`).
  - **Auto-Creation of Missing Milestones:** If no open milestone currently exists within the designated Release Track, the agent or automated script MUST automatically create a new milestone on GitHub (via `gh api repos/{repo}/milestones -f title="..." -f description="..."` or GitHub REST API) before creating or triaging the issue.

---

### 15. Mandatory New Data Source & Issue #108 Multi-Tier Caching System Directives (`src/lookup_cache.py`)

* **Role:** Enforces standard integration patterns for all new and existing data sources, REST APIs, web scrapers, and open-data feeds to ensure full support for the 3-Tier Caching & Quota Synchronization System (Issue #108 / `src/lookup_cache.py`).
* **Core Data Ingestion & Caching Directives:**
  1. **Primary Multi-Tier Cache Gateway Integration:** ALL new data connectors, API feeds, web scrapers, and open-data modules MUST import and utilize the global cache singleton (`from src.lookup_cache import global_cache`). Data fetch routines MUST query `global_cache.get(cache_key)` prior to making external HTTP/REST network requests or disk reads.
  2. **Key Namespacing Strategy:** Every data connector MUST prefix its cache keys using a standard service domain namespace (e.g. `oilpriceapi_{key}`, `alphavant_{key}`, `eia_{series_id}`, `fred_{series_id}`, `socrata_{state}_{dataset}`, `noaa_{location}`, `finlight:{key}`) to prevent key collisions in the unified edge/local storage datastore.
  3. **TTL Enforcement & Dynamic Expiration:** Response payloads MUST be written to `global_cache` using `global_cache.set(cache_key, payload, ttl_seconds=...)` with TTL values matched to the source update frequency:
     - *Real-time Retail Pump Prices / Web Scrapers:* 15 minutes (900 seconds)
     - *Weather Bulletins / SPC Convective Outlooks:* 1 hour (3600 seconds)
     - *Daily Financial / Commodity Spot Prices & Open Data Feeds:* 24 hours (86400 seconds)
     - *Monthly/Weekly Macro Series & Quota Ledgers:* 30–60 days (2,592,000 – 5,184,000 seconds)
  4. **Multi-Environment Quota Ledger Synchronization:** For rate-limited APIs or quota-bound endpoints, data connectors MUST synchronize usage counters across both local Dev VM (`10.42.42.54`) and Production GitHub Actions runners using `global_cache.get_quota_ledger(service)` and `global_cache.update_quota_ledger(service, ...)` stored at key `quota:{service}:current`.
  5. **3-Tier Cascade & Local Disk Fallback:** Connectors MUST preserve the 3-tier resolution cascade (Tier 1 Turso Edge SQLite -> Tier 2 Cloudflare D1/R2 Worker -> Tier 3 Local SQLite `data/lookup_cache.sqlite` + In-Memory Fast Dict) and maintain secondary local JSON disk cache fallbacks (`data/{source}_cache.json`) for 100% offline benchmark execution.
  6. **Defensive Failure Isolation:** Calls to `global_cache` MUST be wrapped defensively in `try/except` blocks so that temporary edge connection failures, missing credentials, or database locks never interrupt core forecasting or data ingestion execution.
  7. **Trading-Hours & Off-Hours Optimization:** Data connectors fetching financial or market-sensitive series SHOULD combine `global_cache` with trading-hours awareness (`is_trading_hours()`) to gate off-hours API calls and eliminate redundant network traffic outside trading windows.

---

### 16. Multi-Repository Issue Routing Directives for Client Applications (`midgley-auto`)

* **Role:** Enforces repository boundary separation for client application issues and integration tracking.
* **Android Auto Repository Routing Rule:** Any GitHub issues, bug reports, feature requests, UI enhancements, or hardware integration proposals specifically regarding the **Android Auto application (`midgley-auto`)** MUST be posted to or transferred to the dedicated **[`KoshiirRa/midgley-auto`](https://github.com/KoshiirRa/midgley-auto)** GitHub repository.
* **Cross-Linking Requirement:** When creating or transferring issues in `KoshiirRa/midgley-auto` that involve API contracts, model endpoints, or backend telemetry, agents MUST include explicit markdown cross-links referencing the corresponding main model repository ([`KoshiirRa/midgley`](https://github.com/KoshiirRa/midgley)) API routes (e.g., `/api/v1/advisor/recommendation` in `src/api_server.py`).

---

### 17. Mandatory GitHub Wiki Documentation Directives for Data Source Changes

* **Role:** Enforces mandatory synchronization between the codebase, developer documentation, and the official GitHub Wiki (`KoshiirRa/midgley.wiki`).
* **Mandatory Wiki Synchronization Directives:**
  1. **New Data Source Addition:** Whenever a new data connector, API feed, open data portal, web scraper, or physical metric is added to the codebase (e.g. in `src/data_ingestion.py`, `src/noaa_weather.py`, `src/nhc_hurricane.py`, `src/bsee_shutins.py`, `src/usace_locks.py`, `src/state_open_data.py`), the agent or developer MUST automatically update the official GitHub Wiki (`https://github.com/KoshiirRa/midgley.wiki.git` on branch `master`):
     - Append a new numbered technical reference section in [`Data-Ingestion-and-APIs.md`](https://github.com/KoshiirRa/midgley/wiki/Data-Ingestion-and-APIs) documenting the connector class name, module file path, API provider, endpoints/URLs, cost profile, and ingested feature keys.
     - Update [`Agent-Architecture.md`](https://github.com/KoshiirRa/midgley/wiki/Agent-Architecture) under Agent 1 to list the new connector module.
     - Update [`Project-History-and-Roadmap.md`](https://github.com/KoshiirRa/midgley/wiki/Project-History-and-Roadmap) under the active system release phase.
  2. **Data Source Deprecation or Removal:** Whenever an existing data feed, scraper, or API connector is removed, retired, or replaced, the agent MUST automatically update the GitHub Wiki to mark the connector as deprecated/removed in `Data-Ingestion-and-APIs.md` or remove it from active agent listings, documenting the rationale and replacement feed.
  3. **Repository Wiki Sync Execution:** Wiki updates MUST be cloned (`git clone https://github.com/KoshiirRa/midgley.wiki.git`), modified, committed, and pushed to `origin/master` as part of every feature implementation workflow.

---

### 18. Mandatory Public Math & Technical Breakdown Page Synchronization Directives (`src/dashboard_generator.py`)

* **Role:** Enforces mandatory synchronization between model feature formulas, mathematical estimators, regional tax structures, and the site's public Math page (`docs/technical_breakdown.html` & `docs/technical_breakdown.md`).
* **Mandatory Math Page Synchronization Directives:**
  1. **Mathematical & Formula Updates:** Whenever new mathematical formulas, estimators, Z-scores, quantile confidence bands, or physical threat metrics are introduced or modified (e.g., 3-2-1 Crack Spread in #169, Stacking Ensemble Quantiles in #170, EIA-930 Grid Stress Z-Scores in #179, NHC Threat Radii in #177), the agent or developer MUST update `generate_technical_breakdown_file()` in `src/dashboard_generator.py`:
     - Add KaTeX-rendered LaTeX formulas and explanatory descriptions under **Section 6: Advanced Quantitative Feature & Physical Data Formulas** in both the HTML template and Markdown generator.
  2. **Regional Tax & Infrastructure Adjustments:** Whenever regional statutory tax burdens, fees, or logistics adjustments are reconciled or modified (e.g. CARB tax burden in #172, C&D Canal detours, Ohio River lock delays in #181), the agent MUST update Section 4 notes and equations in `generate_technical_breakdown_file()`.
  3. **Automatic Re-generation Execution:** The agent MUST execute `python3 -m src.dashboard_generator` to compile and output `docs/technical_breakdown.html` and `docs/technical_breakdown.md` and commit the updated pages whenever model math or connectors are updated.











