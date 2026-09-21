# Release Notes - v0.6.8

**Release Date:** September 21, 2026  
**Build Target:** `dev-vm` (`10.42.42.54`), GitHub Actions & Cloudflare Edge  
**Git Branch:** `dev` / `main`  
**Tracking Issue:** [Issue #326](https://github.com/KoshiirRa/midgley/issues/326)

---

## 🚀 Overview & Release Highlights

Midgley **v0.6.8** resolves a cloud database synchronization schema bug with Turso Edge SQLite Hrana protocol serialization and refactors the episodic memory shock retention pipeline to isolate anomaly evaluations to target regions during multi-hub forecast runs.

---

### 1. Turso Hrana Protocol Integer Serialization Fix (`src/prediction_logger.py` - Issue #326)
- Resolved `HTTP 400: Bad Request - JSON parse error: invalid type: integer '5', expected string` during background prediction cloud sync.
- Casts 64-bit integer values (`forecast_horizon_days`) to string representations (`{"type": "integer", "value": "5"}`) in Hrana JSON argument arrays, strictly conforming to the Turso HTTP protocol specification.

---

### 2. Region-Scoped Episodic Memory Shock Retention (`src/prediction_logger.py` & `src/locations/*/main.py`)
- Upgraded `backfill_actual_prices_and_evaluate(target_region=None)` to accept an explicit `target_region` parameter.
- Filtered memory shock candidates ($|\text{error}| \ge \$0.25/\text{gal}$ or unpredicted directional flips) to the specific region evaluated during per-hub pipeline runs.
- Eliminates redundant global tail re-evaluations across sequential location runs and prevents duplicate retain requests to remote Hindsight / Supabase instances.

---

### 3. Comprehensive Hub Integration
- Updated all 8 location runners to supply their authoritative region identifiers during post-logging price evaluation passes:
  - **National Hub:** `backfill_actual_prices_and_evaluate(target_region="National")`
  - **Tulsa Metro Hub:** `backfill_actual_prices_and_evaluate(target_region="Tulsa_OK")`
  - **Newark Metro Hub:** `backfill_actual_prices_and_evaluate(target_region="Newark_DE")`
  - **Cincinnati Tri-State Hub:** `backfill_actual_prices_and_evaluate(target_region="Cincinnati_OH")` & `backfill_actual_prices_and_evaluate(target_region="Cincinnati_KY")`
  - **Greenville Hub:** `backfill_actual_prices_and_evaluate(target_region="Greenville_NC")`
  - **Charlotte Hub:** `backfill_actual_prices_and_evaluate(target_region="Charlotte_NC")`
  - **Oakland & SF Bay Area Hub:** `backfill_actual_prices_and_evaluate(target_region="Oakland_CA")` & `backfill_actual_prices_and_evaluate(target_region="BayArea_CA")`
  - **Port St. Lucie Hub:** `backfill_actual_prices_and_evaluate(target_region="Port_St_Lucie_FL")`

---

### 4. Automated Verification & Unit Test Suite
- Verified memory and prediction logger unit tests:
  - `tests/test_agent_memory.py` (9/9 passing)
  - `tests/test_memory_telemetry_sync.py` (4/4 passing)
  - `tests/test_mlops_prediction_schema.py` (passing)
- Confirmed zero-regression execution across all local and remote test runners.
