# Release Notes - v0.4.3

**Release Date:** September 5, 2026  
**Build Target:** `dev-vm` (`10.42.42.54`)  
**Git Branch:** `dev`  

---

## 🚀 Key Features, Bug Fixes & Architectural Enhancements

### 1. Refine Execution Audit Naming & Headline Sanitization (Issue #204)
- **Dynamic Batch Execution Audit Pipeline Naming:** Updated the audit pipeline header in [`src/dashboard_generator.py`](file:///c:/Users/concentus/Documents/Random%20Ideas%20-%20LLM%20Unleaded%20Gas%20Price%20Prediction%20Modelling/src/dashboard_generator.py) and [`src/weekly_issue_reporter.py`](file:///c:/Users/concentus/Documents/Random%20Ideas%20-%20LLM%20Unleaded%20Gas%20Price%20Prediction%20Modelling/src/weekly_issue_reporter.py) to output dynamic ISO 8601 UTC execution timestamps (`Daily Forecast Batch Execution ({timestamp_utc}) | Weekly Model Review Report`), eliminating static/stale execution titles.
- **Strict Headline Prose Sanitization (`is_valid_headline()`):** Implemented strict validation filters in [`src/dashboard_generator.py`](file:///c:/Users/concentus/Documents/Random%20Ideas%20-%20LLM%20Unleaded%20Gas%20Price%20Prediction%20Modelling/src/dashboard_generator.py) and [`src/intraday_event_monitor.py`](file:///c:/Users/concentus/Documents/Random%20Ideas%20-%20LLM%20Unleaded%20Gas%20Price%20Prediction%20Modelling/src/intraday_event_monitor.py) to reject raw REST API endpoints (`api.finlight.me`, `api.weather.gov`), raw JSON strings, system logs, code snippets, and short non-headline text from entering the intelligence event matrix and public UI dashboard.
- **Human-Readable Feed Source Formatting (`format_human_source()`):** Replaced technical feed identifiers (`Finlight_v2_API`, `NOAA_NWS_API`, `RSS_Feed`, `CME_Group / NYMEX`) with polished human-readable labels (*Reuters Energy*, *Bloomberg Market Wire*, *NOAA NWS Storm Alert*, *CME Group / NYMEX*, *Google News Energy Feed*) across audit cards, technical breakdown files, and web app components.

---

## 🧪 Verification & Test Suite Results

- **Targeted Test Suite Execution on `dev-vm` (`10.42.42.54`):**
  ```bash
  pytest tests/test_dashboard_generator.py tests/test_intraday_event_monitor.py tests/test_weekly_issue_reporter.py tests/test_audit_box.py
  ```
  **Result:** `35 passed in 399.26s` (100% pass rate across all modified test modules).

---

## 📋 Closed & Superseded GitHub Issues
- **Issue #204**: `feat(mlops): Refine execution audit naming & sanitize news feed headlines` (Closed as completed)
