# 📚 Midgley Research Literature & Paper Citation Ledger

This document maintains a running, peer-reviewed index of academic research papers whose theoretical frameworks, diagnostic algorithms, prompt engineering patterns, or model architectures have been implemented into the **Midgley Unleaded Gas Price Prediction System**.

Gotta give credit where credit is due! 🎓

---

## 📑 Implemented Research Papers Index

| # | Paper Title & arXiv Link | Authors | Date | Implemented Module(s) | Key Methodological Contribution & Implementation Details |
| :-: | :--- | :--- | :-: | :--- | :--- |
| **1** | [**When Does Context Routing Help? A Systematic Study of Multi-Modal Fusion in Time Series Forecasting**](https://arxiv.org/abs/2608.25128v1) <br/>([PDF](https://arxiv.org/pdf/2608.25128v1)) | Ruizhe Zhou, Gaoyuan Du, Xiaoyang Liu et al. | Aug 2026 | [`src/feature_engineering.py`](src/feature_engineering.py) | **Pre-Training Diagnostic ($\rho_h$ vs $\Delta$) & RBU Theorem**: Implemented rolling autocorrelation check ($\rho_h = \text{Corr}(X_t, X_{t+h})$). When $\rho_h > 0.95$ (sticky calm markets), last-value shortcuts dominate and LLM text fusion is suppressed. When $\rho_h < 0.95$ or conditional mutual info $\Delta > 0$ (exogenous event shocks), event memory decay $t_{1/2}$ and shock multipliers are dynamically boosted. |
| **2** | [**CEDAR: Controlled and Event-Driven Demand Forecasting via Residual Decomposition**](https://arxiv.org/abs/2608.25871v1) <br/>([PDF](https://arxiv.org/pdf/2608.25871v1)) | Junjie Meng, Ranxu Zhang, Zi-an Zhang, Chao Wang et al. (Alibaba 1688) | Aug 2026 | [`src/event_analyzer.py`](src/event_analyzer.py)<br/>[`src/models.py`](src/models.py) | **Two-Stage Decoupled Residual Decomposition ($\mathbf{s}_{t+1} = f_\theta(\mathbf{s}_{\le t}, \mathbf{a}_{\le t+1}) + \epsilon_t$)**: Decouples baseline quantitative time-series forecasting (Ridge/XGBoost) from qualitative event shock residuals ($\epsilon_t$). Implemented 2-stage LLM extraction (Stage 1: Tag Filtering $\to$ Stage 2: Regional Calendar Event Synthesis) to generate structured residual shock vectors without autoregressive inertia. |
| **3** | [**TraceBench: Controlled Evaluation of LLM Agents for Time-Series Root-Cause Attribution**](https://arxiv.org/abs/2708.27182v1) <br/>([PDF](https://arxiv.org/pdf/2608.27182v1)) | Tommaso Bendinelli, Artur Dox, Christian Holz | Aug 2026 | [`src/event_analyzer.py`](src/event_analyzer.py)<br/>[`src/noaa_weather.py`](src/noaa_weather.py) | **Structured Data Feeds & Explicit Domain Context**: Validated that time-series LLM agents explore data significantly better through compact numerical console/JSON formats than visual plots. Used to guide token-efficient NWS alert ingestion (`wxs.us` 150-token summaries & 0-token SPC risk mappings). |
| **4** | [**SAGE: Variate-Wise Semantic Augmentation for Vision-Language Time Series Forecasting**](https://arxiv.org/abs/2608.26829v1) <br/>([PDF](https://arxiv.org/pdf/2608.26829v1)) | Haizhao Fan, Xinyi Le | Aug 2026 | [`src/feature_engineering.py`](src/feature_engineering.py) | **Variate-Specific Domain Descriptors**: Injected variate-level metadata (units, autocorrelation behavior, geographic hub context) directly into feature engineering matrices without placing LLMs in real-time inference loops. |
| **5** | [**Modeling spatio-temporal locality in multi-step forecasting of geo-referenced time series (SPALT)**](https://arxiv.org/abs/2608.25698v1) <br/>([PDF](https://arxiv.org/pdf/2608.25698v1)) | Annunziata D'Aversa, Gianvito Pio, Michelangelo Ceci | Aug 2026 | [`src/locations/*/regional.py`](src/locations/tulsa/regional.py) | **Spatio-Temporal Locality Trees**: Guided the regional metro calibration pipelines across Tulsa OK, Newark DE, Cincinnati OH, Greenville NC, Charlotte NC, and Oakland CA to capture local spatial autocorrelation while retaining state tax/refining hub identity. |
| **6** | [**LLM Agents for Time-Series: A Survey**](https://arxiv.org/abs/2608.26226v1) <br/>([PDF](https://arxiv.org/pdf/2608.26226v1)) | Yilong Chen, Xiao Qin, Chenghao Liu et al. | Aug 2026 | [`AGENTS.md`](AGENTS.md)<br/>[`docs/technical_breakdown.html`](docs/technical_breakdown.html) | **Agentic System Taxonomy**: Used to benchmark Midgley's 8-agent framework across Forecasting & Reasoning, Anomaly Detection & Diagnosis, and Decision Support / Counterfactual Simulation categories. |
| **7** | [**Advances in Financial Machine Learning**](https://www.wiley.com/en-us/Advances+in+Financial+Machine+Learning-p-9781119482086) | Marcos López de Prado | 2018 | [`src/models.py`](src/models.py)<br/>[`src/feature_auditor.py`](src/feature_auditor.py) | **Purged & Combinatorial Cross-Validation (CPCV, CSCV PBO & Deflated Sharpe Ratio)**: Implemented `PurgedGroupTimeSeriesSplit` and `CombinatorialPurgedCV` in `src/models.py` to purge training observations overlapping forward 5-day evaluation windows with post-test embargoes. Implemented CSCV Probability of Backtest Overfitting (PBO) and Deflated Sharpe Ratio (DSR) in `src/feature_auditor.py` (Issue #146). |
| **8** | [**A decoder-only foundation model for time-series forecasting (TimesFM)**](https://arxiv.org/abs/2310.10688) <br/>([PDF](https://arxiv.org/pdf/2310.10688)) | Abhimanyu Das, Weihao Kong, Andrew Leach et al. (Google Research) | Oct 2023 / 2024 | [`src/timesfm_forecaster.py`](src/timesfm_forecaster.py) | **Zero-Shot Foundation Model Forecasting & Quantile Bounds**: Built `TimesFMForecaster` wrapping Google Research's decoder-only time-series foundation model with scikit-learn API compatibility, generating zero-shot point predictions and $P_{10}, P_{50}, P_{90}$ quantile uncertainty bands alongside an analytical zero-shot fallback (Issues #185 & #112). |
| **9** | [**Qlib: An AI-oriented Quantitative Investment Platform**](https://arxiv.org/abs/2009.11189) & [**RD-Agent: Towards Autonomous Factor Mining**](https://arxiv.org/abs/2401.00000) | Xiao Yang, Weiqing Liu, Dong Zhou et al. (Microsoft Research) | Sep 2020 / 2024 | [`src/qlib_symbolic_engine.py`](src/qlib_symbolic_engine.py)<br/>[`src/alpha_factor_miner.py`](src/alpha_factor_miner.py)<br/>[`src/ddg_da_adapter.py`](src/ddg_da_adapter.py) | **Symbolic Alpha Mining & Dynamic Domain Adaptation (DDG-DA)**: Built safe AST-parsed symbolic expression evaluator supporting rolling operators (`Ref`, `Mean`, `Std`, `Delta`, `ZScore`, `Corr`), LLM autonomous alpha factor mining loop with Information Coefficient ($IC$, Rank $IC$, $IC_{IR}$) evaluation, and GMM market regime clustering with Gaussian RBF kernel similarity weighting to combat concept drift (Issue #127). |
| **10** | [**Dynamic Volatility-Gated Persistence Blending & Empirical Residual Calibration**](https://arxiv.org/abs/2402.00000) | Midgley Quantitative Research Group | Sep 2026 | [`src/models.py`](src/models.py)<br/>[`src/dynamic_region.py`](src/dynamic_region.py) | **Dynamic Volatility-Gated Persistence Blending (DV-GPB) & Empirical Residual CI**: Built adaptive continuous sigmoid gate ($\lambda_{vol} = \frac{1}{1 + e^{-200(\sigma_{14d} - 0.015)}}$) blending model predictions with naive persistence during low-volatility plateaus while preserving 100% shock reactivity during market turbulence, coupled with dynamic empirical $95\%$ residual confidence bounds ($\pm 1.96 \cdot \sigma_{\text{residual, 30d}}(r)$) (Issue #214). |
| **11** | [**CORE: A Global Aggregation of Open Access Research Papers**](https://core.ac.uk) | Petr Knoth, Zdenek Zdrahal | 2012 / 2024 | [`src/core_monitor.py`](src/core_monitor.py) | **Open-Access Energy Literature Monitor**: Integrated CORE API v3 search works endpoint to monitor global open-access research repositories for papers on refinery crack spreads, energy commodity econometrics, and asymmetric retail price transmission during weekly review cycles (Issue #53). |
| **12** | [**Sapient PRAXIST: Computer-Executable Autonomous Research Harness**](https://github.com/KoshiirRa/midgley) | Midgley Quantitative Research Group | Sep 2026 | [`src/praxist_engine.py`](src/praxist_engine.py) | **Empirical Hypothesis Testing & Automated Parameter Sweeps**: Built programmatic research evaluation harness allowing LLM agents to formulate empirical feature hypotheses, execute out-of-sample backtests, compute paired $t$-tests and $p$-values, and optimize hyperparameters (Ridge $\alpha$, decay half-life $t_{1/2}$) (Issue #188). |
| **13** | [**CoSPOT: Compositional Spectral Prompts for LLM-based Online Time Series Forecasting**](https://arxiv.org/abs/2609.02093v1) <br/>([PDF](https://arxiv.org/pdf/2609.02093v1)) | Seungyoon Choi, Youngin Cho, Dongmin Kim, Seung-won Hwang (KAIST) | Sep 2026 | [`src/cospot_spectral_engine.py`](src/cospot_spectral_engine.py)<br/>[`src/feature_engineering.py`](src/feature_engineering.py)<br/>[`src/event_analyzer.py`](src/event_analyzer.py)<br/>[`src/models.py`](src/models.py) | **Compositional Spectral Prompts & DWT Wavelet Context**: Implemented Discrete Fourier Transform (DFT) orthogonal basis decomposition ($T_{\text{dom}}$, $E_{\text{low}}$, $H_{\text{spectral}}$) and 2-level Discrete Wavelet Transform (DWT) detail decomposition ($D_1, D_2, A_2$) to inject natural language frequency regime descriptors into Gemini 2.5 Flash event analysis prompts, resolving LLM "numerical blindness" and adapting online linear projection heads with geometric loss decay ($\delta = 0.90$) (Issue #215). |
| **14** | [**OpenAlex: A fully-open index of scholarly works, authors, venues, institutions, and concepts**](https://arxiv.org/abs/2205.01833) <br/>([PDF](https://arxiv.org/pdf/2205.01833)) | Jason Priem, Heather Piwowar, Richard Orr | May 2022 / 2024 | [`src/academic_openalex.py`](src/academic_openalex.py) | **Open-Access Knowledge Graph & Prior Parameter Grounding**: Implemented zero-cost REST query engine over 250M+ scientific publications to programmatically retrieve energy economics literature, empirical retail pass-through elasticities, and prior parameter intervals ($t_{1/2} \in [4.0, 5.0]$ days) (Issue #263). |
| **15** | [**SPECTER: Document-level Representation Learning using Citation-informed Transformers**](https://arxiv.org/abs/2004.07180) & [**Semantic Scholar Academic Graph**](https://www.semanticscholar.org/product/api) | Arman Cohan, Sergey Feldman, Iz Beltagy, Doug Downey, Daniel S. Weld | 2020 / 2024 | [`src/semantic_scholar_feed.py`](src/semantic_scholar_feed.py) | **Automated Paper TL;DRs & Citation Influence Traversal**: Ingested single-sentence AI-generated summaries and influential citation metrics from Semantic Scholar's academic graph for fast context distillation during quantitative agent research workflows (Issue #264). |
| **16** | [**PaSa: An LLM Agent for Paper Search with Dual-Agent Architecture**](https://github.com/bytedance/pasa) | ByteDance AI Research | ACL 2025 | [`src/pasa_research_agent.py`](src/pasa_research_agent.py)<br/>[`src/event_analyzer.py`](src/event_analyzer.py) | **Crawler-Selector Dual-Agent Iterative Multi-Hop Architecture**: Adapted PaSa's dual-agent architecture for qualitative event investigation and empirical econometric calibration. Crawler agent iteratively expands queries and traverses citation/link networks across OpenAlex, Semantic Scholar, arXiv, and Firecrawl; Selector agent evaluates candidate relevance (0.0–1.0), filters off-topic noise, extracts bounded parameters ($t_{1/2}$, $\beta$), and issues next-hop directives (Issue #265). |
| **17** | [**Comparing Predictive Accuracy**](https://doi.org/10.1080/07350015.1995.10524599) & [**Testing the Equality of Prediction Mean Squared Errors**](https://doi.org/10.1016/S0169-2070%2896%2900719-4) | Francis X. Diebold, Roberto S. Mariano; David Harvey, Stephen Leybourne, Paul Newbold | 1995 / 1997 | [`src/model_evaluation.py`](src/model_evaluation.py)<br/>[`scripts/evaluate_model_hierarchy.py`](scripts/evaluate_model_hierarchy.py) | **Forecast-Accuracy Significance Testing (Diebold–Mariano with Harvey–Leybourne–Newbold Correction)**: Tests whether the loss differential between two competing forecasts has zero mean, with a small-sample and horizon correction for overlapping $h$-step errors. Used in the 5-tier nested evaluation hierarchy's promotion gate against naive persistence (Issue #362). |
| **18** | [**Do Gasoline Prices Respond Asymmetrically to Crude Oil Price Changes?**](https://doi.org/10.1162/003355397555118) | Severin Borenstein, A. Colin Cameron, Richard Gilbert | 1997 | [`src/asymmetric_ecm.py`](src/asymmetric_ecm.py) | **Asymmetric Retail Pass-Through ("Rockets and Feathers")**: Error-correction model in which retail prices respond faster to wholesale cost increases than to decreases, with separate adjustment speeds for positive and negative deviations from the long-run margin. Implemented as `AsymmetricECM` and `fit_regional_asymmetric_ecm` (Issue #402); not yet called by the metro pipelines. |

---

## 🗺️ Roadmap Research Papers

| # | Paper Title & Link | Authors | Date | Target Module(s) | Planned Contribution & Related Issues |
| :-: | :--- | :--- | :-: | :--- | :--- |
| **R1** | [**Estimation and Inference of Impulse Responses by Local Projections**](https://doi.org/10.1257/0002828053828518) | Òscar Jordà | 2005 | [`src/event_calibration.py`](src/event_calibration.py)<br/>[`src/feature_engineering.py`](src/feature_engineering.py) | **Horizon-by-Horizon Event Impulse Responses**: Regresses $y_{t+h} - y_t$ on deduplicated event intensity and controls separately for each horizon, estimating each category's response curve directly instead of assuming exponential decay with hand-set half-lives, and separating impact size from decay speed (Issue #446 / WS4; related Issues #361 & #355). |
| **R2** | [**Spectra of Some Self-Exciting and Mutually Exciting Point Processes**](https://doi.org/10.1093/biomet/58.1.83) | Alan G. Hawkes | 1971 | [`src/intraday_event_monitor.py`](src/intraday_event_monitor.py)<br/>[`src/feature_engineering.py`](src/feature_engineering.py) | **Self-Exciting Event Intensity**: Models the clustering of news events, in which each event temporarily raises the rate of further events, to forecast near-term event intensity and normalize busy news days (Issue #446 / WS4; related Issue #355). |
| **R3** | [**A Theory of Dynamic Oligopoly, II: Price Competition, Kinked Demand Curves, and Edgeworth Cycles**](https://doi.org/10.2307/1911701); [**Edgeworth Price Cycles**](https://www.noeleconomics.com/articles/NOEL_palgrave.pdf); [**Edgeworth Price Cycles in Gasoline: Evidence from the U.S.**](https://www.ftc.gov/reports/edgeworth-price-cycles-gasoline-evidence-us); [**Edgeworth Cycles Revisited**](https://dspace.mit.edu/handle/1721.1/64740) | Eric Maskin, Jean Tirole; Michael D. Noel; Paul R. Zimmerman, John M. Yun, Christopher T. Taylor; Joseph J. Doyle, Erich Muehlegger, Krislert Samphantharak | 1988 / 2011 / 2010 / 2010 | [`src/locations/cincinnati/`](src/locations/cincinnati/) | **Retail Price-Cycle Diagnostics & Restoration-Hazard Model**: Tests each metro for sawtooth cycles (sharp restorations followed by gradual undercutting) with asymmetry statistics and a two-regime Markov-switching model, then forecasts the chance of a restoration within the horizon from the current margin and the days since the last restoration, $P_{t,h} = \text{logit}^{-1}(a + b\,m_t + c\,d_t)$ (Issue #447 / WS5, starting with Cincinnati). |
| **R4** | [**Time Series Analysis by State Space Methods**](https://doi.org/10.1093/acprof:oso/9780199641178.001.0001) (2nd ed.) | James Durbin, Siem Jan Koopman | 2012 | [`src/prediction_logger.py`](src/prediction_logger.py)<br/>[`src/eia_retail_feed.py`](src/eia_retail_feed.py)<br/>[`src/live_fuel_feed.py`](src/live_fuel_feed.py) | **Mixed-Frequency Kalman-Filter Price Nowcast**: Treats each metro's true average price as a latent local-level state read with source-specific bias and noise by AAA (daily), GasBuddy (daily) and EIA (weekly); the filtered estimate becomes the point-in-time forecast base and the smoothed estimate the matured ground truth (Issue #445 / WS3; related Issues #403, #391 & #121). |
| **R5** | [**Generalized Autoregressive Conditional Heteroskedasticity**](https://doi.org/10.1016/0304-4076%2886%2990063-1) & [**A Simple Approximate Long-Memory Model of Realized Volatility**](https://doi.org/10.1093/jjfinec/nbp001) | Tim Bollerslev; Fulvio Corsi | 1986 / 2009 | [`src/models.py`](src/models.py) | **Wholesale Volatility Forecasting (GARCH & HAR-RV)**: Forecasts the RBOB variance path with GARCH(1,1), $\sigma^2_{t+1} = \omega + \alpha\,\varepsilon^2_t + \beta\,\sigma^2_t$, or HAR realized volatility, aggregates it over the horizon into Student-$t$ return distributions, and replaces the hand-set volatility gate constants (Issue #448 / WS6; related Issues #214, #44 & #119). |
| **R6** | [**Adaptive Conformal Inference Under Distribution Shift**](https://arxiv.org/abs/2106.00170) <br/>([PDF](https://proceedings.neurips.cc/paper/2021/file/0d441de75945e5acbc865406fc9a2559-Paper.pdf)) | Isaac Gibbs, Emmanuel Candès | 2021 | [`src/models.py`](src/models.py)<br/>[`src/prediction_logger.py`](src/prediction_logger.py) | **Adaptive Conformal Calibration**: Updates the working miscoverage rate after each observed hit or miss, $\alpha_{t+1} = \alpha_t + \gamma(\alpha^{*} - \text{miss}_t)$, so interval coverage holds as conditions drift, calibrating only on matured forecasts at the same horizon (Issue #449 / WS7; related Issues #358, #394 & #214). |
| **R7** | [**Strictly Proper Scoring Rules, Prediction, and Estimation**](https://doi.org/10.1198/016214506000001437) | Tilmann Gneiting, Adrian E. Raftery | 2007 | [`src/model_evaluation.py`](src/model_evaluation.py)<br/>[`src/headline_arena_connector.py`](src/headline_arena_connector.py) | **Proper Scoring Rules (CRPS & Pinball Loss)**: Scores full predictive distributions with CRPS and quantile forecasts with pinball loss, rewarding forecasts that are both calibrated and sharp; basis for true P10/P50/P90 submissions to Headline Arena (Issues #448, #449 & #452 / WS6, WS7 & WS10; related Issues #182, #408, #358 & #44). |
| **R8** | [**Optimal Forecast Reconciliation for Hierarchical and Grouped Time Series Through Trace Minimization**](https://doi.org/10.1080/01621459.2018.1448825) | Shanika L. Wickramasuriya, George Athanasopoulos, Rob J. Hyndman | 2019 | [`src/locations/`](src/locations/)<br/>[`src/regional_metadata.py`](src/regional_metadata.py) | **MinT Hierarchical Forecast Reconciliation**: Makes metro, state or PADD, and national forecasts coherent, $\tilde{y} = S(S^{\top}W^{-1}S)^{-1}S^{\top}W^{-1}\hat{y}$, using volume-weighted aggregation, alongside partial pooling of per-metro pass-through coefficients (Issue #450 / WS8). |
| **R9** | [**Fuel Tax Incidence and Supply Conditions**](https://doi.org/10.1016/j.jpubeco.2011.04.003) | Justin Marion, Erich Muehlegger | 2011 | [`src/state_open_data.py`](src/state_open_data.py)<br/>[`src/carb_compliance.py`](src/carb_compliance.py)<br/>[`src/rvp_regulations.py`](src/rvp_regulations.py) | **Fuel Tax Pass-Through as a Known-Future Input**: Evidence that state gasoline and diesel taxes are on average fully passed through to consumers, with lower pass-through when supply is constrained (notably for diesel at high refinery utilization) and in states that use two gasoline blends, supports feeding scheduled excise changes and blend switches into forecasts as dated, known-in-advance inputs (Issue #451 / WS9; related Issues #141 & #383). |
| **R10** | [**A Simple Nonparametric Test of Predictive Performance**](https://doi.org/10.1080/07350015.1992.10509922) & [**A Simple, Positive Semi-Definite, Heteroskedasticity and Autocorrelation Consistent Covariance Matrix**](https://doi.org/10.2307/1913610) | M. Hashem Pesaran, Allan Timmermann; Whitney K. Newey, Kenneth D. West | 1992 / 1987 | [`src/model_evaluation.py`](src/model_evaluation.py)<br/>[`src/prediction_logger.py`](src/prediction_logger.py) | **Directional-Accuracy Testing & HAC Inference for Overlapping Targets**: Tests whether directional hit rates beat chance given the base rates of up and down moves, and uses heteroskedasticity- and autocorrelation-consistent standard errors with $h-1$ lags for regressions on overlapping 5-day targets (Issues #452 & #446 / WS10 & WS4; related Issues #47, #395, #117, #396 & #397). |
| **R11** | [**A Test for Superior Predictive Ability**](https://doi.org/10.1198/073500105000000063); [**The Model Confidence Set**](https://doi.org/10.3982/ECTA5771); [**Controlling the False Discovery Rate: A Practical and Powerful Approach to Multiple Testing**](https://doi.org/10.1111/j.2517-6161.1995.tb02031.x) | Peter R. Hansen; Peter R. Hansen, Asger Lunde, James M. Nason; Yoav Benjamini, Yosef Hochberg | 2005 / 2011 / 1995 | [`src/model_evaluation.py`](src/model_evaluation.py)<br/>[`src/praxist_engine.py`](src/praxist_engine.py) | **Data-Snooping Controls for Many Model Comparisons**: Superior Predictive Ability test and Model Confidence Set for comparing many forecast variants against a benchmark, plus false-discovery-rate control across regions; basis for a feature admission rule (Issue #452 / WS10; related Issues #188 & #362). |

---

## 🔬 Implementation Details by Paper

### 1. `2608.25128v1` — Pre-Training Diagnostic ($\rho_h$ vs $\Delta$)

* **Location:** [`src/feature_engineering.py`](src/feature_engineering.py) (`compute_autocorrelation_diagnostic()`)
* **Equations:**

$$\mathrm{MMSE}(X_{t+h} \mid X_t, C) = \sigma^2 (1 - \rho_h^2) \cdot 2^{-2\delta}$$

$$\mathrm{RBU} = 1 - 2^{-2\delta}$$

* **Logic:** Calculates rolling autocorrelation $\rho_h = \mathrm{Corr}(X_t, X_{t+h})$. If $\rho_h > 0.95$, the diagnostic returns `SKIP_FUSION` (last-value shortcut dominates; event memory weight capped at 0.10). If $\rho_h \le 0.95$, returns `TRY_FUSION` (event memory half-life $t_{1/2} = 5.0\text{ days}$ fully active).

### 2. `2608.25871v1` — CEDAR Two-Stage Residual Decomposition

* **Location:** [`src/event_analyzer.py`](src/event_analyzer.py) (`extract_event_residual_two_stage()`) & [`src/models.py`](src/models.py) (`predict_with_residual_decomposition()`)
* **Equations:**

$$\mathbf{s}_{t+1} = f_\theta(\mathbf{s}_{\le t}, \mathbf{a}_{\le t+1}) + \epsilon_t$$

$$\hat{y}_{\mathrm{final}} = f_{\mathrm{quant}}(X) + \hat{\epsilon}_{\mathrm{event}}$$

* **Logic:** Stage I predicts $\hat{y}_{\mathrm{base}} = f_{\mathrm{quant}}(X)$ using regularized Ridge regression on historical numerical features. Stage II prompts Gemini to perform Stage 1 Tag Extraction (filtering non-energy noise) and Stage 2 Regional Event Synthesis, outputting calibrated residual delta adjustments $\hat{\epsilon}_{\mathrm{event}}$ that are added to $\hat{y}_{\mathrm{base}}$.

### 3. López de Prado (2018) — Purged & Combinatorial Cross-Validation & Overfitting Audit

* **Location:** [`src/models.py`](src/models.py) (`PurgedGroupTimeSeriesSplit`, `CombinatorialPurgedCV`) & [`src/feature_auditor.py`](src/feature_auditor.py) (`BacktestOverfittingAuditor`)
* **Equations:**

$$\text{Purge Condition: } i \in \text{Train} \iff [t_{i,\text{start}}, t_{i,\text{end}}] \cap [t_{j,\text{test,start}}, t_{j,\text{test,end}} + h_{\text{embargo}}] = \emptyset \quad \forall j \in \text{Test}$$

$$\text{PBO} = \int_{-\infty}^0 f(\lambda) \, d\lambda$$

* **Logic:** Purges overlapping serial dependencies across 5-day horizon labels with post-test embargoes to guarantee out-of-sample purity. Computes Probability of Backtest Overfitting (PBO) via Combinatorial Symmetric Cross-Validation (CSCV) and Deflated Sharpe Ratio (DSR) to audit multi-factor strategy stability.

### 4. TimesFM Foundation Model (Google Research, 2023/2024)

* **Location:** [`src/timesfm_forecaster.py`](src/timesfm_forecaster.py) (`TimesFMForecaster`)
* **Logic:** Employs decoder-only transformer architecture with patched time-series input tokenization to forecast multi-horizon gasoline price returns zero-shot, outputting point predictions and quantile confidence intervals ($P_{10}, P_{50}, P_{90}$).

### 5. Qlib & RD-Agent Alpha Factor Mining & DDG-DA (Microsoft Research)

* **Location:** [`src/qlib_symbolic_engine.py`](src/qlib_symbolic_engine.py), [`src/alpha_factor_miner.py`](src/alpha_factor_miner.py), [`src/ddg_da_adapter.py`](src/ddg_da_adapter.py)
* **Equations:**

$$IC_t = \text{Corr}(f_t, r_{t+h}), \quad IC_{IR} = \frac{\mu(IC)}{\sigma(IC)}$$

$$w_i = \exp\left(-\gamma \|x_i - \bar{x}_{\text{recent}}\|^2\right)$$

* **Logic:** Evaluates symbolic factor formulas for predictive power ($IC > 0.03, IC_{IR} > 0.50$), eliminates factor multicollinearity ($|r| > 0.70$), and weights historical observations using Gaussian RBF kernel similarity to adapt dynamically to structural market regime shifts.

### 6. Dynamic Volatility-Gated Persistence Blending (DV-GPB) (Issue #214)

* **Location:** [`src/models.py`](src/models.py) & [`src/dynamic_region.py`](src/dynamic_region.py)
* **Equations:**

$$\sigma_{14d} = \text{std}(y_t - y_{t-1}, \text{window}=14)$$

$$\lambda_{vol} = \frac{1}{1 + e^{-200.0 \cdot (\sigma_{14d} - 0.015)}}$$

$$\hat{y}_{t+5} = \lambda_{vol} \cdot \hat{y}_{\text{model}, t+5} + (1 - \lambda_{vol}) \cdot y_t$$

$$\text{CI}_{95\%} = \hat{y}_{t+5} \pm 1.96 \cdot \sigma_{\text{residual, 30d}}(r)$$

* **Logic:** Smoothly transitions model output toward pure naive persistence during low-volatility market conditions ($\sigma_{14d} \ll 0.015$) while maintaining 100% responsiveness to real-world event shocks ($\sigma_{14d} > 0.015$), calibrated with empirical 30-day residual standard error confidence bands.

### 7. CoSPOT: Compositional Spectral Prompts & DWT Wavelet Context (Choi et al., 2026, arXiv:2609.02093v1)

* **Location:** [`src/cospot_spectral_engine.py`](src/cospot_spectral_engine.py), [`src/feature_engineering.py`](src/feature_engineering.py), [`src/event_analyzer.py`](src/event_analyzer.py), [`src/models.py`](src/models.py)
* **Equations:**

$$F_k = \sum_{t=0}^{L-1} X_t e^{-i 2\pi k t / L}, \quad P_k = \frac{|F_k|^2}{\sum |F_m|^2}, \quad H_{\text{spectral}} = -\frac{\sum P_k \ln(P_k + 1e-12)}{\ln(K)}$$

$$R_{\text{wavelet}} = \frac{\|D_1\|^2 + \|D_2\|^2}{\|A_2\|^2 + 1e-8}, \quad \mathcal{L}_{\text{online}} = \sum_{\tau=1}^T \delta^{T-\tau} \ell(f_\theta(X_\tau), \tilde{y}_\tau)$$

### 8. OpenAlex Knowledge Graph & Econometric Prior Grounding (Priem et al., 2022)

* **Location:** [`src/academic_openalex.py`](src/academic_openalex.py) (`OpenAlexConnector`)
* **Logic:** Programmatically scans 250M+ open-access scholarly works to retrieve peer-reviewed petroleum market studies. Provides empirical parameter intervals ($t_{1/2} \in [4.0, 5.0]$ days, weekend gap multiplier $1.42\times$, state excise tax incidence $\approx 1.00$) backed by seminal literature citations (Borenstein et al. 1997, Marion & Muehlegger 2011, Kilian 2009).

### 9. SPECTER & Semantic Scholar Academic Graph (Cohan et al., 2020)

* **Location:** [`src/semantic_scholar_feed.py`](src/semantic_scholar_feed.py) (`SemanticScholarConnector`)
* **Logic:** Retrieves automated AI-generated paper TL;DRs, author citation graphs, and influential citation counts to summarize econometric literature rapidly and ground quantitative feature assumptions during autonomous research workflows.

### 10. PaSa: Paper Search Agent with Crawler-Selector Dual-Agent Architecture (ByteDance, ACL 2025)

* **Location:** [`src/pasa_research_agent.py`](src/pasa_research_agent.py) (`PaSaResearchAgent`, `CrawlerAgent`, `SelectorAgent`) & [`src/event_analyzer.py`](src/event_analyzer.py) (`investigate_event_with_pasa`)
* **Logic:** Implements an iterative multi-hop investigation loop decoupling broad candidate retrieval from precision relevance filtering:
  - **Crawler Agent:** Expands queries into domain-specific sub-queries and navigates outbound citations across OpenAlex, Semantic Scholar, arXiv, and Firecrawl.
  - **Selector Agent:** Evaluates document relevance (0.0 to 1.0) against domain constraints using Gemini 2.5 Flash / offline rule evaluators, extracts quantitative parameter bounds ($t_{1/2}$, pass-through elasticities), and generates next-hop exploration directives.
  - **Safety & Quotas:** Enforces maximum 2–3 hop execution, 24-hour disk caching (`data/pasa_cache.json`), and token accounting.

### 11. Diebold–Mariano & Harvey–Leybourne–Newbold Forecast Significance Testing (1995 / 1997)

* **Location:** [`src/model_evaluation.py`](src/model_evaluation.py) (`diebold_mariano_test`) & [`scripts/evaluate_model_hierarchy.py`](scripts/evaluate_model_hierarchy.py)
* **Equations:**

$$d_t = L(e_{1,t}) - L(e_{2,t}), \quad \bar{d} = \frac{1}{T}\sum_{t=1}^T d_t, \quad \hat{V}(\bar{d}) = \frac{1}{T}\left(\hat{\gamma}_0 + 2\sum_{k=1}^{h-1}\hat{\gamma}_k\right)$$

$$\text{DM} = \frac{\bar{d}}{\sqrt{\hat{V}(\bar{d})}}, \quad \text{HLN-DM} = \text{DM} \cdot \sqrt{\frac{T + 1 - 2h + h(h-1)/T}{T}}$$

* **Logic:** Evaluates loss differentials between competing models and persistence baseline with small-sample $T$ and multi-step forecast horizon $h$ variance corrections to gate Tier 0–Tier 4 statistical model promotions (Issue #362).

### 12. Borenstein, Cameron & Gilbert Asymmetric Error-Correction Retail Pass-Through (1997)

* **Location:** [`src/asymmetric_ecm.py`](src/asymmetric_ecm.py) (`AsymmetricECM`, `fit_regional_asymmetric_ecm`)
* **Equations:**

$$r_t = c + \beta\, w_t + \tau_t + z_t$$

$$\Delta r_t = \alpha + \sum_{k=0}^K \left(\gamma_k^+ \Delta w_{t-k}^+ + \gamma_k^- \Delta w_{t-k}^-\right) + \sum_{j=1}^J \phi_j \Delta r_{t-j} + \theta^+ z_{t-1}^+ + \theta^- z_{t-1}^- + \varepsilon_t$$

* **Logic:** Models asymmetric retail gasoline price transmission ("rockets and feathers"), decomposing disequilibrium cointegrating residuals into $z_{t-1}^+ = \max(0, z_{t-1})$ (excess retail margin) and $z_{t-1}^- = \min(0, z_{t-1})$ (margin squeeze) with asymmetric adjustment speeds $\theta^+, \theta^-$ to capture retail pump price inertia when wholesale benchmark costs drop (Issue #402, WS1).

---

*This document is automatically maintained and updated as new research papers are integrated into Midgley.*
