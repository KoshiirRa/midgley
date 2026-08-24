# Agent System Specification (AGENTS.md)

This project utilizes an **LLM Multi-Agent Framework** to forecast wholesale and retail unleaded gasoline prices by integrating qualitative real-world event intelligence, **NOAA Weather Models**, **Global Maritime Chokepoints (Hormuz/Suez/Venezuela)**, **Executive Social Media (Trump Posts & Weekend Gap Analysis)**, **Alternative Physical Data (Cboe OVX Volatility & Baker Hughes Rig Counts)**, and **Tulsa Regional Refining Dynamics** into quantitative time-series estimators.

---

## Multi-Agent Architecture Overview

```
               ┌─────────────────────────────────────────────────────────────┐
               │    UNSTRUCTURED NEWS, NOAA WEATHER & PHYSICAL DATA FEEDS    │
               │  • Geopolitical Headlines & OPEC Press Releases             │
               │  • NOAA NWS API (api.weather.gov) - Oklahoma & Basin Alerts │
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
               │            3. TULSA REGIONAL CALIBRATION AGENT              │
               │               (src/tulsa_regional.py)                       │
               │ • Anchors Base Forecast to Live Pump Prices ($3.89/gal)     │
               │ • Computes Cushing WTI Crack Spread & Rack Margins          │
               └──────────────────────────────┬──────────────────────────────┘
                                              │
                                              ▼
               ┌─────────────────────────────────────────────────────────────┐
               │             4. QUANTITATIVE FORECASTING AGENT               │
               │           (Standardized Ridge / XGBoost Estimator)          │
               └──────────────────────────────┬──────────────────────────────┘
                                              │ Base Forecasts
                                              ▼
               ┌─────────────────────────────────────────────────────────────┐
               │             5. SYNTHESIS & SHOCK SIMULATOR AGENT            │
               │ Simulates Refinery Outages, Hormuz Blockades & Weekend Posts │
               └──────────────────────────────┬──────────────────────────────┘
                                              │ Real-Time Adjusted Forecast
                                              ▼
               ┌─────────────────────────────────────────────────────────────┐
               │             6. MLOps PREDICTION LOGGING AGENT               │
               │        (src/prediction_logger.py -> prediction_history.csv)│
               │  Backfills Actual Prices & Evaluates Rolling Error Metrics  │
               │  Automated Daily (02:00 AM) & Saturday (08:00 AM Central) Runners   │
               └──────────────────────────────┘
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

### 3. Tulsa Regional Calibration Agent (`src/tulsa_regional.py`)

* **Role:** Tailors market time series to the Tulsa, OK metropolitan area.
* **Key Mechanisms:**
  - **Cushing WTI Dynamics:** Cushing, OK delivery hub (50 miles from Tulsa).
  - **Live Pump Price Anchor:** Dynamically calibrates historical and projected series to current retail pump prices (e.g. **$3.89/gal**).
  - **Tulsa Rack Margin:** $P_{\text{Tulsa Retail}} = P_{\text{Wholesale RBOB}} + \text{Dynamic Rack Margin}$.

---

### 4. Quantitative Forecasting Agent (`src/models.py`)

* **Role:** Fits regularized linear pipelines (StandardScaler + Ridge Regression α=10.0) and XGBoost regressors on 80/20 chronological train/test splits.
* **Out-of-Time Test Performance (v1.4 Finlight-LLM):**
  - **National Model:** **60.79% Directional Accuracy** ($0.1069 MAE).
  - **Tulsa Model:** **58.15% Directional Accuracy** ($0.1331 MAE).

---

### 5. Synthesis & Scenario Simulator Agent (`main.py` & `tulsa_main.py`)

* **Role:** Enables counterfactual "What-If" scenario simulation.
* **Scenarios Evaluated:**
  - *West Tulsa HF Sinclair Refinery EF-3 Tornado Shock:* +$0.173/gal (+4.58%)
  - *Cushing Keystone Pipeline Spill:* +$0.173/gal (+4.58%)
  - *Strait of Hormuz Tanker Blockade (21M bpd):* +$0.109/gal (+2.88%)
  - *Red Sea / Suez Rerouting Crisis:* +$0.201/gal (+5.32%)
  - *Weekend Executive OPEC Talkdown Post:* $3.780/gal (Monday Open Re-anchoring)
  - *Weekend Foreign Energy Tariff Declaration:* $3.780/gal (Supply Shock Re-anchoring)

---

### 6. MLOps Prediction Logging & Weekly Review Agent (`src/prediction_logger.py` & `.github/workflows/weekly_model_review.yml`)

* **Role:** Manages persistent prediction tracking in `data/prediction_history.csv` and executes weekly performance reviews.
* **Automated Cloud Schedule:** Executes automatically every **Saturday morning at 08:00 AM Central / 13:00 UTC** on GitHub Actions cloud runners.
* **Functions:**
  - `log_predictions()`: Logs 5-day out-of-time forecasts.
  - `backfill_actual_prices_and_evaluate()`: Backfills actual historical prices from `yfinance` as target dates arrive and calculates rolling MAE, RMSE, and Directional Hit Rate.

---

### 7. Public Web Dashboard & Multi-Locale Presentation Agent (`src/dashboard_generator.py`)

* **Role:** Builds and updates the responsive, multi-page public web application deployed to GitHub Pages (`docs/`).
* **Route Structure & Hierarchy:**
  - **Overview Landing Page (`/` / `docs/index.html`):** Executive overview of the Midgley engine, listing current and 5-day projected target forecasts for all active locales, rolling MAE/directional accuracy improvement charts, and core feature pillars.
  - **National Wholesale RBOB Page (`/national` / `docs/national.html` & `docs/national/index.html`):** Dedicated commodity futures page with NYMEX RBOB predictions chart, out-of-time error metrics, global maritime & geopolitical shock scenarios (Hormuz/Suez), and technical driver breakdowns. Accessible via **`National Wholesale`** in the top navbar.
  - **Tulsa Metro Retail Gas Page (`/tulsa` / `docs/tulsa.html` & `docs/tulsa/index.html`):** Dedicated regional retail page calibrated to live pump prices ($3.89/gal), Cushing WTI delivery hub dynamics, West Tulsa HF Sinclair refinery tornado/freeze shock scenarios, and dynamic rack margins ($0.706/gal). Accessible via the top nav **`Metro Areas`** dropdown menu.
  - **Educational Math Guide (`/math` / `docs/math.html`):** Educational reference detailing equations and vector spaces across all 9 feature layers rendered via KaTeX.
