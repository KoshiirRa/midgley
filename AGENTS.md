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
* **Real-Time Financial News Stream (`src/finlight_feed.py`):**
  - **Live Coverage:** Ingests real-time financial energy headlines from tier-1 media (Reuters, Bloomberg, Seeking Alpha, Investing.com) via `finlight.me` REST API.
  - **Dynamic Ingestion:** Queries oil, gasoline, refining outages, OPEC decisions, and global maritime chokepoint shifts.
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

### 4. Localized Metro Area Calibration Agents (`src/tulsa_regional.py`, `src/newark_regional.py`, `src/cincinnati_regional.py`, & `src/oakland_regional.py`)

* **Role:** Ingest the base commodity forecast from the Main Quantitative Model and calibrate to local retail pump prices, dynamic regional rack margins, refinery dynamics, delivery hub logistics, and localized infrastructure shocks.
* **Tulsa Regional Calibration Agent (`src/tulsa_regional.py`):**
  - Tailors market time series to the Tulsa, OK metropolitan area calibrated to live pump prices ($3.89/gal base) & Cushing WTI delivery hub dynamics.
  - Rack margin: $P_{\text{Tulsa Retail}} = P_{\text{Wholesale RBOB}} + \text{Dynamic Rack Margin}$.
* **Newark Regional Calibration Agent (`src/newark_regional.py`):**
  - Tailors market time series to the Newark, DE metropolitan area (PADD 1B Central Atlantic) calibrated to live pump prices ($3.35/gal base) & PBF Delaware City Refinery (180,000 bpd capacity).
  - Integrates **Delaware Bay deepwater lightering alerts (Big Stone Anchorage)** and **Chesapeake & Delaware (C&D) Canal barge detour events** (300 nm detour around Delmarva, $+\$0.097/\text{gal}$ rack margin expansion, $p = 0.00191$).
* **Cincinnati Regional Calibration Agent (`src/cincinnati_regional.py`):**
  - Tailors market time series to the Cincinnati, OH & Northern Kentucky tri-state metropolitan area, modeling the dual-state fuel tax differential (Ohio state fuel tax $0.385/\text{gal}$ vs Kentucky state fuel tax $0.260/\text{gal}$, creating a persistent $\approx \$0.125/\text{gal}$ cross-river retail price gap).
  - Integrates Marathon Catlettsburg KY Refinery dynamics (291,000 bpd capacity), Ohio River marine terminal barge deliveries, and **Lower Mississippi River downriver low-water barge bottlenecks (Cairo, IL confluence & Memphis draft restrictions)**.
* **Oakland & SF Bay Area Regional Calibration Agent (`src/oakland_regional.py`):**
  - Tailors market time series to Oakland, CA ($4.950/gal base) and the 9-County SF Bay Area Region ($5.050/gal base), establishing high-cost PADD 5 West Coast benchmarks ("scare factor").
  - Models statutory **CARB & CA state tax burden ($0.953/gal total)**: 63.4¢ state excise tax, ~25¢ Cap-and-Trade carbon fees, ~18.5¢ LCFS credit overhead, and ~15¢ local sales tax/UST fees.
  - Integrates Chevron Richmond Refinery dynamics (245,000 bpd capacity), PBF Martinez, Valero Benicia, Kinder Morgan SFPP pipeline corridors, **USGS Hayward/San Andreas Fault seismic risks**, **CAL FIRE & PG&E Public Safety Power Shutoff (PSPS) refinery blackout risks**, **NOAA PTWC Tsunami advisories**, and **NHC EPAC Tropical Storm Remnants**.

---

### 5. Synthesis & Scenario Simulator Agent (`main.py`, `tulsa_main.py`, `newark_main.py`, `cincinnati_main.py`, & `oakland_main.py`)

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
* **Automated Daily Schedule:** Executes automatically during daily forecast runs (02:00 AM Central) to maintain clean out-of-time prediction records.
* **Functions:**
  - `log_predictions()`: Logs 5-day out-of-time forecasts.
  - `backfill_actual_prices()`: Queries ground-truth market prices from `yfinance` as target dates mature and backfills actual prices in `prediction_history.csv`.

