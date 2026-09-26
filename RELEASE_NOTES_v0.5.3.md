# Release Notes - v0.5.3
 
**Release Date:** September 13, 2026  
**Build Target:** `dev-vm` (`10.42.42.54`)  
**Git Branch:** `main`  

---

## 🚀 Key Features, Architectural Enhancements & Algorithmic Upgrades

### 1. Global Cloudflare D1 Persistent Edge Deduplication & Anomaly Ledger (Issue #239)
- **Global Edge State Coordination ([`workers/intraday_monitor_worker.ts`](workers/intraday_monitor_worker.ts), [`wrangler.toml`](wrangler.toml)):**
  - Resolved repeated 15-minute triggering of syndicated policy articles by binding Cloudflare D1 (`midgley-cache-d1`, `binding = "DB"`) to the edge intraday monitor worker.
  - Upgraded `isHeadlineDispatchedInCache` and `markHeadlineDispatchedInCache` to persist dispatched RSS event hashes in the `seen_rss_headlines` table with 24-hour TTL, replacing ephemeral, node-local `caches.default` state that suffered from cache misses across shifting global Cloudflare PoPs (e.g., Dallas, Ashburn, Chicago, Frankfurt).
  - Enforced immediate edge dispatch tracking upon message enqueue to `INTRADAY_QUEUE` to prevent burst re-enqueuing.
- **Headline Normalization & Publisher Suffix Stripping:**
  - Implemented `normalizeHeadline()` in TypeScript and `normalize_headline()` in Python to strip dynamic publisher attribution suffixes (e.g., ` - National Taxpayers Union`, ` | OilPrice.com`, ` — Reuters`, ` - CNBC`) and normalize punctuation/casing prior to hashing cache keys.
- **Contextual Stage-1 Anomaly Regex & Agricultural Oil Exclusions:**
  - Refined Stage-1 fast-path gate so standalone `"tariff"` / `"tariffs"` require explicit petroleum/energy context (`oil`, `crude`, `gasoline`, `fuel`, `petroleum`, `refin`, `diesel`, `opec`, `energy`) or explicit trade terms (`"energy tariff"`, `"retaliatory tariff"`).
  - Added `NON_ENERGY_TARIFF_EXCLUDE` and updated `EXCLUDE_KEYWORDS` to immediately filter non-energy macro policy (Section 232/301, Congressional procedure) and agricultural cooking oils (`canola`, `canola oil`, `cooking oil`, `palm oil`, `olive oil`, `soybean oil`) at zero LLM token spend.
- **Persistent Origin Negative-Anomaly Evaluation Ledger ([`src/intraday_event_monitor.py`](src/intraday_event_monitor.py)):**
  - Integrated `_save_evaluated_record()` to persist all processed incoming headlines (both positive anomalies and negative non-anomalies) to [`data/evaluated_headlines.json`](data/evaluated_headlines.json) with rolling 48-hour pruning.
  - Upgraded `is_headline_already_processed()` to check both `data/intraday_events.json` and `data/evaluated_headlines.json`, short-circuiting repeat dispatches on subsequent cycles with zero redundant LLM API invocations.

### 2. Hindsight Scale-to-Zero Proactive Warmup & Resilient Retries (Issue #230)
- **Scale-to-Zero Container Cold-Start Management ([`src/hindsight_client.py`](src/hindsight_client.py)):**
  - Designed `HindsightClient.warmup()` with polling to detect and warm Google Cloud Run scale-to-zero containers before batch memory operations begin.
  - Configured non-blocking Step 0 background warmup thread in [`run_all.py`](run_all.py) so model inference and data ingestion proceed in parallel while container instances initialize.
  - Increased `DEFAULT_TIMEOUT` from 15.0s to 30.0s (configurable via `HINDSIGHT_TIMEOUT`), accommodating Google Cloud Run container cold boots (20–35s) and preventing premature socket timeout failures.
  - Added 2-attempt HTTP retries with exponential backoff on socket read timeouts and connection reset errors across `retain()`, `recall()`, and `reflect()` operations.
  - Enhanced error diagnostics via `_extract_error_detail()` to parse and surface detailed HTTP error bodies from Hindsight.
