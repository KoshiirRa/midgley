---
name: midgley-modeling-pit-safety
description: >-
  Enforces Midgley point-in-time (PIT) data integrity, feature engineering,
  event-memory decay, forecasting estimator calibration, scenario gating,
  prediction ledger safety, and public math synchronization. Use when modifying
  src/feature_engineering.py, src/models.py, src/asymmetric_ecm.py,
  src/metro_nowcast.py, src/scenario_engine.py, src/scenario_simulator.py,
  src/prediction_logger.py, or src/model_evaluation.py.
---

# Midgley Modeling, Feature Engineering & Point-in-Time Safety

Use this runbook whenever changing features, event-decay curves, estimators, conformal/residual intervals, counterfactual scenarios, or prediction ledger/evaluation logic.

## 1. Point-in-Time (PIT) & Ground-Truth Invariants

1. **Genuine Observations Only**: Never relabel estimated, proxy, synthetic, filtered, or smoothed series as observed ground truth. Keep synthetic fixtures isolated to tests or explicitly labeled simulations.
2. **Strict Product & Geography Separation**: Never mix wholesale RBOB, regional retail gasoline, and diesel. Never substitute national retail actuals for missing local actuals. Tag experimental diesel outputs with `EXPERIMENTAL_SIMULATION` and `is_simulation: true`.
3. **Bitemporal Joins**: Join every external observation using both observation date and `as_of` publication timestamp, enforcing real release lags and `as_of <= forecast_origin`. Only use future regulatory/tax schedules announced on or before the forecast origin.
4. **Chronological Splits & Contemporary Inference**:
   - Train/evaluate with chronological/purged splits, configured embargoes, and mature labels.
   - Preserve contemporary unlabeled inference rows for all 1D–5D horizons; never select stale `t-h` rows simply because labels end earlier.
   - Backfill actuals only after target-date maturity and genuine observation availability.

## 2. Feature Engineering & Event Memory (`src/feature_engineering.py`)

1. **Trading-Calendar Alignment**: Forward-map weekend/holiday shocks once to the next trading session and aggregate before a one-to-one merge. Preserve exact market-row count.
2. **Decay & Calibration**: Decay shocks by calendar-elapsed time using configured category-specific half-lives (`CATEGORY_HALF_LIVES_DAYS` / `src/event_calibration.py`). Verify current code values rather than copying historical prose.
3. **Domain & Locale Scoping**: Enforce feature domain bounds, missingness indicators, unit conversions, bounded target inversion, and locale-specific event scoping.

## 3. Forecasting, Scenarios, & Runtime Efficiency

1. **Single-Pass Pipeline Efficiency**:
   - Ingest and engineer features **once** per region/run; reuse the feature frame across horizons without repeated scraping, API calls, or rolling recomputation inside horizon loops.
   - Evaluate/log metrics once per region at conclusion and synchronize cloud predictions once at pipeline completion.
2. **Non-Destructive Ledger (`src/prediction_logger.py`, `src/storage_io.py`)**:
   - Reuse the existing canonical forecast-ID factory across logging, imports, and migrations. Deduplicate exact replays idempotently while preserving distinct legitimate intra-day revisions.
   - Separate prospective live records from retroactive backtests at write time; exclude backtests from public scoreboards by default.
   - Lock shared read-modify-write operations and stage atomic writes (flush, fsync, replace) in the destination directory.
3. **Calibration & Scenarios**:
   - Calibrate residuals and intervals by region and horizon; compare candidates against persistence on aligned out-of-sample origins with configured promotion gates.
   - Preserve configured price/return plausibility bounds and seasonal scenario gating (`src/scenario_engine.py`, `src/scenario_simulator.py`). Label what-if runs as counterfactuals.

## 4. Public Math Synchronization

If any equation, feature, estimator, uncertainty interval, or tax formula changes, update the public math and technical-breakdown generators (`src/dashboard_generator.py` -> `docs/math.html`, `docs/technical_breakdown.md` / `.html`) and model documentation in chronological pipeline order, deriving narratives and signed contributions from actual model outputs.

## 5. Verification

```sh
ruff check .
TESTING=1 pytest -v tests/test_truncation_invariance.py
TESTING=1 pytest -v tests/test_asymmetric_ecm.py tests/test_adaptive_conformal.py
python scripts/audit_feature_leakage.py
```

Also run any targeted tests for the specific estimator, scenario engine, or ledger module modified.
