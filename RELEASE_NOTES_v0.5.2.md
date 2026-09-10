# Release Notes - v0.5.2

**Release Date:** September 10, 2026  
**Build Target:** `dev-vm` (`10.42.42.54`)  
**Git Branch:** `dev`  

---

## 🚀 Key Features, Architectural Enhancements & Algorithmic Upgrades

### 1. CoSPOT Compositional Spectral & Wavelet Feature Prompting Engine (Issue #215, arXiv:2609.02093)
- **Mathematical Frequency & Wavelet Decomposition ([`src/cospot_spectral_engine.py`](file:///src/cospot_spectral_engine.py)):**
  - Integrated theoretical concepts from *CoSPOT: Compositional Spectral Prompts for LLM-based Online Time Series Forecasting* ([arXiv:2609.02093v1](https://arxiv.org/abs/2609.02093v1), KAIST).
  - **Discrete Fourier Transform (DFT) Basis Decomposition:** Decomposes lookback sequences into orthogonal frequency bases:
    $$F_k = \sum_{t=0}^{L-1} X_t e^{-i 2\pi k t / L}, \quad k = 0, \dots, \lfloor L/2 \rfloor$$
    Extracts dominant cycle periods ($T_{\text{dom}} = L / k^*$), normalized spectral power distributions ($P_k$), low-frequency trend energy ratios ($E_{\text{low}}$), and Shannon Spectral Entropy:
    $$H_{\text{spectral}} = -\frac{\sum P_k \ln(P_k + 1e-12)}{\ln(K)}$$
  - **Discrete Wavelet Transform (DWT) Multi-Resolution Filtering:** Uses 2-level Haar wavelet filtering to isolate high-frequency intraday noise ($D_1$), localized 3-5 day shock fluctuations ($D_2$), and macro trend baselines ($A_2$), computing detail-to-approximation energy ratios ($R_{\text{wavelet}}$) and localized shock magnitudes ($|D_1[-1]| + |D_2[-1]|$).
- **Gemini 2.5 Flash Prompt Context Enrichment ([`src/event_analyzer.py`](file:///src/event_analyzer.py)):**
  - Injects structured `[MARKET FREQUENCY & SPECTRAL REGIME (CoSPOT arXiv:2609.02093)]` natural language context directly into Gemini 2.5 Flash single and batch prompt contracts (`LLM_SINGLE_PROMPT` & `LLM_BATCH_PROMPT`).
  - Addresses LLM "numerical blindness" by providing explicit frequency regime descriptors (e.g. *Coherent structural trend* vs *Turbulent non-stationary dispersion*) and localized wavelet noise states.
- **Ultra-Low Compute Online Projection Head Adaptation:**
  - Implemented `CoSPOTOnlineAdapter` with geometric loss decay ($\delta = 0.90$) and L2 regularization to rapidly adapt linear projection weights to non-stationary concept drift without full model retraining:
    $$\mathcal{L}_{\text{online}} = \sum_{\tau=1}^T \delta^{T-\tau} \ell(f_\theta(X_\tau), \tilde{y}_\tau)$$
- **Quantitative Feature Engineering & Chronological Splits ([`src/feature_engineering.py`](file:///src/feature_engineering.py)):**
  - Added 6 rolling spectral features to `create_feature_matrix()`:
    - `cospot_dft_dominant_period`
    - `cospot_dft_low_freq_energy_ratio`
    - `cospot_dft_spectral_entropy`
    - `cospot_dwt_detail_energy_ratio`
    - `cospot_dwt_detail_shock_mag`
    - `cospot_dwt_approx_momentum`
  - Fully integrated into `quant_features` and `hybrid_features` in `prepare_chronological_splits()`.
- **Intraday Anomaly Event Monitor Ingestion ([`src/intraday_event_monitor.py`](file:///src/intraday_event_monitor.py)):**
  - Updated `evaluate_headline_anomaly()` to generate and pass real-time spectral prompt context to `extract_event_features_llm()`, ensuring breaking news impact scoring is conditioned on current frequency-domain market dynamics.
- **Spectral Benchmark Evaluator ([`src/models.py`](file:///src/models.py)):**
  - Added `evaluate_cospot_spectral_benchmarks()` comparing baseline Ridge estimators against spectral-augmented, hybrid-spectral, and online-adapted models on out-of-time test sets.

---

## 🧪 Verification & Test Suite Results

- **Unit & Integration Test Suite (`tests/test_cospot_spectral.py`):**
  - 10 automated test cases verifying DFT spectral feature bounds, DWT wavelet energy ratios, prompt context generation, rolling feature calculation, online adapter geometric decay, and end-to-end model benchmarking:
    ```bash
    pytest tests/test_cospot_spectral.py -v
    ```
    **Result:** `10 passed in 6.61s` (100% pass rate).
- **Regression Test Suites on `dev-vm` (`10.42.42.54`):**
  - `tests/test_event_analyzer.py`, `tests/test_intraday_event_monitor.py`, `tests/test_technical_momentum.py`: `18 passed in 11.00s`.

---

## 📋 Closed & Superseded GitHub Issues
- **Issue #215**: `[Feature Request] Evaluate CoSPOT Compositional Spectral Prompting & Wavelet Context for LLM Forecasting (arXiv:2609.02093)` (Closed as completed)
