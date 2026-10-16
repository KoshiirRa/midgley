# Release Notes - v0.7.2

Midgley **v0.7.2** is a reliability and performance maintenance release delivering comprehensive DataFrame defragmentation, centralized CSV `low_memory` dtype unification, and strict runtime warning hardening across all quantitative estimators and benchmark loaders.

---

## 🎯 Highlights & Improvements

### 1. DataFrame Defragmentation & Copy Barriers
- **Feature Engineering Performance Optimization**: Introduced strategic `.copy()` defragmentation barriers in [`src/feature_engineering.py`](src/feature_engineering.py) and [`src/cospot_spectral_engine.py`](src/cospot_spectral_engine.py).
- **Eliminated Fragmentation Warnings**: Resolved pandas `PerformanceWarning: DataFrame is highly fragmented` when appending multi-factor seasonal, spectral, and macroeconomic features across large time-series windows.

### 2. Dtype Standardization & Centralized Prediction History Loader
- **Safe CSV Ingestion Helper**: Added `read_prediction_history(path)` in [`src/prediction_logger.py`](src/prediction_logger.py) with standardized `PREDICTION_HISTORY_DTYPES` and `low_memory=False`.
- **Eliminated Mixed-Dtype Warnings**: Resolved pandas `DtypeWarning: Columns (10: actual_direction, 31: headline_trigger) have mixed types` across all 10 downstream consumers:
  - `src/prediction_logger.py`
  - `src/dashboard_generator.py`
  - `src/api_server.py`
  - `src/agent_memory.py`
  - `src/weekly_issue_reporter.py`
  - `src/readme_updater.py`
  - `src/social_embed_generator.py`
  - `src/dynamic_region.py`
  - `src/learning_tracker.py`
  - `src/live_fuel_feed.py`

### 3. Comprehensive Benchmark Loader Hardening
- Applied explicit `low_memory=False` to all physical, emissions, and pipeline benchmark datasets:
  - Texas Commission on Environmental Quality (TCEQ) EEERD flaring logs (`src/tceq_emissions.py`)
  - Louisiana Department of Environmental Quality (LDEQ) EDMS emissions (`src/ldeq_emissions.py`)
  - USCG National Response Center (NRC) discharge telemetry (`src/nrc_incidents.py`)
  - Bay Area Air Quality Management District (BAAQMD) flaring events (`src/baaqmd_flares.py`)
  - U.S. Census Bureau Port-Level Petroleum Trade imports (`src/census_trade_feed.py`)
  - Joint Organisations Data Initiative (JODI-Oil) global production balances (`src/jodi_oil_feed.py`)
  - PHMSA Hazardous Liquid Pipeline incidents (`src/phmsa_pipeline.py`)
  - CARB Low Carbon Fuel Standard (LCFS) & Cap-and-Trade compliance indices (`src/carb_compliance.py`)
  - Realized abnormal return event episodes (`src/event_calibration.py`)

### 4. Syntax & LaTeX Delimiter Escape Rectification
- Escaped inline mathematical expressions (`\(N=100\)`) in [`src/dashboard_generator.py`](src/dashboard_generator.py) to prevent Python 3.12+ `SyntaxWarning: invalid escape sequence`.
- Verified 100% test suite pass rate with strict warning-as-errors enforcement:
  ```bash
  pytest -W error::pandas.errors.DtypeWarning -W error::pandas.errors.PerformanceWarning -W error::SyntaxWarning
  ```

---

## 📦 Commits & Attribution
* **Tag**: `v0.7.2`
* **Release Manifest**: `RELEASE_MANIFEST.json`

