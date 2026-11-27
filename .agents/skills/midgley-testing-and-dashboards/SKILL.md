---
name: midgley-testing-and-dashboards
description: >-
  Guides running isolated Midgley test suites under TESTING=1, preventing
  production data pollution, regenerating GitHub Pages dashboards and static
  JSON APIs, and enforcing root-to-docs documentation parity and link safety.
  Use when validating code changes, debugging conftest isolation failures,
  regenerating docs/ artifacts, or syncing mirrored documentation.
---

# Midgley Testing, Dashboard Generation & Documentation Parity

Use this runbook to run isolated verification gates, regenerate static dashboards safely, and maintain documentation parity.

## 1. Isolated Test Execution (`TESTING=1`)

`tests/conftest.py` enforces a session-level SHA-256 checksum guard over `data/` (`verify_data_directory_unpolluted`) and automatically redirects `HISTORY_CSV_PATH`, SQLite databases, and `MIDGLEY_DATA_DIR` into `tmp_path`.

- **Always** run pytest with `TESTING=1`.
- Under `TESTING=1`, all real network sockets, notifications, remote submissions, production ledger writes, and non-isolated dashboard rebuilds must be suppressed.
- When writing new tests, inject `tmp_path` and monkeypatch connector boundaries rather than skipping generator call sites.

### Standard Validation Sequence

1. **Static analysis gate**:
   ```sh
   ruff check .
   ```
2. **Targeted tests for changed areas**:
   - Point-in-time / features: `TESTING=1 pytest -v tests/test_truncation_invariance.py`
   - Docs / links / navigation: `TESTING=1 pytest -v tests/test_docs_links.py`
   - Data sources catalog: `TESTING=1 pytest -v tests/test_dashboard_generator.py -k test_data_sources_page_generation`
   - Telemetry / storage / cache: `TESTING=1 pytest -v tests/test_system_telemetry.py`
3. **Broader suite** (prefer offloading full-suite runs to the Linux dev VM when available):
   ```sh
   TESTING=1 pytest -v tests/
   ```

## 2. Controlled Dashboard & Static API Regeneration

- Always update **generator-owned templates** (`src/dashboard_generator.py`, `src/sources_generator.py`, `src/static_api_exporter.py`) rather than hand-patching generated HTML in `docs/`.
- Regenerate only affected public pages from a **controlled valid-data state**. Never publish mocks, test fixtures, synthetic evaluation scores, or unverified metrics.
- Preserve accessibility attributes, CSP/SRI hashes on CDN assets (e.g., KaTeX), and semantic HTML in source and regional cards.
- **No `file:///` links**: Never emit machine-local `file:///` URLs in markdown, templates, or generated HTML (`tests/test_docs_links.py` fails on any match).

## 3. Root-to-`docs/` Documentation Parity

Seven root Markdown files are mirrored byte-for-byte into `docs/` (checked by `scripts/verify_docs_parity.py`):
- `README.md`, `SELF_HOSTING.md`, `API.md`, `ARCHITECTURE.md`, `DESIGN.md`, `AGENTS.md`, `AI_DISCLOSURE.md`

After editing any canonical root document, synchronize and verify parity:

```sh
python scripts/verify_docs_parity.py --sync
python scripts/verify_docs_parity.py
TESTING=1 pytest -v tests/test_docs_links.py
```
