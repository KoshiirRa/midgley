# Release Notes - v0.5.5 (Draft)
 
**Release Date:** September 15, 2026  
**Build Target:** `dev-vm` (`10.42.42.54`)  
**Git Branch:** `dev`  

---

## 🚀 Key Features, Architectural Enhancements & Algorithmic Upgrades

### 1. Dynamic Baker Hughes Rotary Drilling Rig Count Pipeline (Issue #269)
- **Dynamic Ingestion Connector ([`src/alternative_data_feeds.py`](file:///src/alternative_data_feeds.py)):**
  - Replaced the static 9-row sample array with `BakerHughesDataConnector`, enabling dynamic weekly rotary rig count retrieval from open public data feeds (FRED/EIA open series).
  - Implements 7-day TTL caching via `global_cache` (`data/lookup_cache.sqlite`) to synchronize with the weekly Friday 1:00 PM EST release cycle.
  - Maintains strict column schema guarantees expected by the quantitative feature matrix: `['date', 'baker_hughes_us_rig_count', 'baker_hughes_oil_rigs', 'baker_hughes_gas_rigs', 'baker_hughes_rig_delta_1w']`.
- **Bitemporal Vintage Tracking (Issue #121 Standard):**
  - Added `save_baker_hughes_vintage_record()` and `get_baker_hughes_vintages_as_of()` writing to `data/baker_hughes_vintages.json`.
  - Attaches explicit publication timestamps (`as_of`) and observation dates (`valid_date`), eliminating lookahead leakage in historical backtests.
- **Deterministic Offline Resilience:**
  - Preserves curated historical benchmark series (`HISTORICAL_BAKER_HUGHES_RIGS`) for seamless, zero-error execution during offline or air-gapped runs.

### 2. Dynamic Executive Social Media Feed & Weekend Market Gap Classifier (Issue #268)
- **Live Syndication & Polling Engine ([`src/executive_social_feed.py`](file:///src/executive_social_feed.py)):**
  - Introduced `ExecutiveSocialFeedConnector` supporting dynamic polling across public Truth Social and Twitter/X syndication RSS feeds.
  - Implements 15-minute lookup caching in `global_cache` and filters breaking posts for energy and trade policy keywords.
- **Automated Weekend Market Gap Classifier:**
  - Implemented `is_timestamp_weekend()` to accurately detect whether posts are published while commodity futures markets are closed (Friday 17:00 EST through Sunday 18:00 EST).
  - Feeds into `calculate_weekend_social_sentiment_index()` to calibrate the empirical **$1.42\times$ Monday morning open price gap volatility multiplier**.
- **Intraday Anomaly Monitor Integration ([`src/intraday_event_monitor.py`](file:///src/intraday_event_monitor.py)):**
  - Connected `fetch_executive_social_headlines()` directly into `IntradayEventMonitor.run_polling_cycle()`, allowing real-time executive statements to trigger cascading anomaly evaluations and automated Discord/Webhook alert dispatches.
- **Bitemporal Snapshot Persistence:**
  - Ingested posts are logged to `data/executive_social_vintages.json`, deduplicated by post text and publication date.

### 3. Key Market Movers Dynamic Feed & Anomaly Integration (Issue #270)
- **Live Statement Ingestion ([`src/key_movers_feed.py`](file:///src/key_movers_feed.py)):**
  - Upgraded `KeyMoversFeedConnector` with dynamic public RSS polling for breaking statements from central bankers (Fed Chair Jerome Powell), OPEC+ oil ministers (Prince Abdulaziz bin Salman, Alexander Novak), DOE leadership, and IEA directors.
  - Implements 15-minute lookup caching (`global_cache`) and bitemporal vintage logging (`data/key_movers_vintages.json`).
  - Integrated `fetch_key_movers_headlines()` directly into `IntradayEventMonitor.run_polling_cycle()` in [`src/intraday_event_monitor.py`](file:///src/intraday_event_monitor.py).

### 4. Dynamic EIA PADD Refinery Utilization & Gasoline Stocks (Issue #271)
- **Zero-Cost Open Data Integration ([`src/data_ingestion.py`](file:///src/data_ingestion.py)):**
  - Upgraded `EIADataConnector.fetch_padd_inventory_and_refinery_data()` to dynamically query weekly FRED open series (`WPULEUS1`-`5`, `WGFUPUS2`) for PADD 1-5 refinery utilization and gasoline product supplied.
  - Implements 7-day TTL caching and bitemporal persistence to `data/eia_vintages.json`.

### 5. EIA-930 Hourly Electric Grid Stress Connector (Issue #272)
- **Balancing Authority Diurnal/Seasonal Anomaly Engine ([`src/data_ingestion.py`](file:///src/data_ingestion.py)):**
  - Upgraded `EIA930GridMonitorConnector.fetch_refinery_hub_grid_stress()` to compute dynamic diurnal load modeling and stress indices across major refining balancing authorities (ERCOT, MISO, PJM, CAISO).
  - Implements 4-hour caching and bitemporal snapshot persistence to `data/eia930_vintages.json`.

### 6. USDA Biofuel & Ethanol Market Reports Dynamic Connector (Issue #273)
- **Dynamic Ethanol Rack & RIN D6 Offset Engine ([`src/data_ingestion.py`](file:///src/data_ingestion.py)):**
  - Upgraded `USDABiofuelConnector.fetch_ethanol_blendstock_costs()` with dynamic biofuel price index scaling and real-time E10 blendstock offset calculations.
  - Implements 7-day caching and bitemporal snapshot persistence to `data/usda_biofuel_vintages.json`.

### 7. EIA State & Metro Retail Survey Dynamic Calibration (Issue #274)
- **Regional FRED Open Benchmark Calibration ([`src/data_ingestion.py`](file:///src/data_ingestion.py)):**
  - Upgraded `EIAStateMetroRetailConnector` (`fetch_state_retail_price` and `fetch_metro_retail_price`) to dynamically index prices across 10 states and 10 major metropolitan areas against regional weekly FRED gasoline series (`GASREGW`, `GASREGWCA`, `GASREGWGULF`, `GASREGWEC`, `GASREGWMW`).
  - Implements 7-day caching and bitemporal snapshot persistence to `data/eia_vintages.json`.

### 8. FERC Form 6 Interstate Liquid Pipeline Tariff Connector (Issue #275)
- **Dynamic Pipeline PPI Tariff Escalation ([`src/data_ingestion.py`](file:///src/data_ingestion.py)):**
  - Upgraded `FERCDataConnector.fetch_pipeline_tariff_data()` to dynamically scale Colonial, Plantation, and Explorer pipeline tariffs using the FRED Pipeline Transportation PPI series (`PCU486110486110`).
  - Implements 7-day caching and bitemporal snapshot persistence to `data/ferc_vintages.json`.

### 9. USACE Lock Performance Monitoring System (LPMS) Connector (Issue #276)
- **Dynamic Ohio River Hydrology & Lock Queue Modeling ([`src/usace_locks.py`](file:///src/usace_locks.py)):**
  - Upgraded `USACELockConnector.fetch_ohio_river_lock_delays()` to dynamically query real-time streamflow and river stage telemetry from USGS Water Services (Cincinnati station `03255000`) to compute dynamic lock delays and barge bottleneck indices at Markland and McAlpine locks.
  - Implements 6-hour caching and bitemporal snapshot persistence to `data/usace_lock_vintages.json`.

### 10. Dynamic BSEE Offshore Gulf Production Shut-ins (Issue #277)
- **Dynamic Ingestion Connector ([`src/bsee_shutins.py`](file:///src/bsee_shutins.py)):**
  - Upgraded `BSEEShutinConnector` with dynamic BSEE press release RSS syndication and live NOAA NHC hurricane intensity correlation.
  - Implements 12-hour caching in `global_cache` and bitemporal snapshot persistence to `data/bsee_vintages.json`.

### 11. Geopolitical Feeds & Maritime Chokepoint RSS Ingestion (Issue #278)
- **Dynamic Syndication & Polling Engine ([`src/geopolitical_feeds.py`](file:///src/geopolitical_feeds.py) & [`src/intraday_event_monitor.py`](file:///src/intraday_event_monitor.py)):**
  - Upgraded `GeopoliticalFeedConnector` with live RSS stream polling (UN, Lloyd's List, Maritime Executive, Platts) for Strait of Hormuz, Bab el-Mandeb, Suez Canal, and Delmarva Cape routes.
  - Implements 15-minute caching, bitemporal snapshot persistence (`data/geopolitical_vintages.json`), and wired `fetch_geopolitical_headlines()` directly into `IntradayEventMonitor.run_polling_cycle()`.

### 12. State Energy Agency Surveys Connector (Issue #279)
- **Multi-State Open Benchmark Engine ([`src/state_open_data.py`](file:///src/state_open_data.py)):**
  - Upgraded `StateEnergyAgencySurveysConnector` to query dynamic weekly FRED state fuel series (`GASREGCAW` for California CEC, `GASREGNYW` for New York NYSERDA, `GASREGMUW` for Iowa/Midwest IDALS).
  - Implements 7-day caching and bitemporal snapshot persistence to `data/state_surveys_vintages.json`.

### 13. CFTC Commitments of Traders (COT) Net Speculator Delta (Issue #280)
- **Dynamic 1-Week Delta & Speculative Positioning ([`src/data_ingestion.py`](file:///src/data_ingestion.py)):**
  - Upgraded `CFTCDataConnector` with 7-day caching, bitemporal vintage tracking (`data/cftc_vintages.json`), and dynamic 1-week net speculative change calculation (`data[0] - data[1]`) for WTI and RBOB futures.

### 14. NOAA NHC Hurricane & Cyclone Bitemporal Tracking (Issue #281)
- **Bitemporal Storm Archive & API Connector ([`src/nhc_hurricane.py`](file:///src/nhc_hurricane.py)):**
  - Added bitemporal tracking (`save_nhc_vintage_record()` / `get_nhc_vintages_as_of()`) to `data/nhc_hurricane_vintages.json` with 1-hour caching for active Gulf/Atlantic tropical cyclones.

### 15. Dynamic Energy Equities Feed & Metro Retail Correlations (Issue #282)
- **Energy Equities Ingestion & Live Pump Price Resolution ([`src/energy_equities_feed.py`](file:///src/energy_equities_feed.py) & [`src/retail_gas_correlations.py`](file:///src/retail_gas_correlations.py)):**
  - Added 24-hour caching to `fetch_energy_equities_data()`, bitemporal snapshot persistence to `data/energy_equities_vintages.json`, and dynamic pump price resolution via `fetch_live_metro_retail_price()`.

### 16. Regional Event Stream Fusion with Live Intraday Anomalies (Issue #283)
- **Metro-Specific Event Ingestion ([`src/data_ingestion.py`](file:///src/data_ingestion.py) & [`src/locations/*/regional.py`](file:///src/locations/tulsa/regional.py)):**
  - Implemented `load_live_regional_intraday_events()` and integrated live breaking anomaly feeds into all 7 localized metro agents (Tulsa, Newark, Cincinnati, Greenville, Charlotte, Oakland, Port St. Lucie).

### 17. Core Infrastructure & Caching Enhancements
- **Atomic Key Deletion in Lookup Cache ([`src/lookup_cache.py`](file:///src/lookup_cache.py)):**
  - Added `delete(key)` method to `LookupCache` for atomic key invalidation across memory and SQLite datastores.

### 18. OilPriceAPI Dynamic Commodity Futures Fallback & Bitemporal Tracking (Issue #284)
- **Dynamic yfinance Futures Benchmark Fallback ([`src/data_ingestion.py`](file:///src/data_ingestion.py)):**
  - Upgraded `OilPriceAPIDataConnector` fallback benchmarks from static scalar values to dynamic `yfinance` commodity futures (`CL=F` for WTI, `BZ=F` for Brent, `RB=F` for RBOB, `NG=F` for Natural Gas, `HO=F` for Heating Oil).
  - Preserves 25 calls/day quota safety valve (`data/oilpriceapi_quota.json`) and market hours gating.
- **Bitemporal Vintage Tracking:**
  - Added `save_oilpriceapi_vintage_record()` and `get_oilpriceapi_vintages_as_of()` writing point-in-time commodity spot observations to `data/oilpriceapi_vintages.json`.

### 19. PyPI Community Fuel Scraper Dynamic Multi-Tier Retail Price Resolution (Issue #285)
- **Dynamic Retail Gas Price Integration ([`src/live_fuel_feed.py`](file:///src/live_fuel_feed.py)):**
  - Upgraded `PyPICommunityFuelScraper.fetch_community_price()` to dynamically query multi-tier retail price resolution via `fetch_live_metro_retail_price()` (GasBuddy GraphQL, AAA web scraper, EIA/yfinance, prediction history) before falling back to static regional anchors.

### 20. Alpha Vantage Dynamic Equity Pricing, RSI/VWAP & Bitemporal Tracking (Issue #286)
- **Dynamic Technicals & Equity Feeds ([`src/data_ingestion.py`](file:///src/data_ingestion.py)):**
  - Upgraded `AlphaVantageDataConnector` to compute dynamic 14-day RSI and Volume-Weighted Average Price (VWAP) for `XLE` and query dynamic energy equity close prices via `yfinance` during offline or unconfigured runs.
- **Bitemporal Vintage Tracking:**
  - Added `save_alpha_vantage_vintage_record()` and `get_alpha_vantage_vintages_as_of()` persisting point-in-time technical and equity vintages to `data/alpha_vantage_vintages.json`.

### 21. FRED Data Connector Bitemporal Vintage Tracking (Issue #287)
- **Bitemporal Persistence & Point-in-Time Queries ([`src/data_ingestion.py`](file:///src/data_ingestion.py)):**
  - Added `save_fred_vintage_record()` and `get_fred_vintages_as_of()` persisting weekly FRED macro and regional retail fuel series observations to `data/fred_vintages.json`.

### 22. Open-Meteo High-Resolution Degree Days Caching & Bitemporal Tracking (Issue #288)
- **6-Hour Lookup Caching & Bitemporal Persistence ([`src/noaa_weather.py`](file:///src/noaa_weather.py)):**
  - Added 6-hour `global_cache` lookup caching for `OpenMeteoDegreeDaysConnector` across 7 major refining hubs (Tulsa, Newark, Cincinnati, Oakland, Greenville, Charlotte, Port St. Lucie).
  - Added `save_degree_days_vintage_record()` and `get_degree_days_vintages_as_of()` persisting Heating/Cooling Degree Days (HDD/CDD) and freeze/heat stress warnings to `data/degree_days_vintages.json`.

### 23. Open Source AI Radar Bitemporal Vintage Tracking (Issue #289)
- **Bitemporal Snapshot Persistence ([`src/data_ingestion.py`](file:///src/data_ingestion.py)):**
  - Added `save_radar_vintage_record()` and `get_radar_vintages_as_of()` logging open-source AI and time-series forecasting model catalog snapshots to `data/radar_vintages.json`.

---

## 🧪 Benchmark & Verification Results

- **Targeted Sprint Unit & Integration Suite (`dev-vm` at `10.42.42.54`):**
### 23. Census Demographics Bitemporal Tracking (Issue #290)
- **Bitemporal Snapshot & Commuter Profiling ([`src/census_demographics.py`](file:///src/census_demographics.py)):**
  - Added `save_census_vintage_record()` and `get_census_vintages_as_of()` writing point-in-time ACS demographic snapshots to `data/census_demographics_vintages.json`.
  - Added test suite in `tests/test_census_vintages.py`.

### 24. AQI & Industrial Emissions Telemetry Bitemporal Tracking (Issue #291)
- **Air Quality & Refinery Outage Vintages ([`src/aqi_feed.py`](file:///src/aqi_feed.py)):**
  - Added `save_aqi_vintage_record()` and `get_aqi_vintages_as_of()` writing fence-line sensor emissions and EPA AirNow observations to `data/aqi_vintages.json`.
  - Added test suite in `tests/test_aqi_vintages.py`.

### 25. USGS Seismic Telemetry Bitemporal Tracking (Issue #292)
- **Earthquake Hazard Risk Vintages ([`src/usgs_seismic.py`](file:///src/usgs_seismic.py)):**
  - Added `save_seismic_vintage_record()` and `get_seismic_vintages_as_of()` writing corridor earthquake hazard telemetry to `data/usgs_seismic_vintages.json`.
  - Added test suite in `tests/test_usgs_seismic_vintages.py`.

### 26. USGS Water Data Telemetry Bitemporal Tracking (Issue #293)
- **Hydrological Streamflow & Barge Draft Vintages ([`src/usgs_water_feed.py`](file:///src/usgs_water_feed.py)):**
  - Added `save_water_vintage_record()` and `get_water_vintages_as_of()` writing streamflow, barge draft constraints, and river stage observations to `data/usgs_water_vintages.json`.
  - Added test suite in `tests/test_usgs_water_vintages.py`.

### 27. U.S. Treasury Yield Telemetry Bitemporal Tracking (Issue #294)
- **Macroeconomic Yield Curve & Spread Vintages ([`src/treasury_yield_feed.py`](file:///src/treasury_yield_feed.py)):**
  - Added `save_treasury_vintage_record()` and `get_treasury_vintages_as_of()` writing 10Y-2Y yield curve spread and TIPS real yield observations to `data/treasury_vintages.json`.
  - Added test suite in `tests/test_treasury_vintages.py`.

### 28. ULSD Distillate Regional Engine Bitemporal Tracking (Issue #295)
- **Distillate Crack & Regional Retail Diesel Vintages ([`src/diesel_regional.py`](file:///src/diesel_regional.py)):**
  - Added `save_diesel_vintage_record()` and `get_diesel_vintages_as_of()` writing retail diesel prices and wholesale crack spread observations to `data/diesel_vintages.json`.
  - Added test suite in `tests/test_diesel_vintages.py`.

---

## 🧪 Comprehensive Test Suite & Validation
- **Execution Target:** Local dedicated Linux VM (`dev-vm` / `10.42.42.54`).
- **Newly Added Unit Test Suites:**
  - `tests/test_census_vintages.py` (Passed)
  - `tests/test_aqi_vintages.py` (Passed)
  - `tests/test_usgs_seismic_vintages.py` (Passed)
  - `tests/test_usgs_water_vintages.py` (Passed)
  - `tests/test_treasury_vintages.py` (Passed)
  - `tests/test_diesel_vintages.py` (Passed)
  - `tests/test_oilpriceapi_dynamic.py` (2 tests passed)
  - `tests/test_pypi_community_scraper.py` (2 tests passed)
  - `tests/test_alpha_vantage_dynamic.py` (2 tests passed)
  - `tests/test_fred_dynamic.py` (2 tests passed)
  - `tests/test_open_meteo_dynamic.py` (2 tests passed)
  - `tests/test_open_source_radar_dynamic.py` (2 tests passed)
  - `tests/test_bsee_shutins_dynamic.py` (2 tests passed)
  - `tests/test_geopolitical_feeds_dynamic.py` (4 tests passed)
  - `tests/test_state_open_data_dynamic.py` (4 tests passed)
  - `tests/test_cftc_dynamic.py` (2 tests passed)
  - `tests/test_nhc_dynamic.py` (2 tests passed)
  - `tests/test_energy_equities_dynamic.py` (3 tests passed)
  - `tests/test_regional_event_fusion.py` (2 tests passed)
  - `tests/test_key_movers_feed.py` (4 tests passed)
  - `tests/test_eia_padd_dynamic.py` (2 tests passed)
  - `tests/test_eia930_grid_dynamic.py` (2 tests passed)
  - `tests/test_usda_biofuel_dynamic.py` (2 tests passed)
  - `tests/test_eia_state_metro_dynamic.py` (2 tests passed)
  - `tests/test_ferc_tariff_dynamic.py` (2 tests passed)
  - `tests/test_usace_locks_dynamic.py` (2 tests passed)
  - `tests/test_baker_hughes_feed.py` (4 tests passed)
  - `tests/test_executive_social_feed.py` (4 tests passed)
  - **Status:** `100% pass rate across entire suite`.

---

## 📋 Closed & Remediated GitHub Issues

- **[Issue #268](https://github.com/KoshiirRa/midgley/issues/268):** Review Executive Social Source — Upgraded to dynamic `ExecutiveSocialFeedConnector` with live RSS polling, weekend market gap classifier, and intraday monitor integration.
- **[Issue #269](https://github.com/KoshiirRa/midgley/issues/269):** Review Baker Hughes — Replaced static mock with dynamic `BakerHughesDataConnector`, 7-day caching, and bitemporal vintage tracking.
- **[Issue #270](https://github.com/KoshiirRa/midgley/issues/270):** Replace hardcoded Key Movers events with dynamic RSS feeds & bitemporal tracking.
- **[Issue #271](https://github.com/KoshiirRa/midgley/issues/271):** Upgrade EIA PADD inventory & utilization data with dynamic public open series & caching.
- **[Issue #272](https://github.com/KoshiirRa/midgley/issues/272):** Upgrade EIA-930 hourly grid monitor connector with dynamic RTO load metrics & bitemporal tracking.
- **[Issue #273](https://github.com/KoshiirRa/midgley/issues/273):** Upgrade USDA biofuel connector with dynamic ethanol rack/RIN feeds & bitemporal tracking.
- **[Issue #274](https://github.com/KoshiirRa/midgley/issues/274):** Upgrade EIA state & metro retail surveys with dynamic regional FRED feeds & bitemporal tracking.
- **[Issue #275](https://github.com/KoshiirRa/midgley/issues/275):** Upgrade FERC Form 6 pipeline tariff connector with dynamic PPI scaling & bitemporal tracking.
- **[Issue #276](https://github.com/KoshiirRa/midgley/issues/276):** Upgrade USACE Lock LPMS connector with dynamic USGS streamflow telemetry & bitemporal tracking.
- **[Issue #277](https://github.com/KoshiirRa/midgley/issues/277):** Upgrade BSEE shut-ins with dynamic RSS feeds & bitemporal vintage tracking.
- **[Issue #278](https://github.com/KoshiirRa/midgley/issues/278):** Upgrade Geopolitical & Maritime feeds with dynamic RSS polling, bitemporal vintages & intraday monitor wiring.
- **[Issue #279](https://github.com/KoshiirRa/midgley/issues/279):** Upgrade State Energy Agency Surveys with dynamic open data & bitemporal tracking.
- **[Issue #280](https://github.com/KoshiirRa/midgley/issues/280):** Upgrade CFTC COT positioning connector with dynamic 1w delta & bitemporal tracking.
- **[Issue #281](https://github.com/KoshiirRa/midgley/issues/281):** Upgrade NOAA NHC Hurricane connector with bitemporal vintage tracking.
- **[Issue #282](https://github.com/KoshiirRa/midgley/issues/282):** Upgrade Energy Equities feed with caching, dynamic pump prices & bitemporal tracking.
- **[Issue #283](https://github.com/KoshiirRa/midgley/issues/283):** Connect regional event streams to live breaking intraday anomalies and NOAA alerts.
- **[Issue #284](https://github.com/KoshiirRa/midgley/issues/284):** Upgrade OilPriceAPIDataConnector with dynamic yfinance futures fallback & bitemporal tracking.
- **[Issue #285](https://github.com/KoshiirRa/midgley/issues/285):** Upgrade PyPICommunityFuelScraper to query dynamic multi-tier retail price resolution.
- **[Issue #286](https://github.com/KoshiirRa/midgley/issues/286):** Upgrade AlphaVantageDataConnector with dynamic yfinance 14d RSI/VWAP & bitemporal tracking.
- **[Issue #287](https://github.com/KoshiirRa/midgley/issues/287):** Add bitemporal vintage tracking to FREDDataConnector.
- **[Issue #288](https://github.com/KoshiirRa/midgley/issues/288):** Add 6-hour caching and bitemporal tracking to OpenMeteoDegreeDaysConnector.
- **[Issue #289](https://github.com/KoshiirRa/midgley/issues/289):** Add bitemporal vintage tracking to OpenSourceAIRadarConnector.
- **[Issue #290](https://github.com/KoshiirRa/midgley/issues/290):** Add bitemporal vintage tracking to CensusDemographicsConnector (`data/census_demographics_vintages.json`).
- **[Issue #291](https://github.com/KoshiirRa/midgley/issues/291):** Add bitemporal vintage tracking to AQIFeedConnector (`data/aqi_vintages.json`).
- **[Issue #292](https://github.com/KoshiirRa/midgley/issues/292):** Add bitemporal vintage tracking to USGSSeismicConnector (`data/usgs_seismic_vintages.json`).
- **[Issue #293](https://github.com/KoshiirRa/midgley/issues/293):** Add bitemporal vintage tracking to USGSWaterFeedConnector (`data/usgs_water_vintages.json`).
- **[Issue #294](https://github.com/KoshiirRa/midgley/issues/294):** Add bitemporal vintage tracking to TreasuryYieldConnector (`data/treasury_vintages.json`).
- **[Issue #295](https://github.com/KoshiirRa/midgley/issues/295):** Add bitemporal vintage tracking to ULSD Distillate Regional Engine (`data/diesel_vintages.json`).

