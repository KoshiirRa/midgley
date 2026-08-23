# API & Developer Reference Guide

This document outlines module interfaces, functions, configuration settings, and environment variables for developer integration.

---

## 1. Data Ingestion (`src.data_ingestion`)

### `fetch_market_data(start_date: str = "2022-01-01", end_date: str = None) -> pd.DataFrame`
Fetches financial futures data using `yfinance`:
* **Tickers:** `RB=F` (RBOB Gasoline Futures), `CL=F` (WTI Crude Oil Futures), `BZ=F` (Brent Crude Futures).
* **Returns:** `pd.DataFrame` containing `date`, `gasoline_rbob`, `wti_crude`, `brent_crude`.

### `get_historical_event_dataset() -> pd.DataFrame`
Returns a curated DataFrame of real historical news events, geopolitical conflicts, OPEC decisions, and refinery weather disruptions.
* **Columns:** `date`, `headline`, `category`.

---

## 2. Event Analyzer (`src.event_analyzer`)

### `extract_event_features_llm(headline: str, api_key: str = None) -> dict`
Extracts structured numerical factor metrics from an event headline string using Google Gemini (`gemini-2.5-flash` / `gemini-1.5-flash`).
* **Parameters:**
  * `headline`: News headline text to evaluate.
  * `api_key`: Optional Gemini API Key (defaults to `GEMINI_API_KEY` environment variable).
* **Returns:** Dict containing `geopolitical_risk`, `supply_disruption`, `demand_sentiment`, `opec_action`, `overall_price_pressure`.

### `process_event_dataset(events_df: pd.DataFrame, use_llm_api: bool = False) -> pd.DataFrame`
Applies event scoring across an entire event DataFrame and appends feature metric columns.

---

## 3. Feature Engineering (`src.feature_engineering`)

### `create_feature_matrix(market_df: pd.DataFrame, events_df: pd.DataFrame = None, forecast_horizon: int = 5, decay_half_life_days: float = 5.0) -> pd.DataFrame`
Fuses technical financial indicators with decayed LLM news scores.
* **Parameters:**
  * `forecast_horizon`: Days ahead to forecast (default $5$ days).
  * `decay_half_life_days`: Half-life in business days for news memory decay.

### `prepare_chronological_splits(df: pd.DataFrame, train_ratio: float = 0.8, forecast_horizon: int = 5) -> dict`
Splits dataset chronologically into training and test sets.
* **Returns:** Dictionary containing `X_train_quant`, `X_train_hybrid`, `y_train`, `X_test_quant`, `X_test_hybrid`, `y_test`, and `test_df`.

---

## 4. Models & Evaluation (`src.models`)

### `train_and_compare_models(split_data: dict, model_type: str = "ridge") -> dict`
Trains Baseline Quantitative Model and Hybrid LLM-Augmented Model and computes comparative out-of-time metrics.
* **Supported `model_type` values:** `"ridge"`, `"xgboost"`, `"rf"`.
* **Returns:** Dictionary containing model objects, metric dictionaries (`metrics_quant`, `metrics_hybrid`), improvement percentages, and feature importances.
