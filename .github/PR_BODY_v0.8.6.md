## Summary of Changes

Midgley **v0.8.6** expands the regional metro calibration footprint to 18 active hubs across all seven Petroleum Administration for Defense Districts (PADDs 1–7), migrates qualitative event ingestion to **Gemini 3.8 Flash**, implements genuine daily Permian/Gulf Coast rig telemetry via direct **Cloudflare Browser Run** REST API and edge rendering, and introduces the **Multi-Subscriber Discord Webhook, Direct Message (`discord_dm`) & `/midgley` Slash Command Notification Gateway**.

---

### Key Features & Enhancements

1. **18 Canonical Regional Calibration Hubs Across PADDs 1–7**:
   - **PADD 1A**: Boston & New England (`Boston_MA`, Issue #619 / PR #639)
   - **PADD 1B**: New York Harbor & NY State (`New_York_NY`, Issue #635 / PR #637), Newark & Delaware Valley (`Newark_NJ`)
   - **PADD 1C**: Charlotte & Carolinas (`Charlotte_NC`), Port St. Lucie & South Florida (`Port_St_Lucie_FL`)
   - **PADD 2**: Greater Chicago (`Chicago_IL`, Issue #219 / PR #630), Cincinnati & Ohio Valley (`Cincinnati_OH`), Tulsa & Mid-Continent (`Tulsa_OK`)
   - **PADD 3**: Houston & USGC Mega-Corridor (`Houston_TX`, Issue #220)
   - **PADD 4**: Denver & Rocky Mountain (`Denver_CO`, Issue #618 / PR #636)
   - **PADD 5**: Los Angeles Basin (`Los_Angeles_CA`, Issue #221), San Francisco Bay Area (`San_Francisco_CA`), Seattle & Puget Sound (`Seattle_WA`), Phoenix & Desert Southwest (`Phoenix_AZ`), Anchorage & Cook Inlet (`Anchorage_AK`), Honolulu & Oahu Island (`Honolulu_HI`)
   - **PADD 6**: San Juan & U.S. Caribbean Territories (`San_Juan_PR`, Issue #620)
   - **PADD 7**: Guam & Pacific Island Territories (`Guam_GU`, Issue #621)

2. **Unified Cloudflare Browser Run Client Libraries & Edge Scraping (Issues #533 & #640)**:
   - Centralized, reusable Browser Run client modules in Python ([`src/cloudflare_browser_run.py`](src/cloudflare_browser_run.py)) and TypeScript ([`workers/browser_run.ts`](workers/browser_run.ts)) to render pages to Markdown via serverless headless Chromium (`POST https://api.cloudflare.com/client/v4/accounts/<id>/browser-run/markdown`).
   - Dynamic credential resolution for `CLOUDFLARE_ACCOUNT_ID` and `CLOUDFLARE_API_TOKEN` across environment secrets and workers without hardcoded account IDs in source files.
   - Leveraged Cloudflare Workers Paid Browser Rendering binding (`MYBROWSER.quickAction("markdown", ...)`) with direct REST fallback.
   - Replaced legacy synthetic Permian rig multiplier with genuine bitemporal basin counts.

3. **Multi-Subscriber Discord Webhook, DM & Slash Command Gateway (Issue #235)**:
   - Encrypted persistent subscription registry in SQLite/Turso.
   - Interactive `/midgley` slash commands (`subscribe`, `unsubscribe`, `status`, `forecast`, `test-alert`) with ephemeral responses and direct DM dispatch.
   - 5-digit US ZIP code resolution preserving human-readable geographic locality identities with automatic statutory tax wedge and basis spread synthesis.
   - CARTO Dark Matter basemap tile authentication hardening via `CARTO_API_KEY`.

4. **Gemini 3.8 Flash Migration (Issue #616 / PR #638)**:
   - Upgraded core event extraction, news impact scoring, and reflection synthesis to `gemini-3.8-flash` with low thinking level before the upcoming Gemini 2.5 Flash retirement.

5. **Data Invariants, Test Isolation & Documentation Parity**:
   - Production data isolation guards under `TESTING=1`.
   - Replaced deprecated `datetime.utcnow()` across all connectors.
   - 100% documentation parity between root documentation and `docs/`.
   - Synchronized GitHub Wiki repository across all 15 operational pages.

---

### AI Agent Reconciliation Block

```yaml
release: v0.8.6
target_branch: main
source_branch: dev
migrations_required: true
database_changes:
  - table: discord_subscriptions
    status: created
    migration_file: src/db/schema.sql
environment_variables:
  new_required:
    - DISCORD_PUBLIC_KEY (Cloudflare Worker & local environment for Ed25519 Discord webhook signature verification)
  new_optional:
    - CARTO_API_KEY (Leaflet Dark Matter tile rendering, has valid fallback)
    - CLOUDFLARE_API_TOKEN (Direct Cloudflare Browser Run execution)
    - DISCORD_BOT_TOKEN (Discord DM delivery gateway)
    - DISCORD_APP_ID (Discord Application ID for command registration)
upstream_feed_updates:
  - card_2_2b: Enverus Daily Rig Count (via Cloudflare Browser Run REST & Workers edge)
model_version:
  llm_scorer: gemini-3.8-flash
  thinking_level: low
  version_code: 0.8.6
```

---

### Verification Run Results

- `TESTING=1 pytest -v tests/test_cloudflare_browser_run.py tests/test_enverus_rig_feed.py`: **17/17 passed**
- `npm test` (Vitest): **38/38 passed**
- `TESTING=1 pytest -v tests/test_dashboard_generator.py -k test_data_sources_page_generation`: **passed**
- `TESTING=1 pytest -v tests/test_docs_links.py`: **2/2 passed**
- `TESTING=1 pytest -v tests/test_truncation_invariance.py`: **3/3 passed**
- `TESTING=1 pytest -v tests/test_system_telemetry.py`: **10/10 passed**
- `ruff check .`: **All checks passed!**
- `python scripts/verify_docs_parity.py`: **100% parity verified**
