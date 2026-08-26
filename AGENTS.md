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
  - **Strategy 2 (Free RSS Polling):** Zero-cost 15-minute polling across free energy RSS streams (Google News, NYT, CNBC).
  - **Strategy 1 (Cascading Anomaly Gate):** Regex/keyword trigger gate (`tariff`, `retaliat`, `trade war`, `opec emergency`, `pipeline halt`, `explosion`, `tornado`) evaluating fast-path impact scores. Tripping threshold: \(|\text{overall\_price\_pressure}| \ge 0.40\) or \(\text{supply\_disruption} \ge 0.50\).
  - **Strategy 3 (Trading Hours Adaptive Ingestion):** `is_trading_hours()` helper restricts `finlight.me` fetches to active US commodity trading hours (08:00 AM – 05:00 PM EST, Mon–Fri).
  - **Strategy 4 (Incoming Webhook Gateway & HMAC Security):** `POST /api/v1/events/webhook` endpoint on `src/api_server.py` for direct push ingestion from external alerts (Zapier, IFTTT, Google Alerts). Enforces HMAC-SHA256 signature validation via `X-Midgley-Signature` header when `MIDGLEY_WEBHOOK_SECRET` is set in the environment, rejecting unauthorized payload tampering with HTTP 401.

* **Tiered Multi-Provider LLM Failover Engine (`src/event_analyzer.py`):**
  - **Tier 1 (Primary):** Google **Gemini 2.5 Flash** (`GEMINI_API_KEY`).
  - **Tier 2 (Secondary - Optional):** OpenAI `gpt-4o-mini` (`OPENAI_API_KEY`) / Anthropic `claude-3-5-haiku` (`ANTHROPIC_API_KEY`). Soft-checked if keys exist; safely skipped if absent.
  - **Tier 3 (Safety Net - 100% Guaranteed):** **Offline Rule-Based Lexicon Extractor**. 100% offline, $0 cost, 0 API keys required, zero downtime guarantee.
* **Executive Social Media & Weekend Gap Engine:**
  - **Empirical Correlation:** Econometric analysis confirms $p < 0.01$ correlation between executive social media posts (e.g., Trump OPEC pressure & tariff declarations) and immediate short-term futures return shocks.
  - **Dovish OPEC Pressure:** Posts urging OPEC to lower prices cause immediate average $-1.85\%$ single-day RBOB price drops.
  - **Hawkish Tariff Shocks:** Energy import tariff threats produce $+2.10\%$ 24-hour price surges.
  - **Weekend Market Gap Multiplier:** Saturday/Sunday posts published while commodity markets are closed produce **$1.42\times$ higher Monday morning open price gap volatility**.


---

### 2. Exponential Memory Fusion Agent (`src/feature_engineering.py`)

* **Role:** Solves point-shock persistence by modeling event decay over 2–3 weeks.
* **Mathematical Decay:**
  \[
  \text{Memory}_{t} = \text{Memory}_{t-1} \times e^{-\frac{\ln(2)}{t_{1/2}}} + \text{NewShock}_t
  \]
  where $t_{1/2} = 5.0\text{ days}$ for national macroeconomic/social events and $t_{1/2} = 4.0\text{ days}$ for regional NOAA weather shocks.

---

### 3. Quantitative Forecasting Agent (`src/models.py`)

* **Role:** Fits regularized linear pipelines (StandardScaler + Ridge Regression α=10.0) and XGBoost regressors on 80/20 chronological train/test splits. Main model generates base wholesale RBOB commodity price forecasts.
* **Out-of-Time Test Performance (v1.4 Finlight-LLM):**
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
* **Oakland & SF Bay Area Regional Calibration Agent (`src/locations/oakland/`):**
  - Tailors market time series to Oakland, CA ($4.950/gal base) and the 9-County SF Bay Area Region ($5.050/gal base), establishing high-cost PADD 5 West Coast benchmarks ("scare factor").
  - Models statutory **CARB & CA state tax burden ($0.953/gal total)**: 63.4¢ state excise tax, ~25¢ Cap-and-Trade carbon fees, ~18.5¢ LCFS credit overhead, and ~15¢ local sales tax/UST fees.
  - Integrates Chevron Richmond Refinery dynamics (245,000 bpd capacity), PBF Martinez, Valero Benicia, Kinder Morgan SFPP pipeline corridors, **USGS Hayward/San Andreas Fault seismic risks**, **CAL FIRE & PG&E Public Safety Power Shutoff (PSPS) refinery blackout risks**, **NOAA PTWC Tsunami advisories**, and **NHC EPAC Tropical Storm Remnants**.

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

