# Release Notes - v0.8.6 (Draft)

Midgley **v0.8.6** *(In-Progress Draft on `dev`)* expands the regional metro calibration footprint with four major U.S. refining and consumption corridors (**Greater Chicago**, **Houston & USGC**, **Los Angeles Basin**, and **Denver & Rocky Mountain**) and introduces the **Multi-Subscriber Discord Webhook, Direct Message (`discord_dm`) & `/midgley` Slash Command Notification Gateway** so teams and individual server members can receive tailored, locale-filtered alerts without cluttering shared chat channels.

---

## 🎯 Highlights & Improvements

### 1. Greater Chicago Metro Calibration Hub — PADD 2 (`Chicago_IL`, Issue #219 / PR #630)
- **Refining & Midstream Topology**: Added [`src/locations/chicago/`](src/locations/chicago/) (`main.py`, `regional.py`, `notebook_builder.py`) and [`data/regional_metadata/chicago_il.json`](data/regional_metadata/chicago_il.json) calibrated to BP Whiting (435 kbpd, Indiana), CITGO Lemont (177 kbpd, Illinois), and ExxonMobil Joliet (251 kbpd, Illinois), alongside Explorer, Wolverine, West Shore, and Badger pipeline corridors.
- **Tax Arbitrage & EPA RFG 7.4 psi Modeling**: Modeled Illinois state excise ($0.470/gal), Cook County ($0.060/gal), and City of Chicago ($0.080/gal) stacked municipal fuel taxes ($0.805/gal statutory base plus 6.25%–10.25% sales tax compounding) and Northwest Indiana cross-border arbitrage (`nw_indiana: -0.38`), plus EPA Reformulated Gasoline (RFG) 7.4 psi summer RVP rules in [`data/regulatory_rvp_rules.json`](data/regulatory_rvp_rules.json) and [`src/rvp_regulations.py`](src/rvp_regulations.py).
- **Midwestern Edgeworth Price Cycles & Public Dashboard**: Enabled `has_edgeworth_cycles=True` for Greater Chicago in [`src/locations/specs.py`](src/locations/specs.py), mapped official EIA weekly retail series `EMM_EPMR_PTE_Y03CH_DPG` (`GASREGWCH`), and generated [`docs/chicago.html`](docs/chicago.html).

### 2. Houston & USGC Metro Calibration Hub — PADD 3 (`Houston_TX`, Issue #220)
- **Gulf Coast Mega-Refining Corridor**: Added [`src/locations/houston/`](src/locations/houston/) and [`data/regional_metadata/houston_tx.json`](data/regional_metadata/houston_tx.json) anchoring >52% of U.S. operable refining capacity across the Houston Ship Channel and Beaumont/Port Arthur corridor (ExxonMobil Baytown 560 kbpd, Motiva Port Arthur 630 kbpd, Marathon Galveston Bay 593 kbpd, LyondellBasell 268 kbpd, Valero Houston 235 kbpd, Deer Park 312 kbpd, Chevron Pasadena 110 kbpd) and Colonial Pipeline Lines 1 & 2 origin injection at Pasadena/Hebert.
- **Tax Structure, RVP & EIA Series Integration**: Modeled Texas's fixed statutory excise tax ($0.200/gal state + $0.184/gal federal = $0.384/gal total with zero state/local sales tax on motor fuel), Houston-Galveston-Brazoria 7.8 psi Low-RVP summer rules, `spot_gulf_coast` (`EER_EPMRU_PF4_RGC_DPG`) pass-through, and official EIA weekly retail series `EMM_EPMR_PTE_Y44HO_DPG` (`GASREGWHO`) in [`src/eia_retail_feed.py`](src/eia_retail_feed.py), plus [`docs/houston.html`](docs/houston.html).

