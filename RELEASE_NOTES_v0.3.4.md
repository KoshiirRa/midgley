## 🚀 Midgley Release v0.3.4 Notes

Release **v0.3.4** introduces Ultra-Low Sulfur Diesel (ULSD) distillate modeling, Marcos López de Prado Purged & Combinatorial Cross-Validation, Port St. Lucie metro area forecasting, real-time prediction history logging with actual pump price backfilling, multi-tier cache provenance chains, zero-cost research connectors (NHC Cyclones, BSEE Shut-Ins, EIA-930 Grid Stress, EIA Petroleum Balance, USACE Ohio River Lock Delays), and OilPrice API free tier quota reconciliation.

### 🌟 Key Highlights & Major Features

1. **Ultra-Low Sulfur Diesel (ULSD) & Distillate Crack Spread Engine (`src/diesel.py`, Issue #41)**:
   - Expands Midgley beyond unleaded gasoline into Ultra-Low Sulfur Diesel (`HO=F` futures & 3-2-1 distillate margin feature vectors).
   - Dedicated public web dashboard page (`docs/diesel.html`) and multi-week empirical observation tracking.

2. **Purged & Combinatorial Cross-Validation Engine (`src/models.py`, Issue #117)**:
   - Implements Marcos López de Prado's Purged Group Time Series Split (`PurgedGroupTimeSeriesSplit`) and Combinatorial Purged CV (`CombinatorialPurgedCV`) to eliminate lookahead data leakage in 5-day step-ahead forecasts.
   - REST API endpoint (`GET /api/v1/forecast/purged-cv`) and GitHub Wiki documentation (`Section 9.2`).

3. **MLOps Extended Prediction History & Observability Engine (`src/prediction_logger.py`, Issue #124)**:
   - Extended schema logging out-of-time forecasts and automated backfilling of realized actual pump prices (`prediction_history.csv`).

4. **Provenance Chains & Stale-While-Revalidate (SWR) Cache Gateway (`src/lookup_cache.py`, Issue #45)**:
   - Multi-tier cache gateway supporting provenance tracking, TTL expirations, and stale-while-revalidate fallbacks.

5. **Port St. Lucie Metro Forecasting Model (`src/locations/port_st_lucie/`, Issue #182)**:
   - Calibrates retail gas price predictions for Port St. Lucie, FL, incorporating PADD 1C waterborne terminal freight logistics.

6. **Realized-vs-Predicted Rolling Scoreboard API & Dashboard Section**:
   - Real-time performance evaluation and error metric tracking across all 8 modeled metro locales.

7. **Zero-Cost Research & Physical Data Connectors (Issues #177–#181)**:
   - **NOAA NHC Tropical Cyclone Advisories (`src/nhc_hurricane.py`)**: Gulf Coast refining hub threat scores.
   - **BSEE Offshore Shut-Ins (`src/bsee_shutins.py`)**: Daily Gulf crude shut-in tracking.
   - **EIA-930 Hourly Electric Grid Stress (`EIA930GridMonitorConnector`)**: ERCOT, MISO, PJM, CAISO grid stress z-scores.
   - **Expanded EIA Weekly Petroleum Balance (`EIADataConnector`)**: Implied demand, refiner production, inter-PADD movements.
   - **USACE LPMS Ohio River Lock Delays (`src/usace_locks.py`)**: Commercial barge queue times at Markland and McAlpine locks.

8. **OilPrice API Free Tier Quota Reconciliation**:
   - Reconciled OilPrice API's transition from 10,000-request trial to 50 requests/day free allowance.
   - Built-in persistent quota safety valve (`OILPRICEAPI_MAX_DAILY_CALLS = 25`) caps outgoing calls at 25 calls/day (50% below the 50 calls/day free tier limit), guaranteeing zero 429 rate limit errors when the trial expires.

9. **Cloudflare Edge Worker Stack Trace Sanitization**:
   - Remediated CodeQL `js/stack-trace-exposure` security alerts in `workers/cache_worker.ts` and `workers/intraday_monitor_worker.ts` by returning generic `"Internal Server Error"` payloads while maintaining full Sentry error tracking.

### 🧪 Verification & Audit
- **Unit Test Suite**: 227/227 unit tests passed cleanly (100% pass rate).
- **Public Web App**: Recompiled and verified across all pages (`docs/*.html`).
- **Target Branch**: `main`
