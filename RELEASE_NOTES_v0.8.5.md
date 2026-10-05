# Release Notes - v0.8.5

Midgley **v0.8.5** is a comprehensive data integrity, econometric calibration, security hardening, and operational resilience release. It eliminates proxy fallbacks in regional evaluation ground truth, establishes authentic retail historical cointegration for the Asymmetric Error-Correction Model (ECM), unifies deterministic ledger primary keys across all storage engines, hardens Cloudflare edge security against token replay, and reinforces CI/CD workflow synchronization.

---

## 🎯 Highlights & Improvements

### 1. Authentic Ground Truth Regional Price Series & National Fallback Elimination (Issue #608)
- **Authentic EIA Series Mapping**: Updated [`src/eia_retail_feed.py`](src/eia_retail_feed.py) to ingest dedicated official weekly retail gasoline price series from EIA API v2 and FRED:
  - `Tulsa_OK`: `GASREGWOK` (Oklahoma state retail actuals)
  - `Newark_DE`: `GASREGW01B` (Central Atlantic PADD 1B regional actuals)
  - `Cincinnati_OH`: `GASREGWOH` (Ohio state retail actuals)
  - `Cincinnati_KY`: `GASREGWKY` (Kentucky state retail actuals)
  - `Greenville_NC` & `Charlotte_NC`: `GASREGWNC` (North Carolina state retail actuals)
  - `Port_St_Lucie_FL`: `GASREGWFL` (Florida state retail actuals)
  - `Oakland_CA` & `BayArea_CA`: `GASREGWCA` (California state retail actuals)
  - `National`: `GASREGW` (U.S. National city average)
- **Elimination of Silent Fallbacks**: Refactored `evaluate_prediction_accuracy()` in [`src/prediction_logger.py`](src/prediction_logger.py) to strictly require the matched regional series, raising an explicit alerting warning/error when regional actuals are missing rather than quietly falling back to national prices.

### 2. Asymmetric ECM Refactor on Authentic Retail History & Dynamic Model Versioning (Issue #607)
- **Authentic Cointegration History**: Refactored `get_regional_retail_history()` in [`src/asymmetric_ecm.py`](src/asymmetric_ecm.py) to derive cointegrating price series directly from EIA weekly historical series via bitemporal point-in-time interpolation, eliminating artificial wholesale markup proxies.
- **Dynamic Semantic Model Versioning**: Replaced static model version identifiers with dynamic semantic version tags (`v2.1.0-asym-ecm`) resolved via [`src/version.py`](src/version.py).
- **Index-Safe Series Alignment**: Fixed DatetimeIndex vs. Int64Index alignment to ensure NaN-free feature construction during dynamic time-series regressions.

### 3. Unified Canonical Forecast IDs & Deterministic Ledger Deduplication (Issue #602)
- **Standardized Primary Key Formula**: Unified canonical forecast ID hashing across [`src/prediction_logger.py`](src/prediction_logger.py), [`scripts/clean_and_rekey_prediction_history.py`](scripts/clean_and_rekey_prediction_history.py), and [`scripts/migrate_csv_to_turso.py`](scripts/migrate_csv_to_turso.py):
  $$\text{forecast\_id} = \text{SHA256}(\text{target\_date} : \text{region} : \text{model\_version} : \text{horizon\_days}\text{d} : \text{run\_date})[:16]$$
- **Atomic Deduplication**: Added in-memory deduplication and atomic file swapping in `log_prediction()`, preventing duplicate rows across identical forecast targets.

### 4. Geopolitical Feed Archive Recovery & Union Merge Semantics (Issue #603)
- **Lossless Feed Union**: Implemented `merge_historical_geopolitical_records()` in [`src/geopolitical_feeds.py`](src/geopolitical_feeds.py), deduplicating records by deterministic content hashes (`title:published_date`).
- **Archive Restoration**: Rehydrated historical geopolitical context from `data/wayback_archive_cache.json` without introducing lookahead leakage.

