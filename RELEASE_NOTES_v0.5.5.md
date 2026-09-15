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

### 3. Core Infrastructure & Caching Enhancements
- **Atomic Key Deletion in Lookup Cache ([`src/lookup_cache.py`](file:///src/lookup_cache.py)):**
  - Added `delete(key)` method to `LookupCache` for atomic key invalidation across memory and SQLite datastores.

---

## 🧪 Benchmark & Verification Results

- **Targeted Unit & Integration Suite (`dev-vm` at `10.42.42.54`):**
  - `tests/test_baker_hughes_feed.py` (4 tests passed: fallback integrity, column schema validation, bitemporal persistence, cache hit/miss).
  - `tests/test_executive_social_feed.py` (4 tests passed: weekend gap time window boundaries, benchmark preservation, sentiment index calculation, live parsing & bitemporal storage).
  - **Status:** `8 passed in 5.72s (100% pass rate)`.
- **Full Regression Suite:**
  - Evaluated 43 targeted tests across feature engineering, intraday event monitor, live fuel feeds, and data source caching.
  - **Status:** `43 passed, 464 deselected in 59.95s (100% pass rate)`.

---

## 📋 Closed & Remediated GitHub Issues

- **[Issue #269](https://github.com/KoshiirRa/midgley/issues/269):** Review Baker Hughes — Replaced static mock with dynamic `BakerHughesDataConnector`, 7-day caching, and bitemporal vintage tracking.
- **[Issue #268](https://github.com/KoshiirRa/midgley/issues/268):** Review Executive Social Source — Upgraded to dynamic `ExecutiveSocialFeedConnector` with live RSS polling, weekend market gap classifier, and intraday monitor integration.
