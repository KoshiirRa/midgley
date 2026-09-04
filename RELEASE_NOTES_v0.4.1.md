# Release Notes - v0.4.1

**Release Date:** September 4, 2026  
**Build Target:** `dev-vm` (`10.42.42.54`)  
**Git Branch:** `main`  

---

## 🚀 Key Features, Bug Fixes & Architectural Enhancements

### 1. Python 3.11 SyntaxError Fix in Dashboard Generator (Issue #52 Follow-Up)
- **Precomputed CodeCogs Math URLs:** Precomputes LaTeX equation rendering URLs outside inline f-strings in [`src/dashboard_generator.py`](file:///c:/Users/concentus/Documents/Random%20Ideas%20-%20LLM%20Unleaded%20Gas%20Price%20Prediction%20Modelling/src/dashboard_generator.py), resolving Python 3.11 f-string quote nesting syntax errors (`SyntaxError: f-string expression part cannot include a backslash`).
- **Cross-Python Compatibility:** Restores clean template rendering across Python 3.11, 3.12, 3.13, and 3.14 runtimes.

### 2. Dependency Reconciliation & Security Patches (PR #198)
- **Cloudflare Wrangler & Undici Bump:** Upgraded `undici` to `7.29.0` and ancestor dependency `wrangler` to `4.129.0` in `package.json` and `package-lock.json`.
- **Edge Worker Security:** Eliminates potential HTTP request smuggling and header parsing vulnerabilities in Cloudflare Workers and Node.js fetch runtimes.

### 3. Formalized 3-Branch Synchronization Protocol (`AGENTS.md`)
- **Repository Architecture Specification:** Updated [`AGENTS.md`](file:///c:/Users/concentus/Documents/Random%20Ideas%20-%20LLM%20Unleaded%20Gas%20Price%20Prediction%20Modelling/AGENTS.md) and [`scripts/wiki_update.py`](file:///c:/Users/concentus/Documents/Random%20Ideas%20-%20LLM%20Unleaded%20Gas%20Price%20Prediction%20Modelling/scripts/wiki_update.py) to explicitly mandate the 3-branch workflow (`dev`, `main`, and `self-hosted`).
- **Mandatory Reconciliation Rule:** Establishes that whenever `dev` is merged into `main`, `self-hosted` MUST also be reconciled with `dev` (`git checkout self-hosted && git merge dev && git push origin self-hosted`) to maintain feature parity between the production showcase and the blank-slate container framework.

### 4. Continuous Forecast & Intraday Anomaly Log Revisions
- **Daily Automated Predictions:** Updated persistent prediction logs (`data/prediction_history.csv`) and public web dashboard embeds across all 8 active regional hubs (National, Tulsa, Newark, Cincinnati, Greenville, Charlotte, Oakland, Port St. Lucie).

---

## 🧪 Verification & Test Suite Results

- **Full Test Suite Execution on `dev-vm` (`10.42.42.54`):**
  ```bash
  PYTHONPATH=. pytest
  ```
  **Result:** `283 passed in 781.61s` (100% pass rate across all test modules).

---

## 📋 Closed & Superseded GitHub Pull Requests
- **PR #198**: `chore(deps): bump undici and wrangler` (Merged into `dev`)
