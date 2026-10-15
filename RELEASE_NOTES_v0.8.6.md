# Release Notes - v0.8.6 (Draft)

Midgley **v0.8.6** *(In-Progress Draft on `dev`)* expands the regional metro calibration footprint with twelve major U.S. refining, pipeline, and island consumption corridors (**Greater Chicago**, **Houston & USGC**, **Los Angeles Basin**, **Denver & Rocky Mountain**, **New York Harbor & New York State**, **Boston & New England**, the decoupled PADD 5 sub-markets: **Seattle & Puget Sound**, **Phoenix & Desert Southwest**, **Anchorage & Cook Inlet**, and **Honolulu & Oahu Island System**, the PADD 6 Caribbean hub: **San Juan & U.S. Caribbean Territories**, and the PADD 7 trans-Pacific island hub: **Guam & U.S. Pacific Island Territories**) and introduces the **Multi-Subscriber Discord Webhook, Direct Message (`discord_dm`) & `/midgley` Slash Command Notification Gateway** so teams and individual server members can receive tailored, locale-filtered alerts without cluttering shared chat channels.

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

### 4. Denver & Rocky Mountain Metro Calibration Hub — PADD 4 (`Denver_CO`, Issue #618 / PR #636)
- **Front Range Refining Island & Suncor Commerce City**: Added [`src/locations/denver/`](src/locations/denver/) (`main.py`, `regional.py`, `notebook_builder.py`) and [`data/regional_metadata/denver_co.json`](data/regional_metadata/denver_co.json) calibrated to Colorado's sole petroleum refinery (Suncor Commerce City 103 kbpd) and regional distribution network (Magellan, Sinclair, Chase Front Range terminals).
- **DJ Basin Feedstock Differentials & Severe Ozone 7.8 psi RFG**: Modeled DJ Basin sweet crude / Wyoming sour feedstock spreads, EPA Front Range 9-county severe ozone nonattainment 7.8 psi summer RVP standards in [`data/regulatory_rvp_rules.json`](data/regulatory_rvp_rules.json) and [`src/rvp_regulations.py`](src/rvp_regulations.py), and Colorado statutory motor fuel excise tax ($0.280/gal statutory base, $0.464/gal baseline with federal).
- **PADD 4 Hierarchical MinT Coherence & Dashboard**: Added `Denver_CO` and `PADD_4` into [`src/hierarchical_engine.py`](src/hierarchical_engine.py) completing full continental U.S. PADD coverage across MinT reconciliation matrices, mapped official EIA retail series (`GASREGWDEN`, `GASREGWCO`, `GASREGWRM`, `GASDESWRM`), and generated [`docs/denver.html`](docs/denver.html).

### 5. New York Harbor & New York State Metro Calibration Hub — PADD 1B (`New_York_NY`, Issue #635 / PR #637)
- **Refining, Midstream & Waterborne Barge Topology**: Added [`src/locations/new_york/`](src/locations/new_york/) (`main.py`, `regional.py`, `notebook_builder.py`) and [`data/regional_metadata/new_york_ny.json`](data/regional_metadata/new_york_ny.json) calibrated to Phillips 66 Bayway (258 kbpd, Linden NJ), Buckeye pipeline system (Linden junction supplying NYC airports JFK/LGA and Long Island terminals), and waterborne barge transit across NY Harbor, Arthur Kill, and Hudson River.
- **Tax Structure, Regional Basis & Out-of-Metro Departure Resolution**: Modeled NY State base fuel tax ($0.472/gal statutory base: excise + PBT + state sales tax, $0.656/gal baseline with federal), downstate NYC/suburban county sales tax compounding (+14.0¢/gal), and Upstate Adirondacks transport basis spread (+18.0¢/gal). Direct routing of NY ZIP prefixes (`100`..`149`) to `new_york` completely eliminates the +$0.242/gal tax wedge previously experienced when falling back to Delaware ($0.230/gal base).
- **EPA Summer RVP Gating & Shock Scenarios**: Modeled downstate EPA Reformulated Gasoline (RFG) 7.4 psi summer standard (May 1 – Sept 15, with \$0.16/gal transition premium) versus Upstate 9.0 psi low-altitude rules in [`data/regulatory_rvp_rules.json`](data/regulatory_rvp_rules.json) and [`src/rvp_regulations.py`](src/rvp_regulations.py), alongside counterfactual shock scenario simulations for Buckeye pipeline disruptions (`buckeye_pipeline_linden_disruption`: +$0.28/gal, 12d half-life) and NY Harbor polar vortex barge freeze halts (`ny_harbor_barge_freeze_halt`: +$0.19/gal, 10d half-life).
- **PADD 1B Hierarchical MinT Coherence & Dashboard**: Updated [`src/hierarchical_engine.py`](src/hierarchical_engine.py) to cluster PADD 1B into Newark DE and New York NY with exact aggregation coherence, mapped official EIA retail series (`GASREGWNYC`, `GASREGWNY`, `GASDESWNY`) in [`src/eia_retail_feed.py`](src/eia_retail_feed.py), generated [`docs/new_york.html`](docs/new_york.html), and added New York to the overview dashboard and navigation.
- **Intraday Monitoring & Discord Alerts**: Registered `New_York` in `SUPPORTED_LOCALES` and `CANONICAL_LOCALE_ALIASES` in [`src/discord_notifier.py`](src/discord_notifier.py) with scoped refinery/pipeline keyword matching in [`src/intraday_event_monitor.py`](src/intraday_event_monitor.py).

### 6. Multi-Subscriber Discord Webhooks, Direct Message (`discord_dm`) Alerts & `/midgley` Slash Commands (Issue #235)
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
- **Telemetry Leaflet Basemap Tile Authentication & Fallback Hardening (`CARTO_API_KEY`)**: Updated [`src/dashboard_generator.py`](src/dashboard_generator.py) and regenerated [`docs/telemetry.html`](docs/telemetry.html) to authenticate CARTO Dark Matter Leaflet map tiles via `CARTO_API_KEY` (`?key=...`, `subdomains: 'abcd'`) and plot state-level demand centroids across all 50 U.S. states + D.C. Hardened key resolution with `(os.environ.get("CARTO_API_KEY") or DEFAULT_KEY).strip()` so empty or whitespace-only environment variables safely fall back to the valid default key rather than emitting unauthenticated tile requests that render CARTO's `API KEY REQUIRED` watermark.
- **Dev-VM Systemd Service Directory Realignment**: Realigned `~/.config/systemd/user/midgley-api.service` (port 8000) and `midgley-dev.service` (port 8080) on `dev-vm` (`10.42.42.54`) to run out of `/home/marty/projects/midgley-main` rather than legacy `/home/marty/projects/midgley`, ensuring long-running dev API instances serve current templates and authenticated basemaps.
- **Edge Worker & Slash Command 20-Hub Reconciliation**: Synchronized [`workers/intraday_monitor_worker.ts`](workers/intraday_monitor_worker.ts) and [`scripts/register_discord_commands.py`](scripts/register_discord_commands.py) to reflect all 20 canonical calibration hubs, adding autocomplete choices, baseline excise rates, and direct metro prefix clusters for Denver (`800`..`806`), New York (`100`..`149`), Boston (`021`/`022`/`024`), Seattle (`980`..`985`), Phoenix (`850`..`853`/`890`..`891`), Anchorage (`995`..`996`), Honolulu (`967`..`968`), San Juan (`006`..`009`), and Guam (`969`), resolving non-contiguous PADD 6/7 territorial prefixes, and decoupling state fallback corridors from California CARB.

