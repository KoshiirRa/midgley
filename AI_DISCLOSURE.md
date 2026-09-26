# AI Use & Assistance Disclosure

This document provides a transparent and formal disclosure regarding the use of Artificial Intelligence (AI), Large Language Models (LLMs), and autonomous agent frameworks across the **`midgley`** codebase lifecycle—spanning software development, code review, quality assurance, in-pipeline event extraction, and automated maintenance.

---

## 🧭 Principles of AI Utilization

We adhere to the following principles when integrating AI tools into this project:
1. **Transparency:** Clearly documenting which models, tools, and platforms are utilized in codebase authoring, review, and runtime operation.
2. **Human Oversight & Accountability:** AI models act as assistive and exploratory tools. Maintainers and human developers retain full accountability for architectural decisions, system safety, security hygiene, and production releases.
3. **Verification & Testing:** All AI-suggested code, refactors, and test suites must pass rigorous automated testing (`pytest`), static analysis/linting (`ruff`, `flake8`, `mypy`), and empirical backtesting before merging.
4. **Security & Privacy:** No sensitive credentials, private keys, API secrets, or personal data are exposed or passed into model prompts or public logging pipelines.

---

## 🤖 Taxonomy of AI & LLM Systems in Use

The project distinguishes between **Development & Code Review Assistance** (offline tools used by developers) and **Runtime Forecasting & Data Extraction Engines** (in-pipeline agents embedded in the live forecasting software).

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          AI & LLM ECOSYSTEM IN USE                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  🛠️ SOFTWARE DEVELOPMENT & CODING                                           │
│     • Primary Model: Google Gemini (Gemini 3.7 Flash, Gemini 2.5 Flash,     │
│       Gemini Pro / Antigravity Agentic Assistant)                           │
│     • Scope: Code authoring, feature implementation, refactoring,           │
│       unit test generation, and documentation drafting.                     │
│                                                                             │
│  🔍 CODE REVIEW & QUALITY ASSURANCE                                         │
│     • Primary Models: Anthropic Claude (Claude Opus 5.5, Claude 3.7 Sonnet),│
│       OpenAI ChatGPT (ChatGPT 6 Astra, GPT-4o / o-series)                   │
│     • Scope: Automated & interactive pull request review, edge-case audits, │
│       architectural critique, security assessment, and test validation.     │
│                                                                             │
│  ⚡ RUNTIME PIPELINE & EVENT EXTRACTION AGENTS                              │
│     • Primary Model: Google Gemini (gemini-2.5-flash / gemini-1.5-flash)    │
│     • Scope: Ingestion & impact scoring of unstructured financial news,     │
│       NOAA weather alerts, geopolitical disruption headlines, weekly issue  │
│       self-reviews, and Hindsight episodic memory post-mortems.             │
│     • Fallbacks: Zero-cost deterministic domain NLP lexicon & offline rules.│
│                                                                             │
│  📊 QUANTITATIVE ESTIMATION (Non-Generative Core)                           │
│     • Models: Standardized Ridge Regression (α=10.0) & XGBoost              │
│     • Scope: Mathematical time-series estimation on engineered numerical    │
│       feature matrices (strictly deterministic statistical estimators).     │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 1. 🛠️ Development & Coding Assistance

* **Primary LLM Engine:** **Google Gemini** (Gemini 3.7 Flash, Gemini 2.5 Flash, Gemini Pro / Antigravity Agentic Assistant)
* **Applications:**
  - Generating initial scaffolding, data connector integrations, and regional calibration logic.
  - Writing comprehensive unit and regression test suites (`tests/`).
  - Refactoring legacy routines and optimizing algorithmic performance.
  - Authoring Markdown documentation, API specifications, and mathematical guides.

## 2. 🔍 Code Review, Audit & Quality Assurance

* **Primary LLM Engines:**
  - **Anthropic Claude** (Claude Opus 5.5, Claude 3.7 Sonnet, Claude 3.5 Sonnet)
  - **OpenAI ChatGPT** (ChatGPT 6 Astra, GPT-4o, OpenAI o1 / o3 series)
* **Applications:**
  - Multi-perspective pull request (PR) code review and differential analysis.
  - Static security and dependency vulnerability audits.
  - Logic verification and boundary condition / edge-case stress testing.
  - Identification of subtle time-series lookahead bias and data leakage hazards.

## 3. ⚡ In-Pipeline Event Extraction & Runtime Agents

* **Primary LLM Engine:** **Google Gemini** (`gemini-2.5-flash` / `gemini-1.5-flash` via `google-genai` SDK)
* **Applications:**
  - **Event & Sentiment Analysis ([`src/event_analyzer.py`](src/event_analyzer.py)):** Parsing live financial news (`finlight.me`), geopolitical headlines, and maritime chokepoints into structured, bounded impact vectors $[-1.0, +1.0]$.
  - **Weekly Performance Review & Issue Triage ([`src/weekly_issue_reporter.py`](src/weekly_issue_reporter.py)):** Automated weekly self-review of model accuracy convergence and GitHub issue backlog prioritization.
  - **Episodic Memory Reflection ([`src/agent_memory.py`](src/agent_memory.py) & [`src/hindsight_client.py`](src/hindsight_client.py)):** Generating qualitative post-mortem reflections on prediction anomalies.
* **Deterministic Fallback:** Zero-cost offline regex & domain NLP lexicons guarantee continuous, fail-safe forecasting operations if API quotas are exhausted or offline execution is mandated.

## 4. 📊 Separation of Generative AI vs. Quantitative Forecasters

It is critical to note that **the core quantitative price forecasting models are not generative text models**.
* Price return forecasts and retail pump price spreads are generated by deterministic, regularized statistical estimators (**Standardized Ridge Regression** $\alpha=10.0$ and **XGBoost Regressors**) operating on numerical matrices.
* Generative LLMs contribute exclusively through structured, bounded qualitative feature vectors (e.g. event shock intensity, regulatory transition timelines) that serve as input columns to the quantitative estimator alongside physical market fundamentals (EIA inventories, crack spreads, NOAA degree days, river stages, and pipeline tariffs).

---

## 🛡️ Governance & Continuous Updates

This disclosure is maintained as a living document under version control. Whenever new LLM models, code review agents, or automated developer tools are introduced into the project workflow, this document is updated accordingly.

*Last Updated: September 2026*
