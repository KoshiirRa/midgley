# Release Notes - v0.6.6

**Release Date:** September 18, 2026  
**Build Target:** `dev-vm` (`10.42.42.54`) & Cloudflare Edge  
**Git Branch:** `dev` / `main`  
**Tracking Issue:** [Issue #314](https://github.com/KoshiirRa/midgley/issues/314)

---

## 🚀 Overview & Release Highlights

Midgley **v0.6.6** introduces **Discrete Multi-Horizon Step-Ahead Forecasting (1D–5D)**, automated historical test-split backfilling across all forecast horizons, horizon-aware MLOps prediction logging, and populates genuine empirical performance metrics across the dashboard's "Forecast Horizon Accuracy Breakdown" scoreboard.

---

### 1. Discrete Multi-Horizon Model Training Engine (`src/models.py` - Issue #314)
- Implemented `train_multi_horizon_models()` to train separate, un-interpolated Ridge / ElasticNet / Stacking estimators for discrete forecasting steps:
  - **1-Day Horizon (24h Ahead)**
  - **2-Day Horizon (48h Ahead)**
  - **3-Day Horizon (72h Ahead)**
  - **4-Day Horizon (96h Ahead)**
  - **5-Day Horizon (1-Week Ahead / Baseline)**
- Tailors feature engineering, momentum lags, and exponential event decay half-lives ($t_{1/2}$) specifically to each target lead time.

---

### 2. Horizon-Aware MLOps Prediction Logging & Deduplication (`src/prediction_logger.py`)
- Upgraded `log_predictions()` and `ensure_history_store()` to explicitly record and track `forecast_horizon_days` (1, 2, 3, 4, 5) per logged forecast.
- Fixed historical deduplication subset to include `forecast_horizon_days` in `drop_duplicates()`, preventing sequential multi-horizon predictions from overwriting earlier horizon records.
- Enhanced `backfill_new_region_history()` to accept `forecast_horizon_days` and backfill mature out-of-time test predictions across all 5 horizons.
- Upgraded `_infer_horizon_days()` with business-day delta inference from `log_timestamp` to `forecast_target_date` for legacy log records.

---

### 3. Comprehensive Hub Integration (`src/locations/*/main.py`)
- Updated National wholesale RBOB pipeline (`src/locations/national/main.py`) and all regional metro hubs to execute discrete 1D–5D model training and logging:
  - **National Hub:** Wholesale RBOB futures 1D–5D models.
  - **Tulsa Metro Hub (`Tulsa_OK`):** Cushing WTI & West Tulsa refinery crack margin 1D–5D models.
  - **Newark Metro Hub (`Newark_DE`):** PADD 1B & Delaware City refinery detour 1D–5D models.
  - **Cincinnati Tri-State Hub (`Cincinnati_OH` & `Cincinnati_KY`):** Dual-state tax & inland waterway tow draft 1D–5D models.
  - **Greenville Hub (`Greenville_NC`):** PADD 1C Colonial Pipeline delivery 1D–5D models.
  - **Charlotte Hub (`Charlotte_NC`):** PADD 1C Charlotte rack terminal 1D–5D models.
  - **Oakland & SF Bay Area Hub (`Oakland_CA` & `BayArea_CA`):** PADD 5 CARB & Richmond refinery 1D–5D models.
  - **Port St. Lucie Hub (`Port_St_Lucie_FL`):** PADD 1C waterborne terminal freight 1D–5D models.

---

### 4. REST API & Static Feeds Multi-Horizon Integration (`src/api_server.py`)
- Upgraded `_get_forecast_impl()` in `src/api_server.py` to read genuine discrete horizon models (`day_1` through `day_5`) directly from prediction history when available, falling back gracefully to smooth linear progression only if discrete horizons are missing.
- Refreshed all static JSON payloads under `docs/api/v1/` with discrete multi-horizon price outputs.

---

### 5. Empirical Scoreboard Horizon Breakdown (`src/prediction_logger.py` & `docs/index.html`)
- Resolved zero values in the public dashboard's "Forecast Horizon Accuracy Breakdown" scoreboard.
- Populated historical evaluations ($N > 0$), rolling MAE, RMSE, and Directional Hit Rates (%) across 1D, 2D, 3D, 4D, and 5D horizons.

---

### 6. Automated Unit Tests (`tests/test_multi_horizon_forecasting.py`)
- Added comprehensive unit test coverage verifying:
  - `train_multi_horizon_models()` training across horizons 1 through 5.
  - Business day horizon inference with weekend rollover handling.
  - Multi-horizon prediction logging, backfilling, and scoreboard breakdown metric generation.
- Full pytest suite (28 passing tests across unit test modules).
