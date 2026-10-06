# Handoff — New and under-used data sources for Midgley

**Repo:** `KoshiirRa/midgley` (pyproject 0.8.4)
**Prepared:** 5 Oct 2026
**Companion documents:** Midgley_review_2026-10-05.md (finding IDs T-1 to T-37, plus the earlier A-, E-, D- IDs) and midgley-synthetic-regional-data-handoff.md (21 Sep, regional retail history)
**Scope:** which data Midgley should add, which existing feeds to fix first, and the rules every new feed must pass. This document is self-contained. Read sections 1–2 before implementing anything.
**How the facts were checked:** each source, series ID, endpoint, date and licence term below was checked on the provider's own site on 5 Oct 2026. Anything that couldn't be confirmed there is marked *unverified*. What Midgley uses today was checked in the code.

---

## 0. Summary

**The biggest gap isn't a missing exotic feed. It's history.** Midgley pulls from about 40 data providers, but almost all of them reach the model only as a value on the last row; the training history behind them is a sine wave, a constant or a hard-coded fallback (A-3, D-1). A new feed that only adds another live value repeats that pattern. So this document ranks sources by whether they supply **real, point-in-time history from 2022 onward** and whether they fix a known finding.

**Three things to know before starting:**
- **Nothing in `src/` calls the EIA API.** Every EIA number comes through FRED, which mirrors only the U.S. and PADD retail series and none of the weekly supply IDs the code asks it for. So those requests fail and fall back to hard-coded values.
- **USGS is retiring the API Midgley uses for river levels.** Requests slow down from 16 Nov 2026 and the service shuts down on 22 Feb 2027.
- **The live pump price comes from scrapes whose terms don't appear to allow it.** The code tries GasBuddy first, then the AAA website. AAA's terms prohibit archiving and commercial use, GasBuddy offers no data licence, and the scraped values end up in the public ledger (section 8).

**Shortlist**

| # | Source | What it fixes or adds | Cost | Effort | Priority |
|---|---|---|---|---|---|
| 1 | **EIA API v2: weekly retail** for San Francisco, Ohio, Florida and PADDs 1B, 1C, 2 | Real regional ground truth (E-2) | Free | M | P0 |
| 2 | **EIA API v2: weekly stocks, utilisation, production; Cushing; ethanol; monthly PADD 3→1 flows** | Replaces six sine-wave feature families (A-3) | Free | M | P0 |
| 3 | **State tax notices + EIA tax table; EPA fuel waivers** | Ohio's 4 Oct tax holiday and the RVP calendar (T-4) | Free | S | P0 |
| 4 | **USGS Water Data API** (replacement) + NOAA NWPS forecasts | Keeps the river feed alive; real river history | Free | S–M | P0 (deadline) |
| 5 | **NYMEX holiday calendar; contract-month prices** | Horizons on trading days (A-8); roll-aware target and spreads (A-5) | Free | S–M | P0 |
| 6 | **CFTC disaggregated, filtered to RBOB** | Real positioning history instead of fallbacks (D-1) | Free | S | P1 |
| 7 | **NOAA/NASA temperature history; Nebraska and USDA ethanol; EPA RIN; Baker Hughes archive; CEC Fuels Watch** | Real history for the remaining placeholders | Free | M–L | P1 |
| 8 | **BLS metro average prices; ALFRED vintages** | Monthly metro check (incl. Philadelphia–Wilmington for Newark); point-in-time national history | Free | S | P1 |
| 9 | **CARB LCFS weekly log; cap-and-invest auction results; CEC margins; refinery-closure breaks** | Real California compliance costs and margins | Free | M | P1 |
| 10 | **GDELT, Geopolitical Risk index, Economic Policy Uncertainty** | Event features with 10–40 years of history (A-6, T-5) | Free | L | P2 |
| 11 | **Coast Guard port conditions** (Florida) and **state upset reports** (Delaware, Contra Costa, LA) | Local supply shocks | Free | M | P2 |
| 12 | **Kalshi AAA gas-price markets** | The toughest external benchmark for 1-day and weekly forecasts | Free, but terms forbid storage and ML use without permission | S | P3 (ask first) |
| 13 | **OPIS rack + retail** for the nine metros' terminals | Terminal wholesale prices and metro retail history no free source has | Paid | M | Decide |

**Skip for now:** AIS ship tracking (no free history), Sentinel-5P satellite NO₂ (no evidence it detects refinery outages), Google Trends (alpha API only), station-level prices (no U.S. state publishes them, and the commercial sources forbid archiving).

---

## 1. Context

### 1.1 What Midgley forecasts
- A national wholesale benchmark: NYMEX RBOB front month (`RB=F`), 1–5 business days ahead.
- Retail regular gasoline for 9 metros: Tulsa_OK, Newark_DE, Cincinnati_OH, Cincinnati_KY, Greenville_NC, Charlotte_NC, Port_St_Lucie_FL, Oakland_CA, BayArea_CA.
- Training history starts 2022-01-03 (`fetch_market_data(start_date="2022-01-01")`). Runs daily at 22:17 UTC on GitHub Actions; the repo and its dashboard are **public**.

### 1.2 What it already pulls (verified in `src/`, 5 Oct 2026)

| Area | Providers in use | State of the data |
|---|---|---|
| Futures and markets | yfinance `RB=F`, `CL=F`, `HO=F`, `BZ=F`, `NG=F`, `^OVX`, `^TNX`/`^FVX`/`^IRX`; Alpha Vantage; OilPriceAPI | Continuous front months only; no individual contract months, so no roll adjustment (A-5) |
| Retail prices | Live only: GasBuddy GraphQL, then the AAA website scrape (a Google Places `fuelOptions` function exists but nothing calls it). History: FRED `GASREGW` plus regional IDs (`GASREGWOK`, `GASREGWKY`, `GASREGWNC`, `GASREGWOH`, …) | No real metro history; only Newark gets actuals, and they're the U.S. average (E-2) |
| Wholesale spot | FRED `DGASNYH`, `DGASUSGULF` | Today's value broadcast over every date (T-36); LA CARBOB a fixed 2.890 |
| EIA fundamentals | EIA weekly IDs (`WPULEUS1`–`5`, `WGFUPUS2`) requested from FRED; PADD values hard-coded as fallbacks | **No call to `api.eia.gov` anywhere in `src/`**; stocks, utilisation, production and inter-PADD movements are sine waves in history |
| Positioning | CFTC legacy dataset `6dca-aqww` on `socrata.cftc.gov`, `$limit=10`, no contract filter | 65 of 65 vintages are fallbacks (D-1) |
| Rigs | Baker Hughes site, Barchart, FRED `OGUSROTRIG` | Newest records are a test mock (T-29) |
| Weather and hazards | weather.gov, Open-Meteo (forecast), Pirate Weather, NASA POWER (unreachable module), NOAA CO-OPS, NHC, USGS water and seismic, NASA FIRMS, AirNow | Degree days and river risk are cosine/sine climatology in history |
| Supply chain and safety | PHMSA, NRC, TCEQ, LDEQ, BAAQMD, USACE locks, BSEE, IMF PortWatch, FERC eForms | Mostly live-only; several are constants (T-36) |
| Policy and compliance | EPA RIN (EMTS), CARB LCFS and cap-and-trade, RVP rules, `known_future_events.json`, state tax rates in `state_open_data.py` | CARB is a hand-typed list of 10 semi-annual points; the tax calendar is hand-typed and wrong (T-4); ethanol and D6 RIN are sine waves in history |
| Demand and macro | BTS TSI (FRED `TSIFRGHT`), FHWA VMT, Census, JODI | Monthly, mostly unused by the model |
| News and events | Google News RSS, NYT RSS, finlight, Truth Social, Firecrawl, SEC EDGAR 8-K, Headline Arena, Hindsight memory | No usable history: duplicates, and the history file is overwritten weekly (T-5) |