### 5. Deterministic Tax Holiday Restoration & Business-Day Evaluation Windows (Issue #601)
- **Ohio HB 519 Sales Tax Holiday**: Corrected statutory tax schedules in [`src/rvp_regulations.py`](src/rvp_regulations.py) to model Ohio's temporary sales tax holiday (August 1–10, 2026), ensuring standard excise rates automatically restore on August 11, 2026.
- **Business-Day Horizon Realization**: Aligned maturity date calculations in [`src/prediction_logger.py`](src/prediction_logger.py) with standard business days (`pd.bdate_range(..., periods=5)`) matching NYMEX market settlement cycles.

### 6. Security Hardening, Token Replay Defense & Secret Hygiene (Issue #605)
- **Cloudflare D1 Replay Invalidation**: Enforced single-use link consumption in [`workers/intraday_monitor_worker.ts`](workers/intraday_monitor_worker.ts) with transactional SQL checks (`INSERT INTO intraday_flag_tokens`).
- **Safe Link Formatting & Webhook Payloads**: Ensured URL query parameters in Discord alert embeds are properly escaped and expanded headline truncation boundaries to preserve high-severity intelligence context.
- **NASA FIRMS Secret Rotation**: Rotated committed API keys and enforced runtime environment variable injection with non-empty validation in [`src/benchmark_updater.py`](src/benchmark_updater.py).

### 7. Workflow Dirty-Tree Guard & Fail-Closed Cloud Synchronization (Issue #606)
- **Safe Dirty-Tree Staging**: Updated `.github/workflows/gas_price_forecast.yml` and `.github/workflows/weekly_model_review.yml` to stage untracked files before running `git status --porcelain`, preventing uncommitted artifact loss.
- **Fail-Closed DB Synchronization**: Configured synchronization scripts to fail closed on database push errors, notifying maintainers via dead-man switch heartbeats (Healthchecks.io).
- **Isolated Headline Arena Jobs**: Decoupled Headline Arena sync into an isolated, non-blocking GitHub Actions workflow.

### 8. Dynamic Narrative Attribution Drivers & KaTeX SRI Hashes (Issue #604)
- **Proportional Model Driver Decomposition**: Refactored [`src/narrative_generator.py`](src/narrative_generator.py) to compute attribution drivers directly from the net forecast delta:
  $$\sum_{i=1}^3 d_i = \Delta_{\text{forecast}}, \quad \operatorname{sgn}(d_i) = \operatorname{sgn}(\Delta_{\text{forecast}})$$
- **Elimination of Static Literals**: Replaced hardcoded accuracy strings (`MAPE: 4.52% | RMSE: $0.1540`) in [`src/dashboard_generator.py`](src/dashboard_generator.py) with dynamic metrics computed from `prediction_history.csv`.
- **Verified Subresource Integrity (SRI)**: Updated KaTeX 0.16.8 CSS and JS hashes in [`src/sources_generator.py`](src/sources_generator.py) and verified against jsdelivr CDN digests.

---

## 📦 Closed Issues

| Issue | Title | Component |
| :--- | :--- | :--- |
| **#601** | `fix(regulations): Correct tax calendar for Ohio holiday & statutory rates, and align calendar vs business-day evaluation window` | Regulations / MLOps |
| **#602** | `fix(data-integrity): Unify forecast ID generation across logger, re-keying, and Turso migration to prevent ledger duplication` | Data Integrity / Ledger |
| **#603** | `fix(data-ingestion): Fix geopolitical feed refresh data truncation and repair headline deduplication logic` | Data Ingestion / NLP |
| **#604** | `fix(dashboard): Ground narrative card attribution drivers in computed model SHAP/linear impacts and verify KaTeX SRI hashes` | Dashboard / Presentation |
| **#605** | `fix(security): Harden intraday flag links, enforce D1 replay table, fix headline truncation, and rotate committed FIRMS key` | Security / Edge |
| **#606** | `fix(workflows): Fix dirty-tree guard, isolate Headline Arena sync, and ensure resilient forecast ledger commits` | CI/CD / Workflows |
| **#607** | `fix(modeling): Reconcile asymmetric ECM retail forecasting with genuine retail price history and distinct model versioning` | Econometrics / Modeling |
| **#608** | `fix(ground-truth): Ingest authentic regional retail gasoline price series and eliminate cross-geography fallbacks` | Ground Truth / EIA |
