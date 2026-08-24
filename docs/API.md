# Developer API Documentation (docs/API.md)

Complete module and function reference for the `midgley` LLM Gas Price Forecasting framework.

---

## 1. NOAA Weather Integration (`src.noaa_weather`)

### `fetch_live_noaa_alerts(zones: list = None) -> list`
Fetches active severe weather alerts from NOAA NWS API (`api.weather.gov`) for specified state/zone codes (default: `['OK', 'TX', 'LA']`).

### `get_national_production_weather_dataset() -> pd.DataFrame`
Returns historical NOAA weather advisories for major US refining/production basins (Gulf Coast Hurricanes, Permian & Bakken Freezes).

### `get_cincinnati_weather_dataset() -> pd.DataFrame`
Returns localized NOAA weather advisories for Cincinnati / Hamilton County (`OHZ077`) and Northern KY (`KYZ091`).

### `get_oakland_weather_dataset() -> pd.DataFrame`
Returns localized NOAA weather, environmental & seismic advisories for Alameda (`CAZ508`), Contra Costa (`CAZ511`), San Francisco (`CAZ006`), and Santa Clara (`CAZ513`).

---

## 2. Oakland & SF Bay Area Regional Forecasting (`src.oakland_regional`)

### `fetch_oakland_market_data(start_date: str = "2022-01-01", end_date: str = None, live_oakland_price: float = 4.950, live_bayarea_price: float = 5.050) -> pd.DataFrame`
Fetches market data tailored to Oakland ($RB=F$, $CL=F$, $BZ=F$), dynamically calibrates retail series to Oakland ($4.950 base) and SF Bay Area ($5.050 base), and computes Richmond crack spread and CARB regulatory tax burden ($0.953/gal).

### `get_oakland_regional_events() -> pd.DataFrame`
Returns merged dataset of PADD 5 Chevron Richmond refinery events, CARB CaRFG transition shocks, Kinder Morgan SFPP pipeline events, USGS Hayward fault quakes, CAL FIRE / PG&E PSPS power shutoffs, PTWC tsunami alerts, and localized NOAA weather advisories.

---

## 3. Tulsa Regional Forecasting (`src.tulsa_regional`)

### `fetch_tulsa_market_data(start_date: str = "2022-01-01", end_date: str = None, live_current_price: float = 3.89) -> pd.DataFrame`
Fetches market data tailored to Tulsa, OK ($RB=F$, Cushing $CL=F$, $BZ=F$) and dynamically calibrates the retail series to match live pump prices (`live_current_price = 3.89`).

### `get_tulsa_regional_events() -> pd.DataFrame`
Returns merged dataset of Tulsa refinery events and localized NOAA weather alerts.

---

## 3. MLOps Prediction Logging (`src.prediction_logger`)

### `log_predictions(predictions_df: pd.DataFrame, region: str = "Tulsa_OK", model_version: str = "v1.2-NOAA-Ridge") -> int`
Appends new 5-day out-of-time model predictions to `data/prediction_history.csv`.

### `backfill_actual_prices_and_evaluate() -> pd.DataFrame`
Queries actual historical market prices from `yfinance` up to today, matches target dates, and populates ground-truth price records in `prediction_history.csv`.

---

## 4. Weekly Performance Review & Feedback Loop Runner (`.github/workflows/weekly_model_review.yml`)

### `generate_performance_report() -> pd.DataFrame`
Generates an empirical summary report table aggregating MAE, RMSE, and Directional Hit Rate by Region and Model Version. Used by the Saturday automated runner (`.github/workflows/weekly_model_review.yml`) to feed performance validation signals back into model re-calibration and feature weight optimization.

---

## 5. Live Fuel Feeds (`src.live_fuel_feed`)

### `fetch_gasbuddy_tulsa_prices(zip_code: str = "74103") -> dict`
Queries GasBuddy GraphQL API for real-time station prices in Tulsa, OK.

---

## 6. Dashboard & Multi-Locale Web Generator (`src.dashboard_generator`)

### `generate_public_dashboard()`
Generates all public HTML web app pages into `docs/`: `index.html` (overview), `national.html` & `national/index.html` (`/national`), `tulsa.html` & `tulsa/index.html` (`/tulsa`), and `math.html` (`/math`).

### `get_nav_header(active_tab: str, rel_prefix: str = "") -> str`
Returns standard sticky HTML navigation header with active tab highlighting and the **`Metro Areas`** dropdown menu.

### `calculate_rolling_metrics() -> tuple`
Reads `data/prediction_history.csv` and returns arrays `(dates, rolling_mae, rolling_hit)` tracking rolling MAE and directional accuracy improvement over time.

### `fetch_google_maps_fuel_prices(place_id: str = None, api_key: str = None) -> dict`
Queries Google Places API (New) for station `fuelOptions` details (`REGULAR`, `MIDGRADE`, `PREMIUM`, `DIESEL`). Requires `GOOGLE_MAPS_API_KEY`.
