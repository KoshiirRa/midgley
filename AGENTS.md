# Agent System Specification (AGENTS.md)

This project utilizes an **LLM Multi-Agent Framework** to forecast wholesale unleaded gasoline prices by integrating qualitative real-world event intelligence into quantitative time-series models.

---

## Agent Architecture Overview

```
                      ┌──────────────────────────────────────────────┐
                      │             UNSTRUCTURED NEWS FEED           │
                      └──────────────────────┬───────────────────────┘
                                             │
                                             ▼
                      ┌──────────────────────────────────────────────┐
                      │            EVENT EXTRACTION AGENT            │
                      │     (LLM NLP Factor Vector Extraction)       │
                      └──────────────────────┬───────────────────────┘
                                             │  Structured Scores
                                             ▼
┌──────────────────────────────┐     ┌────────────────────────────────┐
│ QUANTITATIVE DATA ENGINE     │     │ EXPONENTIAL MEMORY FUSION AGENT│
│ (EIA / Yahoo Finance / FRED) ├────►│  (Decays Shock Memory t1/2=5d) │
└──────────────────────────────┘     └───────────────┬────────────────┘
                                                     │ Unified Feature Matrix
                                                     ▼
                                     ┌────────────────────────────────┐
                                     │ QUANTITATIVE FORECASTING AGENT │
                                     │  (Ridge / XGBoost Estimator)   │
                                     └───────────────┬────────────────┘
                                                     │ Base Forecasts
                                                     ▼
                                     ┌────────────────────────────────┐
                                     │ SYNTHESIS & SHOCK SIMULATOR    │
                                     │             AGENT              │
                                     └───────────────┬────────────────┘
                                                     │ Real-Time Adjusted Forecast
                                                     ▼
                                     ┌────────────────────────────────┐
                                     │       FINAL OUTPUT / PROMPT    │
                                     └────────────────────────────────┘
```

---

## Agent Specifications

### 1. Event Extraction Agent (`src/event_analyzer.py`)

* **Role:** Translates raw, unstructured textual news feeds (OPEC press releases, geopolitical bulletins, weather warnings, macro rate announcements) into structured, bounded numeric factor vectors.
* **Model Engine:** Google Gemini (`gemini-2.5-flash` / `gemini-1.5-flash`) via `google-genai` SDK with deterministic NLP fallback.
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
* **Output Schema:**
  ```json
  {
    "geopolitical_risk": 0.8,
    "supply_disruption": 0.4,
    "demand_sentiment": 0.0,
    "opec_action": 0.0,
    "overall_price_pressure": 0.38
  }
  ```

---

### 2. Exponential Memory Fusion Agent (`src/feature_engineering.py`)

* **Role:** Solves the "single-day point shock" problem by modeling real-world news persistence.
* **Mathematical Function:** Applies exponential memory decay ($half\text{-}life = 5.0\text{ business days}$) to simulate how shock events affect market expectations over 2–3 weeks:
  \[
  \text{Memory}_{t} = \text{Memory}_{t-1} \times e^{-\frac{\ln(2)}{5.0}} + \text{NewShock}_t
  \]
* **Output:** Continuous time-series features (`event_geopolitical_risk`, `event_supply_disruption`, `event_overall_price_pressure`) fused chronologically with technical market indicators.

---

### 3. Quantitative Forecasting Agent (`src/models.py`)

* **Role:** Trains baseline quantitative models (prices, moving averages, crack spread proxies) alongside hybrid LLM-augmented models.
* **Algorithm:** Standardized Ridge Regression ($\alpha=10.0$) and XGBoost Regressor ($depth=3, lr=0.03$).
* **Ablation Duty:** Evaluates out-of-time test set performance and outputs key error metrics:
  - Mean Absolute Error (MAE)
  - Root Mean Squared Error (RMSE)
  - Mean Absolute Percentage Error (MAPE %)
  - Directional Hit Rate (%)

---

### 4. Synthesis & Scenario Simulator Agent (`main.py`)

* **Role:** Enables counterfactual scenario testing ("What-If" analysis).
* **Workflow:**
  1. Accepts user-provided natural language shock scenarios (e.g. *"Category 5 Hurricane approaching Gulf Coast refinery complex"*).
  2. Invokes the **Event Extraction Agent** to score the shock.
  3. Injects shock scores into the current market state.
  4. Runs the **Quantitative Forecasting Agent** to produce the baseline vs. shocked price forecast and delta ($+\$/\text{gal}$).

---

## Execution & API Keys

To configure live Gemini LLM API calls for the Event Extraction Agent:
```bash
export GEMINI_API_KEY="your-api-key-here"
python main.py --use-llm-api
```
If `GEMINI_API_KEY` is omitted, the agent automatically runs the deterministic NLP domain lexicon scorer for reproducible offline experimentation.
