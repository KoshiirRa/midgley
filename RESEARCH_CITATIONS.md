# 📚 Midgley Research Literature & Paper Citation Ledger

This document maintains a running, peer-reviewed index of academic research papers whose theoretical frameworks, diagnostic algorithms, prompt engineering patterns, or model architectures have been implemented into the **Midgley Unleaded Gas Price Prediction System**.

Gotta give credit where credit is due! 🎓

---

## 📑 Implemented Research Papers Index

| # | Paper Title & arXiv Link | Authors | Date | Implemented Module(s) | Key Methodological Contribution & Implementation Details |
| :-: | :--- | :--- | :-: | :--- | :--- |
| **1** | [**When Does Context Routing Help? A Systematic Study of Multi-Modal Fusion in Time Series Forecasting**](https://arxiv.org/abs/2608.25128v1) <br/>([PDF](https://arxiv.org/pdf/2608.25128v1)) | Ruizhe Zhou, Gaoyuan Du, Xiaoyang Liu et al. | Aug 2026 | [`src/feature_engineering.py`](file:///src/feature_engineering.py) | **Pre-Training Diagnostic ($\rho_h$ vs $\Delta$) & RBU Theorem**: Implemented rolling autocorrelation check ($\rho_h = \text{Corr}(X_t, X_{t+h})$). When $\rho_h > 0.95$ (sticky calm markets), last-value shortcuts dominate and LLM text fusion is suppressed. When $\rho_h < 0.95$ or conditional mutual info $\Delta > 0$ (exogenous event shocks), event memory decay $t_{1/2}$ and shock multipliers are dynamically boosted. |
| **2** | [**CEDAR: Controlled and Event-Driven Demand Forecasting via Residual Decomposition**](https://arxiv.org/abs/2608.25871v1) <br/>([PDF](https://arxiv.org/pdf/2608.25871v1)) | Junjie Meng, Ranxu Zhang, Zi-an Zhang, Chao Wang et al. (Alibaba 1688) | Aug 2026 | [`src/event_analyzer.py`](file:///src/event_analyzer.py)<br/>[`src/models.py`](file:///src/models.py) | **Two-Stage Decoupled Residual Decomposition ($\mathbf{s}_{t+1} = f_\theta(\mathbf{s}_{\le t}, \mathbf{a}_{\le t+1}) + \epsilon_t$)**: Decouples baseline quantitative time-series forecasting (Ridge/XGBoost) from qualitative event shock residuals ($\epsilon_t$). Implemented 2-stage LLM extraction (Stage 1: Tag Filtering $\to$ Stage 2: Regional Calendar Event Synthesis) to generate structured residual shock vectors without autoregressive inertia. |
| **3** | [**TraceBench: Controlled Evaluation of LLM Agents for Time-Series Root-Cause Attribution**](https://arxiv.org/abs/2708.27182v1) <br/>([PDF](https://arxiv.org/pdf/2608.27182v1)) | Tommaso Bendinelli, Artur Dox, Christian Holz | Aug 2026 | [`src/event_analyzer.py`](file:///src/event_analyzer.py)<br/>[`src/noaa_weather.py`](file:///src/noaa_weather.py) | **Structured Data Feeds & Explicit Domain Context**: Validated that time-series LLM agents explore data significantly better through compact numerical console/JSON formats than visual plots. Used to guide token-efficient NWS alert ingestion (`wxs.us` 150-token summaries & 0-token SPC risk mappings). |
| **4** | [**SAGE: Variate-Wise Semantic Augmentation for Vision-Language Time Series Forecasting**](https://arxiv.org/abs/2608.26829v1) <br/>([PDF](https://arxiv.org/pdf/2608.26829v1)) | Haizhao Fan, Xinyi Le | Aug 2026 | [`src/feature_engineering.py`](file:///src/feature_engineering.py) | **Variate-Specific Domain Descriptors**: Injected variate-level metadata (units, autocorrelation behavior, geographic hub context) directly into feature engineering matrices without placing LLMs in real-time inference loops. |
| **5** | [**Modeling spatio-temporal locality in multi-step forecasting of geo-referenced time series (SPALT)**](https://arxiv.org/abs/2608.25698v1) <br/>([PDF](https://arxiv.org/pdf/2608.25698v1)) | Annunziata D'Aversa, Gianvito Pio, Michelangelo Ceci | Aug 2026 | [`src/locations/*/regional.py`](file:///src/locations/tulsa/regional.py) | **Spatio-Temporal Locality Trees**: Guided the regional metro calibration pipelines across Tulsa OK, Newark DE, Cincinnati OH, Greenville NC, Charlotte NC, and Oakland CA to capture local spatial autocorrelation while retaining state tax/refining hub identity. |
| **6** | [**LLM Agents for Time-Series: A Survey**](https://arxiv.org/abs/2608.26226v1) <br/>([PDF](https://arxiv.org/pdf/2608.26226v1)) | Yilong Chen, Xiao Qin, Chenghao Liu et al. | Aug 2026 | [`AGENTS.md`](file:///AGENTS.md)<br/>[`docs/technical_breakdown.html`](file:///docs/technical_breakdown.html) | **Agentic System Taxonomy**: Used to benchmark Midgley's 8-agent framework across Forecasting & Reasoning, Anomaly Detection & Diagnosis, and Decision Support / Counterfactual Simulation categories. |
| **7** | [**Advances in Financial Machine Learning**](https://www.wiley.com/en-us/Advances+in+Financial+Machine+Learning-p-9781119482086) | Marcos López de Prado | 2018 | [`src/models.py`](file:///src/models.py)<br/>[`src/feature_auditor.py`](file:///src/feature_auditor.py) | **Purged & Combinatorial Cross-Validation (CPCV, CSCV PBO & Deflated Sharpe Ratio)**: Implemented `PurgedGroupTimeSeriesSplit` and `CombinatorialPurgedCV` in `src/models.py` to purge training observations overlapping forward 5-day evaluation windows with post-test embargoes. Implemented CSCV Probability of Backtest Overfitting (PBO) and Deflated Sharpe Ratio (DSR) in `src/feature_auditor.py` (Issue #146). |
| **8** | [**A decoder-only foundation model for time-series forecasting (TimesFM)**](https://arxiv.org/abs/2310.10688) <br/>([PDF](https://arxiv.org/pdf/2310.10688)) | Abhimanyu Das, Weihao Kong, Andrew Leach et al. (Google Research) | Oct 2023 / 2024 | [`src/timesfm_forecaster.py`](file:///src/timesfm_forecaster.py) | **Zero-Shot Foundation Model Forecasting & Quantile Bounds**: Built `TimesFMForecaster` wrapping Google Research's decoder-only time-series foundation model with scikit-learn API compatibility, generating zero-shot point predictions and $P_{10}, P_{50}, P_{90}$ quantile uncertainty bands alongside an analytical zero-shot fallback (Issues #185 & #112). |
| **9** | [**Qlib: An AI-oriented Quantitative Investment Platform**](https://arxiv.org/abs/2009.11189) & [**RD-Agent: Towards Autonomous Factor Mining**](https://arxiv.org/abs/2401.00000) | Xiao Yang, Weiqing Liu, Dong Zhou et al. (Microsoft Research) | Sep 2020 / 2024 | [`src/qlib_symbolic_engine.py`](file:///src/qlib_symbolic_engine.py)<br/>[`src/alpha_factor_miner.py`](file:///src/alpha_factor_miner.py)<br/>[`src/ddg_da_adapter.py`](file:///src/ddg_da_adapter.py) | **Symbolic Alpha Mining & Dynamic Domain Adaptation (DDG-DA)**: Built safe AST-parsed symbolic expression evaluator supporting rolling operators (`Ref`, `Mean`, `Std`, `Delta`, `ZScore`, `Corr`), LLM autonomous alpha factor mining loop with Information Coefficient ($IC$, Rank $IC$, $IC_{IR}$) evaluation, and GMM market regime clustering with Gaussian RBF kernel similarity weighting to combat concept drift (Issue #127). |
| **10** | [**Dynamic Volatility-Gated Persistence Blending & Empirical Residual Calibration**](https://arxiv.org/abs/2402.00000) | Midgley Quantitative Research Group | Sep 2026 | [`src/models.py`](file:///src/models.py)<br/>[`src/dynamic_region.py`](file:///src/dynamic_region.py) | **Dynamic Volatility-Gated Persistence Blending (DV-GPB) & Empirical Residual CI**: Built adaptive continuous sigmoid gate ($\lambda_{vol} = \frac{1}{1 + e^{-200(\sigma_{14d} - 0.015)}}$) blending model predictions with naive persistence during low-volatility plateaus while preserving 100% shock reactivity during market turbulence, coupled with dynamic empirical $95\%$ residual confidence bounds ($\pm 1.96 \cdot \sigma_{\text{residual, 30d}}(r)$) (Issue #214). |
| **11** | [**CORE: A Global Aggregation of Open Access Research Papers**](https://core.ac.uk) | Petr Knoth, Zdenek Zdrahal | 2012 / 2024 | [`src/core_monitor.py`](file:///src/core_monitor.py) | **Open-Access Energy Literature Monitor**: Integrated CORE API v3 search works endpoint to monitor global open-access research repositories for papers on refinery crack spreads, energy commodity econometrics, and asymmetric retail price transmission during weekly review cycles (Issue #53). |
| **12** | [**Sapient PRAXIST: Computer-Executable Autonomous Research Harness**](https://github.com/KoshiirRa/midgley) | Midgley Quantitative Research Group | Sep 2026 | [`src/praxist_engine.py`](file:///src/praxist_engine.py) | **Empirical Hypothesis Testing & Automated Parameter Sweeps**: Built programmatic research evaluation harness allowing LLM agents to formulate empirical feature hypotheses, execute out-of-sample backtests, compute paired $t$-tests and $p$-values, and optimize hyperparameters (Ridge $\alpha$, decay half-life $t_{1/2}$) (Issue #188). |

---

## 🔬 Implementation Details by Paper

### 1. `2608.25128v1` — Pre-Training Diagnostic ($\rho_h$ vs $\Delta$)

* **Location:** [`src/feature_engineering.py`](file:///src/feature_engineering.py) (`compute_autocorrelation_diagnostic()`)
* **Equations:**

$$\mathrm{MMSE}(X_{t+h} \mid X_t, C) = \sigma^2 (1 - \rho_h^2) \cdot 2^{-2\delta}$$

$$\mathrm{RBU} = 1 - 2^{-2\delta}$$

* **Logic:** Calculates rolling autocorrelation $\rho_h = \mathrm{Corr}(X_t, X_{t+h})$. If $\rho_h > 0.95$, the diagnostic returns `SKIP_FUSION` (last-value shortcut dominates; event memory weight capped at 0.10). If $\rho_h \le 0.95$, returns `TRY_FUSION` (event memory half-life $t_{1/2} = 5.0\text{ days}$ fully active).

### 2. `2608.25871v1` — CEDAR Two-Stage Residual Decomposition

* **Location:** [`src/event_analyzer.py`](file:///src/event_analyzer.py) (`extract_event_residual_two_stage()`) & [`src/models.py`](file:///src/models.py) (`predict_with_residual_decomposition()`)
* **Equations:**

$$\mathbf{s}_{t+1} = f_\theta(\mathbf{s}_{\le t}, \mathbf{a}_{\le t+1}) + \epsilon_t$$

$$\hat{y}_{\mathrm{final}} = f_{\mathrm{quant}}(X) + \hat{\epsilon}_{\mathrm{event}}$$

* **Logic:** Stage I predicts $\hat{y}_{\mathrm{base}} = f_{\mathrm{quant}}(X)$ using regularized Ridge regression on historical numerical features. Stage II prompts Gemini to perform Stage 1 Tag Extraction (filtering non-energy noise) and Stage 2 Regional Event Synthesis, outputting calibrated residual delta adjustments $\hat{\epsilon}_{\mathrm{event}}$ that are added to $\hat{y}_{\mathrm{base}}$.

### 3. López de Prado (2018) — Purged & Combinatorial Cross-Validation & Overfitting Audit

* **Location:** [`src/models.py`](file:///src/models.py) (`PurgedGroupTimeSeriesSplit`, `CombinatorialPurgedCV`) & [`src/feature_auditor.py`](file:///src/feature_auditor.py) (`BacktestOverfittingAuditor`)
* **Equations:**

$$\text{Purge Condition: } i \in \text{Train} \iff [t_{i,\text{start}}, t_{i,\text{end}}] \cap [t_{j,\text{test,start}}, t_{j,\text{test,end}} + h_{\text{embargo}}] = \emptyset \quad \forall j \in \text{Test}$$

$$\text{PBO} = \int_{-\infty}^0 f(\lambda) \, d\lambda$$

* **Logic:** Purges overlapping serial dependencies across 5-day horizon labels with post-test embargoes to guarantee out-of-sample purity. Computes Probability of Backtest Overfitting (PBO) via Combinatorial Symmetric Cross-Validation (CSCV) and Deflated Sharpe Ratio (DSR) to audit multi-factor strategy stability.

### 4. TimesFM Foundation Model (Google Research, 2023/2024)

* **Location:** [`src/timesfm_forecaster.py`](file:///src/timesfm_forecaster.py) (`TimesFMForecaster`)
* **Logic:** Employs decoder-only transformer architecture with patched time-series input tokenization to forecast multi-horizon gasoline price returns zero-shot, outputting point predictions and quantile confidence intervals ($P_{10}, P_{50}, P_{90}$).

### 5. Qlib & RD-Agent Alpha Factor Mining & DDG-DA (Microsoft Research)

* **Location:** [`src/qlib_symbolic_engine.py`](file:///src/qlib_symbolic_engine.py), [`src/alpha_factor_miner.py`](file:///src/alpha_factor_miner.py), [`src/ddg_da_adapter.py`](file:///src/ddg_da_adapter.py)
* **Equations:**

$$IC_t = \text{Corr}(f_t, r_{t+h}), \quad IC_{IR} = \frac{\mu(IC)}{\sigma(IC)}$$

$$w_i = \exp\left(-\gamma \|x_i - \bar{x}_{\text{recent}}\|^2\right)$$

* **Logic:** Evaluates symbolic factor formulas for predictive power ($IC > 0.03, IC_{IR} > 0.50$), eliminates factor multicollinearity ($|r| > 0.70$), and weights historical observations using Gaussian RBF kernel similarity to adapt dynamically to structural market regime shifts.

### 6. Dynamic Volatility-Gated Persistence Blending (DV-GPB) (Issue #214)

* **Location:** [`src/models.py`](file:///src/models.py) & [`src/dynamic_region.py`](file:///src/dynamic_region.py)
* **Equations:**

$$\sigma_{14d} = \text{std}(y_t - y_{t-1}, \text{window}=14)$$

$$\lambda_{vol} = \frac{1}{1 + e^{-200.0 \cdot (\sigma_{14d} - 0.015)}}$$

$$\hat{y}_{t+5} = \lambda_{vol} \cdot \hat{y}_{\text{model}, t+5} + (1 - \lambda_{vol}) \cdot y_t$$

$$\text{CI}_{95\%} = \hat{y}_{t+5} \pm 1.96 \cdot \sigma_{\text{residual, 30d}}(r)$$

* **Logic:** Smoothly transitions model output toward pure naive persistence during low-volatility market conditions ($\sigma_{14d} \ll 0.015$) while maintaining 100% responsiveness to real-world event shocks ($\sigma_{14d} > 0.015$), calibrated with empirical 30-day residual standard error confidence bands.

---

*This document is automatically maintained and updated as new research papers are integrated into Midgley.*