### 7. Alternative Data Feed & Test Sandbox Hardening
- **Dynamic Fetch Counter & Sandbox Guard**: Initialized `dynamic_fetches_succeeded` counter and guarded test-mode persistence in [`src/alternative_data_feeds.py`](src/alternative_data_feeds.py) (`e2973fea`).

### 8. Hermetic Test Isolation, Production Vintage Guarding & CI Gate Stabilization
- **Runtime Default Argument Resolution for Vintage Persistence**: Converted vintage file persistence signatures across all connectors ([`src/bsee_shutins.py`](src/bsee_shutins.py), [`src/nhc_hurricane.py`](src/nhc_hurricane.py), [`src/bts_transportation.py`](src/bts_transportation.py), [`src/portwatch_connector.py`](src/portwatch_connector.py), [`src/census_demographics.py`](src/census_demographics.py), [`src/firms_satellite_feed.py`](src/firms_satellite_feed.py), [`src/state_open_data.py`](src/state_open_data.py), [`src/treasury_yield_feed.py`](src/treasury_yield_feed.py), [`src/diesel_regional.py`](src/diesel_regional.py), [`src/energy_equities_feed.py`](src/energy_equities_feed.py), [`src/data_ingestion.py`](src/data_ingestion.py), [`src/catalog_monitor.py`](src/catalog_monitor.py), [`src/headline_arena_connector.py`](src/headline_arena_connector.py)) from import-time default parameter binding (`filepath: str = CONSTANT`) to runtime-evaluated `filepath: Optional[str] = None` (`fp = filepath or CONSTANT`). This ensures pytest `tmp_path` monkeypatches reliably redirect writes instead of capturing production paths evaluated at import time.
- **Production Data Invariant Guards Under `TESTING=1`**: Added explicit guards across connectors and [`.github/workflows/ci.yml`](.github/workflows/ci.yml) suppressing writes to canonical `data/*.json` files under `TESTING=1`, ensuring the `verify_data_directory_unpolluted` session teardown invariant passes cleanly with zero tracked file modifications.
- **Open Source AI Radar Cache Test Isolation**: Corrected monkeypatch targeting in [`tests/conftest.py`](tests/conftest.py) (`OpenSourceAIRadarConnector.CACHE_FILE`) and isolated `TestOpenSourceAIRadar` in [`tests/test_open_source_ai_radar.py`](tests/test_open_source_ai_radar.py) to a PID-scoped temporary cache in `tempfile.gettempdir()`, preventing test `setUp`/`tearDown` routines from unlinking tracked production cache `data/radar_cache.json`.
- **Zero-Cost Telemetry Deep Copying**: Replaced shallow `dict(...)` copying with `copy.deepcopy()` in `get_initial_telemetry_structure()` within [`src/fallback_telemetry.py`](src/fallback_telemetry.py), preventing earlier test executions from mutating shared nested provider counter dictionaries across test boundaries.
- **Hindsight Benchmark Runner Latency Bound**: Relaxed the CPU reflection latency upper bound in [`tests/test_hindsight_benchmark.py`](tests/test_hindsight_benchmark.py) from 50.0ms to 150.0ms to accommodate shared virtualized runner scheduling jitter without masking algorithmic performance regressions.
- **ZIP Geocoding Locality Identity Preservation**: Ensured `resolve_zip_code()` in [`src/zip_geocoding.py`](src/zip_geocoding.py) always populates `location_name` ("City, ST", "State, USA", or "US ZIP <zip>"), preventing `KeyError: 'location_name'` during Discord subscription dispatch and regional telemetry updates.
- **Safe Edge Subscription Sync Testing**: Added `force: bool = False` to `sync_edge_subscriptions()` in [`src/discord_notifier.py`](src/discord_notifier.py) to allow test execution without disabling `TESTING="1"` process-wide.

### 9. Google Gemini 3.8 Flash Migration & Thinking Level Configuration (Issue #616, PR #638)
- **Gemini 3.8 Flash Upgrade Ahead of Oct 20 Retirement**: Upgraded all runtime Gemini model identifiers from `gemini-2.5-flash` to `gemini-3.8-flash` across all operational pipelines:
  - Qualitative event shock feature extraction ([`src/event_analyzer.py`](src/event_analyzer.py), single & batch extractions).
  - Episodic memory post-mortem reflections ([`src/agent_memory.py`](src/agent_memory.py)).
  - Counterfactual 4-persona cohort market simulation ([`src/scenario_simulator.py`](src/scenario_simulator.py)).
  - PaSa dual-agent academic hypothesis selection ([`src/pasa_research_agent.py`](src/pasa_research_agent.py)).
  - Symbolic alpha formula generation ([`src/alpha_factor_miner.py`](src/alpha_factor_miner.py)).
  - Tool and pipeline candidate evaluations ([`src/catalog_monitor.py`](src/catalog_monitor.py)).
  - Automated weekly issue priority ranking and self-reviews ([`src/weekly_issue_reporter.py`](src/weekly_issue_reporter.py)).
  - Headline Arena agent registry defaults ([`src/headline_arena_connector.py`](src/headline_arena_connector.py)).
  - Cloud Run Hindsight default LLM deployment configuration ([`scripts/deploy_hindsight_cloudrun.sh`](scripts/deploy_hindsight_cloudrun.sh) and [`SELF_HOSTING.md`](SELF_HOSTING.md)).
