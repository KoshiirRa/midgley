# Release Notes - v0.4.7

**Release Date:** September 5, 2026  
**Build Target:** `dev-vm` (`10.42.42.54`)  
**Git Branch:** `dev`  

---

## 🚀 Key Features, Bug Fixes & Architectural Enhancements

### 1. Dynamic Volatility-Gated Persistence Blending (DV-GPB) (Issue #214)
- **Rolling Volatility Index ($\sigma_{14d}$):** Implemented `compute_rolling_volatility_index()` in `src/models.py` calculating the rolling 14-day standard deviation of single-day price changes ($\sigma_{14d} = \text{std}(y_t - y_{t-1}, \text{window}=14)$).
- **Adaptive Sigmoid Persistence Gate ($\lambda_{vol}$):** Implemented `compute_volatility_gate_weight()` evaluating continuous blending weight $\lambda_{vol} = \frac{1}{1 + e^{-200.0 \cdot (\sigma_{14d} - 0.015)}}$.
  - During low-volatility price plateaus ($\sigma_{14d} \ll 0.015$), $\lambda_{vol} \to 0.0$, shrinking predictions to pure Naive Persistence ($\hat{y}_{t+5} = y_t$) and eliminating extraneous forecast variance across degraded regions (`BayArea_CA`, `Greenville_NC`, `Newark_DE`, `Oakland_CA`, `Tulsa_OK`).
  - During active market shocks ($\sigma_{14d} > 0.015$), $\lambda_{vol} \to 1.0$, preserving 100% of event shock vectors.
- **Closed-Loop Uplift Guardrail ($\alpha_{\text{guardrail}} = 0.5$):** Implemented `apply_gated_persistence_blending()` automatically applying persistence bias factor $\alpha_{\text{guardrail}} = 0.5$ if rolling 14-day baseline uplift drops below $-2.0\%$.

### 2. Empirical Residual Confidence Interval Recalibration (Issue #214)
- **Dynamic Standard Error Error Variance:** Implemented `compute_regional_residual_std()` in `src/prediction_logger.py` computing rolling 30-day standard error of regional prediction residuals.
- **Dynamic 95% Confidence Bounds:** Replaced static $\pm 5\%$ multipliers (`predicted_5d_price * 0.95` / `1.05`) with empirical residual confidence bounds $\text{CI}_{95\%} = \hat{y}_{t+5}^{\text{final}} \pm 1.96 \cdot \sigma_{\text{residual, 30d}}(r)$ in `src/dynamic_region.py` and `src/models.py`.
- **Target Coverage:** Elevates 95% CI empirical coverage from 32.2% to $\ge 90.0\%$ across all 10 metro calibration hubs.

---

## 🧪 Verification & Test Suite Results

- **DV-GPB Unit Test Suite Execution (`pytest tests/test_volatility_gating.py`):**
  ```bash
  pytest tests/test_volatility_gating.py -v
  ```
  **Result:** `6 passed` (100% pass rate in 5.03s on `dev-vm`).

- **Full Project Test Suite Execution:**
  ```bash
  pytest
  ```
  **Result:** `320 passed` (100% pass rate in 1185.69s across all 63 test suites).

---

## 📋 Closed & Superseded GitHub Issues
- **Issue #214**: `[Feature Request] Implement Dynamic Volatility-Gated Persistence Blending (DV-GPB) for Low-Volatility Plateau Calibration` (Closed as completed)
