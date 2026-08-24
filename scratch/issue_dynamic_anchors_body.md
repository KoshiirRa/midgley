## Problem Statement

Currently, localized regional forecasting modules (`src/tulsa_regional.py`, `src/newark_regional.py`, `src/cincinnati_regional.py`, `src/oakland_regional.py`) utilize static fallback base price anchor constants (e.g. `$3.890` for Tulsa, `$3.350` for Newark, `$3.450` for Cincinnati, `$4.950` for Oakland). As real-world retail gas prices fluctuate over time (e.g., live Oakland / Bay Area AAA average currently **~$5.55–$5.62/gal**), static base anchors drift out of alignment with ground-truth consumer pump reality.

---

## Technical Solution & Architecture Plan

Upgrade `src/live_fuel_feed.py` and regional forecasting modules to dynamically fetch and ingest live real-time retail pump price averages at runtime via GasBuddy / AAA / EIA feeds prior to running model calibration and 5-day return predictions.

### 1. Dynamic Live Fuel Feed Module (`src/live_fuel_feed.py`)
- Expand existing GasBuddy / EIA scrapers into a unified function `fetch_live_metro_retail_prices(region_code: str) -> float`.
- Add zip code and metro region mapping for:
  - **National**: EIA US Regular All Formulations Average (`EIA API` / `yfinance`)
  - **Tulsa, OK**: GasBuddy Zip `74103` / AAA Oklahoma Metro Average
  - **Newark, DE**: GasBuddy Zip `19711` / AAA Delaware Metro Average
  - **Cincinnati, OH & NKY**: GasBuddy Zip `45202` (OH side) and Zip `41011` (KY side)
  - **Oakland & SF Bay Area, CA**: GasBuddy Zip `94612` (Oakland) / AAA Bay Area Metro Average

### 2. Regional Model Calibration Updates (`src/*_regional.py` & `*_main.py`)
- Update `fetch_tulsa_market_data()`, `fetch_newark_market_data()`, `fetch_cincinnati_market_data()`, and `fetch_oakland_market_data()` to default `live_current_price` dynamically from `src.live_fuel_feed`.
- Maintain a robust fallback chain: `Live GasBuddy GraphQL API` $\rightarrow$ `AAA Metro Web Scraper` $\rightarrow$ `EIA Weekly Regional Retail` $\rightarrow$ `Last Known prediction_history.csv Price`.

### 3. Public Web Dashboard & MLOps Integration
- Pass live queried base prices into `src/dashboard_generator.py` so landing page cards (`docs/index.html`), navbar headers, and regional pages reflect real-time live pump prices.
- Persist live ingested base prices into `data/prediction_history.csv` via `src/prediction_logger.py`.

---

## Tasks & Checklist

- [ ] Refactor `src/live_fuel_feed.py` to support multi-locale live price fetching.
- [ ] Wire dynamic fetching into `src/tulsa_regional.py`, `src/newark_regional.py`, `src/cincinnati_regional.py`, and `src/oakland_regional.py`.
- [ ] Add unit tests in `tests/test_live_fuel_feed.py` verifying API response handling and fallback mechanisms.
- [ ] Verify execution in `.github/workflows/gas_price_forecast.yml` daily cloud runner.
