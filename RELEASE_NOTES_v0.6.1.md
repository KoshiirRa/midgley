# Release Notes - v0.6.1

**Release Date:** September 17, 2026  
**Build Target:** `dev-vm` (`10.42.42.54`)  
**Git Branch:** `main` / `dev`  

---

## 🚀 Overview & Patch Highlights

Midgley **v0.6.1** is a targeted patch release that addresses environment loading and tool execution edge cases following the release of the **Headline Arena Energy Forecasting Benchmark Connector** (v0.6.0) and enhanced regional environmental intelligence tooling.

---

## 🛠️ Bug Fixes & Operational Polish

### 1. Headline Arena Connector Automatic `.env` Fallback Loading ([`src/headline_arena_connector.py`](file:///src/headline_arena_connector.py))
- **Issue:** When running local operator diagnostic CLI commands (e.g., `python -m src.headline_arena_connector --status`) on environments where environment variables were stored in `.env` rather than exported to the global shell, the connector previously reported `Configured: False`.
- **Resolution:** Added automatic multi-tier environment loading (`python-dotenv` integration with deterministic custom parser fallback) at module initialization. Local CLI status checks and test routines now seamlessly resolve `HEADLINE_ARENA_CLIENT_ID`, `HEADLINE_ARENA_CLIENT_SECRET`, and `HEADLINE_ARENA_DEV_SUBMIT` directly from the project root `.env` file.

### 2. Model Context Protocol (MCP) Ozone Telemetry Response Fix ([`src/mcp_server.py`](file:///src/mcp_server.py))
- **Issue:** The MCP tool handler for `get_regional_ozone_alerts` lacked a return statement when processing corridor-level queries (e.g. `corridor="bay_area"`), resulting in `NoneType` responses and unit test failures.
- **Resolution:** Restored the standard `[types.TextContent(type="text", text=json.dumps(res, indent=2))]` MCP response wrapper across all regional corridor branches.

---

## 🧪 Comprehensive Test Suite & Validation

- **Execution Target:** Dedicated Linux VM (`dev-vm` / `10.42.42.54`) & Local Windows Environment.
- **Test Suite Results:**
  - `tests/test_headline_arena_connector.py` (17/17 tests passing)
  - `tests/test_aqi_feed.py` (16/16 tests passing)
  - `tests/test_dashboard_generator.py` (18/18 tests passing)
- **Pass Rate:** 100%.

---

## 📋 Upgrading

To pull and update to the latest patch release:

```bash
git fetch origin
git checkout main
git pull origin main
pip install -e .
```