- **Low-Cost Flash Model Pinning & Outlier Retention Filter ([`scripts/deploy_hindsight_cloudrun.sh`](scripts/deploy_hindsight_cloudrun.sh), [`src/prediction_logger.py`](src/prediction_logger.py)):**
  - Configured `HINDSIGHT_API_LLM_MODEL="gemini-2.5-flash"` on Cloud Run deployment scripts, replacing unpinned default Pro models and reducing reasoning token costs by >90%.
  - Restricted automatic prediction memory retention to genuine prediction anomaly shocks ($|error| \ge \$0.25/\text{gal}$ or directional flips), eliminating unnecessary LLM fact extraction overhead on normal forecast evaluations.

### 3. Zero-Data-Loss Pending Memory Reconciliation Ledger ([`src/agent_memory.py`](src/agent_memory.py))
- **Local SQLite Dual-State Schema & Auto-Migration:**
  - Added `cloud_synced INTEGER DEFAULT 0` column to local SQLite memory store (`data/agent_memory.sqlite`), marking experiences successfully ingested by remote pgvector.
  - Integrated automatic column detection and SQLite `ALTER TABLE` migration on startup.
- **Automatic Pending Memory Draining (`sync_pending_memories()`):**
  - Implemented automatic reconciliation in `AgentMemoryManager` called whenever Hindsight is available during retain, recall, and reflection operations.
  - Queries all un-synced local records (`cloud_synced = 0`), pushes them in batch to Vectorize Hindsight, and atomically marks them as synced (`mark_as_synced()`), ensuring 100% zero data loss even when executions start during Cloud Run cold starts or transient network blips.
- **Unit Test Execution Isolation:**
  - Enforced strict `TESTING=1` network isolation across `src/hindsight_client.py` and `src/prediction_logger.py`, preventing test suite hangs and enabling fast offline validation (<3.0s total test runtime).

### 4. Comprehensive Python 3.13 Warning & Deprecation Resolutions
- **AST Node Deprecations ([`src/qlib_symbolic_engine.py`](src/qlib_symbolic_engine.py)):**
  - Replaced deprecated `ast.Num` with `ast.Constant` across AST expression parsers, ensuring forward compatibility with Python 3.13 and 3.14.
- **Pandas Unit String Standardization ([`src/prediction_logger.py`](src/prediction_logger.py)):**
  - Replaced ambiguous timedelta unit strings with standardized unit `'D'` (`pd.to_timedelta(w_int, unit='D')`).
- **Regex & String Escape Sequences ([`src/catalog_monitor.py`](src/catalog_monitor.py), [`scripts/generate_standalone_example.py`](scripts/generate_standalone_example.py)):**
  - Corrected raw string escape sequences and LaTeX KaTeX formatting strings to eliminate `SyntaxWarning: invalid escape sequence` warnings.
- **W&B Logger Lifecycle Standardization ([`src/wandb_logger.py`](src/wandb_logger.py)):**
  - Mapped deprecated `reinit=True` parameter to `reinit="finish_previous"` per modern Weights & Biases SDK standards.

---

## 🧪 Benchmark & Verification Results

- **Strict Zero-Warning Test Suite Execution:**
  - `python -W error -m pytest tests/test_agent_memory.py tests/test_intraday_event_monitor.py` passed with 0 warnings / 0 errors on `dev-vm` (`10.42.42.54`).
- **Hindsight Warmup & Memory Reconciliation Suite ([`tests/test_agent_memory.py`](tests/test_agent_memory.py)):**
  - 14 passed in 0.17s verifying proactive warmup, retry handling, local FTS5 indexing, and pending memory synchronization.
- **Intraday Anomaly & Deduplication Test Suite ([`tests/test_intraday_event_monitor.py`](tests/test_intraday_event_monitor.py)):**
  - 18 passed in 0.42s covering publisher suffix stripping, Stage-1 keyword gates, and rolling negative-anomaly deduplication.
- **Full Test Suite:**
  - All 34 tests passed in 2.95s on `dev-vm`.

---

## 📋 Closed & Superseded GitHub Issues
- **Issue #239**: `fix(intraday): Fix repetitive RSS event triggering via Cloudflare edge deduplication and negative-anomaly caching` (Completed)
- **Issue #230**: `feat(memory): Vectorize Hindsight episodic agent memory integration, scale-to-zero proactive warmup, and zero-data-loss reconciliation ledger` (Enhanced & Verified)