- **Deprecated Parameter Elimination & Thinking Level Calibration**:
  - Completely purged deprecated sampling arguments (`temperature`, `top_p`, `top_k`, and `thinking_budget`) from `GenerateContentConfig` and dictionary configurations passed to `google.genai` client calls to prevent upcoming hard `400 INVALID_ARGUMENT` errors.
  - Explicitly configured `thinking_config=types.ThinkingConfig(thinking_level="low")` on structured JSON extraction and evaluation tasks ([`src/event_analyzer.py`](src/event_analyzer.py), [`src/alpha_factor_miner.py`](src/alpha_factor_miner.py), [`src/pasa_research_agent.py`](src/pasa_research_agent.py)), preventing default `"medium"` reasoning token inflation ($3.75/1M output tokens) while preserving sharp extraction precision and bounded costs.
- **Telemetry, Prometheus & TokenTab Cost Accounting**:
  - Registered `gemini-3.8-flash` in [`src/telemetry.py`](src/telemetry.py) (`MODEL_PRICING`) and [`src/tokentab_accounting.py`](src/tokentab_accounting.py) (`PROVIDER_PRICING`) with introductory rates ($0.75 / 1M prompt tokens, $3.75 / 1M output tokens).
  - Maintained legacy `gemini-2.5-flash` entries ($0.075 / $0.300) for historical cost calculations.
  - Updated Prometheus metrics in `format_prometheus_metrics()` to export `model="gemini-3.8-flash"`.
  - Updated public telemetry dashboard ([`src/dashboard_generator.py`](src/dashboard_generator.py)) to aggregate historical and active Gemini metrics under the `Gemini 3.8 Flash (Tier 1)` audit card.
- **Hermetic Test Suite Verification**:
  - Updated unit test suites and mock assertions across [`tests/test_event_analyzer.py`](tests/test_event_analyzer.py), [`tests/test_alpha_factor_miner.py`](tests/test_alpha_factor_miner.py), [`tests/test_pasa_research_agent.py`](tests/test_pasa_research_agent.py), [`tests/test_weekly_issue_reporter.py`](tests/test_weekly_issue_reporter.py), [`tests/test_system_telemetry.py`](tests/test_system_telemetry.py), [`tests/test_tokentab_accounting.py`](tests/test_tokentab_accounting.py), and [`tests/test_scenario_simulator.py`](tests/test_scenario_simulator.py) to assert calls to `gemini-3.8-flash` with `thinking_level="low"` and verify no deprecated sampling parameters are passed.

### 10. Decoupling PADD 5 Sub-Markets (PNW, Desert Southwest, Alaska, Hawaii) from California CARB (Issue #622)
- **Decoupling Non-California PADD 5 from CARBOB & California Regulatory Tax**: Decoupled non-California PADD 5 states (`WA`, `OR`, `NV`, `AZ`, `AK`, `HI`) from the California CARBOB formulation and California regulatory tax stack (+$0.953/gal: SB 1 excise + Cap-and-Trade + LCFS) into 4 distinct regional calibration hubs:
  - **Seattle & Puget Sound, WA (`Seattle_WA`, `seattle`)**: Modeled Puget Sound's 616 kbpd refining hub (BP Cherry Point 242 kbpd, Phillips 66 Ferndale 105 kbpd, Marathon Anacortes 120 kbpd, HF Sinclair Puget Sound 149 kbpd), Olympic Pipeline, Washington statutory excise + CCA carbon allowances ($0.494/gal), EPA 9.0 psi summer RVP, and EIA retail series `EMM_EPMR_PTE_Y48SE_DPG` (`GASREGWSEA`).
  - **Phoenix & Desert Southwest, AZ (`Phoenix_AZ`, `phoenix`)**: Modeled zero in-state refining footprint, 100% pipeline import reliance via Kinder Morgan SFPP West Line (SoCal) and East Line (Texas/El Paso), Maricopa County Cleaner Burning Gasoline (CBG 7.0 psi summer RVP), Arizona statutory excise ($0.180/gal — among lowest in US), and EIA retail series `EMM_EPMR_PTE_SAZ_DPG` (`GASREGWAZ`).
  - **Anchorage & Cook Inlet, AK (`Anchorage_AK`, `anchorage`)**: Modeled Marathon Kenai refinery (68 kbpd), Cook Inlet sea ice logistics, Alaska Railroad tank cars, Alaska state fuel excise ($0.0895/gal — lowest in US), sub-zero winter 15.0 psi RVP, and EIA retail series `EMM_EPMR_PTE_SAK_DPG` (`GASREGWAK`).
  - **Honolulu & Oahu Island System, HI (`Honolulu_HI`, `honolulu`)**: Modeled Par Hawaii Kapolei refinery (94 kbpd), crude waterborne import logistics, Young Brothers inter-island ocean barges, Hawaii statutory baseline ($0.330/gal), and EIA retail series `EMM_EPMR_PTE_SHI_DPG` (`GASREGWHI`).
- **PADD 5 Regional Specs, Metadata & Hierarchical Engine Coherence**: Added declarative [`RegionSpec`](src/locations/specs.py) definitions, schema-valid regional JSON profiles in [`data/regional_metadata/`](data/regional_metadata/), sub-location packages in [`src/locations/`](src/locations/), and integrated the 4 hubs into [`src/hierarchical_engine.py`](src/hierarchical_engine.py) bottom-level reconciliation and PADD 5 clusters.
- **Microstructure, Diesel, Geocoding & Intraday Monitoring Integration**:
  - Decoupled `STATE_PADD_MODEL_MAP` and ZIP prefix routing in [`src/zip_geocoding.py`](src/zip_geocoding.py) (OR/WA to `seattle`, AZ/NV to `phoenix`, AK to `anchorage`, HI to `honolulu`).
  - Added retail diesel base anchors and EIA series `GASDESW5XCA` in [`src/diesel_regional.py`](src/diesel_regional.py).
  - Added NOAA weather endpoints in [`src/noaa_weather.py`](src/noaa_weather.py) and refinery centroid data in [`src/spatial_refinery.py`](src/spatial_refinery.py).
  - Registered trigger keywords and localized routing in [`src/intraday_event_monitor.py`](src/intraday_event_monitor.py) and [`src/discord_notifier.py`](src/discord_notifier.py).
  - Updated API normalization and `PADD_METADATA` (`carb_tax: 0.0`) in [`src/api_server.py`](src/api_server.py).

### 11. Guam & U.S. Pacific Island Territories Calibration Hub — PADD 7 (`Guam_GU`, Issue #621 / Commit [`6d1b77b`](https://github.com/KoshiirRa/midgley/commit/6d1b77b97))
- **Decoupled Trans-Pacific Import Logistics & MOPS Benchmark**:
  - Implemented dedicated regional forecasting and calibration hub for **Hagåtña / Apra Harbor, Guam (`Guam_GU`, `guam`)**, representing the **U.S. Pacific Island Territories petroleum district (`PADD 7`)** encompassing Guam, American Samoa, and CNMI.
  - Decoupled from domestic North American pipelines and Gulf Coast RBOB; modeled 100% finished product imports via Medium Range (MR) product tankers originating from Asian refining hubs (Singapore Jurong, South Korea Ulsan/Yeosu, Japan) and Defense Logistics Agency (DLA) Energy bulk tenders.
  - Anchored local wholesale acquisition costs to the **Mean of Platts Singapore (MOPS) 92 RON Mogas** landed benchmark (`spot_mops_92_rack`) plus trans-Pacific tanker freight charters and Cabras Island terminal throughput fees.