---

### 7. Model Performance Review & Continuous Feedback Loop Agent (`.github/workflows/weekly_model_review.yml`)

* **Role:** Operates automated weekly model performance evaluations and maintains a continuous feedback loop into the quantitative forecasting engine to drive accuracy improvements over time.
* **Automated Cloud Schedule:** Executes automatically every **Saturday morning at 08:00 AM Central / 13:00 UTC** on GitHub Actions cloud runners.
* **Continuous Feedback Loop Mechanism:**
  - **Rolling Error Metrics:** Evaluates rolling MAE, RMSE, and Directional Hit Rate metrics across 30-day, 60-day, and 90-day historical evaluation windows.
  - **Empirical Feedback Loop:** Feeds diagnostic loss signals back into estimator re-calibration, adjusting regularized Ridge regression hyperparameters ($\alpha$), updating LLM feature decay half-lives ($t_{1/2}$), and fine-tuning prompt scoring weights to continuously refine model accuracy.

---

### 8. Public Web Dashboard & Multi-Locale Presentation Agent (`src/dashboard_generator.py`)

* **Role:** Builds and updates the responsive, multi-page public web application deployed to GitHub Pages (`docs/`).
* **Route Structure & Hierarchy:**
  - **Overview Landing Page (`/` / `docs/index.html`):** Executive overview of the Midgley engine, listing current and 5-day projected target forecasts for all active locales, rolling MAE/directional accuracy improvement charts, and core feature pillars.
  - **National Wholesale RBOB Page (`/national` / `docs/national.html` & `docs/national/index.html`):** Dedicated commodity futures page with NYMEX RBOB predictions chart, out-of-time error metrics, global maritime & geopolitical shock scenarios (Hormuz/Suez), and technical driver breakdowns. Accessible via **`National Wholesale`** in the top navbar.
  - **Tulsa Metro Retail Gas Page (`/tulsa` / `docs/tulsa.html` & `docs/tulsa/index.html`):** Dedicated regional retail page calibrated to live pump prices ($3.89/gal), Cushing WTI delivery hub dynamics, West Tulsa HF Sinclair refinery tornado/freeze shock scenarios, and dynamic rack margins ($0.706/gal). Accessible via the top nav **`Metro Areas`** dropdown menu.
  - **Educational Math Guide (`/math` / `docs/math.html`):** Educational reference detailing equations and vector spaces across all 9 feature layers rendered via KaTeX.

---

### 9. Dev Environment & Permanent Server Agent (`dev-vm` Port 8080)

* **Role:** Manages the persistent local development environment on `dev-vm` (`10.42.42.54`), keeping the permanent `dev` branch active and serving the web dashboard live on port 8080.
* **Key Specifications:**
  - **Dedicated Dev Branch:** Tracks the permanent `dev` branch (`origin/dev`) at `/home/marty/projects/midgley`.
  - **Systemd User Service:** Managed by `midgley-dev.service` (`python3 -m http.server 8080 --directory /home/marty/projects/midgley/docs --bind 0.0.0.0`) with automatic restart capabilities (`Restart=always`).
  - **User Linger:** User linger enabled (`loginctl enable-linger marty`) to ensure background web service persistence across host reboots.

---

### 10. Nightly Dev Release Automation Agent (`.github/workflows/nightly_dev_release.yml`)

* **Role:** Executes automated nightly pre-releases tracking whatever is committed on the permanent `dev` branch.
* **Automated Cloud Schedule:** Executes daily at **03:00 AM Central / 08:00 UTC** on GitHub Actions.
* **Key Specifications:**
  - **Tagging Strategy:** Tagged as `dev-YYYY-MM-DD` and published as a GitHub Pre-Release.
  - **Automated Changelog Generation:** Parses git commit history since the preceding nightly release, formatting structured release notes with commit messages, commit hashes, and author attributions.


