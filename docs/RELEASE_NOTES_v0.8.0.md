# Release Notes - v0.8.0

Midgley **v0.8.0** is a milestone release delivering major pipeline execution acceleration, decoupled edge cloud database synchronization, resilient knowledge graph self-healing, atomic file storage invariants, and append-only prediction ledger revisions.

---

## 🎯 Highlights & Improvements

### 1. Pipeline Execution Acceleration & Cloud Sync Decoupling (Issue #498)
- **Decoupled Cloud Synchronization**: Decoupled `sync_predictions_to_cloud()` from inner per-horizon prediction logging loops and evaluation steps. Consolidated remote edge database synchronization (Turso / Cloudflare D1) into a single batch execution at pipeline completion in `run_all.py`.
- **Eliminated Non-Trading Day Cache Invalidation Trap**: Resolved perpetual cache misses in `backfill_actual_prices_and_evaluate()` by explicitly filtering missing date candidates to valid business days (`dayofweek < 5`) and caching confirmed market closures in `data/rbob_actuals_cache.json`.
- **Batched Commodity Futures Ingestion**: Multi-ticker download (`["RB=F", "CL=F", "BZ=F", "HO=F"]`) with process-level session caching (`_MARKET_DATA_SESSION_CACHE`) in `src/data_ingestion.py`.
- **In-Memory Scoreboard DataFrame Propagation**: Passed pre-loaded prediction history DataFrames across `src/api_server.py`, `src/social_embed_generator.py`, and `src/dashboard_generator.py` to eliminate repetitive disk re-parsing and redundant metric calculations.
- **Empirical Benchmarks**:
  - Daily pipeline CI runtime reduced from **~4 hours** to **< 5 minutes** (>95% reduction).
  - Intraday event anomaly dispatch reduced from **~45 minutes** to **< 6 seconds** (~500x speedup).
  - Static API exporter export across 9 locales reduced from **55+ minutes** to **19.75s**.
  - Social embed preview card generation for 11 locales reduced from **18.4 minutes** to **6.96s**.

### 2. Knowledge Graph SQLite Self-Healing & Resiliency
- **Corrupted Image Auto-Recovery**: Wrapped SQLite database loading in `KnowledgeGraphEngine._load_from_db()` (`src/knowledge_graph.py`) with automatic quarantine and clean database re-initialization upon encountering malformed disk images, preventing crash loops.

### 3. Atomic Storage Engine & Zero-Truncation I/O (Issue #424)
- **Same-Directory Tempfile Staging**: Standardized `atomic_write()`, `atomic_write_csv()`, and `atomic_write_json()` in `src/storage_io.py` using `.tmp-*.partial` staging within the target directory.
- **Forced Fsync & Clean Rollback**: Enforced explicit `handle.flush()` and `os.fsync(handle.fileno())` prior to atomic `os.replace()`, preventing 0-byte file truncation from runner timeouts or process termination.

### 4. Append-Only Prediction Ledger & Advisory File Locking (Issue #434)
- **Immutable UUIDv4 `forecast_id`**: Every forecast issuance is uniquely tracked with an immutable UUIDv4 identifier and UTC timestamp (`issued_at_utc`).
- **Cross-Platform Advisory Locking**: Wrapped prediction history, token accounting, telemetry, and retail feed ledgers with file locks (`file_lock`) to prevent concurrent process race conditions.

### 5. Dynamic Anomaly Retention & Hindsight Reconciliation Engine (Issue #557)
- **Direct Evaluation-Batch Retention**: Refactored `backfill_actual_prices_and_evaluate()` in `src/prediction_logger.py` to directly evaluate and retain newly backfilled rows (`evaluated_rows_indices`) in the active pass, eliminating static DataFrame `tail(10)` sampling biases.
- **Temporal Sorting for Fallback Candidate Sweeps**: Enforced deterministic temporal sorting (`forecast_target_date DESC`, `log_timestamp DESC`) across historical prediction ledgers to prevent stale historical records from shadowing recent trading days.
- **Automated Historical Catch-Up CLI**: Added `scripts/reconcile_hindsight_memory.py` and `AgentMemoryManager.reconcile_unretained_prediction_anomalies()`, automatically reconciling and dual-dispatching missing historical prediction anomalies from September 25, 2026 onward to Vectorize Hindsight Hosted SaaS and SQLite FTS5.

---

## 📦 Commits & Attribution
* **Key Commits**:
  - `45772152` - `perf(pipeline): decouple cloud sync from inner loops and optimize dataframe re-use (#498)`
  - `dbfe714e` - `perf(pipeline): eliminate redundant yfinance downloads, batch commodity feeds, and accelerate CI runtimes (#498)`
  - `Issue #557` - `fix(memory): dynamic anomaly retention & hindsight reconciliation engine (#557)`
* **Milestone**: v0.8 "Storage Modernization & Performance"