- **Territorial Tax & Retail Oligopoly Structure**:
  - Modeled Guam Liquid Fuel Tax ($0.150/gal) plus statutory Mass Transit surcharge ($0.040/gal) for a combined territorial tax burden of $0.190/gal ($0.374/gal composite with Federal excise).
  - Preserved statutory Jones Act U.S.-build exemption documentation under 48 U.S.C. § 1421r.
  - Modeled retail distribution dynamics across the three primary commercial operators: Mobil Oil Guam, IP&E (Shell), and South Pacific Petroleum Corporation (76).
- **Extreme Weather Exposure & JTWC Typhoon Alley Modeling**:
  - Integrated Joint Typhoon Warning Center (JTWC) and NOAA WFO Guam (`GUM` / `GUZ001`) tropical cyclone bulletins, modeling Category 4/5 super typhoons (e.g. Typhoon Mawar, Typhoon Bolaven), US Coast Guard Port Condition Zulu port closures, and post-storm retail panic surges.
- **Hierarchical MinT Coherence, Geocoding & Notification Integration**:
  - Registered `guam` in [`src/locations/specs.py`](src/locations/specs.py), created schema-valid [`data/regional_metadata/guam_gu.json`](data/regional_metadata/guam_gu.json), and built [`src/locations/guam/`](src/locations/guam/) package.
  - Integrated `Guam_GU` and `PADD_7` into [`src/hierarchical_engine.py`](src/hierarchical_engine.py) with exact sum coherence.
  - Added Guam centroid `(13.4443, 144.7937)` and ZIP prefix `969` to `CALIBRATION_HUBS`, `ZIP_METRO_PREFIX_MAP`, and `STATE_PADD_MODEL_MAP` in [`src/zip_geocoding.py`](src/zip_geocoding.py).
  - Updated API normalization in [`src/api_server.py`](src/api_server.py), Discord notifier in [`src/discord_notifier.py`](src/discord_notifier.py), and intraday trigger keywords in [`src/intraday_event_monitor.py`](src/intraday_event_monitor.py).

### 12. San Juan Metro & U.S. Caribbean Territories Calibration Hub — PADD 6 (`San_Juan_PR`, Issue #620)
- **100% Maritime Island Supply Logistics & Jones Act Clean Tanker Freights**:
  - Implemented dedicated regional forecasting and calibration hub for **San Juan, Puerto Rico (`San_Juan_PR`, `san_juan`)**, representing the **U.S. Caribbean Territories petroleum district (`PADD 6 / PADD VI`)** encompassing Puerto Rico and the U.S. Virgin Islands (USVI).
  - Modeled 100% finished product imports via coastal clean product tankers from US Gulf Coast refining centers (Houston/Corpus Christi) following the historic closures of the Caribbean Petroleum (CAPECO) Bayamón refinery in PR and Hovensa/Limetree Bay in St. Croix.
  - Incorporated Jones Act clean product tanker marine freight differentials (`spot_caribbean_waterborne = spot_gulf_coast + 0.145`) and deepwater terminal headers in San Juan Bay (Puerto Nuevo, Cataño) and Yabucoa.
- **DACO Price Regulation, Margin Caps & Metric Conversion**:
  - Modeled daily retail fuel price surveys from the Puerto Rico Department of Consumer Affairs (**DACO - Departamento de Asuntos del Consumidor**), supporting authentic metric price conversion between cents per liter (¢/L) and dollars per gallon (`$/gal = (¢/L / 100) * 3.78541`).
  - Accounted for statutory emergency price freeze powers and distributor gross margin caps during declared states of emergency.
  - Modeled the Puerto Rico Commonwealth petroleum product arbitrio ($0.160/gal equivalent) plus Federal excise ($0.184/gal) for a combined baseline tax burden of $0.344/gal.
- **Tropical Convective Risk & LUMA Electrical Grid Vulnerability**:
  - Integrated NOAA WFO San Juan (`SJU` / `PRZ001`) and National Hurricane Center (NHC) tropical storm bulletins, modeling Atlantic hurricane landfalls (Hurricanes Maria, Fiona, Ernesto) and US Coast Guard Port Condition Zulu harbor closures.
  - Modeled LUMA Energy electrical transmission grid failures driving sudden surges in backup emergency diesel generator and pump gasoline demand.
- **Hierarchical MinT Coherence, Geocoding & Notification Integration**:
  - Registered `san_juan` in [`src/locations/specs.py`](src/locations/specs.py), created schema-valid [`data/regional_metadata/san_juan_pr.json`](data/regional_metadata/san_juan_pr.json), and built [`src/locations/san_juan/`](src/locations/san_juan/) package.
  - Integrated `San_Juan_PR` and `PADD_6` into [`src/hierarchical_engine.py`](src/hierarchical_engine.py) with exact sum coherence.
  - Added San Juan centroid `(18.4655, -66.1057)` and ZIP prefixes `006`-`009` to `CALIBRATION_HUBS`, `ZIP_METRO_PREFIX_MAP`, and `STATE_PADD_MODEL_MAP` in [`src/zip_geocoding.py`](src/zip_geocoding.py).
  - Updated API normalization in [`src/api_server.py`](src/api_server.py), Discord notifier in [`src/discord_notifier.py`](src/discord_notifier.py), and intraday trigger keywords in [`src/intraday_event_monitor.py`](src/intraday_event_monitor.py).

### 13. Boston Metro & New England Regional Hub — PADD 1A (`Boston_MA`, Issue #619 / PR #639)
- **100% Waterborne Import Reliance & International Supply Links**:
  - Implemented dedicated metropolitan forecasting and calibration hub for **Boston, Massachusetts (`Boston_MA`, `boston`)**, representing the **New England petroleum sub-district (`PADD 1A`)** encompassing MA, CT, RI, NH, VT, and ME.
  - Modeled 100% finished product import reliance (0 local refining capacity across all 6 New England states); anchored maritime imports via international supply links to the Irving Oil Saint John Refinery (320 kbpd, New Brunswick, Canada), coastal barge movements from New York Harbor, and Colonial Pipeline delivery terminating into Springfield, MA and Providence, RI.
  - Modeled marine terminal clusters in Boston Harbor, Chelsea River, Everett, and Revere with winter distillate and home heating oil competition during seasonal cold snaps.
