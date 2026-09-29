# Release Notes - v0.8.0

Midgley **v0.8.0** is a milestone release delivering major pipeline execution acceleration, decoupled edge cloud database synchronization, resilient knowledge graph self-healing, atomic file storage invariants, append-only prediction ledger revisions, roll-adjusted continuous commodity returns, adaptive conformal uncertainty bounds, unified statistical hypothesis validation, semantic news deduplication, and MinT hierarchical multi-metro reconciliation.

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

### 6. Roll-Adjusted RBOB Futures & Regional Wholesale Supply Hubs (Issue #444)
- **Backward Ratio Roll Adjustment**: Implemented `compute_roll_adjusted_rbob()` in `src/data_ingestion.py`, eliminating artificial contract roll returns (+14.1% late-Feb and -10.2% late-Aug) caused by NYMEX Chapter 191 seasonal RVP delivery specifications (13.5 psi winter vs 7.4 psi summer).
- **Physical Spot Hub Matrix**: Added `fetch_regional_wholesale_spot_matrix()` mapping each modeled metro locale to its authentic physical wholesale benchmark (`DGASNYH`, `DGASUSGULF`, `LA_CARBOB`, Group 3 Mid-Continent, Chicago CBOB).

### 7. Adaptive Conformal Inference & Quantile Generation (Issue #449)
- **Gibbs & Candès Adaptive Conformal Inference**: Added `AdaptiveConformalInference` in `src/models.py`, dynamically adjusting interval coverage threshold $\alpha_{t+1} = \alpha_t + \gamma(\alpha^* - \text{miss}_t)$ under non-stationary market distribution shift.
- **Parametric Student-$t$ Predictive Quantiles**: Added `compute_calibrated_quantiles()`, generating valid $P_{10}, P_{50}, P_{90}$ predictive quantiles and directional probabilities for Headline Arena competitive scoring.

### 8. Unified Statistical Evaluation Harness & Model Confidence Set (Issue #452)
- **Pesaran-Timmermann Directional Test**: Added `pesaran_timmermann_test()` in `src/model_evaluation.py` to test whether directional hit rates statistically exceed random market chance.
- **Newey-West Multi-Horizon HAC Standard Errors**: Added `compute_newey_west_hac_standard_error()` with Bartlett kernel lag bandwidth $J = h - 1$ for overlapping forecast horizon errors.
- **Hansen's Model Confidence Set (MCS)**: Added `model_confidence_set()` executing iterative loss trimming at $\alpha = 0.10$ via stationary block bootstrap.
- **Benjamini-Hochberg FDR Control & Feature Admission Gate**: Added `benjamini_hochberg_fdr_control()` and `FeatureAdmissionGate` to prevent feature bloat and data snooping.
- **Automated Verification CLI**: Added `scripts/evaluate_forecast_rigor.py`.

### 9. Semantic News Deduplication & Local Projections (Issue #446)
- **Rolling-Window News Clustering**: Added `cluster_and_deduplicate_headlines()` in `src/event_analyzer.py` combining Jaccard similarity, containment indexing, and character 3-gram Dice coefficients over rolling 48-hour windows, grouping syndicated news wires and cutting extraction compute by 40–70%.
- **Rolling Shock Normalization**: Added `normalize_event_shocks()` for logarithmic and rolling 90-day z-score shock scaling.
- **Jordà (2005) Local Projections**: Added `estimate_local_projections_impulse_responses()` in `src/feature_engineering.py` estimating non-parametric multi-horizon impulse response curves with Newey-West HAC standard errors.

### 10. MinT Hierarchical Reconciliation Engine (Issue #450)
- **Minimum Trace Optimal Combination**: Implemented `MinTHierarchicalEngine` and `reconcile_mint()` in `src/hierarchical_engine.py` (Wickramasuriya et al. 2019), enforcing exact mathematical summation consistency across National $\to$ PADD $\to$ Metro levels.
- **Empirical Bayes Parameter Shrinkage**: Added `empirical_bayes_shrinkage_regression()`, shrinking data-sparse regional coefficients toward regional cluster priors.

---

## 📦 Commits & Attribution
* **Key Issues Completed**:
  - Issue #444 - `fix(data-ingestion): Implement roll-adjusted RBOB futures returns and map metros to regional wholesale supply hubs`
  - Issue #449 - `feat(uncertainty): Calibrated prediction intervals and proper quantile generation via Adaptive Conformal Inference`
  - Issue #452 - `feat(evaluation): Build unified statistical evaluation harness, Model Confidence Set & feature admission gate`
  - Issue #446 - `feat(nlp): Rework news-event features with semantic deduplication, rolling scaling, and local projections`
  - Issue #450 - `feat(hierarchical): Partial pooling and MinT hierarchical reconciliation across metro, state, and national forecasts`
  - Issue #498 - `perf(pipeline): eliminate redundant yfinance downloads, batch commodity feeds, and accelerate CI runtimes`
  - Issue #557 - `fix(memory): dynamic anomaly retention & hindsight reconciliation engine`
* **Milestone**: v0.8 "Storage Modernization, Math Rigor & Performance"
