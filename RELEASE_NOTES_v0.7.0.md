# Release Notes - v0.7.0

**Release Date:** September 21, 2026  
**Build Target:** `dev-vm` (`10.42.42.54`), GitHub Actions & Cloudflare Edge  
**Git Branch:** `dev` / `main`  
**Tracking Issues:** [Issue #343](https://github.com/KoshiirRa/midgley/issues/343), [Issue #354](https://github.com/KoshiirRa/midgley/issues/354), [Issue #344](https://github.com/KoshiirRa/midgley/issues/344), [Issue #341](https://github.com/KoshiirRa/midgley/issues/341)

---

## 🚀 Overview & Release Highlights

Midgley **v0.7.0** delivers critical security hardening across the administrative API gateway, CLI upgrade reconciler, and API key authentication middleware, alongside an end-to-end econometric remediation eliminating temporal lookahead leakage across the time-series feature engineering and stacking ensemble pipelines.

---

### 1. Upgrade Reconciler RCE Remediation & Safe Execution Model (`scripts/check_updates.py` - Issue #343)
- **Eliminated Arbitrary Command Execution (`shell=True`):** Removed dangerous dynamic shell invocation of unvalidated upstream manifest strings.
- **Enforced Allowlisted Actions (`ALLOWLISTED_ACTIONS`):** Restricted reconciler automation to strict, pre-defined argument vectors (`retrain_regional_models`, `update_static_dashboard`, `run_migrations`) executed with `shell=False`.
- **HTTPS Scheme Enforcement:** Added strict validation ensuring update manifest endpoints originate from secure `https://` URLs, preventing insecure scheme downgrade attacks.
- **Cross-Platform Console Compatibility:** Replaced raw Unicode emojis with ASCII-safe status tags (`[*]`, `[+]`, `[!]`) to ensure seamless execution across Windows (`cp1252`) and POSIX environments.

---

### 2. Time-Series Feature Engineering & Stacking Leakage Elimination (`src/feature_engineering.py` & `src/models.py` - Issue #354)
- **Eliminated Backward Imputation (`bfill`):** Replaced backward lookahead filling on feature lags with chronological forward-filling (`ffill().fillna(0.0)`), guaranteeing zero future information leaks into historical observations.
- **Chronological Split Boundary Purging:** Enforced an $h$-step boundary purge gap (`train_slice_end = max(1, split_idx - forecast_horizon)`) in `prepare_chronological_splits()`, ensuring target values ($y_t = P_{t+h}$) at the tail of the training set never overlap or leak into the test evaluation slice.
- **Training-Slice Autocorrelation Routing Diagnostic:** Refactored `compute_context_routing_diagnostic()` to evaluate target autocorrelation exclusively on the training partition ($k = \lfloor N \times \text{train\_ratio} \rfloor$).
- **Purged Stacking Cross-Validation:** Updated `build_stacking_ensemble_pipeline()` to default to `PurgedGroupTimeSeriesSplit(n_splits=5, label_horizon_steps=5, embargo_steps=5)` with contiguous test partitions, eliminating out-of-fold training leakage in meta-regressors.

---

### 3. Global Middleware Authentication Route Matching Fix (`src/api_server.py` - Issue #344)
- **Exact Root Path Matching:** Replaced loose prefix matching on `"/"` with exact equality (`request.url.path == "/"`) for public root documentation.
- **Strict Protected Route Enforcement:** Enforces API key verification on all protected endpoints (`/api/v1/prices/*`, `/api/v1/forecast/*`, `/api/v1/combined`, `/mcp/*`) while preserving public access strictly for explicit endpoints (`/docs`, `/redoc`, `/openapi.json`, `/.well-known`, `/health`).

---

### 4. Admin Secret Fail-Closed Security Hardening (`src/api_server.py` - Issue #341)
- **Removed Hardcoded Fallback Secret:** Eliminated default development token (`midgley_dev_admin_secret_2026`).
- **Fail-Closed Verification:** Enforced immediate `HTTP 401 Unauthorized` rejection when `MIDGLEY_ADMIN_SECRET` is unset, empty, or whitespace-only on the server.

---

### 5. Automated Verification & Regression Test Suite
- **`tests/test_check_updates.py`:** Validates RCE prevention, allowlisted action execution, legacy command translation, and insecure URL fallback rejection.
- **`tests/test_temporal_leakage.py`:** Validates absence of backward filling, $h$-step split boundary purging, train-slice diagnostic computation, stacking CV purging, and chronological ordering.
- **`tests/test_api_server.py`:** Verifies fail-closed admin secret verification and global API key middleware route enforcement.
- **Test Results:** 100% pass rate across all 32 core test suites without regressions.