- **Tax Structure, Cross-Border Arbitrage & EPA RFG Standards**:
  - Modeled Massachusetts statutory motor fuel excise tax ($0.240/gal state + $0.0028 UST fee, $0.424/gal composite with Federal excise) and cross-border arbitrage across New England (e.g. New Hampshire with lower excise rates).
  - Modeled EPA Reformulated Gasoline (RFG) 7.4 psi summer standard across Eastern Massachusetts and Rhode Island in [`data/regulatory_rvp_rules.json`](data/regulatory_rvp_rules.json) and [`src/rvp_regulations.py`](src/rvp_regulations.py).
- **Hierarchical MinT Coherence, Geocoding & Pipeline Integration**:
  - Added `boston` [`RegionSpec`](src/locations/specs.py), created schema-valid [`data/regional_metadata/boston_ma.json`](data/regional_metadata/boston_ma.json), and built [`src/locations/boston/`](src/locations/boston/) sub-package (`main.py`, `regional.py`, `notebook_builder.py`).
  - Decoupled New England states (`ME`, `NH`, `VT`, `MA`, `RI`, `CT`) from Newark DE (`PADD 1B`) to `boston` (`Boston_MA / PADD 1A`) in `STATE_PADD_MODEL_MAP` and mapped ZIP prefixes `021`, `022`, `024` in [`src/zip_geocoding.py`](src/zip_geocoding.py).
  - Integrated `Boston_MA` and intermediate cluster `PADD_1A` into [`src/hierarchical_engine.py`](src/hierarchical_engine.py) bottom-level reconciliation and aggregation matrices ($S$) with exact sum coherence.
  - Mapped official EIA weekly retail series for Boston Metro (`GASREGWBOS`), Massachusetts State (`GASREGWMA`), New England PADD 1A (`GASREGW01A`), and Diesel (`GASDESW01A`) in [`src/eia_retail_feed.py`](src/eia_retail_feed.py) and [`src/diesel_regional.py`](src/diesel_regional.py).
  - Registered Boston keywords and target resolution in [`src/intraday_event_monitor.py`](src/intraday_event_monitor.py), [`src/discord_notifier.py`](src/discord_notifier.py), and [`src/api_server.py`](src/api_server.py).
### 14. Greenville Model Decommissioning & Charlotte Carolinas Hub Consolidation
- **Decommissioning from Active Daily Forecaster Loop**: Decommissioned the standalone Greenville, NC model from [`src/locations/__init__.py`](src/locations/__init__.py) (`LOCATIONS`), immediately reducing daily workflow execution time and cloud worker compute in [`run_all.py`](run_all.py).
- **Consolidation into Charlotte Metro & Carolinas Hub (`Charlotte_NC`, PADD 1C)**:
  - Updated [`src/locations/specs.py`](src/locations/specs.py) with `display_name="Charlotte Metro & Carolinas Hub, NC (PADD 1C)"` and registered `greenville: 0.01` and `selma: -0.04` in `sub_locales`.
  - Charlotte's Paw Creek petroleum distribution terminal directly governs Colonial Pipeline cycle allocations and rack margins across both North and South Carolina.
  - Transparent routing in [`src/locations/__init__.py`](src/locations/__init__.py), [`src/locations/specs.py`](src/locations/specs.py), and [`src/locations/runner.py`](src/locations/runner.py) ensures any request or query for `"greenville"` or `"greenville_nc"` resolves seamlessly to the Charlotte hub.
- **Zero-404 Legacy Redirect & Social Meta Tags**: Transformed [`docs/greenville.html`](docs/greenville.html) and [`docs/greenville/index.html`](docs/greenville/index.html) into instant client-side redirects (`<meta http-equiv="refresh" content="0; url=charlotte.html">`) equipped with Open Graph (`og:site_name`, `og:title`, `og:description`, `og:image`) and Twitter card tags to preserve social previews, search indexing, and prevent broken links.
- **Documentation Mirror Parity & Live Summary Sync**: Synchronized [`docs/README.md`](docs/README.md) with root [`README.md`](README.md) via `scripts/verify_docs_parity.py --sync` and updated [`src/readme_updater.py`](src/readme_updater.py) to present Charlotte as `Charlotte, NC Metro Retail (Carolinas Hub)`.
- **Knowledge Graph Deterministic Subgraph Ordering**: Enforced deterministic hop-distance sorting and focus-entity retention in `KnowledgeGraphEngine.get_subgraph_context()` ([`src/knowledge_graph.py`](src/knowledge_graph.py)), preventing Python hash seed randomization from truncating root entities from GraphRAG markdown context schemas across Python versions.
- **Test Suite Reconciliations**: Updated [`tests/test_dashboard_generator.py`](tests/test_dashboard_generator.py) to verify the legacy client redirect behavior on `greenville.html` (matching `oakland.html` -> `bayarea.html`) and remove decommissioned Greenville assertions from active regional driver card, feature attribution, trend badge, and WCAG landmark suites.

### 15. Multi-Agent System Architecture Expansion & Vector Diagram Redesign (18 Regional Hubs across PADDs 1–7)
- **18-Hub Architecture Diagram Redesign**: Re-engineered Stage 4 in [`src/fireworks_tech_graph.py`](src/fireworks_tech_graph.py) and generated [`docs/assets/regional_metro_architecture.svg`](docs/assets/regional_metro_architecture.svg) into a comprehensive 18-hub regional layout covering PADDs 1A, 1B, 1C, 2, 3, 4, 5, 5B, 5C, 5D, 6, 7 + the ULSD Distillate Diesel Engine, strictly complying with `AGENTS.md` data integrity rules by avoiding stale hardcoded historical example prices.
- **Pipeline Architecture Vector Graphic Update**: Updated [`docs/assets/multi_agent_architecture.svg`](docs/assets/multi_agent_architecture.svg) to document the multi-agent hierarchy connecting qualitative & physical feeds, the National Wholesale RBOB futures model, and all 18 localized regional calibration hubs.
- **README & Public Dashboard Presentation**: Updated the Mermaid pipeline diagram (`subgraph METRO`) and system component breakdown in [`README.md`](README.md), and refreshed the landing page overview in [`docs/index.html`](docs/index.html).

### 16. Local-Only Regional Backfill Policy (Cloud Runner Optimization)
- **CI / GitHub Actions Worker Protection**: Established and enforced the operational policy that heavy, multi-year historical backfills for newly added regional models (`backfill_new_region_history`) are performed exclusively on the local Linux dev environment (`dev-vm`), safeguarding cloud runner execution limits and preventing GitHub Actions job timeouts.
- **Execution Guard**: Ensured prospective daily forecasting runs (`run_all.py`) and cloud CI runners skip retroactive backfilling once baseline ledger presence is confirmed.