* **Role:** Manages persistent prediction tracking by writing 5-day out-of-time forecasts to `data/prediction_history.csv` and backfilling actual historical market prices as target dates arrive.
* **Automated Daily Schedule & Target Calculation:** Executes automatically during daily forecast runs (02:00 AM Central). For every daily run, the 5-day out-of-time target date is automatically computed as `run_date + 5 days` (e.g. run date `2026-08-24` -> target date `2026-08-29`), maintaining clean out-of-time prediction records.
* **Functions:**
  - `log_predictions()`: Logs 5-day out-of-time forecasts with dynamically calculated target dates.
  - `backfill_actual_prices()`: Queries ground-truth market prices from `yfinance` as target dates mature and backfills actual prices in `prediction_history.csv`.

---

### 7. Model Performance Review & Continuous Feedback Loop Agent (`.github/workflows/weekly_model_review.yml`, `src/weekly_issue_reporter.py` & `src/catalog_monitor.py`)

* **Role:** Operates automated weekly model performance evaluations, self-reviews open GitHub repository issues, monitors public developer catalog lists for newly added tools, and maintains a continuous feedback loop into the quantitative forecasting engine to drive accuracy improvements over time.
* **Automated Cloud Schedule:** Executes automatically every **Saturday morning at 08:00 AM Central / 13:00 UTC** on GitHub Actions cloud runners.
* **Continuous Feedback Loop & Self-Review Mechanism:**
  - **Rolling Error Metrics:** Evaluates rolling MAE, RMSE, and Directional Hit Rate metrics across 30-day, 60-day, and 90-day historical evaluation windows.
  - **Open GitHub Issue Self-Review:** Fetches all open repository issues on `KoshiirRa/midgley` via `gh` CLI or GitHub REST API, evaluates each issue's potential modeling impact using Gemini 2.5 Flash (with a domain-specific heuristic fallback), ranks issues, and selects the top issue expected to yield the largest accuracy/MAE improvement.
  - **Automated Developer Catalog Monitor (`src/catalog_monitor.py` & `data/catalog_monitors_state.json`):** Continuously tracks 6 major developer catalog indexes (`public-apis`, `free-for-dev`, `freestuff.dev`, `free-for-life`, `awesome`, `awesome-selfhosted`). On weekly runs, evaluates newly added catalog items with Gemini 2.5 Flash and automatically files GitHub Feature Request issues for items scoring $\ge 7.0/10.0$.
  - **Empirical Feedback Loop:** Feeds diagnostic loss signals back into estimator re-calibration, adjusting regularized Ridge regression hyperparameters ($\alpha$), updating LLM feature decay half-lives ($t_{1/2}$), and fine-tuning prompt scoring weights to continuously refine model accuracy.

---

### 8. Public Web Dashboard & Multi-Locale Presentation Agent (`src/dashboard_generator.py`)

* **Role:** Builds and updates the responsive, multi-page public web application deployed to GitHub Pages (`docs/`).
* **Dynamic Overview Card Engine:** Dynamically queries real-time live retail pump prices via `fetch_live_metro_retail_price()` for all regional metro cards (`Tulsa_OK`, `Newark_DE`, `Cincinnati_OH`, `Oakland_CA`, `BayArea_CA`), while preserving NYMEX RBOB commodity futures benchmark pricing ($3.184/gal - $3.270/gal) for the **National Wholesale** contract card.
* **Route Structure & Hierarchy:**
  - **Overview Landing Page (`/` / `docs/index.html`):** Executive overview of the Midgley engine, listing current and 5-day projected target forecasts for all active locales, rolling MAE/directional accuracy improvement charts, and core feature pillars.
  - **National Wholesale RBOB Page (`/national` / `docs/national.html` & `docs/national/index.html`):** Dedicated commodity futures page with NYMEX RBOB predictions chart, out-of-time error metrics, global maritime & geopolitical shock scenarios (Hormuz/Suez), and technical driver breakdowns. Accessible via **`National Wholesale`** in the top navbar.
  - **Tulsa Metro Retail Gas Page (`/tulsa` / `docs/tulsa.html` & `docs/tulsa/index.html`):** Dedicated regional retail page calibrated to live pump prices ($3.89/gal), Cushing WTI delivery hub dynamics, West Tulsa HF Sinclair refinery tornado/freeze shock scenarios, and dynamic rack margins ($0.706/gal). Accessible via the top nav **`Metro Areas`** dropdown menu.
  - **Educational Math Guide (`/math` / `docs/math.html`):** Educational reference detailing equations and vector spaces across all 10 feature layers rendered via KaTeX (including Section 10 multiline `aligned` CARB tax breakdown).

