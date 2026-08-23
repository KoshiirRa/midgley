# Agent System Specification (AGENTS.md)

This project utilizes an **LLM Multi-Agent Framework** to forecast wholesale and retail unleaded gasoline prices by integrating qualitative real-world event intelligence, **NOAA Weather Models**, and **Tulsa Regional Refining Dynamics** into quantitative time-series estimators.

---

## Multi-Agent Architecture Overview

```
               ┌─────────────────────────────────────────────────────────────┐
               │              UNSTRUCTURED NEWS & NOAA WEATHER FEEDS         │
               │  • Geopolitical Headlines & OPEC Press Releases             │
               │  • NOAA NWS API (api.weather.gov) - Oklahoma & Basin Alerts │
               └──────────────────────────────┬──────────────────────────────┘
                                              │
                                              ▼
               ┌─────────────────────────────────────────────────────────────┐
               │           1. EVENT & WEATHER EXTRACTION AGENT               │
               │        (Google Gemini 2.5 Flash / Domain NLP Lexicon)       │
               │ • Geopolitical Risk  • Supply Disruption  • OPEC Action     │
               │ • NOAA Tornado Risk  • NOAA Polar Vortex  • Hurricane Track │
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
               │       Simulates Refinery Outages, Tornadoes, & OPEC Cuts    │
               └──────────────────────────────┬──────────────────────────────┘
                                              │ Real-Time Adjusted Forecast
                                              ▼
               ┌─────────────────────────────────────────────────────────────┐
               │             6. MLOps PREDICTION LOGGING AGENT               │
               │        (src/prediction_logger.py -> prediction_history.csv)│
               │  Backfills Actual Prices & Evaluates Rolling Error Metrics  │
               └─────────────────────────────────────────────────────────────┘
```

---

## Agent Specifications

### 1. Event & Weather Extraction Agent (`src/event_analyzer.py` & `src/noaa_weather.py`)

* **Role:** Translates raw, unstructured news bulletins and NOAA Weather Service alerts into structured numeric factor vectors.
* **Model Engine:** Google Gemini (`gemini-2.5-flash` / `gemini-1.5-flash`) via `google-genai` SDK with deterministic NLP lexicon fallback.
* **System Prompt Contract:**
  ```text
  You are an expert energy market economist and oil commodities analyst.
  Analyze the following energy news headline/event description and extract structured numerical impact scores regarding unleaded gasoline and crude oil prices.

  Headline/Event: "{headline}"

  Return ONLY a raw JSON object with the following fields:
  - "geopolitical_risk": float between -1.0 (de-escalation/peace) and +1.0 (war/sanctions/conflict)
  - "supply_disruption": float between 0.0 (no disruption) and +1.0 (major refinery/pipeline/shipping shutdown)
  - "demand_sentiment": float between -1.0 (severe economic slowdown/recession) and +1.0 (booming demand/driving season)
  - "opec_action": float between -1.0 (production surge/price war) and +1.0 (steep supply cuts)
  - "overall_price_pressure": float between -1.0 (strong downward price pressure) and +1.0 (strong upward price pressure)
  ```

---

### 2. Exponential Memory Fusion Agent (`src/feature_engineering.py`)

* **Role:** Solves point-shock persistence by modeling event decay over 2–3 weeks.
* **Mathematical Decay:**
  \[
  \text{Memory}_{t} = \text{Memory}_{t-1} \times e^{-\frac{\ln(2)}{t_{1/2}}} + \text{NewShock}_t
  \]
  where $t_{1/2} = 5.0\text{ days}$ for national macroeconomic events and $t_{1/2} = 4.0\text{ days}$ for regional NOAA weather shocks.

---

### 3. Tulsa Regional Calibration Agent (`src/tulsa_regional.py`)

* **Role:** Tailors market time series to the Tulsa, OK metropolitan area.
* **Key Mechanisms:**
  - **Cushing WTI Dynamics:** Cushing, OK delivery hub (50 miles from Tulsa).
  - **Live Pump Price Anchor:** Dynamically calibrates historical and projected series to current retail pump prices (e.g. **$\$3.89/\text{gal}$**).
  - **Tulsa Rack Margin:** $P_{\text{Tulsa Retail}} = P_{\text{Wholesale RBOB}} + \text{Dynamic Rack Margin}$.

---

### 4. Quantitative Forecasting Agent (`src/models.py`)

* **Role:** Fits regularized linear pipelines (StandardScaler + Ridge Regression $\alpha=10.0$) and XGBoost regressors on 80/20 chronological train/test splits.
* **Out-of-Time Test Performance:**
  - **National Model:** **60.79% Directional Accuracy** ($0.1151\text{ MAE}$).
  - **Tulsa Model:** **58.15% Directional Accuracy** ($0.1331\text{ MAE}$).

---

### 5. Synthesis & Scenario Simulator Agent (`main.py` & `tulsa_main.py`)

* **Role:** Enables counterfactual "What-If" scenario simulation.
* **Scenarios Evaluated:**
  - *West Tulsa HF Sinclair Refinery EF-3 Tornado Shock:* $+\$0.212/\text{gal}\ (+5.60\%)$
  - *Cushing Keystone Pipeline Spill:* $+\$0.251/\text{gal}\ (+6.62\%)$
  - *Polar Vortex Grid Freeze:* $+\$0.220/\text{gal}\ (+5.80\%)$

---

### 6. MLOps Prediction Logging Agent (`src/prediction_logger.py`)

* **Role:** Manages persistent prediction tracking in `data/prediction_history.csv`.
* **Functions:**
  - `log_predictions()`: Logs 5-day out-of-time forecasts.
  - `backfill_actual_prices_and_evaluate()`: Backfills actual historical prices from `yfinance` as target dates arrive and calculates rolling MAE, RMSE, and Directional Hit Rate.