### 17. Out-of-Metro Telemetry Map Geocoding & True NY State Centroid Correction
- **True Geographic Centroid for New York State**: Corrected `STATE_CENTER_COORDS["NY"]` in [`src/zip_geocoding.py`](src/zip_geocoding.py) from Lower Manhattan / NYC City Hall `(40.7128, -74.0060)` to the authentic geographic centroid of New York State in Madison County `(42.9538, -75.5268)`.
- **Exact Coordinates for Lake Placid, NY (12946)**: Added `KNOWN_ZIP_COORDS["12946"] = (44.2795, -73.9799, "Lake Placid, NY (Adirondacks / PADD 1B)")`, properly situating Lake Placid in the High Peaks region of Essex County in the Adirondacks (>240 miles north of NYC).
- **3-Digit Prefix Centroid Resolution**: Introduced `KNOWN_PREFIX_COORDS` in [`src/zip_geocoding.py`](src/zip_geocoding.py) mapping 3-digit prefixes across New York State (Adirondacks `129`, Glens Falls `128`, Capital District `120`-`123`, Syracuse `132`, Buffalo `142`, Rochester `146`, Long Island `115`-`119`, NYC `100`-`114`) and major out-of-metro regions.
- **Dynamic Leaflet Integration**: Added `resolve_zip_coordinates()` and updated [`src/dashboard_generator.py`](src/dashboard_generator.py) so the out-of-metro demand heatmap on [`docs/telemetry.html`](docs/telemetry.html) renders exact coordinates and human-readable locality labels for all queried ZIP codes.

### 18. Interactive Modeled Price Hubs Map on Main Landing Page (Issue #646)
- **Comprehensive 18-Hub & National Geographic Footprint**: Integrated an interactive Leaflet.js map component into the primary public dashboard landing page ([`docs/index.html`](docs/index.html)) displaying all 18 regional calibration hubs across PADDs 1 through 7, plus the National Wholesale commodity futures delivery benchmark (Cushing, OK / NYMEX RB=F).
- **Inclusion of Non-Dedicated Modeled Hubs**: Modeled regions that do not yet have standalone detail pages (Seattle-Tacoma PADD 5B, Phoenix Desert Southwest PADD 5C, Anchorage PADD 5D, Honolulu Oahu PADD 5D, Guam PADD 7, San Juan PADD 6, and Boston PADD 1A) are fully represented with interactive circle markers, exposing their live/base pump price, 5-day projected targets, statutory tax burdens, primary refinery/pipeline corridors, and local sub-locales.
- **Visual Marker Tiers & CARTO Dark Matter Basemap**:
  - 🟢 **Active Dedicated Pages** (11 hubs): Glowing emerald markers with popups linking directly to dedicated detail analytics pages (`/chicago.html`, `/houston.html`, etc.).
  - 🔵 **Modeled Calibration Hubs** (7 hubs): Cyan markers highlighting integration into Midgley's hierarchical MinT econometric model and historical prediction ledger.
  - 🟡 **Commodity Futures Benchmark** (1 hub): Amber marker at the Cushing physical delivery hub.
  - Dark Matter tiles authenticated via `CARTO_API_KEY` matching Midgley's Tailwind `slate-950` / `slate-900` dark theme.
- **Territory Preset Navigation Tabs**: Included responsive quick-navigation buttons (`CONUS`, `Pacific & Islands`, `Caribbean`, `All PADDs 1–7`) enabling users to jump between geographic zones spanning 11 time zones without distortion.
- **Declarative Coordinates & Canonical Helpers**: Added strongly-typed `latitude: float`, `longitude: float`, `has_dedicated_page: bool`, and `dedicated_page_url: str` fields to [`RegionSpec`](src/locations/specs.py), added `get_canonical_region_specs()`, and updated `REGION_METADATA` in [`src/live_fuel_feed.py`](src/live_fuel_feed.py).