---

### 9. Dev Environment & Permanent Server Agent (`dev-vm` Port 8080 & Systemd Local Workflow Timers)

* **Role:** Manages the persistent local development environment on `dev-vm` (`10.42.42.54`), keeping the permanent `dev` branch active, serving the web dashboard live on port 8080, and running local scheduled workflow equivalents (daily forecasting & weekly model issue self-reviews).
* **Key Specifications:**
  - **Dedicated Dev Branch:** Tracks the permanent `dev` branch (`origin/dev`) at `/home/marty/projects/midgley`.
  - **Systemd Web & API Services:** Managed by `midgley-dev.service` (dashboard web server on port 8080) and `midgley-api.service` (FastAPI / MCP gateway on port 8000).
  - **Systemd Scheduled Local Workflow Timers:**
    - `midgley-daily-forecast.timer`: Executes `scripts/run_local_daily_forecast.sh` daily at **02:00 AM Central / 07:00 UTC**.
    - `midgley-intraday-polling.timer`: Executes `scripts/run_local_intraday_polling.sh` **every 15 minutes** 24/7 (running zero-cost RSS energy news polling, evaluating shock thresholds, and auto-revising forecasts/dashboard on anomalies).
    - `midgley-weekly-review.timer`: Executes `scripts/run_local_weekly_review.sh` every **Saturday at 08:00 AM Central / 13:00 UTC** (running model backtests, GitHub open issue self-reviews via Gemini, and public dashboard updates).
  - **User Linger:** User linger enabled (`loginctl enable-linger marty`) to ensure background web services and scheduled timers run 24/7 across host reboots.

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
* **Service Orchestration:** Managed by `midgley-api.service` running continuously on `dev-vm` (`https://local-dev.dwarvenbard.com` / `10.42.42.54:8000`).
* **Scraper Fallback Sequence (`src/live_fuel_feed.py`):**
  - **Step 1 (GasBuddy GraphQL):** Real-time station queries by zip code.
  - **Step 2 (AAA Metro BS4 Scraper):** Targeted BeautifulSoup metro table parsing by region keywords (e.g. `Oakland`, `San Francisco`, `Tulsa`, `Wilmington`, `Cincinnati`, `Covington`). Rejects unparseable headers to return `None` rather than matching global top-nav header text.
  - **Step 3 (EIA / yfinance RBOB Futures Benchmark):** RBOB futures contract close plus regional rack margin offset.
  - **Step 4 (prediction_history.csv Clean History):** Prior validated regional base price (sanitized against anomalies $< \$4.50$ for CA regions).
  - **Step 5 (Static Regional Fallback Anchor):** Locale-specific base anchors ($5.550 Oakland, $5.650 Bay Area, $3.890 Tulsa, $3.350 Newark, $3.450 Cincinnati).
* **Key Components:**
  - **SQLite/In-Memory Response Cache (`src/lookup_cache.py`):** 15-minute TTL cache protecting upstream GasBuddy and AAA web scrapers from rate limits.
  - **RESTful API Endpoint Gateway (`src/api_server.py`):** FastAPI application serving `/api/v1/prices/live`, `/api/v1/forecast/predict`, `/api/v1/combined`, `/api/v1/forecast/simulate`, `/openapi.json`, and GPT Action manifest (`/.well-known/ai-plugin.json`).
  - **Model Context Protocol (MCP) Server (`src/mcp_server.py`):** Exposes MCP tools (`get_live_gas_prices`, `get_gas_price_prediction`, `get_live_and_forecast`, `simulate_fuel_market_shock`), static locale resources (`resource://midgley/locales/{locale}`), and prompt templates (`prompt://midgley/market_summary`) across both `stdio` and `HTTP/SSE` transport modes (`/mcp/sse`).



