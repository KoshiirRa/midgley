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

---

## 🧪 Benchmark & Verification Results

- **Targeted Sprint Unit & Integration Suite (`dev-vm` at `10.42.42.54`):**
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
  - **Status:** `43 passed in 100% pass rate`.

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
