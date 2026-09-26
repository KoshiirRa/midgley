# Release Notes - v0.7.1

Midgley **v0.7.1** is a targeted patch release addressing regional data-alignment discrepancies, prediction history logging reconciliation, advisory file lock gitignore rules, and documentation parity synchronization identified following the initial v0.7.0 live daily workflow execution (Issue #489).

---

## 🎯 Highlights & Fixes

### 1. Newark, DE Regional Key & Metadata Reconciliation (Issue #489)
- **Runner Key Correction**: Updated `REGION_MODULE_MAP` in [`src/locations/runner.py`](src/locations/runner.py) to map `"newark"` and `"newark_de"` to default logger key `"Newark_DE"` (previously misconfigured as `"Newark_NJ"`).
- **Resilient Metadata ID Resolution**: Added alias normalization dictionary `REGION_ALIASES` in [`src/regional_metadata.py`](src/regional_metadata.py) (`newark` $\to$ `newark_de`, `tulsa` $\to$ `tulsa_ok`, `cincinnati` $\to$ `cincinnati_oh`, etc.) to guarantee profile discovery when short location keys are supplied.
- **Explicit Regional Profile Keys**: Added `"logger_region_key"` to all 8 metadata profiles in [`data/regional_metadata/*.json`](data/regional_metadata/).
- **RVP Regulations Alignment**: Registered `"Newark_DE"` in [`src/rvp_regulations.py`](src/rvp_regulations.py) `DEFAULT_RVP_RULES["regions"]` and `alias_map`.

### 2. Prediction History Ledger Reconciliation
- Re-labeled all 1,194 records in [`data/prediction_history.csv`](data/prediction_history.csv) from `Newark_NJ` to `Newark_DE`.
- Cleaned up unmigrated legacy rows with missing base prices using `cleanse_prediction_history()`, resolving the `$nan/gal` display bug in public dashboards and README forecast summaries.

### 3. Advisory File Lock Git Exclusion
- Added `*.lock` and `data/*.lock` to [`.gitignore`](.gitignore) to prevent temporary lock files produced by [`src/storage_io.py`](src/storage_io.py) (`file_lock()`) from being committed by CI/CD auto-commit actions.
- Untracked committed lock files from the git repository.

### 4. Documentation & Mirror Parity
- Re-synchronized root documentation files with their `docs/` mirrors (`README.md`, `SELF_HOSTING.md`, `API.md`, `ARCHITECTURE.md`, `DESIGN.md`, `AGENTS.md`, `AI_DISCLOSURE.md`).
- Verified 100% parity assertion with `python scripts/verify_docs_parity.py`.

---

## 📦 Commits & Attribution
* **Issue**: [#489](https://github.com/KoshiirRa/midgley/issues/489)
* **Tag**: `v0.7.1`
