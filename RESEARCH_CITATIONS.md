# 📚 Midgley Research Literature & Paper Citation Ledger

This document maintains a running, peer-reviewed index of academic research papers whose theoretical frameworks, diagnostic algorithms, prompt engineering patterns, or model architectures have been implemented into the **Midgley Unleaded Gas Price Prediction System**.

Gotta give credit where credit is due! 🎓

---

## 📑 Implemented Research Papers Index

| # | Paper Title & arXiv Link | Authors | Date | Implemented Module(s) | Key Methodological Contribution & Implementation Details |
| :-: | :--- | :--- | :-: | :--- | :--- |
| **1** | [**When Does Context Routing Help? A Systematic Study of Multi-Modal Fusion in Time Series Forecasting**](https://arxiv.org/abs/2608.25128v1) <br/>([PDF](https://arxiv.org/pdf/2608.25128v1)) | Ruizhe Zhou, Gaoyuan Du, Xiaoyang Liu et al. | Aug 2026 | [`src/feature_engineering.py`](file:///c:/Users/concentus/Documents/Random%20Ideas%20-%20LLM%20Unleaded%20Gas%20Price%20Prediction%20Modelling/src/feature_engineering.py) | **Pre-Training Diagnostic ($\rho_h$ vs $\Delta$) & RBU Theorem**: Implemented rolling autocorrelation check ($\rho_h = \text{Corr}(X_t, X_{t+h})$). When $\rho_h > 0.95$ (sticky calm markets), last-value shortcuts dominate and LLM text fusion is suppressed. When $\rho_h < 0.95$ or conditional mutual info $\Delta > 0$ (exogenous event shocks), event memory decay $t_{1/2}$ and shock multipliers are dynamically boosted. |
| **2** | [**CEDAR: Controlled and Event-Driven Demand Forecasting via Residual Decomposition**](https://arxiv.org/abs/2608.25871v1) <br/>([PDF](https://arxiv.org/pdf/2608.25871v1)) | Junjie Meng, Ranxu Zhang, Zi-an Zhang, Chao Wang et al. (Alibaba 1688) | Aug 2026 | [`src/event_analyzer.py`](file:///c:/Users/concentus/Documents/Random%20Ideas%20-%20LLM%20Unleaded%20Gas%20Price%20Prediction%20Modelling/src/event_analyzer.py)<br/>[`src/models.py`](file:///c:/Users/concentus/Documents/Random%20Ideas%20-%20LLM%20Unleaded%20Gas%20Price%20Prediction%20Modelling/src/models.py) | **Two-Stage Decoupled Residual Decomposition ($\mathbf{s}_{t+1} = f_\theta(\mathbf{s}_{\le t}, \mathbf{a}_{\le t+1}) + \epsilon_t$)**: Decouples baseline quantitative time-series forecasting (Ridge/XGBoost) from qualitative event shock residuals ($\epsilon_t$). Implemented 2-stage LLM extraction (Stage 1: Tag Filtering $\to$ Stage 2: Regional Calendar Event Synthesis) to generate structured residual shock vectors without autoregressive inertia. |
| **3** | [**TraceBench: Controlled Evaluation of LLM Agents for Time-Series Root-Cause Attribution**](https://arxiv.org/abs/2608.27182v1) <br/>([PDF](https://arxiv.org/pdf/2608.27182v1)) | Tommaso Bendinelli, Artur Dox, Christian Holz | Aug 2026 | [`src/event_analyzer.py`](file:///c:/Users/concentus/Documents/Random%20Ideas%20-%20LLM%20Unleaded%20Gas%20Price%20Prediction%20Modelling/src/event_analyzer.py)<br/>[`src/noaa_weather.py`](file:///c:/Users/concentus/Documents/Random%20Ideas%20-%20LLM%20Unleaded%20Gas%20Price%20Prediction%20Modelling/src/noaa_weather.py) | **Structured Data Feeds & Explicit Domain Context**: Validated that time-series LLM agents explore data significantly better through compact numerical console/JSON formats than visual plots. Used to guide token-efficient NWS alert ingestion (`wxs.us` 150-token summaries & 0-token SPC risk mappings). |
| **4** | [**SAGE: Variate-Wise Semantic Augmentation for Vision-Language Time Series Forecasting**](https://arxiv.org/abs/2608.26829v1) <br/>([PDF](https://arxiv.org/pdf/2608.26829v1)) | Haizhao Fan, Xinyi Le | Aug 2026 | [`src/feature_engineering.py`](file:///c:/Users/concentus/Documents/Random%20Ideas%20-%20LLM%20Unleaded%20Gas%20Price%20Prediction%20Modelling/src/feature_engineering.py) | **Variate-Specific Domain Descriptors**: Injected variate-level metadata (units, autocorrelation behavior, geographic hub context) directly into feature engineering matrices without placing LLMs in real-time inference loops. |
| **5** | [**Modeling spatio-temporal locality in multi-step forecasting of geo-referenced time series (SPALT)**](https://arxiv.org/abs/2608.25698v1) <br/>([PDF](https://arxiv.org/pdf/2608.25698v1)) | Annunziata D'Aversa, Gianvito Pio, Michelangelo Ceci | Aug 2026 | [`src/locations/*/regional.py`](file:///c:/Users/concentus/Documents/Random%20Ideas%20-%20LLM%20Unleaded%20Gas%20Price%20Prediction%20Modelling/src/locations/tulsa/regional.py) | **Spatio-Temporal Locality Trees**: Guided the regional metro calibration pipelines across Tulsa OK, Newark DE, Cincinnati OH, Greenville NC, Charlotte NC, and Oakland CA to capture local spatial autocorrelation while retaining state tax/refining hub identity. |
| **6** | [**LLM Agents for Time-Series: A Survey**](https://arxiv.org/abs/2608.26226v1) <br/>([PDF](https://arxiv.org/pdf/2608.26226v1)) | Yilong Chen, Xiao Qin, Chenghao Liu et al. | Aug 2026 | [`AGENTS.md`](file:///c:/Users/concentus/Documents/Random%20Ideas%20-%20LLM%20Unleaded%20Gas%20Price%20Prediction%20Modelling/AGENTS.md)<br/>[`docs/technical_breakdown.html`](file:///c:/Users/concentus/Documents/Random%20Ideas%20-%20LLM%20Unleaded%20Gas%20Price%20Prediction%20Modelling/docs/technical_breakdown.html) | **Agentic System Taxonomy**: Used to benchmark Midgley's 8-agent framework across Forecasting & Reasoning, Anomaly Detection & Diagnosis, and Decision Support / Counterfactual Simulation categories. |

---

## 🔬 Implementation Details by Paper

### 1. `2608.25128v1` — Pre-Training Diagnostic ($\rho_h$ vs $\Delta$)

* **Location:** [`src/feature_engineering.py`](file:///c:/Users/concentus/Documents/Random%20Ideas%20-%20LLM%20Unleaded%20Gas%20Price%20Prediction%20Modelling/src/feature_engineering.py) (`compute_autocorrelation_diagnostic()`)
* **Equations:**

$$\mathrm{MMSE}(X_{t+h} \mid X_t, C) = \sigma^2 (1 - \rho_h^2) \cdot 2^{-2\delta}$$

$$\mathrm{RBU} = 1 - 2^{-2\delta}$$

* **Logic:** Calculates rolling autocorrelation $\rho_h = \mathrm{Corr}(X_t, X_{t+h})$. If $\rho_h > 0.95$, the diagnostic returns `SKIP_FUSION` (last-value shortcut dominates; event memory weight capped at 0.10). If $\rho_h \le 0.95$, returns `TRY_FUSION` (event memory half-life $t_{1/2} = 5.0\text{ days}$ fully active).

### 2. `2608.25871v1` — CEDAR Two-Stage Residual Decomposition

* **Location:** [`src/event_analyzer.py`](file:///c:/Users/concentus/Documents/Random%20Ideas%20-%20LLM%20Unleaded%20Gas%20Price%20Prediction%20Modelling/src/event_analyzer.py) (`extract_event_residual_two_stage()`) & [`src/models.py`](file:///c:/Users/concentus/Documents/Random%20Ideas%20-%20LLM%20Unleaded%20Gas%20Price%20Prediction%20Modelling/src/models.py) (`predict_with_residual_decomposition()`)
* **Equations:**

$$\mathbf{s}_{t+1} = f_\theta(\mathbf{s}_{\le t}, \mathbf{a}_{\le t+1}) + \epsilon_t$$

$$\hat{y}_{\mathrm{final}} = f_{\mathrm{quant}}(X) + \hat{\epsilon}_{\mathrm{event}}$$

* **Logic:** Stage I predicts $\hat{y}_{\mathrm{base}} = f_{\mathrm{quant}}(X)$ using regularized Ridge regression on historical numerical features. Stage II prompts Gemini to perform Stage 1 Tag Extraction (filtering non-energy noise) and Stage 2 Regional Event Synthesis, outputting calibrated residual delta adjustments $\hat{\epsilon}_{\mathrm{event}}$ that are added to $\hat{y}_{\mathrm{base}}$.

---

*This document is automatically maintained and updated as new research papers are integrated into Midgley.*
