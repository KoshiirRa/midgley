# Release Notes - v0.4.4

**Release Date:** September 5, 2026  
**Build Target:** `dev-vm` (`10.42.42.54`)  
**Git Branch:** `dev`  

---

## 🚀 Key Features, Bug Fixes & Architectural Enhancements

### 1. CORE Open-Access Research Paper Monitoring (Issue #53)
- **CORE API V3 Integration (`src/core_monitor.py`):** Integrated the [CORE API](https://core.ac.uk/services/api) (`https://api.core.ac.uk/v3/search/works`) to monitor open-access research papers on energy commodity forecasting, refining rack margins, oil market volatility, and machine learning time-series literature.
- **Weekly Self-Review Reporter Integration (`src/weekly_issue_reporter.py`):** Appends `## 🔬 Relevant CORE Open-Access Research Papers` alongside arXiv research preprints in the Saturday weekly model performance review report.
- **GitHub Workflow Integration (`.github/workflows/weekly_model_review.yml`):** Added `CORE_API_KEY: ${{ secrets.CORE_API_KEY }}` secret environment variable for execution on GitHub Actions cloud runners.
- **Resilience & Fault Tolerance:** Features a strict 10-second timeout limit and graceful fallback notice when external network interruptions or API rate limits occur.

---

## 🧪 Verification & Test Suite Results

- **Unit & Integration Test Suite Execution (`pytest`):**
  ```bash
  pytest tests/test_core_monitor.py tests/test_weekly_issue_reporter.py -v
  ```
  **Result:** `12 passed` (100% pass rate).
- **Full Repository Test Suite Execution:**
  ```bash
  pytest
  ```
  **Result:** `304 passed in 733.59s` (100% pass rate across all 304 test items).

---

## 📋 Closed & Superseded GitHub Issues
- **Issue #53**: `feat(core-api): Monitor open-access research papers via CORE API during weekly self-review` (Closed as completed)