### 1.3 Which findings new data can fix

| Finding | What's missing | Section |
|---|---|---|
| E-2, T-1 | Real regional retail history and ground truth | 4.1, 4.2 |
| A-5 | Individual futures contract prices for a roll-adjusted target | 4.4 |
| A-3, D-1 | Real history for every "fundamental" feature family | 3, 4.3, 5 |
| A-8 | Exchange holidays | 4.5 |
| T-4 | Statutory tax rates and change dates | 4.6, 6.2 |
| A-6, T-5 | Event and news features with honest history | 6.4 |
| T-1 (pass-through) | Wholesale price at the terminals behind each metro | 7 |

---

## 2. Admission rules for any new feed

A feed goes into the model only if it passes all of these. They exist because the current feature set failed them (A-3, D-1, D-3, D-4).

1. **Real history over the training window.** It must supply observed values from 2022-01-03 onward (or the project shortens the window). A feed that can only supply today's value is allowed for the live nowcast and the dashboard, **never as a model feature**.
2. **Point-in-time.** Every observation is stored with `obs_date`, `published_at` (when the provider released it) and `fetched_at`. Training joins on `published_at <= origin_time`. Where the provider revises (EIA, BLS, FRED), keep the vintages or apply a documented publication lag.
3. **Entity-keyed.** Each value carries the entity it describes (region, PADD, terminal, gauge). Unknown entities raise; nothing falls back to another region (D-3).
4. **Quality-flagged.** `LIVE`, `CACHED`, `STALE`, `BENCHMARK` or `SYNTHETIC`. Fallbacks are never stored as observations, and training reads only `LIVE`/`CACHED`.
5. **Licence allows automated download and the intended storage.** The repo, `data/` and the dashboard are public, so committing raw data is redistribution. Licensed or terms-restricted data (OPIS, AAA, GasBuddy, Google Places) must stay out of git and off the public site; only derived forecasts are published.
6. **Earns its place.** Admit a feed family only after a purged-CV ablation shows it improves out-of-sample loss (or a declared evaluation metric), and add it to the truncation-invariance test (T-33) including the last row.

**How to wire it (existing code):**
- Store observations with `VintageStore.record_observation(feed, entity, obs_date, values, published_at=…, fetched_at=…, quality=…)` and read them with `query_as_of(feed, entity, target_date, as_of_time=…, allow_quality=…, publication_lag_days=…)` (`src/vintage_store.py`). This is the one storage design that's already correct; today only Baker Hughes writes to it and nothing reads it.
- Always pass three arguments explicitly, because the defaults are unsafe:
  - `published_at`: it defaults to the fetch time, which breaks both deduplication and point-in-time joins.
  - `as_of_time`: it defaults to now, which is look-ahead.
  - `allow_quality=("LIVE", "CACHED")` for training: the default also admits `BENCHMARK`.
- Use `src/http_client.py` for every new HTTP call (retries, timeouts, one User-Agent).
- One module per provider, with a backfill command (`python -m src.feeds.<name> --backfill 2022-01-01`) and an incremental update used by the daily run.

---

## 3. Fix the feeds you already have (quick wins, all free)

These aren't new providers, but each one turns a placeholder or a dead request into real history. Do them before adding anything in sections 4–6.

| # | Current state (verified in `src/`) | What's wrong | Do this instead |
|---|---|---|---|
| 3.1 | Regional retail history requested from FRED as `GASREGWOK`, `GASREGWKY`, `GASREGWNC`, `GASREGWOH`, `GASREGW01B`, `GASREGW01C`, `GASREGWMW`, `GASREGWCA`, `GASREGWFL`, `GASREGWEC`, `GASREGWGULF`, `GASREGWCW`, `GASREGCAW` | Of these, only `GASREGWCW` (PADD 5) exists on FRED. FRED mirrors just the U.S. and PADD I–V series (`GASREGW`, `GASREGECW`, `GASREGMWW`, `GASREGGCW`, `GASREGRMW`, `GASREGWCW`); it has no sub-PADD, state or city retail. | Call EIA API v2 directly for the city/state/PADD series in section 4.1. |
| 3.2 | EIA weekly IDs `WPULEUS1`–`5` and `WGFUPUS2` requested from **FRED** (`data_ingestion.py:557-561`), with hard-coded PADD fallbacks (87.4, 92.1, 94.6, 85.2) | FRED hosts none of them, so every run falls back. Also, `WPULEUS1`–`5` aren't EIA's PADD IDs (`WPULEUS3` is the U.S. total; PADD utilisation IDs look like `W_NA_YUP_R20_PER`). | EIA API v2, section 4.3. |
| 3.3 | Rig count from FRED `OGUSROTRIG` | That series doesn't exist on FRED. | Baker Hughes' own historical archive (Excel, from 2000) plus the weekly Friday report. |
| 3.4 | CFTC legacy dataset `6dca-aqww` on `socrata.cftc.gov`, `$limit=10`, no contract filter (`data_ingestion.py:2931-2946`) | Takes whatever market comes back first; all 65 committed vintages are fallbacks. | `publicreporting.cftc.gov`, Disaggregated futures-only `72hh-3qpy` (or futures+options `kh3c-gbw2`), filtered `cftc_contract_market_code=111659` (NYMEX RBOB; code confirmed only by third-party sites, so check it on the first call). Backfill from the start of the disaggregated report (2006; unverified). Positions are as of Tuesday and published Friday, so the feature is available from Friday's close. |
| 3.5 | FRED daily spot `DGASNYH`, `DGASUSGULF`; LA CARBOB a constant 2.890 | Today's value is broadcast over every date since 2022 (T-36). | Load the dated history; add Los Angeles RBOB (`DRGASLA` on FRED, `EER_EPMRR_PF4_Y05LA_DPG` on EIA). EIA releases these weekly (data through Tuesday, out Wednesday), so a given day's spot price is 1–7 days late: use it as a lagged feature, not a same-day input. The prices come from Refinitiv (LSEG) and FRED marks them copyrighted, so don't commit the raw series to the public repo. |
| 3.6 | National retail history `GASREGW` (latest values only) | Revisions and publication timing ignored | Use ALFRED vintages: the FRED API with `realtime_start = realtime_end = D` returns the series as known on date D (vintages for `GASREGW` from 2009, `DGASNYH` from 2011). |
| 3.7 | USGS river data from `waterservices.usgs.gov` (`usgs_water_feed.py`, `usace_locks.py`) | **USGS is retiring this API.** From 16 Nov 2026 every request gets a 2-second delay, rising to 60 seconds in Jan–Feb 2027, and the service shuts down on 22 Feb 2027. | Migrate to `api.waterdata.usgs.gov` (OGC API, free key) **before 16 Nov 2026**, and backfill daily values: Ohio River at Cincinnati (03255000) from 1987, Mississippi at Memphis (07032000) from 1933, St. Louis (07010000) from 1861. Values carry an approval status; provisional values get revised. |
| 3.8 | `nasa_power.py` exists but nothing reaches it; degree days are a cosine climatology in history | A-3 | Use it (or one of the sources in section 5) for real daily temperature history per hub. |
| 3.9 | FERC tariff feature is a constant | No information | Use the FERC oil-pipeline index multiplier, which changes every 1 July (1.019976 for Jul 2025–Jun 2026; 1.014290 for Jul 2026–Jun 2027), and Colonial's own tariff PDFs (archive back to 2012 on colpipe.com). Plantation now files as Products (SE) Pipe Line Corporation. |
| 3.10 | Hurricane features from live NHC products | Backtests have no point-in-time history | For backtests use the NHC advisory text archive (1998–) and GIS forecast-cone archive (2008–). Don't use HURDAT2 best tracks: they're re-analysed after the season, so they leak hindsight. |

