# Developer API Documentation (docs/API.md)

Complete module and function reference for the `midgley` LLM Gas Price Forecasting framework.

---

## 1. NOAA Weather Integration (`src.noaa_weather`)

### `fetch_live_noaa_alerts(zones: list = None) -> list`
Fetches active severe weather alerts from NOAA NWS API (`api.weather.gov`) for specified state/zone codes (default: `['OK', 'TX', 'LA']`).

### `get_national_production_weather_dataset() -> pd.DataFrame`
Returns historical NOAA weather advisories for major US refining/production basins (Gulf Coast Hurricanes, Permian & Bakken Freezes).

### `get_tulsa_cushing_weather_dataset() -> pd.DataFrame`
Returns localized NOAA weather advisories for Tulsa County (`OKZ060`) and Cushing/Payne County (`OKZ066`).

---

## 2. Tulsa Regional Forecasting (`src.tulsa_regional`)

### `fetch_tulsa_market_data(start_date: str = "2022-01-01", end_date: str = None, live_current_price: float = 3.89) -> pd.DataFrame`
Fetches market data tailored to Tulsa, OK ($RB=F$, Cushing $CL=F$, $BZ=F$) and dynamically calibrates the retail series to match live pump prices (`live_current_price = 3.89`).

### `get_tulsa_regional_events() -> pd.DataFrame`
Returns merged dataset of Tulsa refinery events and localized NOAA weather alerts.

---

## 3. MLOps Prediction Logging (`src.prediction_logger`)

### `log_predictions(predictions_df: pd.DataFrame, region: str = "Tulsa_OK", model_version: str = "v1.2-NOAA-Ridge") -> int`
Appends new model predictions to `data/prediction_history.csv`.

### `backfill_actual_prices_and_evaluate() -> pd.DataFrame`
Queries actual historical market prices from `yfinance` up to today, matches target dates, and populates actual prices, errors, and directional hit outcomes.

### `generate_performance_report() -> pd.DataFrame`
Generates a summary report table aggregating MAE, RMSE, and Directional Hit Rate by Region and Model Version.

---

## 5. Dashboard & Multi-Locale Web Generator (`src.dashboard_generator`)

### `generate_public_dashboard()`
Generates all public HTML web app pages into `docs/`: `index.html` (overview), `national.html` & `national/index.html` (`/national`), `tulsa.html` & `tulsa/index.html` (`/tulsa`), and `math.html` (`/math`).

### `get_nav_header(active_tab: str, rel_prefix: str = "") -> str`
Returns standard sticky HTML navigation header with active tab highlighting and the **`Metro Areas`** dropdown menu.

### `calculate_rolling_metrics() -> tuple`
Reads `data/prediction_history.csv` and returns arrays `(dates, rolling_mae, rolling_hit)` tracking rolling MAE and directional accuracy improvement over time.


---

## 4. Live Fuel Feeds (`src.live_fuel_feed`)

### `fetch_gasbuddy_tulsa_prices(zip_code: str = "74103") -> dict`
Queries GasBuddy GraphQL API for real-time station prices in Tulsa, OK.

### `fetch_google_maps_fuel_prices(place_id: str = None, api_key: str = None) -> dict`
Queries Google Places API (New) for station `fuelOptions` details (`REGULAR`, `MIDGRADE`, `PREMIUM`, `DIESEL`). Requires `GOOGLE_MAPS_API_KEY`.