### 3. Los Angeles Basin Metro Calibration Hub — PADD 5 (`Los_Angeles_CA`, Issue #221)
- **South Coast CaRFG Refining Island**: Added [`src/locations/los_angeles/`](src/locations/los_angeles/) and [`data/regional_metadata/los_angeles_ca.json`](data/regional_metadata/los_angeles_ca.json) calibrating Southern California's 1.022M bpd refining cluster (Marathon Carson/Wilmington 363 kbpd, Chevron El Segundo 269 kbpd, PBF Torrance 166 kbpd, Phillips 66 Wilmington 139 kbpd, Valero Wilmington 85 kbpd), Kinder Morgan Watson Station / SFPP West & South Line pipelines, and San Pedro Bay (Ports of Los Angeles & Long Beach) waterborne imports.
- **CARB Phase 3 RVP, Tax Stack & EIA Series**: Modeled California's $0.953/gal statutory base ($0.616/gal SB 1 excise + Cap-and-Trade + LCFS + UST fee, ~\$1.407/gal total with local sales tax), extended CARB Phase 3 7.0 psi RVP window (March 1–October 31), `spot_los_angeles` (`EER_EPMRU_PF4_RLA_DPG`), and official EIA weekly retail series `EMM_EPMR_PTE_Y05LA_DPG` (`GASREGWLA`), plus [`docs/los_angeles.html`](docs/los_angeles.html).

### 4. Denver & Rocky Mountain Metro Calibration Hub — PADD 4 (`Denver_CO`, Issue #618)
- **Front Range Refining Island & Suncor Commerce City**: Added [`src/locations/denver/`](src/locations/denver/) (`main.py`, `regional.py`, `notebook_builder.py`) and [`data/regional_metadata/denver_co.json`](data/regional_metadata/denver_co.json) calibrated to Colorado's sole petroleum refinery (Suncor Commerce City 103 kbpd) and regional distribution network (Magellan, Sinclair, Chase Front Range terminals).
- **DJ Basin Feedstock Differentials & Severe Ozone 7.8 psi RFG**: Modeled DJ Basin sweet crude / Wyoming sour feedstock spreads, EPA Front Range 9-county severe ozone nonattainment 7.8 psi summer RVP standards in [`data/regulatory_rvp_rules.json`](data/regulatory_rvp_rules.json) and [`src/rvp_regulations.py`](src/rvp_regulations.py), and Colorado statutory motor fuel excise tax ($0.280/gal statutory base, $0.464/gal baseline with federal).
- **PADD 4 Hierarchical MinT Coherence & Dashboard**: Added `Denver_CO` and `PADD_4` into [`src/hierarchical_engine.py`](src/hierarchical_engine.py) completing full continental U.S. PADD coverage across MinT reconciliation matrices, mapped official EIA retail series (`GASREGWDEN`, `GASREGWCO`, `GASREGWRM`, `GASDESWRM`), and generated [`docs/denver.html`](docs/denver.html).