---

## 4. New official sources (free) — the core of the work

### 4.1 EIA weekly retail prices by city, state and PADD — regional ground truth (E-2, T-1)

The 21 Sep handoff already asked for this; it hasn't been built, and the current mapping points at FRED IDs that don't exist (3.1). These are the verified EIA series to use.

**Access:** `https://api.eia.gov/v2/petroleum/pri/gnd/data/?api_key=KEY&frequency=weekly&data[0]=value&facets[series][]=<ID>` (free key; up to 5,000 rows per call).

**Timing:** prices are as of 8 a.m. local time on Monday and are released on **Tuesday at about 10 a.m. ET** (Wednesday when Monday is a federal holiday; next: Columbus Day, released Wed 14 Oct 2026). EIA doesn't revise published values in practice. Note the methodology break on 14 May 2018.

| Metro | Best EIA series | ID | Tier | History |
|---|---|---|---|---|
| National | U.S. | `EMM_EPMR_PTE_NUS_DPG` | Country | 1990 |
| Oakland_CA, BayArea_CA | San Francisco (Alameda, Contra Costa, Marin, San Francisco, San Mateo counties, so it includes Oakland) | `EMM_EPMR_PTE_Y05SF_DPG` | City | 2000 |
| Cincinnati_OH | Ohio (EIA's Cleveland series doesn't cover Cincinnati) | `EMM_EPMR_PTE_SOH_DPG` | State | May 2003 |
| Port_St_Lucie_FL | Florida (EIA's Miami series covers Broward, Miami-Dade and Palm Beach only) | `EMM_EPMR_PTE_SFL_DPG` | State | 2003 |
| Newark_DE | PADD 1B Central Atlantic | `EMM_EPMR_PTE_R1Y_DPG` | PADD | 1993 |
| Charlotte_NC, Greenville_NC | PADD 1C Lower Atlantic | `EMM_EPMR_PTE_R1Z_DPG` | PADD | 1993 |
| Tulsa_OK, Cincinnati_KY | PADD 2 Midwest | `EMM_EPMR_PTE_R20_DPG` | PADD | 1992 |
| (reference) | California | `EMM_EPMR_PTE_SCA_DPG` | State | 2000 |

- EIA publishes no Oklahoma, Kentucky, North Carolina or Delaware series. For those five metros the honest choice is a PADD-level target, labelled as such on the dashboard (or the metro is dropped until licensed data exists; section 7).
- Oakland_CA and BayArea_CA resolve to the same official series. Either merge them or accept that their scores can't be told apart.
- Score retail weekly against the survey whose Monday falls in the target week, as the 21 Sep handoff specified. Store `published_at` = the Tuesday release.

### 4.2 BLS average retail price by metro — independent monthly check

BLS publishes "Gasoline, unleaded regular, per gallon" average prices monthly, from 1978, through the BLS API (v2 needs free registration).

| Area | ID | Use for |
|---|---|---|
| San Francisco–Oakland–Hayward | `APUS49B74714` | Oakland_CA, BayArea_CA |
| Miami–Fort Lauderdale–West Palm Beach | `APUS35B74714` | Port_St_Lucie_FL (nearby; St. Lucie County isn't in it) |
| Philadelphia–Camden–Wilmington | `APUS12B74714` | Newark_DE (includes the Wilmington, DE metro) |
| South region | `APU030074714` | Charlotte_NC, Greenville_NC |
| U.S. city average; Midwest | `APU000074714`; `APU020074714` *(IDs inferred from the pattern; unverified)* | National; Tulsa, Cincinnati |

- Released mid-month (August data on 11 Sep; next release 14 Oct 2026). No Cincinnati or Charlotte series exists.
- Too slow for a 1–5 day target, but it's an official, metro-level series that moves independently of RBOB. Use it to check that each metro's forecasts and EIA mapping are plausible, and as a monthly evaluation layer.

### 4.3 EIA fundamentals — replace six sine-wave feature families (A-3, D-1)

**Access:** `https://api.eia.gov/v2/seriesid/PET.<ID>.<W|M>?api_key=KEY` (the backward-compatible route; confirm the exact form on the first call).
**Timing:** the Weekly Petroleum Status Report comes out **Wednesday 10:30 a.m. ET** (Thursday 12:00 p.m. in holiday weeks; next: Thu 15 Oct and Thu 12 Nov 2026). Data are for the week ending the previous Friday. EIA's revision policy for these series wasn't confirmed, so store vintages.

| Placeholder in `feature_engineering.py` | Real series | ID | Freq | From |
|---|---|---|---|---|
| `eia_gasoline_stocks_us_total` (225 + 15·cos) | Total gasoline stocks: PADD 1, PADD 1B | `WGTSTP11`, `WGTST1B1` ✔; U.S. `WGTSTUS1`, PADD 1C `WGTST1C1`, PADDs 2–5 `WGTSTP21`–`WGTSTP51` *(pattern, unverified)* | W | 1990 |
| `eia_refinery_utilization_us_total` (89 + 4·sin) | Refinery utilisation: U.S.; PADD 2; PADD 3 | `WPULEUS3`; `W_NA_YUP_R20_PER`; `W_NA_YUP_R30_PER` | W | 1990 / 2010 |
| `eia_refinery_net_production_padd1`, `_padd3` | Refiner and blender net production of finished gasoline | `WGFRPP12`, `WGFRPP32` | W | 1993 |
| `eia_pipeline_movements_padd3_to_padd1` | Pipeline movements PADD 3 → PADD 1: blending components **plus** finished gasoline (add the two) | `MBCMPP1P31` + `MGFMPP1P31` | M (≈2-month lag) | 1986 |
| *(new)* Cushing, OK crude stocks — matters for Tulsa | Cushing stocks excluding SPR | `W_EPC0_SAX_YCUOK_MBBL` | W | 2004 |
| *(new)* Gasoline demand | U.S. product supplied of finished gasoline | `WGFUPUS2` | W | 1991 |
| `usda_ethanol_rack_price` support | Fuel ethanol production; stocks | `W_EPOOXE_YOP_NUS_MBBLD`; `W_EPOOXE_SAE_NUS_MBBL` | W | 2010 |

Notes:
- PADD 1 "production" is mostly ethanol blending at terminals, not refining, so read it as a supply-chain signal, not refinery output.
- The monthly movements series runs about two months behind; use it only as a slow regime feature.

### 4.4 Futures by contract month — the roll-adjusted target (A-5)

| Source | What it gives | Status |
|---|---|---|
| EIA daily NYMEX futures, contracts 1–4 | RBOB `EER_EPMRR_PE1_Y35NY_DPG` … `PE4` (from 2005); WTI `RCLC1`–`RCLC4` (from 1983) | **Discontinued after 5 Apr 2024** ("Futures prices after April 5, 2024, are not available"). Good for researching roll gaps and spreads up to 2024 only. |
| Yahoo Finance contract-month symbols via yfinance | e.g. `RBX26.NYM` (Nov 2026), `RBZ26.NYM`; same pattern for `CL` and `HO` | The symbols exist and quote live. Whether Yahoo keeps history for **expired** contracts is unverified, so start archiving the first three contracts' daily settlements into `VintageStore` now. |
| CME settlement pages | Official settlements | CME labels website data "reference only"; the licensed history is CME DataMine (paid). |

**The fix for A-5 doesn't need new data:** RBOB contracts expire on the last business day of the month before delivery, so the expiry calendar alone tells you which h-day windows straddle a roll. Compute targets on the same contract, or drop or flag the straddling windows. Use the contract-month prices above for calendar-spread features once enough history is archived.

### 4.5 Calendars — NYMEX holidays (A-8) and demand holidays

- **`pandas_market_calendars`** (MIT, v5.4.0) ships a CME Globex energy and metals calendar (`cme_globex_energy_and_metals`; check the exact name with `mcal.get_calendar_names()`), including early closes. Holiday rules ship in the package, so pin and upgrade it deliberately.
- **`holidays`** (MIT) covers U.S. federal and state holidays for all of Midgley's states and includes XNYS and XCME market calendars. It has no school-holiday category.
- Cross-check against CME's own published holiday calendar each year.
- Use the exchange calendar for horizons and target dates (no more `pd.bdate_range`), and federal/state holidays as demand dummies (Memorial Day, 4 July, Labor Day, Thanksgiving).

### 4.6 Statutory taxes — replace the hand-typed calendar (T-4)

| Source | What it gives | Limits |
|---|---|---|
| EIA "Federal and State Motor Fuels Taxes" (`eia.gov/petroleum/marketing/monthly/xls/fueltaxes.xlsx`; also BTS dataset `e5cn-ri8q` on data.transportation.gov) | All state rates, as of 1 Jan and 1 Jul | Twice-yearly snapshots, not a change calendar |
| FHWA Table MF-121T | Rates with effective dates | Annual, about a year late |
| Federation of Tax Administrators | Current rates | No history |
| State revenue departments (Ohio Department of Taxation, CDTFA, NCDOR, and the OK, KY, FL and DE equivalents) | Official notices of upcoming changes | No common format; check monthly, plus a news monitor (6.4) for "gas tax holiday" / "fuel tax suspension" |

**Verified current changes to load now:**
- Ohio: 38.5¢ → 0.0001¢/gal from 12:01 a.m. 4 Oct 2026 to 11:59 p.m. 2 Jan 2027 (HB 519). Cincinnati_OH only; Kentucky is unaffected.
- California excise: 61.2¢ from 1 Jul 2025, 63.4¢ from 1 Jul 2026 (CDTFA). The sales tax on gasoline is 2.25% plus district taxes, not 7.25%.
- North Carolina: 41.0¢ for 2026 (40.3¢ in 2025), reset every 1 Jan (NCDOR).
- No official national list of upcoming changes exists, so keep `known_future_events.json` but generate it from these sources, with `source_url` and `announced_on` on every row.

### 4.7 Point-in-time national history — ALFRED

FRED's vintage archive holds every past version of `GASREGW` (from 2009) and `DGASNYH` (from 2011). Calling the FRED API with `realtime_start = realtime_end = D` returns the series as it was known on date D. The vintage date is when FRED posted the value (Tuesday afternoon for `GASREGW`), so use it as the availability timestamp. Check other series with `fred/series/vintagedates`.

---

## 5. Real history for the other placeholder families (free)

Each row replaces a sine wave, a constant or a live-only value that the model currently trains on.

| Feature family (today) | Source | History | Lag and revisions | Licence / gotchas |
|---|---|---|---|---|
| **Heating/cooling degree days per hub** (cosine climatology, `feature_engineering.py:493`, `:524`) | NOAA NCEI GHCN-Daily via the Access Data Service (`ncei.noaa.gov/access/services/data/v1?dataset=daily-summaries&bbox=…&dataTypes=TMAX,TMIN`) | Station-dependent, decades | Daily; the dataset is rebuilt about weekly, so values change (daily `superghcnd_diff` files let you rebuild past versions) | Free |
| | NASA POWER daily point API (the repo's `nasa_power.py` already wraps it) | 1981 | ~2 days; recent values are later replaced (GEOS-IT → MERRA-2) | Free; coarse ½°×⅝° grid |
| | NOAA CPC population-weighted HDD/CDD by state and Census division | 1981 | ~5 days *(unverified)* | Free; state level suits Ohio, Kentucky, Oklahoma, North Carolina, Florida, California, Delaware |
| | Open-Meteo Historical Weather (ERA5 from 1940) and Previous Runs API (archived forecasts at fixed lead times, from Jan 2024) | 1940 | ~5 days (ERA5) | **Free tier is non-commercial only**; commercial use of the historical API needs a paid plan. Previous Runs is the only source here that gives point-in-time *forecast* degree days. |
| **CFTC positioning** (`80000 + 16000·sin`) | See 3.4: disaggregated RBOB, code 111659 | 2006 *(unverified)* | Tuesday positions, Friday release | Free |
| **River barge risk** (sine, `:621-660`) | USGS daily values on the new API (3.7) | Cincinnati 1987, Memphis 1933, St. Louis 1861 | 1–2 days; provisional values revised | Free; migrate before 16 Nov 2026 |
| | NOAA NWPS stage forecasts: Ohio at Cincinnati `CCNO1`, Mississippi at Memphis `MEMT1`, St. Louis `EADM7` (`api.water.noaa.gov/nwps/v1/gauges/{id}/stageflow/forecast`) | NWPS keeps none | Issued and valid times included | Free, no key. Forecast **history** only from the Iowa Environmental Mesonet archive of NWS river forecasts (since 2012; coverage of these gauges unverified) |
| | USDA weekly barge freight rates (St. Louis, Cincinnati, Cairo–Memphis), Grain Transportation Report / AgTransport | Years | Weekly | Free; dataset ID unverified |
| **California CARBOB stocks, refinery runs** (`cec_carbob_stocks…`, `norcal_/socal_refinery_utilization_pct`) | CEC Weekly Fuels Watch (Tableau with Excel download) | 2005 | Posted Wed/Thu by 5 p.m. PT; "subject to refinery revision", no vintages | Free. **Statewide only**: CEC removed the North/South split, so the NorCal/SoCal features can't be backfilled and should be replaced by one statewide series |
| **Ethanol rack price** (`1.65 + 0.20·sin`) | Nebraska Dept. of Water, Energy and Environment monthly ethanol and gasoline rack prices (FOB Omaha, PDF) | 1982 | Monthly; from 2021 the ethanol price includes the RIN | Free; no free *daily* rack price exists |
| | USDA AMS MyMarketNews: National Daily Ethanol Report (slug 3617), Weekly (3616, includes CBOT/NYMEX settlements), Weekly Ag Energy Roundup (2805, includes the CME Chicago Ethanol futures nearby) | Jul 2022 (3616/3617) | Daily / weekly | Free key; these are **ethanol plant** prices, not terminal rack |
| **D6 RIN price** (`0.52 + 0.08·sin`) | EPA EMTS weekly volume-weighted average price of separated RINs by D-code | 2010 | Updated monthly; posting lag looks like 4–6 weeks *(unverified)*; values can be revised | Free; dashboard CSV export, no API. Lag the feature by at least one month |
| **Rig counts** (test mock as latest value, T-29) | Baker Hughes historical North America rotary rig count archive (Excel) plus the weekly report (Friday noon CT) | 2000 (archive files) | Weekly | Free with citation; re-download after methodology changes |
| **AQI** (71 of 85 records are a deterministic baseline) | EPA AirData daily AQI by CBSA; AirNow file products for recent days | Decades | AirData updated twice a year (June, December) and revised; AirNow is preliminary | Free. The economic link to gasoline prices is weak; consider dropping the family instead |
| **FERC tariff** (constant) | FERC oil-pipeline index multiplier (3.9) | Annual | Changes 1 Jul | Free |
| **Hurricanes** | NHC advisory archive (1998–) and GIS forecast-cone archive (2008–) | 1998 | As issued | Free; don't use HURDAT2 for backtests (re-analysed after the season) |

---

## 6. Genuinely new signals worth adding (free)

### 6.1 California price structure and compliance costs (Oakland_CA, BayArea_CA)

California is the one market where the price wedge between RBOB and the pump is large, policy-driven and published. Midgley currently types it in by hand.

| Source | What it gives | Cadence / history | Notes |
|---|---|---|---|
| **CARB weekly LCFS credit-transfer log** (`ww2.arb.ca.gov/resources/documents/weekly-lcfs-credit-transfer-activity-reports`) | A cumulative XLSX listing every credit transfer with completion date, posting date, price and volume (e.g. a volume-weighted $83.77/MT for 14–20 Sep 2026) | Weekly, posted the following Tuesday; log start date unverified | Replaces the 10 hand-typed LCFS points in `carb_compliance.py`. Monthly PDF summaries exist from Jan 2014 (Dec 2014 and Dec 2015 missing) and differ slightly (they exclude zero-price transfers but include pending ones). |
| **CARB auction settlement summary** (`ww2.arb.ca.gov/resources/documents/summary-auction-settlement-prices-and-results`) | Current and advance settlement prices and volumes for every auction since Nov 2012 (joint with Québec since Nov 2014) | Quarterly (Feb/May/Aug/Nov), results about a week later; PDF, plus a dashboard data download from Q4 2014 | The program was extended to 2045 and renamed **"Cap-and-Invest"** by AB 1207 and SB 840 (signed 19 Sep 2025); 2026 rule amendments were proposed in April 2026 (adoption unverified). |
| **CEC Estimated Gasoline Price Breakdown and Margins** | Monthly statewide components: crude cost, refinery costs and profits, distribution and marketing margin, LCFS and cap-and-trade costs (about 17¢ and 25¢ a gallon in Jan 2026), taxes and fees | Monthly, ~6-week lag (July data posted 11 Sep 2026) | CEC calls the page "temporary while a new dashboard is being developed", so expect breaks. |
| **CEC SB 1322 refiner cost disclosure** | Monthly gross and net refining margins (statewide and per anonymised refiner), crude cost, sales by channel | ≤45 days after month end | Some months were restated (May–Nov 2024); CEC flags the net margins as unreliable. Use the gross margin. |
| **Refinery closures** (structural breaks) | Phillips 66 Los Angeles stopped processing crude around 16 Oct 2025; Valero Benicia completed idling in April 2026 and now supplies Northern California through imports | Events | Add regime indicators. A model trained on 2022–2025 Bay Area behaviour has not seen a Northern California market without Benicia. |
| **Refinery upset reports** beyond BAAQMD | Contra Costa County Community Warning System and hazmat dashboard (near real time; HTML/Power BI, no export); South Coast AQMD Rule 1118 flare notifications for LA refineries (real time, scrape) | Event | Complements the existing BAAQMD feed. |

CEC's market-oversight division (DPMO) publishes no dataset, and refinery maintenance reports filed with the CEC are confidential, so there's no free California outage schedule.

### 6.2 Fuel-policy events (all regions)

| Source | What it gives | Access |
|---|---|---|
| **EPA emergency fuel waivers** (`epa.gov/gasoline-standards/fuel-waivers`) | Every waiver 2005–2026 with its letter: summer RVP/E15, state boutique fuels, hurricanes, Arctic diesel. In 2026, a nationwide E15/RVP waiver was issued 25 Mar, effective 1 May, renewed in 20-day steps, and the 20 Aug renewal moved the switch to winter gasoline up to 1 Sep. | HTML page and PDFs; no API or RSS, so scrape and parse the effective windows |
| **Federal Register API** (`federalregister.gov/api/v1`) | All EPA fuel rules since 1994; filter `conditions[agencies][]=environmental-protection-agency`, `conditions[cfr][title]=40`, `conditions[cfr][part]=1090` (fuels) or `80` (RFS). The `public-inspection-documents` endpoint shows filings before publication. | Free, no key, JSON/CSV |

These two replace the hand-typed "EPA statutory" RVP rows in `known_future_events.json` (T-4) with dated, sourced events. The 2026 waiver shows why: it moved the effective winter switch to 1 Sep this year, which a fixed 16 Sep row can't capture.

### 6.3 Supply logistics by region

| Region | Source | What it gives | Access and limits |
|---|---|---|---|
| Port_St_Lucie_FL | **U.S. Coast Guard port conditions** via NAVCEN (`navcen.uscg.gov/port-status`) | Condition WHISKEY / X-RAY / YANKEE / ZULU (tropical-storm winds expected within 72 / 48 / 24 / 12 h) for Sector Miami (Port Everglades), Sector Jacksonville (Port Canaveral) and Sector St. Petersburg (Port Tampa Bay) | Per-sector RSS of Broadcast Notices to Mariners; the status page is JavaScript-rendered with no API. Homeport was retired 12 Apr 2025. No official history, so archive it yourself. |
| | Why it matters | EIA: Florida has no refineries and no pipeline from surplus states; its gasoline arrives by ship, and Port Tampa Bay handles nearly half of it. Port closures are the main Florida-specific supply shock. | — |
| Charlotte_NC, Greenville_NC | Colonial Pipeline and PPL (formerly Plantation) | Tariffs are public (Colonial archive from 2012); allocation notices go only to shippers through the T4 portal; line-space values are paid (Argus, Platts; ICE LN1/LN2 futures listed in June 2026 settle on Platts) | No free daily signal. Use the news monitor (6.4) for Colonial outages and allocations. |
| Newark_DE | Delaware DNREC environmental release notifications (`derns.dnrec.delaware.gov`) | Releases and upsets, including the Delaware City refinery, notified within 24 h | HTML list and alerts |
| Cincinnati_OH/KY | Indiana IDEM virtual file cabinet (BP Whiting); Ohio EPA spills (ArcGIS JSON, no facility names); Illinois IEMA hazmat CSV | Midwest refinery and terminal incidents | PDFs or bulk files; lag unverified. Oklahoma DEQ excess-emission reports aren't public, so Tulsa has no equivalent. |
| All | IMF PortWatch (already used) | `portcalls_tanker`, `import_tanker`, `export_tanker` by U.S. port | Weekly Tuesday update with retroactive revisions; whether tankers are split into crude and product is unverified |

AIS ship tracking isn't worth it yet: aisstream.io is free but has no history and needs a long-running process, and NOAA MarineCadastre runs about a quarter behind (backfill only).

### 6.4 News and events with real history (A-6, T-5)

Today's event features come from Google News RSS, have no usable history and were wiped by the weekly refresh. These sources have years of history and permissive terms.

| Source | What it gives | History / cadence | Terms |
|---|---|---|---|
| **GDELT 2.0** (Events, Mentions, GKG) | Every news article it sees, with first-seen time, URL, themes and tone; BigQuery tables `gdelt-bq.gdeltv2.*` or raw 15-minute files | Feb 2015 → now, every 15 min. The DOC API (`api.gdeltproject.org/api/v2/doc/doc`) searches a rolling 3 months, 250 records per call, about one request every 5 s. Whether the raw files are still updating in Oct 2026 wasn't confirmed (the blog is active; the AWS mirror is not). | Free for academic, commercial and government use, with citation |
| **Caldara–Iacoviello Geopolitical Risk index, daily** (`matteoiacoviello.com/gpr_files/data_gpr_daily_recent.xls`) | A newspaper-based daily index | 1985 →; updated Mondays; dated vintages kept (`…_YYYYMMDD.xls`); recent values are preliminary and get revised | Free with citation (Caldara & Iacoviello, 2022, *AER*) |
| **U.S. daily Economic Policy Uncertainty** (FRED `USEPUINDXD`) | Daily news-based index | 1985 →; ~1-day lag; ALFRED vintages from 2014 | CC BY 4.0 at source |
| **OPEC decisions** | Känzig's oil-supply news shocks (daily OPEC-announcement surprises; CC BY 4.0; updated every ~6 months with a 4–5 month lag) and OPEC press releases for meeting dates (no feed) | Research and backtests; known-future meeting calendar | Free |

**How to use them honestly:**
- Use GDELT's first-seen timestamp as `published_at`, and dedupe by canonical URL (fixes D-5 and T-21 at the source).
- GPR and EPU give the model a geopolitical signal with 40 years of history, instead of an event count that only exists on the last row.
- **Don't let an LLM re-score historical headlines for training.** A current LLM already knows how those events turned out, so its scores would leak hindsight. For backtests, use non-LLM features (GDELT themes and tone, GPR, EPU) or a model whose knowledge cutoff precedes the evaluation window; evaluate LLM-scored features only on forecasts issued live.

### 6.5 Market expectations as an external benchmark

| Source | What it gives | Blocker |
|---|---|---|
| **Kalshi** AAA gas-price markets | Daily national (`KXAAAGASD`), weekly (`KXAAAGASW`) and monthly (`KXAAAGASM`) markets settling on AAA's average, plus daily state markets including Ohio, Florida, North Carolina and California (`KXAAAGASDCA` confirmed; other state tickers unverified). Public read endpoints with candlesticks. | **Terms:** the Developer Agreement limits API use to a member's own trading and bans storing or sharing the data; the data terms ban ML/AI use. Use only with written permission from Kalshi; otherwise, compare manually. |
| Polymarket | A few thin AAA-based gas markets | Terms restrict commercial use and redistribution; liquidity too thin |
| **EIA STEO** | Monthly retail gasoline price forecasts (U.S. and PADDs); every past issue archived as Excel since Aug 2004, so point-in-time benchmarking is possible | Monthly, so only a long-horizon sanity check; series IDs unverified (confirm from Table 4b of any `*_base.xlsx`) |

A market-implied price for the next day or week is the toughest benchmark Midgley could publish against. It's only worth pursuing if Kalshi grants permission.

### 6.6 Demand and competition structure (lower priority)

| Source | What it gives | Notes |
|---|---|---|
| TSA checkpoint throughput | National daily passenger counts (posted Mon–Fri, revised later) | Snapshot it yourself; a travel-demand proxy around holidays |
| Florida DOT traffic counts (ArcGIS `Traffic_TMSCOUNT_TDA`) | Hourly and daily volumes, rolling 6 months | The only free daily state feed found; check freshness |
| Caltrans PeMS | Bay Area (District 4) detector volumes since 2001 | Free account; terms and formats unverified |
| OpenStreetMap (Overpass or Geofabrik extracts) | Every fuel station with brand and operator tags; history back to 2012 | ODbL (attribution, share-alike for distributed databases). Useful to classify markets for the Edgeworth module (share of independents) |
| Census County Business Patterns | Gas-station counts by county (NAICS 447) | Annual (2023 latest); free API key required since May 2026 |
| Google Trends | Search interest ("gas shortage", "gas prices") as a panic-buying signal | Official API is still an application-only alpha; `pytrends` is archived |
| University of Michigan survey | Expected gas-price change over 1 and 5 years (Tables 39–40) | Monthly; free to download but no redistribution |

No U.S. state publishes station-level pump prices by law (unlike Germany or Western Australia), so there's no free station-level history for the Edgeworth module.

---

## 7. Paid data worth pricing

Free sources can't give terminal-level wholesale prices or metro retail history for Tulsa, Cincinnati, Charlotte, Greenville, Newark or Port St. Lucie. If Midgley is going to keep promising metro-level forecasts, this is where the money would go.

| Product | What it covers for Midgley | History |
|---|---|---|
| **OPIS rack prices** (30,000+ daily prices, 1,500+ terminals) | Tulsa [560] plus the Magellan, Conoco and Sinclair sub-racks; Cincinnati [300]; Covington KY [312]; Charlotte [46]; Selma NC [205]; Port Everglades [176]; Fort Lauderdale [64]; West Palm Beach [828]; Wilmington DE [243]; San Francisco [954]; Richmond [955]; San Jose [958] | Terminal level from Jul 2001 |
| **OPIS spot** | Group 3 (Mid-Continent, the Tulsa market), Chicago, San Francisco | From 1982 / 1990 / 1986 |
| **OPIS retail** (the data behind AAA's site) | ~5 million daily prices from ~150,000 outlets; history by station, ZIP, county or metro | Retail from 1996; DataHouse metro history from 2007 |
| OPIS Refinery Maintenance Report | Planned and unplanned outages by PADD | — |
| Argus US Products / Platts | Group Three and Group Three RBOB, Chicago, U.S. West Coast end-of-day prices (Platts Midwest Group 3 sub-octane settles ICE's GDL futures) | — |
| IIR Energy | Unit-level refinery outages, daily | — |
| Kpler / Vortexa | Refined-product tanker flows | From 2016–2017 |
| CME DataMine | Official settlement history by contract month (RBOB, ethanol) | Full |
| Kayrros (now part of Energy Aspects) | Satellite crude tank inventories; a refined-product product wasn't found | 8+ years |

**Recommendation:** if there's budget for one purchase, price **OPIS rack plus retail for the nine metros' terminals**. It fixes the two things free data can't: real metro ground truth everywhere (E-2), and the rack-to-retail pass-through the ECM is supposed to model (T-1). Licensed data must stay out of the public repo and dashboard; publish only Midgley's own forecasts.

---

## 8. Licensing check on what Midgley already uses

The repo, `data/` and the dashboard are public, so storing a value in a committed file is redistribution. Several current sources don't allow that. *(This is a terms-of-use reading, not legal advice; confirm before relying on it.)*

| Source in use | What its terms say | Midgley today | Action |
|---|---|---|---|
| AAA website (`gasprices.aaa.com`, scraped in `live_fuel_feed.py`) | Users may not "reproduce, distribute, create derivative works, display, modify, archive or otherwise exploit" the content; any commercial use is prohibited. The data comes from OPIS. | Second source tried for the live pump anchor; the value is stored in the public ledger (`current_base_price`) | Stop scraping; replace with EIA (weekly) or licensed OPIS. The 21 Sep handoff already flagged this. |
| Google Places API `fuelOptions` | No pre-fetching, storing or caching (except place IDs, and lat/lng for 30 days), and Maps content may not be used to "train, test, validate or fine-tune" ML models | `fetch_google_maps_fuel_prices()` exists in `live_fuel_feed.py`, but nothing calls it | Don't wire it in as a price history or a model input. |
| GasBuddy GraphQL | Terms on automated access weren't confirmed; no public data licence exists (owned by PDI Technologies) | First source tried for the live anchor | Treat as not permitted until confirmed. |
| EIA daily spot prices (via FRED `DGASNYH`, `DGASUSGULF`) | Supplied to EIA by Refinitiv (LSEG); FRED marks them copyrighted | Committed in data files | Use for modelling; don't commit the raw series. |
| Open-Meteo (forecast API in use; archive proposed) | Free tier is for non-commercial use only | In use | Decide whether Midgley is commercial (question 1, section 11). |

**Free and permissive** (fine for automated download and storage, with attribution where noted): EIA (check its reuse policy), BLS, FRED/ALFRED (series-by-series), CFTC, USGS, NOAA/NWS/NCEI/CPC, NASA POWER and FIRMS, CARB, CEC, EPA, Federal Register, GDELT (citation), GPR (citation), EPU (CC BY 4.0), Känzig (CC BY 4.0), OpenStreetMap (ODbL), `holidays` and `pandas_market_calendars` (MIT).

**Restricted:** Kalshi and Polymarket (no storage or ML use without permission), University of Michigan (no redistribution), Google Trends (alpha access only).

---

## 9. Coverage by metro

| Metro | Retail truth (free) | Wholesale reference | Local supply signals | Policy and tax | Paid upgrade |
|---|---|---|---|---|---|
| National | EIA U.S. weekly; ALFRED vintages | RBOB contract months (yfinance), EIA contracts 1–4 to Apr 2024 | WPSR stocks, utilisation, product supplied | EPA waivers, Federal Register | CME DataMine |
| Tulsa_OK | EIA PADD 2 weekly (no Oklahoma series) | RBOB; Gulf Coast spot (lagged). Group 3, the local market, is paid only | Cushing crude stocks; PADD 2 utilisation; no public refinery upset data in Oklahoma | Oklahoma rate (EIA tax table) | OPIS Tulsa rack, Group 3 spot |
| Cincinnati_OH | EIA Ohio weekly | RBOB; Chicago and Group 3 are paid only | PADD 2 stocks and utilisation; Ohio River at Cincinnati (USGS 03255000, NWPS `CCNO1`); BP Whiting (IDEM), Ohio EPA spills | **Ohio tax holiday, 4 Oct 2026 – 2 Jan 2027** | OPIS Cincinnati rack |
| Cincinnati_KY | EIA PADD 2 weekly (no Kentucky series) | Same as Cincinnati_OH | Same | Kentucky rate (EIA tax table) | OPIS Covington KY rack |
| Newark_DE | EIA PADD 1B weekly; BLS Philadelphia–Camden–Wilmington monthly | RBOB; New York Harbor spot (lagged) | PADD 1B gasoline stocks (`WGTST1B1`); Delaware City refinery (DNREC notifications, FIRMS) | Delaware rate | OPIS Wilmington DE rack |
| Charlotte_NC, Greenville_NC | EIA PADD 1C weekly; BLS South monthly | RBOB; Gulf Coast spot (lagged) | PADD 1C stocks; PADD 3 → 1 pipeline movements (monthly); Colonial news | North Carolina resets every 1 Jan (41.0¢ in 2026) | OPIS Charlotte and Selma racks |
| Port_St_Lucie_FL | EIA Florida weekly; BLS Miami–Fort Lauderdale–West Palm Beach monthly (excludes St. Lucie County) | RBOB; Gulf Coast spot (lagged) — supply is by ship | Coast Guard port conditions for Sectors Miami, Jacksonville, St. Petersburg; NHC advisories; PortWatch tanker calls | Florida rate | OPIS Port Everglades and West Palm Beach racks |
| Oakland_CA, BayArea_CA | EIA San Francisco weekly (covers Alameda and Contra Costa); EIA California weekly; BLS San Francisco–Oakland–Hayward monthly | Los Angeles RBOB/CARBOB spot (`DRGASLA`, lagged); no free San Francisco spot | CEC Fuels Watch (statewide); CEC margins; BAAQMD, Contra Costa and SCAQMD upset reports; Benicia and Phillips 66 closures as structural breaks | Excise 63.4¢ from 1 Jul 2026; sales tax 2.25% plus district; CARB LCFS weekly log; cap-and-invest auctions | OPIS San Francisco and Richmond racks |

---

## 10. Implementation order and acceptance criteria

Effort is a rough guide: **S** = under a day, **M** = 1–3 days, **L** = a week or more.

**Phase 0 — this week, and before 16 Nov 2026**
1. Load the Ohio tax holiday and its 3 Jan 2027 reversal; correct the California and North Carolina rows; drop the RVP price rows (4.6, 6.2). **S**
2. EIA API v2 client; the retail ground-truth mapping in 4.1, with the tier recorded in `data_source_provenance`; WPSR series in 4.3. **M**
3. Migrate USGS calls to `api.waterdata.usgs.gov` (3.7). **S–M, hard deadline 16 Nov 2026**
4. NYMEX calendar for horizons and target dates; same-contract (roll-aware) targets (4.4, 4.5). **S–M**
5. Take the AAA and GasBuddy scrapes out of the model path and the committed ledger, or get licences (8). **S** once decided

**Phase 1 — next 2–3 weeks: real history for existing families**
6. Fix CFTC (3.4), spot history (3.5), rigs (3.3), FERC (3.9); add ALFRED vintages (4.7) and BLS metro prices (4.2). **M**
7. Backfill degree days, ethanol, D6 RIN, California Fuels Watch and river levels (section 5). **M–L**
8. Start archiving contract-month settlements (4.4) and Coast Guard port conditions (6.3) daily, since neither has free history. **S**
9. Admit each family to the model only after a purged-CV ablation; drop the ones that don't help (AQI is the likeliest candidate). **M**

**Phase 2 — new signals**
10. California compliance and price structure: CARB LCFS weekly log, cap-and-invest auctions, CEC margins, closure regime flags (6.1). **M**
11. EPA fuel waivers and the Federal Register API (6.2). **S–M**
12. GDELT, GPR and EPU event features, with non-LLM scoring for backtests (6.4). **L**
13. Regional upset feeds: Delaware DNREC, Contra Costa, SCAQMD (6.1, 6.3). **M**
14. Decisions: OPIS (section 7) and Kalshi permission (6.5).

**Acceptance criteria**
- [ ] Every metro's actuals come from a named official series, with the tier (`EIA_CITY_SanFrancisco`, `EIA_STATE_OH`, `EIA_PADD_1C`, …) recorded on each row. No metro uses another geography's series without saying so, and no request goes to a FRED ID that doesn't exist.
- [ ] No training feature is a deterministic function of the calendar: an automated check fails any column whose R² against sin/cos of day-of-year (plus a constant) exceeds 0.99 over the training window.
- [ ] Every admitted feed has `published_at` on every record, at least 90% `LIVE`/`CACHED` coverage of the training window, and an entry in the truncation-invariance test that includes the last row.
- [ ] Every new family has a recorded purged-CV ablation result.
- [ ] No horizon or target date falls on a NYMEX holiday, and no h-day target spans a contract expiry unadjusted.
- [ ] The tax calendar reproduces Ohio's 4 Oct 2026 cut and 3 Jan 2027 reversal and California's 1 Jul changes, with `source_url` on every row.
- [ ] No licensed or restricted data (AAA, Google Places, GasBuddy, OPIS, Kalshi, raw Refinitiv spot prices) is committed to the public repo or shown on the dashboard.
- [ ] No call goes to `waterservices.usgs.gov` after 16 Nov 2026.

---

## 11. Open questions for Marty

1. **Is Midgley commercial, now or later?** The answer decides whether you can use Open-Meteo's free tier, and it matters for Kalshi, Polymarket, University of Michigan, AAA and Google terms.
2. **Is there budget for OPIS rack and retail data** for the nine metros' terminals? If not, should Tulsa, Cincinnati_KY, Newark, Charlotte and Greenville be relabelled as PADD-level forecasts, or dropped until real metro data exists?
3. **Should Oakland_CA and BayArea_CA merge?** Both map to the same official series (San Francisco), and both get the same free wholesale reference.
4. **What should the live pump anchor be** once the AAA and GasBuddy scrapes go? The free option is the latest EIA weekly price, which can be up to 8 days old. A licensed feed would fix that.
5. **Do you want to ask Kalshi for written permission** to use its AAA gas-price markets as a published benchmark?

---

## 12. Do not

- **Don't add a feed as a model feature if it only has a live value.** That's exactly how A-3 happened.
- **Don't store fallback or benchmark values as observations,** or label them `LIVE`.
- **Don't let an LLM score historical headlines for training.** It knows the outcomes. Backtest with non-LLM event features; evaluate LLM features on live forecasts only.
- **Don't backtest on revised data as if it were known at the time** (HURDAT2, re-analysed weather, revised EIA/BLS values): use vintages or a publication lag.
- **Don't scrape AAA or GasBuddy, or store Google Places content.**
- **Don't commit licensed data** to the public repo or publish it on the dashboard.
