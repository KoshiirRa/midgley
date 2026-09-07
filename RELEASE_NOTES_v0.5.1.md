# Release Notes - v0.5.1 (In Progress)

**Release Date:** September 7, 2026  
**Build Target:** `dev-vm` (`10.42.42.54`)  
**Git Branch:** `dev`  

---

## 🚀 Key Features, Bug Fixes & Architectural Enhancements

### 1. Dedicated Academic Citations & Peer-Reviewed Research Literature Portal (Issue #228)
- **Standalone Web Portal ([`docs/citations.html`](file:///docs/citations.html)):** Built a responsive Tailwind + KaTeX academic literature portal documenting all 12 peer-reviewed research papers and foundation algorithms powering the Midgley forecasting architecture.
- **Interactive Search & Filtering:** Added real-time category filtering chips (*All Papers*, *Time-Series & Quant*, *LLM Agents & NLP*, *Backtesting & Overfitting*, *Spatio-Temporal*) and instant text search across titles, authors, and methodologies.
- **Full KaTeX Mathematical Formulas:** Rendered theoretical formulas directly on cards, including Zhou et al. Pre-Training Context Routing ($\rho_h$ vs $\Delta$), Alibaba CEDAR two-stage residual decomposition ($\mathbf{s}_{t+1} = f_\theta(\mathbf{s}) + \epsilon_t$), López de Prado Purged CPCV conditions, Qlib Information Coefficient ($IC / IC_{IR}$), and Midgley Dynamic Volatility-Gated Persistence Blending ($\lambda_{vol}$).
- **Streamlined Math Guide Integration ([`docs/math.html`](file:///docs/math.html)):** Refactored Section 11 of the Educational Math Guide into a high-visibility summary portal card linking directly to `citations.html` and `RESEARCH_CITATIONS.md`.
- **Global Header Navigation Parity:** Updated header navigation across all dashboard pages (`index.html`, `national.html`, `math.html`, `telemetry.html`, `diesel.html`, `savings.html`, `citations.html`) with direct links to the new Citations portal.

### 2. Comprehensive Project Backlog Triage & Roadmap Alignment
- **Full No-Status Triage:** Triaged all 13 open backlog issues in *No Status* on **Project Midgley - Master Roadmap** (Project #12), assigning conventional commits title standards, appropriate repository labels, milestone tags, and complete project metadata (Status, Priority, Workstream, Effort, Target, Risk).
- **Master Roadmap Epics Proposed:**
  - `[Feature Epic] Tier 2 Regional Metro Hubs Expansion`: Consolidating Chicago (Issue #219), Houston (Issue #220), and Los Angeles Basin (Issue #221).
  - `[Documentation Epic] Comprehensive Math Guide Modernization & Pipeline Restructuring`: Consolidating Issues #222–#227 and #229.
