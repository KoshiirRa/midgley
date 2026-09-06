# Release Notes - v0.4.8

**Release Date:** September 5, 2026  
**Build Target:** `dev-vm` (`10.42.42.54`)  
**Git Branch:** `main`  

---

## 🚀 Key Features & Architectural Enhancements

### 1. Bitemporal Vintage Tracking (`as_of`) for EIA Data Ingestion (Issue #121)
- **Bitemporal EIA Data Architecture (`src/data_ingestion.py` & `src/alternative_data_feeds.py`):** Extended `EIADataConnector` and `EIAStateMetroRetailConnector` methods (`fetch_padd_inventory_and_refinery_data`, `fetch_state_retail_price`, `fetch_metro_retail_price`) to attach explicit publication release timestamps (`as_of`), observation period dates (`valid_date`), and honesty flags (`is_vintage_reconstructed: False` for live queries, `True` for historical backfills).
- **Persistent Vintage Storage (`data/eia_vintages.json`):** Implemented `save_eia_vintage_record()` and `get_eia_vintages_as_of()` static helpers on `EIADataConnector` to save live observation snapshots and enable point-in-time point queries.
- **Point-in-Time Feature Engineering (`src/feature_engineering.py`):** Updated `create_feature_matrix()` to accept an `as_of_cutoff` parameter (`as_of <= target_run_date`), ensuring zero lookahead leakage from restated EIA figures during model retraining and historical backtests.
- **Unit Test Suite (`tests/test_eia_bitemporal_vintages.py`):** Added comprehensive unit test suite covering bitemporal metadata fields, JSON vintage persistence, point-in-time lookup queries, and cutoff feature matrix generation (4/4 passed clean on `dev-vm`).

---

## 🧪 Verification & Test Suite Results

- **Bitemporal EIA Unit Test Suite (`pytest tests/test_eia_bitemporal_vintages.py`):**
  ```bash
  pytest tests/test_eia_bitemporal_vintages.py -v
  ```
  **Result:** `4 passed` (100% pass rate on `dev-vm`).
- **Full System Test Suite Execution (`pytest`):**
  **Result:** `334 passed` (100% pass rate across all 334 test cases).

---

## 📋 Closed GitHub Issues
- **Issue #121**: `[Feature Request] Implement Bitemporal Vintage Tracking (as_of) for EIA Data Ingestion` (Closed as completed)
