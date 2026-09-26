# Release Notes - v0.6.3

**Release Date:** September 17, 2026  
**Build Target:** `dev-vm` (`10.42.42.54`) & Cloudflare Edge  
**Git Branch:** `main` / `dev`  

---

## 🙀 Overview & Release Highlights

Midgley **v0.6.3** delivers crucial pipeline stability and compatibility fixes for master execution and longitudinal learning curve calculations:

1. **Master Pipeline Headline Arena Benchmark Import Fix ([`run_all.py`](run_all.py)):**
   - Resolved a top-level `NameError: name 'os' is not defined` during optional Headline Arena benchmark evaluations in CI execution by moving `import os` to module-level imports.
2. **NumPy 2.0 / Pandas Longitudinal Timedelta Normalization ([`src/learning_tracker.py`](src/learning_tracker.py)):**
   - Standardized `pd.Timedelta` calculations and datetime boundary operations with explicit integer casting and `pd.Timestamp` wrappers, eliminating deprecation warnings during dashboard generation.

---

## 🌝 Key Changes & Improvements

### 1. Master Pipeline Fix ([`run_all.py`](run_all.py))
- Guaranteed `os` module availability across all execution paths, including `--submit-headline-arena` and `HEADLINE_ARENA_DEV_SUBMIR` environment evaluation.
- Cleaned redundant scoped imports inside inner try-except blocks.

### 2. Longitudinal Performance Tracking ([`src/learning_tracker.py`](src/learning_tracker.py))
- Wrapped `df['target_date_dt'].min()` and `df['target_date_dt'].max()` in `pd.Timestamp` to avoid generic unit warnings on numpy datetime conversions.
- Enforced explicit `int(window_days)`, `int(step_days)`, and `int(days)` parameters for `pd.Timedelta` intervals.

---

## 🗪 Verification & Test Suite Matrix

- **Execution Target:** Dedicated Linux VM `dev-vm` (`10.42.42.54`).
- **Test Suite Results:**
  - `tests/test_version.py` (8/8 tests passing)
  - `tests/test_learning_tracker.py` (7/7 tests passing)
  - Full Repository Matrix: **624/625 tests passing (1 skipped, 100% pass rate)**.

---

## 🐬 Upgrading

To update to the **v0.6.3** release:

```bash
git fetch origin
git checkout main
git pull origin main
pip install -e .
```