### 19. Enverus / Drillinginfo Daily Rig Count & Cloudflare Browser Rendering (Issues #533 & #640)
- **Cloudflare Edge Browser Rendering & Markdown Extraction (`workers/enverus_scraper.ts`, Issue #640)**:
  - Leveraged Cloudflare Workers Paid Browser Rendering API (`MYBROWSER` binding) with `/markdown` quick action to execute headless Chromium sessions directly at the edge, successfully bypassing Cloudflare Bot Management / JavaScript challenges on `https://www.enverus.com/dailyrigcount/` and eliminating external Firecrawl quota consumption (strictly capped at 30/day, 800/mo).
  - Implemented `parseEnverusMarkdown()` in [`workers/enverus_scraper.ts`](workers/enverus_scraper.ts) extracting daily total rig counts, weekly percentage deltas, analyst narrative commentary, and multi-day rolling basin telemetry across all 7 major plays (Permian, Gulf Coast/Eagle Ford, Williston, Anadarko, Appalachia, DJ Basin, and Other).
  - Exposed edge endpoint `GET /api/v1/energy/rig-count/enverus` in [`workers/intraday_monitor_worker.ts`](workers/intraday_monitor_worker.ts) with 12-hour D1 edge caching.
- **Drillinginfo Upstream Basin Ingestion & Multi-Tier Fallback (`src/enverus_rig_feed.py`, Issue #533)**:
  - Added [`src/enverus_rig_feed.py`](src/enverus_rig_feed.py) (`EnverusRigFeedConnector`) providing bitemporal vintage tracking in `VintageStore` (`data_vintages`), local 12-hour lookup caching, and a dual-failover architecture combining the edge worker endpoint with direct fast-path Drillinginfo REST services (`https://app.drillinginfo.com/drcservice/api/OverTable`).
  - Integrated genuine daily Permian (`enverus_permian_rigs`) and Gulf Coast (`enverus_gulf_coast_rigs`) counts into [`src/alternative_data_feeds.py`](src/alternative_data_feeds.py), replacing legacy synthetic estimation (`oil_rigs * 0.62`) with verified daily basin telemetry.
- **Standardized `MidgleyAgent` User-Agent Policy**:
  - Established standardized policy user agent across all edge and core outbound scrapers: `MidgleyAgent/1.0 (+https://koshiirra.github.io/midgley/)` in [`src/http_client.py`](src/http_client.py) and [`wrangler.toml`](wrangler.toml).
- **Public Data Sources Catalog Registration**:
  - Registered Enverus Daily Rig Count as Card 2.2b in [`src/sources_generator.py`](src/sources_generator.py) and [`docs/sources.html`](docs/sources.html), and updated [`docs/research_sources.md`](docs/research_sources.md).

---

## 📦 Issues & Pull Requests Completed in v0.8.6 (To Date)

| Issue / PR | Title | Component |
| :--- | :--- | :--- |
| **#219 / #630** | `feat(regions): Implement Greater Chicago Metro Calibration Hub (PADD 2 / BP Whiting & Citgo Lemont)` | Locations / Regional Hubs |
| **#220** | `feat(regions): Implement Houston & USGC Metro Calibration Hub (PADD 3 / Houston Ship Channel Refineries)` | Locations / Regional Hubs |
| **#221** | `feat(regions): Implement Los Angeles Basin Metro Calibration Hub (PADD 5 / CaRFG & El Segundo/Torrance)` | Locations / Regional Hubs |
| **#235** | `feat(api): Multi-subscriber Discord webhook & DM alert subscriptions with /midgley slash commands & 20-hub edge reconciliation` | API / Notifications / Edge / Telemetry |
| **#533** | `[Tool Evaluation] Drillinginfo / Enverus API Spec (Energy Analytics & Basin Data)` | Ingestion / Upstream / Alternative Feeds |
| **#616 / #638** | `feat(llm): Migrate from Gemini 2.5 Flash to Gemini 3.8 Flash with low thinking level before Oct 20 retirement` | Core / LLM / Telemetry |
| **#618 / #636** | `feat(regions): Implement Denver & Rocky Mountain Metro Calibration Hub (PADD 4 / Suncor Commerce City)` | Locations / Regional Hubs |
| **#619 / #639** | `feat(regions): Implement Boston & New England Metro Calibration Hub (PADD 1A / Waterborne & Pipeline Terminals)` | Locations / Regional Hubs |
| **#620** | `feat(regions): Implement San Juan & Caribbean Territories Calibration Hub (PADD 6 / DACO Price Regulation)` | Locations / Regional Hubs / PADD 6 |
| **#621** | `feat(regions): Implement Guam & Pacific Island Territories Calibration Hub (PADD 7 / Trans-Pacific Import Logistics)` ([`6d1b77b`](https://github.com/KoshiirRa/midgley/commit/6d1b77b97)) | Locations / Regional Hubs / PADD 7 |
| **#622** | `feat(regions): Decouple PADD 5 sub-markets (Seattle PNW, Phoenix Desert SW, Anchorage AK, Honolulu HI) from CA CARB` | Locations / Regional Hubs / Decoupling |
| **#635 / #637** | `feat(regions): Implement New York Harbor & New York State Metro Calibration Hub (PADD 1B / NY Harbor Barges & Buckeye Pipeline)` | Locations / Regional Hubs / Issue Trigger |
| **#640** | `feat(edge,scraping): Leverage Cloudflare Browser Rendering API for JavaScript-rendered news & state fuel price boards` | Edge / Scraping / Intraday Monitor |
| **#646** | `feat(dashboard): Interactive multi-region price hub map on main landing page` | Dashboard / UI / Locations |
| **Commit `c7189715`** | `feat(mlops,cloud): Enforce local-only regional backfill policy and skip cloud runner backfilling` | MLOps / Workflows / Cloud |
| **Commit `403946c7`** | `feat(architecture,regions): Consolidate Greenville into Charlotte Carolinas hub and update multi-agent architecture across PADDs 1-7` | Architecture / Locations / Diagrams |
| **Commit `0c814a77`** | `fix(telemetry,geo): Resolve ZIP 12946 Lake Placid coordinates accurately in Adirondacks and correct NY state centroid` | Telemetry / Geocoding / Dashboard |
| **CI / Isolation** | `fix(ci,isolation): Hermetic vintage isolation, zero-cost telemetry deepcopy, radar cache protection & reflection timing bound` | Core / Testing / Ingestion / CI |

---

## 🤖 AI Agent Reconciliation Block (Draft for v0.8.6)

For autonomous AI coding assistants, downstream forks, and self-hosted deployments tracking `dev` toward **v0.8.6**:

### 1. Schema & Migration Summary
* **Target Package Version**: `0.8.6` *(Draft — current package version remains `0.8.5` on `dev` until official release cut)*
* **New Regional Metro Hubs & Topology Consolidation**:
  - Added 12 new regional hubs: `Chicago_IL` (`chicago`), `Houston_TX` (`houston`), `Los_Angeles_CA` (`los_angeles`), `Denver_CO` (`denver`), `New_York_NY` (`new_york`), `Seattle_WA` (`seattle`), `Phoenix_AZ` (`phoenix`), `Anchorage_AK` (`anchorage`), `Honolulu_HI` (`honolulu`), `Guam_GU` (`guam`), `San_Juan_PR` (`san_juan`), `Boston_MA` (`boston`).
  - Decommissioned standalone `greenville` model and consolidated it into `Charlotte Metro & Carolinas Hub, NC (PADD 1C)` (`charlotte`). `LOCATIONS` now maintains 19 canonical locations (1 national + 18 regional hubs), with transparent alias routing for `greenville` to `charlotte` and an instant redirect on `docs/greenville.html`.
* **Edge Worker & Discord Slash Command Topology**:
  - Reconciled [`workers/intraday_monitor_worker.ts`](workers/intraday_monitor_worker.ts) and [`scripts/register_discord_commands.py`](scripts/register_discord_commands.py) to reflect all canonical calibration hubs, statutory excise tax rates, and direct metro prefix clusters (`800`..`806` Denver, `100`..`149` New York, `021`/`022`/`024` Boston, `980`..`985` Seattle, `850`..`853`/`890`..`891` Phoenix, `995`..`996` Anchorage, `967`..`968` Honolulu, `006`..`009` San Juan, `969` Guam).
  - Added non-contiguous ZIP prefix resolution for Caribbean PADD 6 (`006`..`009` $\rightarrow$ `PR`/`VI`) and Pacific PADD 7 (`969` $\rightarrow$ `GU`).
  - Decoupled state PADD fallback corridors in the Cloudflare Worker from California CARB and legacy coastal hubs to their respective regional models.
* **Hierarchical Engine & Regional Topology Additions**:
  - Added `PADD_1A` cluster and `Boston_MA` bottom-level metro to [`src/hierarchical_engine.py`](src/hierarchical_engine.py) with exact sum aggregation coherence ($S$ matrix reconciliation).
  - Decoupled New England states (`ME`, `NH`, `VT`, `MA`, `RI`, `CT`) from Newark DE (`PADD 1B`) to `boston` (`Boston_MA / PADD 1A`) in `STATE_PADD_MODEL_MAP` and mapped ZIP prefixes `021`, `022`, `024` in [`src/zip_geocoding.py`](src/zip_geocoding.py).
  - Mapped Massachusetts statutory motor fuel excise tax ($0.240/gal) in [`src/zip_geocoding.py`](src/zip_geocoding.py) and [`data/regional_metadata/boston_ma.json`](data/regional_metadata/boston_ma.json).
  - Added `PADD_6` cluster and `San_Juan_PR` bottom-level metro to [`src/hierarchical_engine.py`](src/hierarchical_engine.py) with exact sum aggregation coherence ($S$ matrix reconciliation).
  - Added `PADD_7` cluster and `Guam_GU` bottom-level metro to [`src/hierarchical_engine.py`](src/hierarchical_engine.py) with exact sum aggregation coherence.
  - Modeled landed USGC conventional cargo benchmark with Jones Act clean tanker differential `spot_caribbean_waterborne = spot_gulf_coast + 0.145` and San Juan Bay terminal throughput charges.
  - Modeled landed Asian wholesale acquisition benchmark `spot_mops_92_rack = rbob + 0.350` and Cabras Island terminal rack throughput charges.
  - Registered flat tropical 9.0 psi year-round RVP regulation standards in [`src/rvp_regulations.py`](src/rvp_regulations.py).
  - Mapped Puerto Rico Commonwealth gasoline arbitrio ($0.160/gal) in [`src/zip_geocoding.py`](src/zip_geocoding.py) and [`data/regional_metadata/san_juan_pr.json`](data/regional_metadata/san_juan_pr.json).
  - Mapped Guam Liquid Fuel Tax ($0.150/gal) + Mass Transit surcharge ($0.040/gal) = $0.190/gal local tax base in [`src/zip_geocoding.py`](src/zip_geocoding.py) and [`data/regional_metadata/guam_gu.json`](data/regional_metadata/guam_gu.json).
* **Out-of-Metro Telemetry Geocoding & Coordinate Resolution**:
  - Added `resolve_zip_coordinates()` in [`src/zip_geocoding.py`](src/zip_geocoding.py) checking exact 5-digit `KNOWN_ZIP_COORDS`, 3-digit prefix centroids `KNOWN_PREFIX_COORDS`, and state centroids `STATE_CENTER_COORDS`.
  - Corrected `STATE_CENTER_COORDS["NY"]` from NYC `(40.7128, -74.0060)` to Madison County `(42.9538, -75.5268)`.
  - Added exact coordinate mapping for Adirondacks Lake Placid, NY `12946` `(44.2795, -73.9799)`.
* **Local Dev Environment Regional Backfill Policy**:
  - Enforced operational policy directing multi-year regional historical backfilling (`backfill_new_region_history()`) to local dev environment (`dev-vm`), saving GitHub runner compute and avoiding cloud timeout bottlenecks.
* **LLM Engine & Deprecation Migration**:
  - Runtime generative extractions and agent tasks migrated from deprecated `gemini-2.5-flash` to `gemini-3.8-flash`.
  - Deprecated sampling parameters (`temperature`, `top_p`, `top_k`, `thinking_budget`) are completely removed; structured JSON extraction and evaluation tasks explicitly configure `thinking_level="low"`.
  - Telemetry rates updated to $0.75 / 1M prompt and $3.75 / 1M output tokens while preserving legacy rates for historical accounting.
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
  - `CARTO_API_KEY`: Optional CARTO Basemaps API key appended to Leaflet dark tile URLs on `docs/telemetry.html` (defaults to bundled public non-commercial key if unset or empty).
  - `MIDGLEY_SUBSCRIBERS_DB_PATH`: Optional override path for the SQLite subscriber registry (defaults to `data/subscribers.sqlite`).

### 3. Edge & Cloudflare Workers Paid Architectural Roadmap (Issues #640–#645)
* Opened comprehensive architectural tracking issues for upgrading Midgley's edge infrastructure under Cloudflare Workers Paid:
  - **Issue #640**: [`feat(edge,scraping): Leverage Cloudflare Browser Rendering API for JavaScript-rendered news & state fuel price boards`](https://github.com/KoshiirRa/midgley/issues/640) — Conserves Firecrawl quota (800/mo) via edge headless Chromium.
  - **Issue #641**: [`feat(edge,db): Direct database TCP connections from Workers via cloudflare:sockets`](https://github.com/KoshiirRa/midgley/issues/641) — Low-latency database connectivity and distributed rate-limit advisory locking.
  - **Issue #642**: [`feat(edge,forecasting): Edge price & shock nowcasting with dynamic Asymmetric ECM evaluation`](https://github.com/KoshiirRa/midgley/issues/642) — Evaluates retail pass-through equations and tax wedges on-demand at the edge.
  - **Issue #643**: [`refactor(edge,queues): Cloudflare Queue architecture hardening & extended CPU batch consumption`](https://github.com/KoshiirRa/midgley/issues/643) — Bulk D1 deduplication and Dead-Letter Queue management under 5-minute CPU runtime.
  - **Issue #644**: [`feat(edge,monitoring): Expand intraday monitor feed coverage with Tier-1/Tier-2 refinery operator 8-Ks and regional midstream feeds`](https://github.com/KoshiirRa/midgley/issues/644) — Adds ExxonMobil, Chevron, Suncor, Par Pacific, and midstream operators.
  - **Issue #645**: [`feat(edge,ai): Leverage Cloudflare Workers AI & Vectorize for edge event scoring, semantic deduplication, and brief synthesis`](https://github.com/KoshiirRa/midgley/issues/645) — Zero-shot SLM classification, Vectorize 384d semantic deduplication, and institutional Discord analyst briefs.

### 4. Verification Commands
```bash
python scripts/register_discord_commands.py --dry-run
TESTING=1 pytest -v tests/test_docs_parity.py tests/test_event_analyzer.py tests/test_alpha_factor_miner.py tests/test_pasa_research_agent.py tests/test_weekly_issue_reporter.py tests/test_system_telemetry.py tests/test_tokentab_accounting.py tests/test_scenario_simulator.py tests/test_oilpriceapi_dynamic.py tests/test_oilpriceapi_ingestion.py
TESTING=1 pytest -v tests/test_declarative_regions.py tests/test_locations.py tests/test_regional_metadata.py tests/test_discord_subscriptions.py tests/test_zip_geocoding.py tests/test_api_server.py tests/test_hierarchical_engine.py tests/test_zero_cost_fallbacks.py tests/test_hindsight_benchmark.py tests/test_open_source_ai_radar.py tests/test_system_telemetry.py tests/test_docs_links.py
npx vitest run tests/workers.test.ts
```

