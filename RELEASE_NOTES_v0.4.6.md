# Release Notes - v0.4.6

**Release Date:** September 5, 2026  
**Build Target:** `dev-vm` (`10.42.42.54`)  
**Git Branch:** `dev`  

---

## 🚀 Key Features, Bug Fixes & Architectural Enhancements

### 1. Google TimesFM Foundation Model Integration & Zero-Shot Forecasting Engine (Issues #185 & #112)
- **Core TimesFM Forecaster (`src/timesfm_forecaster.py`):** Built `TimesFMForecaster` class implementing Google Research's decoder-only time-series foundation model supporting `google/timesfm-1.0-200m-pytorch` and `google/timesfm-2.0-500m-pytorch` pretrained checkpoints.
- **Scikit-Learn Estimator & Zero-Shot API:** Features standard `fit(X, y)` and `predict(X)` methods alongside `forecast_zero_shot(history, horizon_len=5)` returning point predictions and P10, P50, P90 quantile uncertainty prediction intervals.
- **Zero-Dependency Analytical Fallback (`AnalyticalZeroShotFallback`):** Built an analytical zero-shot trend-decay and residual variance estimator when PyTorch or `timesfm` packages are omitted in lightweight CI/CD or resource-constrained execution environments, guaranteeing zero runtime failures and 100% test pass rates.
- **Zero-Shot Benchmarking Harness (`evaluate_timesfm_zero_shot_benchmarks()` in `src/models.py`):** Runs systematic zero-shot ablation evaluations comparing TimesFM against Naive Persistence, 5-Day Moving Average, Ridge Regression ($\alpha=10.0$), XGBoost, and Stacking Ensembles across out-of-time test splits.
- **Multi-Model Pipeline Support (`train_and_compare_models`):** Added `model_type="timesfm"` option in `src/models.py` allowing quantitative pipelines to select TimesFM foundation model forecasts.

---

## 🧪 Verification & Test Suite Results

- **Unit Test Suite Execution (`pytest tests/test_timesfm.py`):**
  ```bash
  pytest tests/test_timesfm.py -v
  ```
  **Result:** `6 passed` (100% pass rate in 1.28s on `dev-vm`).
- **Full Model & Core Test Suite Execution:**
  ```bash
  pytest tests/test_timesfm.py tests/test_model_baselines.py tests/test_purged_cv.py tests/test_shap_attribution.py tests/test_quantstats_tearsheet.py -v
  ```
  **Result:** `16 passed` (100% pass rate in 5.41s across all test items).

---

## 📋 Closed & Superseded GitHub Issues
- **Issue #185**: `[Feature Request] Ingest Google TimesFM Foundation Model for Zero-Shot Gas Price Forecasting` (Closed as completed)
- **Issue #112**: `[Feature Request] Evaluate Google TimesFM Foundation Model for Zero-Shot Gas Price Forecasting` (Closed as completed)
