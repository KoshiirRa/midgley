# Contributing to Midgley

Thank you for your interest in contributing to Midgley!

## Development Setup

Midgley is developed across a dedicated Linux development environment (`dev-vm`) and GitHub Actions:

1. **Clone the Repository:**
   ```bash
   git clone https://github.com/KoshiirRa/midgley.git
   cd midgley
   ```
2. **Create a Virtual Environment:**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.lock
   ```
3. **Run Linting & Tests:**
   ```bash
   ruff check .
   pytest -v tests/
   ```

## Development Guidelines

* **POSIX Pathing & Line Endings:** Enforce LF (`\n`) line endings across all Python, shell, and markdown files.
* **Deterministic Builds:** Use `requirements.lock` generated via `pip-compile`.
* **Zero Temporal Leakage:** Always use forward-fill (`ffill()`) rather than backward imputation (`bfill()`) on time-series features.
* **Clean Commits:** Write conventional commit messages (`feat:`, `fix:`, `docs:`, `test:`, `refactor:`).
* **PR Verification:** Ensure all CI checks (pytest on Python 3.11-3.13, ruff) pass cleanly on PR submissions.
