---
name: midgley-connector-workflow
description: >-
  Guides adding, modifying, debugging, or deprecating Midgley data connectors and
  intelligence feeds in src/. Use when integrating a new data source, updating
  cache TTLs or quota caps, adding bitemporal vintage tracking, or synchronizing
  the public Data Sources page and governance documentation.
---

# Midgley Data Connector & Feed Workflow

Use this runbook whenever adding, replacing, modifying, or deprecating an upstream data connector in Midgley.

## 1. Pre-Implementation Checks

1. **Cost & Provider Gate**: Reject Apify and any new paid services. Preserve existing explicitly configured optional providers without enabling new spend or expanding usage silently.
2. **Inspect Existing Patterns**: Review `src/lookup_cache.py`, `src/http_client.py`, `src/vintage_store.py`, and an existing connector (e.g., `src/eia_api_client.py` or `src/bts_transportation.py`) before writing code.
3. **Check Credential & Offline Paths**: Ensure missing credentials or offline execution degrade gracefully with honest status metadata rather than fabricating ground truth.

## 2. Implementation Checklist

1. **Cache-First Access (`src/lookup_cache.py`)**:
   - Query `global_cache` before any external HTTP request.
   - Use service-namespaced keys and source-appropriate TTLs. Do not conflate cache TTL with upstream update cadence, publication lag, or guaranteed fresh observations.
   - Preserve the Turso -> Cloudflare D1/R2 -> local SQLite/in-memory cascade and local disk fallbacks.
2. **Quota & Network Safety (`src/http_client.py`)**:
   - Enforce configured caps (Firecrawl: 800/month, 30/day; Finlight: 150/month, 10/day) and honor upstream `Retry-After` headers.
   - Use bounded timeouts, bounded retries, and circuit-breaker behavior; avoid tight polling loops.
   - Use `defusedxml` for all untrusted XML/RSS/Atom feeds.
   - Distinguish invalid credentials from exhausted quotas; stop repeated failing calls and surface the blocker without logging secrets.
3. **Point-in-Time Provenance (`src/vintage_store.py`)**:
   - Record both observation date and `as_of` publication timestamp, source URL, geography, missingness, and quality tier (`LIVE`, `CACHED`, `BENCHMARK`, `STALE`, `SYNTHETIC`).
   - Never relabel estimated, proxy, or synthetic fallback values as observed ground truth.
4. **Test Isolation (`TESTING=1`)**:
   - Put `TESTING=1` fast paths **inside** the connector so generator and pipeline call sites remain monkeypatchable.
   - Suppress all real sockets/network calls under `TESTING=1`.
5. **Telemetry & Wiring**:
   - Record connector status, latency, failures, cache age, and quota consumption via `src/connector_telemetry.py` / `src/catalog_monitor.py`.
   - Wire ingestion into `src/event_analyzer.py` or `src/data_ingestion.py` (once per region/run — never inside horizon loops).

## 3. Required Companion Updates

Apply every applicable companion change from `AGENTS.md`:

- **`src/sources_generator.py`**: Add/update the feed card with module/class, provider/endpoints, auth requirements, features/consumers, cost, TTL, update cadence, and deprecation rationale. Preserve native typography and semantic HTML.
- **Configuration & Docs**: Update `.env.example`, `SELF_HOSTING.md`, and `ARCHITECTURE.md` if new environment variables or endpoints are introduced, then sync mirrors via `python scripts/verify_docs_parity.py --sync`.
- **Wiki**: Prepare corresponding wiki updates locally if remote wiki editing is not explicitly authorized.

## 4. Verification

Run targeted checks in an isolated environment:

```sh
ruff check .
TESTING=1 pytest -v tests/test_dashboard_generator.py -k test_data_sources_page_generation
TESTING=1 pytest -v tests/test_system_telemetry.py
TESTING=1 pytest -v tests/test_docs_links.py
```

Also add and run a focused unit test in `tests/test_<connector>.py` covering cache hits, `TESTING=1` isolation, missing-credential fallback, and vintage `as_of` provenance.
