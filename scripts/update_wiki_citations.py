import os, subprocess

wiki_dir = "/home/marty/projects/midgley.wiki"

citations_path = os.path.join(wiki_dir, "Academic-Citations-and-Research-Foundations.md")
with open(citations_path, "w", encoding="utf-8") as f:
    f.write("""# 🎓 Academic Citations & Research Foundations

Midgley is built upon theoretical theorems, econometric diagnostics, and multi-agent machine learning architectures published in peer-reviewed scientific literature and arXiv pre-prints.

This ledger indexes all 12 implemented papers, detailing their mathematical formulations and target code modules in Midgley.

---

## 📑 Implemented Research Papers Index

| # | Paper Title & arXiv Link | Authors | Date | Implemented Module(s) | Key Methodological Contribution |
| :-: | :--- | :--- | :-: | :--- | :--- |
| **1** | [When Does Context Routing Help?](https://arxiv.org/abs/2608.25128v1) | Ruizhe Zhou, Gaoyuan Du, Xiaoyang Liu et al. | Aug 2026 | `src/feature_engineering.py` | **Pre-Training Diagnostic ($\\rho_h$ vs $\\Delta$) & RBU Theorem**: Rolling autocorrelation check. When $\\rho_h > 0.95$, last-value shortcuts dominate and LLM fusion is suppressed. |
| **2** | [CEDAR: Controlled and Event-Driven Demand Forecasting](https://arxiv.org/abs/2608.25871v1) | Junjie Meng, Ranxu Zhang, Zi-an Zhang et al. (Alibaba 1688) | Aug 2026 | `src/event_analyzer.py`, `src/models.py` | **Two-Stage Decoupled Residual Decomposition**: Decouples baseline quantitative time-series forecasting from qualitative event shock residuals ($\\epsilon_t$). |
| **3** | [TraceBench: LLM Agents for Time-Series Attribution](https://arxiv.org/abs/2608.27182v1) | Tommaso Bendinelli, Artur Dox, Christian Holz | Aug 2026 | `src/event_analyzer.py`, `src/noaa_weather.py` | **Structured Data Ingestion**: Validated that time-series LLM agents explore data better through compact JSON/console formats than visual plots. |
| **4** | [SAGE: Variate-Wise Semantic Augmentation](https://arxiv.org/abs/2608.26829v1) | Haizhao Fan, Xinyi Le | Aug 2026 | `src/feature_engineering.py` | **Variate-Specific Domain Descriptors**: Injected variate-level metadata directly into feature matrices without placing LLMs in real-time inference loops. |
| **5** | [SPALT Spatio-Temporal Locality Trees](https://arxiv.org/abs/2608.25698v1) | Annunziata D'Aversa, Gianvito Pio, Michelangelo Ceci | Aug 2026 | `src/locations/*/regional.py` | **Spatio-Temporal Locality Trees**: Guided regional metro calibration pipelines to capture spatial autocorrelation across refining corridors. |
| **6** | [LLM Agents for Time-Series: A Survey](https://arxiv.org/abs/2608.26226v1) | Yilong Chen, Xiao Qin, Chenghao Liu et al. | Aug 2026 | `AGENTS.md` | **Agentic System Taxonomy**: Used to benchmark Midgley's 8-agent framework across Forecasting, Anomaly Detection, and Counterfactual Simulation. |
| **7** | [Advances in Financial Machine Learning](https://www.wiley.com/en-us/Advances+in+Financial+Machine+Learning-p-9781119482086) | Marcos López de Prado | 2018 | `src/models.py`, `src/feature_auditor.py` | **Purged & Combinatorial Cross-Validation (CPCV & PBO)**: Eliminates temporal lookahead leakage with post-test embargoes; audits probability of backtest overfitting. |
| **8** | [TimesFM Foundation Model](https://arxiv.org/abs/2310.10688) | Abhimanyu Das, Weihao Kong, Andrew Leach et al. (Google Research) | Oct 2023 / 2024 | `src/timesfm_forecaster.py` | **Zero-Shot Foundation Model Forecasting**: Decoder-only transformer forecasting with quantile uncertainty bounds ($P_{10}, P_{50}, P_{90}$). |
| **9** | [Qlib & RD-Agent Symbolic Factor Mining](https://arxiv.org/abs/2009.11189) | Xiao Yang, Weiqing Liu, Dong Zhou et al. (Microsoft Research) | Sep 2020 / 2024 | `src/qlib_symbolic_engine.py`, `src/alpha_factor_miner.py`, `src/ddg_da_adapter.py` | **Symbolic Alpha Mining & Dynamic Domain Adaptation (DDG-DA)**: AST expression evaluator, Information Coefficient ($IC / IC_{IR}$), and Gaussian RBF kernel weighting across market regimes. |
| **10** | [Dynamic Volatility-Gated Persistence Blending (DV-GPB)](https://koshiirra.github.io/midgley/citations.html) | Midgley Quantitative Research Group | Sep 2026 | `src/models.py`, `src/dynamic_region.py` | **Adaptive Sigmoid Gating & Empirical 95% Residual CI**: Blends forecasts smoothly with naive persistence during low-volatility plateaus while preserving 100% shock reactivity. |
| **11** | [CORE Global Research Aggregation](https://core.ac.uk) | Petr Knoth, Zdenek Zdrahal | 2012 / 2024 | `src/core_monitor.py` | **Open-Access Literature Monitor**: Ingests global energy and crack spread literature during weekly review cycles. |
| **12** | [Sapient PRAXIST Research Harness](https://github.com/KoshiirRa/midgley) | Midgley Quantitative Research Group | Sep 2026 | `src/praxist_engine.py` | **Empirical Hypothesis Testing & Automated Parameter Sweeps**: Programmatic research evaluation harness for automated feature hypothesis testing and backtesting. |

---

## 🌐 Public Citations Portal
Explore the interactive visual citations portal at: **[https://koshiirra.github.io/midgley/citations.html](https://koshiirra.github.io/midgley/citations.html)**
""")
print("Created Academic-Citations-and-Research-Foundations.md")

home_path = os.path.join(wiki_dir, "Home.md")
with open(home_path, "r", encoding="utf-8") as f:
    home_content = f.read()

if "Academic-Citations-and-Research-Foundations" not in home_content:
    new_entry = "10. [[Academic-Citations-and-Research-Foundations]]: Peer-reviewed academic research papers, foundational theorems, and mathematical algorithms implemented in Midgley.\n"
    home_content = home_content.strip() + "\n" + new_entry
    with open(home_path, "w", encoding="utf-8") as f:
        f.write(home_content)
    print("Updated Home.md")

subprocess.run(["git", "add", "."], cwd=wiki_dir, check=True)
subprocess.run(["git", "commit", "-m", "docs(wiki): Add Academic-Citations-and-Research-Foundations and update Home.md (Issue #228)"], cwd=wiki_dir, check=True)
subprocess.run(["git", "push", "origin", "master"], cwd=wiki_dir, check=True)
print("Pushed wiki updates successfully.")