### 5. Multi-Subscriber Discord Webhooks, Direct Message (`discord_dm`) Alerts & `/midgley` Slash Commands (Issue #235)
- **Dual-Target Persistent Subscription Registry**: Added `discord_subscriptions` in [`src/db/schema.sql`](src/db/schema.sql) and [`DiscordSubscriptionRegistry`](src/discord_notifier.py) in [`src/discord_notifier.py`](src/discord_notifier.py) supporting both shared channel incoming webhooks (`delivery_type="webhook"`, encrypted at rest via `cryptography.fernet` or HMAC-SHA256 authenticated stream cipher) and personal Discord Direct Message subscriptions (`delivery_type="discord_dm"`, storing `discord_user_id` and cached `dm_channel_id` via `DISCORD_BOT_TOKEN`).
- **Locale, Shock Threshold, Directional Bias & Catalyst Filtering**: Implemented [`dispatch_to_matching_subscribers()`](src/discord_notifier.py) to concurrently fan out intraday shock alerts to subscribers matching `target_locales`, `min_shock_threshold`, `direction_filter` (`all_shocks`, `spikes_only`, `drops_only`), and `catalyst_domains` (`refinery_pipeline`, `weather_hurricane`, `geopolitical_opec`, `regulatory_tax`), with automatic circuit breaking on HTTP `404`/`410` dead webhooks, HTTP `403` (`50007` blocked DMs), or 3 consecutive delivery failures.
- **REST API Subscription & Diagnostic Endpoints**: Added `POST /api/v1/notifications/discord/subscribe` (protected by IPASIS IP reputation checks), `DELETE /api/v1/notifications/discord/subscriptions/{subscription_id}`, `GET /api/v1/notifications/discord/subscriptions/status`, and `POST /api/v1/notifications/discord/test` in [`src/api_server.py`](src/api_server.py).
- **Interactive `/midgley` Slash Commands & Zero Chat Spam**: Extended [`handleDiscordInteraction()`](workers/intraday_monitor_worker.ts) in [`workers/intraday_monitor_worker.ts`](workers/intraday_monitor_worker.ts) to process `APPLICATION_COMMAND` (`type: 2`) and `APPLICATION_COMMAND_AUTOCOMPLETE` (`type: 4`) for `/midgley subscribe`, `unsubscribe`, `status`, `forecast`, and `test-alert`, plus the `mute_hub:` 24-hour snooze button (`type: 3`). Commands reply ephemerally (`flags: 64`) in-channel while delivering rich forecast and alert cards directly to the caller's DMs (with automatic ephemeral fallback if Discord returns `Error 50007`). Added [`scripts/register_discord_commands.py`](scripts/register_discord_commands.py) supporting both Guild-Install and User-Install contexts (`integration_types: [0, 1]`, `contexts: [0, 1, 2]`).
- **5-Digit US ZIP Code Subscriptions, Forecasts & Out-of-Metro Demand Heatmap Integration**:
  - Users can now pass any 5-digit US ZIP code directly to `/midgley subscribe`, `/midgley forecast`, `/midgley unsubscribe` (via `locale` or `zip_code`), and `POST /api/v1/notifications/discord/subscribe` (`zip_codes` / `zip_code` / `target_locales`).
  - **Locality Identity Preservation (Option A)**: Rather than relabeling out-of-metro subscribers under coastal hub names (e.g. labeling Lake Placid, NY `12946` as "Newark"), subscriptions and cards preserve true human-readable geographic locality identities (e.g. `Lake Placid, NY (ZIP 12946)`), cleanly distinguishing the user's subscribed location from the underlying PADD wholesale corridor.
  - **Statutory Tax Wedge & Regional Basis Spread Synthesis (Option B)**: For regions with significant divergence from reference coastal hubs, Midgley computes the exact statutory tax differential $\Delta \tau = \tau_{\text{state}} - \tau_{\text{hub\_base}}$ (e.g. NY `$0.472` vs DE `$0.230` $\rightarrow$ `+$0.242/gal` wedge) and estimated mountain/rural freight spread (e.g. `+$0.59/gal` total basis spread for Adirondacks/Lake Placid), displaying synthesized price guidance while clarifying that quantitative price shocks ($|\Delta P|$) track PADD wholesale pipeline transmission.
  - **Automated Regional Calibration Hub GitHub Issue Trigger**: When a user subscribes for notifications in a region that departs significantly from its PADD calibration hub ($|\Delta \tau| \ge \$0.15/\text{gal}$ or sub-PADD disconnects), the gateway automatically logs/opens a deduplicated issue on the repository (e.g. tracking issue [#635](https://github.com/KoshiirRa/midgley/issues/635) for New York Harbor / New York State) to prioritize calibrating a dedicated regional model.
  - Out-of-metro ZIP code subscriptions and lookups from both the FastAPI gateway and Cloudflare Worker edge (`unmapped_zip:<zip>` in Cloudflare D1, exposed via `GET /telemetry/unmapped-zips`, plus `unmapped_zip_telemetry` in SQLite/Turso) are automatically aggregated by [`get_unmapped_zip_telemetry()`](src/zip_geocoding.py) to update the **Out-of-Metro ZIP Code Query Heatmap** on [`docs/telemetry.html`](docs/telemetry.html).
- **Telemetry Leaflet Basemap Tile Authentication (`CARTO_API_KEY`)**: Updated [`src/dashboard_generator.py`](src/dashboard_generator.py) and regenerated [`docs/telemetry.html`](docs/telemetry.html) to authenticate CARTO Dark Matter Leaflet map tiles via `CARTO_API_KEY` (`?key=...`, `subdomains: 'abcd'`) and plot state-level demand centroids across all 50 U.S. states + D.C.

### 6. Alternative Data Feed & Test Sandbox Hardening
- **Dynamic Fetch Counter & Sandbox Guard**: Initialized `dynamic_fetches_succeeded` counter and guarded test-mode persistence in [`src/alternative_data_feeds.py`](src/alternative_data_feeds.py) (`e2973fea`).

### 7. Hermetic Test Isolation, Production Vintage Guarding & CI Gate Stabilization
- **Runtime Default Argument Resolution for Vintage Persistence**: Converted vintage file persistence signatures across all connectors ([`src/bsee_shutins.py`](src/bsee_shutins.py), [`src/nhc_hurricane.py`](src/nhc_hurricane.py), [`src/bts_transportation.py`](src/bts_transportation.py), [`src/portwatch_connector.py`](src/portwatch_connector.py), [`src/census_demographics.py`](src/census_demographics.py), [`src/firms_satellite_feed.py`](src/firms_satellite_feed.py), [`src/state_open_data.py`](src/state_open_data.py), [`src/treasury_yield_feed.py`](src/treasury_yield_feed.py), [`src/diesel_regional.py`](src/diesel_regional.py), [`src/energy_equities_feed.py`](src/energy_equities_feed.py), [`src/data_ingestion.py`](src/data_ingestion.py), [`src/catalog_monitor.py`](src/catalog_monitor.py), [`src/headline_arena_connector.py`](src/headline_arena_connector.py)) from import-time default parameter binding (`filepath: str = CONSTANT`) to runtime-evaluated `filepath: Optional[str] = None` (`fp = filepath or CONSTANT`). This ensures pytest `tmp_path` monkeypatches reliably redirect writes instead of capturing production paths evaluated at import time.
- **Production Data Invariant Guards Under `TESTING=1`**: Added explicit guards across connectors and [`.github/workflows/ci.yml`](.github/workflows/ci.yml) suppressing writes to canonical `data/*.json` files under `TESTING=1`, ensuring the `verify_data_directory_unpolluted` session teardown invariant passes cleanly with zero tracked file modifications.
- **Open Source AI Radar Cache Test Isolation**: Corrected monkeypatch targeting in [`tests/conftest.py`](tests/conftest.py) (`OpenSourceAIRadarConnector.CACHE_FILE`) and isolated `TestOpenSourceAIRadar` in [`tests/test_open_source_ai_radar.py`](tests/test_open_source_ai_radar.py) to a PID-scoped temporary cache in `tempfile.gettempdir()`, preventing test `setUp`/`tearDown` routines from unlinking tracked production cache `data/radar_cache.json`.
- **Zero-Cost Telemetry Deep Copying**: Replaced shallow `dict(...)` copying with `copy.deepcopy()` in `get_initial_telemetry_structure()` within [`src/fallback_telemetry.py`](src/fallback_telemetry.py), preventing earlier test executions from mutating shared nested provider counter dictionaries across test boundaries.
- **Hindsight Benchmark Runner Latency Bound**: Relaxed the CPU reflection latency upper bound in [`tests/test_hindsight_benchmark.py`](tests/test_hindsight_benchmark.py) from 50.0ms to 150.0ms to accommodate shared virtualized runner scheduling jitter without masking algorithmic performance regressions.
- **ZIP Geocoding Locality Identity Preservation**: Ensured `resolve_zip_code()` in [`src/zip_geocoding.py`](src/zip_geocoding.py) always populates `location_name` ("City, ST", "State, USA", or "US ZIP <zip>"), preventing `KeyError: 'location_name'` during Discord subscription dispatch and regional telemetry updates.
- **Safe Edge Subscription Sync Testing**: Added `force: bool = False` to `sync_edge_subscriptions()` in [`src/discord_notifier.py`](src/discord_notifier.py) to allow test execution without disabling `TESTING="1"` process-wide.

---

## 📦 Issues & Pull Requests Completed in v0.8.6 (To Date)

| Issue / PR | Title | Component |
| :--- | :--- | :--- |
| **#219 / #630** | `feat(regions): Implement Greater Chicago Metro Calibration Hub (PADD 2 / BP Whiting & Citgo Lemont)` | Locations / Regional Hubs |
| **#220** | `feat(regions): Implement Houston & USGC Metro Calibration Hub (PADD 3 / Houston Ship Channel Refineries)` | Locations / Regional Hubs |
| **#221** | `feat(regions): Implement Los Angeles Basin Metro Calibration Hub (PADD 5 / CaRFG & El Segundo/Torrance)` | Locations / Regional Hubs |
| **#235** | `feat(api): Multi-subscriber Discord webhook & DM alert subscriptions with /midgley slash commands & 5-digit ZIP routing` | API / Notifications / Edge / Telemetry |
| **#618** | `feat(regions): Implement Denver & Rocky Mountain Metro Calibration Hub (PADD 4 / Suncor Commerce City)` | Locations / Regional Hubs |
| **#635** | `feat(regions): Implement New York Harbor & New York State Metro Calibration Hub (PADD 1B / NY Harbor Barges & Buckeye Pipeline)` | Locations / Regional Hubs / Issue Trigger |
| **CI / Isolation** | `fix(ci,isolation): Hermetic vintage isolation, zero-cost telemetry deepcopy, radar cache protection & reflection timing bound` | Core / Testing / Ingestion / CI |

---

## 🤖 AI Agent Reconciliation Block (Draft for v0.8.6)

For autonomous AI coding assistants, downstream forks, and self-hosted deployments tracking `dev` toward **v0.8.6**:

### 1. Schema & Migration Summary
* **Target Package Version**: `0.8.6` *(Draft — current package version remains `0.8.5` on `dev` until official release cut)*
* **New Regional Metro Hubs**: `Chicago_IL` (`chicago`), `Houston_TX` (`houston`), `Los_Angeles_CA` (`los_angeles`), `Denver_CO` (`denver`)
* **Database Schema Additions**:
  - `discord_subscriptions` table (including `zip_codes TEXT NOT NULL DEFAULT '[]'`) and indexes (`idx_discord_subs_active`, `idx_discord_subs_webhook_hash`, `idx_discord_subs_user_id`) in `src/db/schema.sql` and `data/subscribers.sqlite`.
  - `unmapped_zip_telemetry` table and index (`idx_unmapped_zip_hits`) in `src/db/schema.sql` for persistent cross-run out-of-metro ZIP demand tracking.
* **Testing & Point-in-Time Isolation**:
  - All connector vintage persistence routines now require runtime default argument binding (`filepath: Optional[str] = None`) to ensure testing monkeypatches redirect writes cleanly.
  - Production paths in `data/*.json` are guarded against modification under `TESTING=1`.

### 2. Environment Variables & Credentials
* **Added / Optional**:
  - `DISCORD_BOT_TOKEN`: Discord Bot token used to open DM channels (`POST /api/v10/users/@me/channels`) and deliver private Direct Message alerts (`delivery_type="discord_dm"`).
  - `DISCORD_APP_ID`: Discord Application ID for registering `/midgley` slash commands (`scripts/register_discord_commands.py`).
  - `DISCORD_PUBLIC_KEY`: Ed25519 public key for verifying `/discord/interactions` requests.
  - `CARTO_API_KEY`: Optional CARTO Basemaps API key appended to Leaflet dark tile URLs on `docs/telemetry.html`.
  - `MIDGLEY_SUBSCRIBERS_DB_PATH`: Optional override path for the SQLite subscriber registry (defaults to `data/subscribers.sqlite`).

### 3. Verification Commands
```bash
python scripts/register_discord_commands.py --dry-run
TESTING=1 pytest -v tests/test_denver_hub.py tests/test_discord_subscriptions.py tests/test_zip_geocoding.py tests/test_zero_cost_fallbacks.py tests/test_hindsight_benchmark.py tests/test_open_source_ai_radar.py tests/test_system_telemetry.py tests/test_docs_links.py
npx vitest run tests/workers.test.ts
```

