---
name: midgley-release-and-governance
description: >-
  Guides Midgley GitHub issue triage, PR/release Markdown formatting, active
  release-notes consolidation, RELEASE_MANIFEST.json updates, and authorized
  dev -> main -> self-hosted release reconciliation. Use when preparing a
  release, updating release notes, triaging issues, or running upgrade
  reconciliation checks.
---

# Midgley Release Management & GitHub Governance

Use this runbook for issue triage, PR/release authoring, release-notes consolidation, and authorized release reconciliation.

## 1. External Action Authorization Gate

- **Do not** push branches, publish releases, trigger remote deployments, edit the remote GitHub wiki, or submit live external benchmarks without explicit user authorization.
- If an external step is unauthorized or credentials are unavailable, prepare all local changes/files and report the exact pending action cleanly.
- Never pass raw GitHub tokens inline in CLI commands or environment overrides; rely on `gh auth` keyring credentials.

## 2. Issue Triage & PR Formatting

1. **Three-Track Routing**:
   - UI / API / general software -> **Software/UI**
   - Estimators / features / calibration -> **Model**
   - Performance reviews / telemetry / meta-agent -> **Weekly Review/MLOps**
   - Android Automotive / Auto client -> route to `KoshiirRa/midgley-auto` and cross-link backend contracts.
2. **Markdown Payloads**:
   - Always write Markdown bodies for `gh issue`, `gh pr`, or `gh release` to a temporary file and pass `--body-file` or `--notes-file`. Never pass shell-interpreted inline Markdown strings.

## 3. Routine Tasks vs. Authorized Releases

- **Routine Tasks**:
  - Work on `dev` (never develop directly on `main`).
  - Append completed changes, issue references, and check results to the **single active in-progress** `RELEASE_NOTES_v*.md` file.
  - Do **not** create per-issue release files or bump `pyproject.toml` / `src/version.py` versions during routine work.
- **Authorized Official Releases (`dev` -> `main` -> `self-hosted`)**:
  1. Align version in `pyproject.toml` and fallback in `src/version.py`.
  2. Regenerate and verify `RELEASE_MANIFEST.json` via `src/release_manifest.py` (preserving `/api/v1/system/releases/latest`).
  3. Finalize the release notes with migration guidance and a structured **AI Agent Reconciliation Block** covering:
     - Feature and environment variable changes
     - Dependency and schema migrations
     - Self-hosted upgrade steps (dry-run via `python scripts/check_updates.py`; never auto-reconcile implicitly)
  4. Sync root docs to `docs/` via `python scripts/verify_docs_parity.py --sync` and prepare wiki updates.
  5. When reconciling to `self-hosted`, preserve its blank-slate national/default scope and never force-push shared data (`production-data-deployment` concurrency group).

## 4. Verification

```sh
ruff check .
python scripts/verify_docs_parity.py
TESTING=1 pytest -v tests/test_docs_links.py
```
