"""
Wiki Synchronization Script for Midgley v0.8.6 (scripts/sync_wiki_v086.py)
Synchronizes /home/marty/projects/midgley.wiki with the latest architecture:
- 18 Regional Metro Calibration Hubs across PADDs 1-7
- Google Gemini 3.8 Flash LLM Engine
- Enverus Daily Rig Count Feed (Card 2.2b)
- Discord Bot & Slash Commands (/midgley) with Ed25519 interactions
- 5-digit ZIP geocoding & out-of-metro subscriber telemetry
- Environment variables & database migrations for v0.8.6
- RELEASE_NOTES_v0.8.5.md and RELEASE_NOTES_v0.8.6.md
"""

import os
import re
import sys
import shutil


def sync_wiki(repo_dir: str, wiki_dir: str):
    if not os.path.exists(wiki_dir):
        print(f"Error: Wiki directory '{wiki_dir}' does not exist.")
        sys.exit(1)

    print(f"Starting Wiki synchronization targeting: {wiki_dir}")

    # -------------------------------------------------------------
    # 1. Copy direct counterpart files from repo to wiki
    # -------------------------------------------------------------
    direct_copies = [
        ("API.md", "API.md"),
        ("ARCHITECTURE.md", "ARCHITECTURE.md"),
        ("AGENTS.md", "AGENTS.md"),
        ("SELF_HOSTING.md", "SELF_HOSTING.md"),
        ("SELF_HOSTING.md", "Self-Hosting.md"),
        ("RELEASE_NOTES_v0.8.5.md", "RELEASE_NOTES_v0.8.5.md"),
        ("RELEASE_NOTES_v0.8.6.md", "RELEASE_NOTES_v0.8.6.md"),
    ]

    for src_rel, dst_rel in direct_copies:
        src_path = os.path.join(repo_dir, src_rel)
        dst_path = os.path.join(wiki_dir, dst_rel)
        if os.path.exists(src_path):
            shutil.copy2(src_path, dst_path)
            print(f"  [Copied] {src_rel} -> {dst_rel}")
        else:
            print(f"  [Warning] Source file not found: {src_path}")

    # -------------------------------------------------------------
    # 2. Update Home.md
    # -------------------------------------------------------------
    home_path = os.path.join(wiki_dir, "Home.md")
    if os.path.exists(home_path):
        with open(home_path, "r", encoding="utf-8") as f:
            home_text = f.read()

        # Update version badges
        home_text = re.sub(r"Release-v[0-9.]+-orange", "Release-v0.8.6-orange", home_text)
        home_text = re.sub(r"releases/tag/v[0-9.]+", "releases/tag/v0.8.6", home_text)
        home_text = re.sub(r"Dev-v[0-9.]*--?dev-blue", "Dev-v0.8.6--dev-blue", home_text)
        home_text = re.sub(r"\(`midgley` v[0-9.]+[^\)]*\)", "(`midgley` v0.8.6 / v0.8.6-dev)", home_text)
        home_text = home_text.replace("Gemini 2.5 Flash", "Gemini 3.8 Flash")

        # Replace stale forecast table block if present
        if "<!-- START_LIVE_FORECAST -->" in home_text:
            live_portal_block = """<!-- START_LIVE_FORECAST -->
### 📢 Live Price Forecasts & Real-Time Analytics Portal

Midgley continuously generates rolling 1-day to 5-day out-of-time price forecasts across **18 Regional Metro Calibration Hubs** and national wholesale RBOB futures (`RB=F`).

👉 **[Access the Live Interactive Dashboard & Visual Analytics (koshiirra.github.io/midgley)](https://koshiirra.github.io/midgley/)**

| PADD Region | Calibration Hub | Primary Refining / Ingestion Infrastructure | Model Pipeline |
| :--- | :--- | :--- | :--- |
| **National** | Wholesale RBOB (`RB=F`) | NYMEX / CME Futures & 3-2-1 Crack Spreads | `v1.6-Ipatieff-National-Ridge` |
| **PADD 1A** | Boston & New England, MA | Irving Oil Saint John & Waterborne Imports | `v1.6-Ipatieff-Boston-Ridge` |
| **PADD 1B** | New York Harbor & NY State, NY | Phillips 66 Bayway & Buckeye Pipeline | `v1.6-Ipatieff-NewYork-Ridge` |
| **PADD 1B** | Newark & Northern NJ, DE | PBF Delaware City & C&D Canal Lightering | `v1.6-Ipatieff-Newark-Ridge` |
| **PADD 1C** | Charlotte & Carolinas Hub, NC/SC | Colonial Pipeline Paw Creek & Selma/Apex | `v1.6-Ipatieff-Charlotte-Ridge` |
| **PADD 1C** | Port St. Lucie & South FL, FL | Port Everglades & Port Canaveral Waterborne | `v1.6-Ipatieff-PortStLucie-Ridge` |
| **PADD 2** | Greater Chicago, IL/IN | BP Whiting & CITGO Lemont (Edgeworth Cycles) | `v1.6-Ipatieff-Chicago-Ridge` |
| **PADD 2** | Cincinnati Tri-State, OH/KY | Marathon Catlettsburg & Ohio River Barges | `v1.6-Ipatieff-CincinnatiOH-Ridge` |
| **PADD 2** | Tulsa Metro, OK | HF Sinclair Tulsa & Cushing Delivery Hub | `v1.6-Ipatieff-Tulsa-Ridge` |
| **PADD 3** | Houston Metro & USGC, TX | ExxonMobil Baytown & Motiva Port Arthur | `v1.6-Ipatieff-Houston-Ridge` |
| **PADD 4** | Denver & Rocky Mountain, CO | Suncor Commerce City & High-Altitude RVP | `v1.6-Ipatieff-Denver-Ridge` |
| **PADD 5** | SF Bay Area 9-County, CA | Chevron Richmond & CaRFG Clean Fuel Wedge | `v1.6-Ipatieff-BayArea-Ridge` |
| **PADD 5** | Los Angeles Basin, CA | Marathon Carson/Wilmington & San Pedro Bay | `v1.6-Ipatieff-LosAngeles-Ridge` |
| **PADD 5B** | Seattle-Tacoma & Puget Sound, WA | bp Cherry Point & Olympic Pipeline | `v1.6-Ipatieff-Seattle-Ridge` |
| **PADD 5C** | Phoenix & Desert Southwest, AZ | Kinder Morgan SFPP West/East Pipeline Headers | `v1.6-Ipatieff-Phoenix-Ridge` |
| **PADD 5D** | Anchorage & Southcentral AK, AK | Marathon Kenai & Cook Inlet Marine Barges | `v1.6-Ipatieff-Anchorage-Ridge` |
| **PADD 5D** | Honolulu & Oahu Island, HI | Par Hawaii Kapolei & Inter-Island Ocean Barges | `v1.6-Ipatieff-Honolulu-Ridge` |
| **PADD 6** | San Juan & U.S. Caribbean, PR | DACO Regulated Margins & USGC Jones Act Tankers | `v1.6-Ipatieff-SanJuan-Ridge` |
| **PADD 7** | Hagåtña & Apra Harbor, Guam | Asia-Pacific Product Tankers (MOPS 92 Singapore) | `v1.6-Ipatieff-Guam-Ridge` |

*🌐 Live actuals, directional confidence intervals, and MLOps scoreboards are updated dynamically on GitHub Pages.*
<!-- END_LIVE_FORECAST -->"""
            home_text = re.sub(
                r"<!-- START_LIVE_FORECAST -->.*?<!-- END_LIVE_FORECAST -->",
                live_portal_block,
                home_text,
                flags=re.DOTALL
            )

        with open(home_path, "w", encoding="utf-8") as f:
            f.write(home_text)
        print("  [Updated] Home.md")

    # -------------------------------------------------------------
    # 3. Update Regional-Metro-Models.md
    # -------------------------------------------------------------
    rmm_path = os.path.join(wiki_dir, "Regional-Metro-Models.md")
    rmm_content = """# 🗺️ Regional Metro Calibration Models & Geographic Sub-Packages

Midgley calibrates national wholesale RBOB futures (`RB=F`) to regional retail pump prices using modular subpackages located in `src/locations/`. Each regional calibration agent incorporates localized rack margins, delivery hub logistics, state tax burdens, refining infrastructure, and local weather/seismic alert vectors across **18 Canonical Regional Calibration Hubs** covering all Petroleum Administration for Defense Districts (PADDs 1 through 7).

---

## 🏗️ 18 Canonical Regional Metro Calibration Specifications

### 1. Tulsa Metro Model (`src/locations/tulsa/`)
* **PADD Region:** PADD 2 (Mid-Continent)
* **Key Delivery Hub:** Cushing, OK WTI Futures Delivery Hub
* **Refining Infrastructure:** West Tulsa HF Sinclair Refinery (125,000 bpd capacity)
* **Calibration Equation:**
  $$P_{\\text{Tulsa Retail}} = P_{\\text{Wholesale RBOB}} + \\text{Dynamic Rack Margin}_{\\text{Tulsa}} + T_{\\text{OK Tax}}$$
* **Local Shocks Modeled:** HF Sinclair refinery outages, Cushing pipeline spills, SPC convective tornado outlooks for Tulsa County (`OKZ060`).

---

### 2. Newark Metro Model (`src/locations/newark/`)
* **PADD Region:** PADD 1B (Central Atlantic)
* **Refining Infrastructure:** PBF Delaware City Refinery (190,000 bpd capacity)
* **Delivery & Logistics Corridors:** Delaware Bay deepwater lightering (Big Stone Anchorage), USGS Delaware River cooling water temperature thermal limits (`01477050`), estuarine salinity front tracking (`00095`), & Chesapeake & Delaware (C&D) Canal barge detour events.
* **Calibration Equation:**
  $$P_{\\text{Newark Retail}} = P_{\\text{Wholesale RBOB}} + \\text{Dynamic Rack Margin}_{\\text{Newark}} + T_{\\text{DE Tax}} + \\Delta P_{\\text{Canal Detour}}$$
* **Detour Premium Impact:** C&D Canal closure triggers a 300 nm marine detour around Delmarva Peninsula, causing a +$0.097/gal rack margin expansion ($p = 0.00191$).

---

### 3. Cincinnati Tri-State Metro Model (`src/locations/cincinnati/`)
* **PADD Region:** PADD 2 / Tri-State (OH / KY / IN)
* **Refining Infrastructure:** Marathon Catlettsburg, KY Refinery (290,000 bpd capacity)
* **Microstructure Cycles:** Asymmetric Edgeworth Price Cycling (quick sharp price jumps followed by slow undercutting decays).
* **Calibration Equations:**
  $$P_{\\text{Cincinnati OH}} = P_{\\text{Wholesale RBOB}} + \\text{Dynamic Rack Margin} + T_{\\text{OH Tax}} + \\Delta P_{\\text{River Draft}}$$
  $$P_{\\text{Cincinnati KY}} = P_{\\text{Wholesale RBOB}} + \\text{Dynamic Rack Margin} + T_{\\text{KY Tax}} + \\Delta P_{\\text{River Draft}}$$
* **Dual-State Tax Differential:** Ohio state fuel tax ($0.385/gal) vs Kentucky fuel tax ($0.315/gal), generating cross-river retail arbitrage.
* **USGS Ohio River Telemetry:** Gauging Cincinnati Ohio River stage (`03255000`) and Markland Locks low-water draft restrictions halting barge tows.

---

### 4. Charlotte Metro & Carolinas Hub Model (`src/locations/charlotte/`)
* **PADD Region:** PADD 1C (Lower Atlantic)
* **Refining Logistics:** 100% pipeline-dependent via Colonial Pipeline Lines 1 & 2 originating in Pasadena/Houston, TX.
* **Breakout Junctions:** Colonial Pipeline Paw Creek (Charlotte terminal farm) and Selma/Apex breakout hubs.
* **Consolidation Note:** Greenville, NC was consolidated into this unified Carolinas Calibration Hub (Issue #635).
* **Cross-Border Tax Differential:** North Carolina state fuel tax ($0.404/gal) vs South Carolina state tax ($0.288/gal).
* **Weather Alert Vectors:** Mecklenburg County (`NCZ071`) Catawba River flood stages and winter freezing rain/ice storms.

---

### 5. SF Bay Area 9-County Regional Model (`src/locations/bay_area/`)
* **PADD Region:** PADD 5 (West Coast)
* **Refining Infrastructure:** Chevron Richmond (245 kbpd), Valero Benicia (145 kbpd), Shell/PBF Martinez (157 kbpd), Phillips 66 Rodeo (140 kbpd renewable fuels).
* **Consolidation Note:** Oakland, CA was aliased and consolidated into this comprehensive 9-county regional model.
* **Regulatory Fuel Standard:** California CARB CaRFG reformulated gasoline mandate and Low Carbon Fuel Standard (LCFS) credit burdens ($0.953/gal combined state tax/regulatory wedge).
* **Physical Hazard Risk Matrix:** USGS Hayward Fault seismic pipeline trip valves, PG&E Public Safety Power Shutoffs (PSPS), and atmospheric river flood stages on the Carquinez Strait.

---

### 6. Port St. Lucie Metro Model (`src/locations/port_st_lucie/`)
* **PADD Region:** PADD 1C (Lower Atlantic - Florida Peninsula)
* **Refining Logistics:** Zero in-state refining capacity; >95% waterborne marine barge offloading dependency via Port Everglades (Fort Lauderdale) and Port Canaveral marine tanker terminals.
* **Calibration Equation:**
  $$P_{\\text{PSL Retail}} = P_{\\text{Wholesale RBOB}} + \\text{Dynamic Rack Margin} + T_{\\text{FL Tax}} + \\Delta P_{\\text{Waterborne Detour}}$$
* **Weather & Marine Vulnerability:** Atlantic tropical cyclone tracks (hurricanes Ian, Nicole, Milton), St. Lucie County (`FLZ147`) evacuation demand surges, and Gulf-to-Atlantic Jones Act tanker transit delays.

---

### 7. Greater Chicago Metro Model (`src/locations/chicago/`)
* **PADD Region:** PADD 2 (Midwest)
* **Refining Infrastructure:** BP Whiting, IN (435,000 bpd capacity - largest inland refinery in the US) & CITGO Lemont, IL (177,000 bpd).
* **Pipelines & Corridors:** Wolverine, West Shore, Badger, and Explorer Pipelines connecting Lake Michigan terminals.
* **Microstructure Cycles:** Severe asymmetric Edgeworth price cycling across Cook County, DuPage County, and Northwest Indiana.
* **Tax Wedge:** Illinois combined state + Cook County + Chicago municipal fuel taxes ($0.550/gal baseline tax burden) vs Northwest Indiana tax relief ($0.380/gal differential).

---

### 8. Houston Metro & USGC Model (`src/locations/houston/`)
* **PADD Region:** PADD 3 (Gulf Coast)
* **Refining Infrastructure:** ExxonMobil Baytown (560 kbpd), Motiva Port Arthur (630 kbpd - largest refinery in North America), Marathon Galveston Bay (593 kbpd), Valero Houston (205 kbpd).
* **Pipeline Corridors:** Origin point for Colonial Pipeline Lines 1 & 2 (carrying 2.5 million bpd to East Coast) and Explorer Pipeline (to Midwest).
* **Market Characteristics:** Lowest statutory fuel excise taxes ($0.200/gal), zero pipeline transport markup, direct correlation with international export parity and USGC waterborne tanker loadings.

---

### 9. Los Angeles Basin Model (`src/locations/los_angeles/`)
* **PADD Region:** PADD 5 (West Coast - Southern California)
* **Refining Infrastructure:** Marathon Carson/Wilmington (363 kbpd), Chevron El Segundo (269 kbpd), PBF Torrance (166 kbpd), Valero Wilmington (135 kbpd).
* **Logistics:** Kinder Morgan SFPP pipeline system (North Line to Central Valley, East Line to Barstow/Vegas, West Line to San Diego) and San Pedro Bay marine tanker moorings.
* **Regulatory Compliance:** Strict South Coast Air Quality Management District (SCAQMD) and CARB CaRFG specifications with ultra-tight seasonal summer/winter blend transitions.

---

### 10. Denver Metro & Rocky Mountain Hub (`src/locations/denver/`)
* **PADD Region:** PADD 4 (Rocky Mountain)
* **Refining Infrastructure:** Suncor Commerce City Refinery (103,000 bpd capacity - sole refinery in Colorado).
* **High-Altitude Specifications:** Statutory 85-octane regular unleaded allowed due to high atmospheric altitude (>5,000 ft), lowering refining blending expense.
* **Winter Weather Risks:** Severe Front Range blizzard closures on I-70/I-25 corridors and sub-zero freeze-offs in the DJ Basin.

---

### 11. New York Harbor & NY State Hub (`src/locations/new_york/`)
* **PADD Region:** PADD 1B (Central Atlantic)
* **Refining Infrastructure:** Phillips 66 Bayway, NJ (258 kbpd), New York Harbor barge terminals, Buckeye Pipeline.
* **Logistics & Delivery:** Northern terminus of Colonial Pipeline; marine barge transfers to Long Island Sound and Hudson River terminals up to Albany.
* **Urban vs Rural Wedge:** Manhattan and Westchester congestion premiums vs Upstate Albany/Adirondack distribution markups.

---

### 12. Seattle-Tacoma & Puget Sound (`src/locations/seattle/`)
* **PADD Region:** PADD 5B (Pacific Northwest)
* **Refining Infrastructure:** bp Cherry Point (242 kbpd) & Phillips 66 Ferndale (105 kbpd) in Whatcom County.
* **Pipeline:** Olympic Pipeline System running north-south from Puget Sound refineries to Portland, OR.
* **CARB Decoupling (Issue #622):** Explicitly decoupled from California CARB rules; Washington Climate Commitment Act (CCA) carbon allowances modeled independently.

---

### 13. Phoenix Metro & Desert Southwest (`src/locations/phoenix/`)
* **PADD Region:** PADD 5C (Desert Southwest)
* **Refining Infrastructure:** Zero in-state refineries; 100% dependent on interstate pipeline shipments via Kinder Morgan SFPP West Line (from LA Basin) and East Line (from El Paso, TX).
* **Market Dynamics:** Dual-source arbitrage where prices swing dynamically based on LA vs Gulf Coast refining outages.

---

### 14. Anchorage & Southcentral Alaska Hub (`src/locations/anchorage/`)
* **PADD Region:** PADD 5D (Alaska)
* **Refining Infrastructure:** Marathon Kenai Refinery (68 kbpd) on the Cook Inlet.
* **Distribution Logistics:** Cook Inlet ice-class marine product tankers and Alaska Railroad tank car corridors to Fairbanks.
* **Lowest Fuel Tax:** State gasoline tax rate of $0.0895/gal (lowest in the United States).

---

### 15. Honolulu & Oahu Island Hub (`src/locations/honolulu/`)
* **PADD Region:** PADD 5D (Hawaii)
* **Refining Infrastructure:** Par Hawaii Kapolei Refinery (94 kbpd) on Oahu.
* **Logistics:** Young Brothers inter-island tug-and-barge transshipments to Maui, Kauai, and Hawaii Island.
* **Import Parity:** Dependent on foreign crude tankers (crude imports from South America and Asia-Pacific).

---

### 16. Hagåtña & Apra Harbor, Guam (`src/locations/guam/`)
* **PADD Region:** PADD 7 (Western Pacific Territories)
* **Logistics:** 100% ocean-tanker import dependence via Asia-Pacific refiners (Singapore and South Korea MOPS 92 RON gasoline benchmark).
* **Infrastructure:** Cabras Island Fuel Pier, Mobil and Shell marine storage headers at Apra Harbor.
* **Typhoon Vulnerability:** Super typhoon port closures, naval fuel replenishment competition, and long-lead maritime supply lines.

---

### 17. San Juan Metro & U.S. Caribbean Territories (`src/locations/san_juan/`)
* **PADD Region:** PADD 6 (Caribbean Territories)
* **Logistics:** Waterborne Jones Act product tankers from Houston and Corpus Christi, TX, plus USVI storage terminals.
* **Regulatory Oversight:** Puerto Rico Department of Consumer Affairs (DACO) statutory maximum gross profit margin caps on wholesale and retail fuel distributors.
* **Hurricane Tracking:** Comprehensive Caribbean tropical cyclone disruption tracking across San Juan Bay tanker moorings.

---

### 18. Boston Metro & New England Hub (`src/locations/boston/`)
* **PADD Region:** PADD 1A (New England)
* **Refining Infrastructure:** Irving Oil Saint John Refinery (320 kbpd, New Brunswick, Canada) and waterborne tanker imports into Boston Harbor.
* **Winter Distillate Competition:** Severe seasonal margin spikes when winter cold snaps trigger dual-fuel power generation switching from natural gas to fuel oil/ULSD.

---

## 🗺️ GeoPandas Spatial Distance-Decay & Refinery Buffering Engine (Issue #95)

Midgley integrates **GeoPandas** (`geopandas`) and **Shapely** (`shapely`) in `src/spatial_refinery.py` to calculate spatial distance-decay factors from oil refineries, pipeline corridors, and petroleum marine terminals to regional retail gas station clusters.

### Spatial Engine Features:
- **WGS84 Point Indexing & Web Mercator Projection (`EPSG:3857`):** Maps key refining assets and metro cluster centroids.
- **Multi-Ring Spatial Buffer Polygons:** Generates buffer polygon rings (`25mi`, `50mi`, `100mi`, `250mi`, `500mi`) around refining infrastructure.
- **Exponential Spatial Attenuation:** Computes exponential spatial decay weights:
  $$w(d) = \\exp\\left(-\\frac{d}{150.0}\\right)$$
- **Refinery Outage Shock Propagation Multiplier ($\\Delta P_{\\text{shock}}$):** Scales localized price shock impact by refinery capacity (bpd), outage severity, and spatial distance-decay weight $w(d)$.
- **Spherical Haversine Fallback Engine:** Automatically falls back to mathematical Haversine calculations when GeoPandas is uninstalled in lightweight container environments.
"""

    with open(rmm_path, "w", encoding="utf-8") as f:
        f.write(rmm_content)
    print("  [Updated] Regional-Metro-Models.md")

    # -------------------------------------------------------------
    # 4. Update Data-Ingestion-and-APIs.md
    # -------------------------------------------------------------
    apis_path = os.path.join(wiki_dir, "Data-Ingestion-and-APIs.md")
    if os.path.exists(apis_path):
        with open(apis_path, "r", encoding="utf-8") as f:
            apis_text = f.read()

        apis_text = apis_text.replace("Gemini 2.5 Flash", "Gemini 3.8 Flash")

        enverus_section = """
---

## 2.2b Enverus Daily Rig Count & Basin Telemetry (src/enverus_rig_feed.py, Issues #533, #640)
* **Module:** `src/enverus_rig_feed.py` & `workers/enverus_scraper.ts`
* **Edge Scraper:** Cloudflare Browser Rendering API (`MYBROWSER` binding) accessing `https://www.enverus.com/dailyrigcount/` via edge Markdown conversion with 12-hour edge caching.
* **REST Failover:** Direct fallback to Drillinginfo API endpoints (`app.drillinginfo.com/drcservice/api/*`).
* **Bitemporal Tracking:** Persists release dates and publication timestamps to `data/enverus_rig_vintages.json`.
* **Basin Metrics Ingested:** Permian, Gulf Coast, Eagle Ford, Bakken, Williston, Appalachia, and Total US Daily Rig Counts.
* **Feature Injection:** `enverus_permian_rigs` and `enverus_gulf_coast_rigs` in the quantitative feature matrix replacing stale weekly multipliers.
"""
        if "Enverus Daily Rig Count" not in apis_text:
            if "## 3. Incoming Intraday Webhook Gateway" in apis_text:
                apis_text = apis_text.replace("## 3. Incoming Intraday Webhook Gateway", enverus_section + "\n## 3. Incoming Intraday Webhook Gateway")
            else:
                apis_text += enverus_section

        discord_section = """
---

## 22. Discord Bot Gateway, Slash Commands & Edge Subscriptions (Issue #235)
* **Module:** `src/discord_notifier.py`, `workers/intraday_monitor_worker.ts` & `src/zip_geocoding.py`
* **Slash Commands Supported (`/midgley`):**
  - `/midgley forecast <locale>`: Retrieves instantaneous 5-day price predictions for any of the 18 calibration hubs or geocoded 5-digit ZIP codes.
  - `/midgley subscribe <zip_code>`: Subscribes a Discord channel or user Direct Message channel to daily morning price updates and high-severity anomaly alerts.
  - `/midgley unsubscribe <zip_code>`: Deactivates an active ZIP subscription.
  - `/midgley alerts`: Lists registered alert thresholds and active subscriptions.
  - `/midgley status`: Returns system status, model engine version (Gemini 3.8 Flash), and data feed freshness.
* **Edge Interaction Webhook Route:** `POST /discord/interactions` hosted on Cloudflare Workers with cryptographic **Ed25519 signature verification** (`X-Signature-Ed25519` and `X-Signature-Timestamp` via `tweetnacl`).
* **Multi-Subscriber SQLite Registry:** `data/subscribers.sqlite` storing channel IDs, user IDs, 5-digit zero-padded ZIP targets, and notification preference flags.
* **CARTO Basemap Demand Telemetry:** Unmapped out-of-metro subscriber lookups are aggregated into `data/unmapped_zip_telemetry.json` and rendered as Leaflet interactive demand heatmaps on `docs/telemetry.html`.
"""
        if "Discord Bot Gateway" not in apis_text:
            apis_text += discord_section

        with open(apis_path, "w", encoding="utf-8") as f:
            f.write(apis_text)
        print("  [Updated] Data-Ingestion-and-APIs.md")

    # -------------------------------------------------------------
    # 5. Update Agent-Architecture.md
    # -------------------------------------------------------------
    aa_path = os.path.join(wiki_dir, "Agent-Architecture.md")
    if os.path.exists(aa_path):
        with open(aa_path, "r", encoding="utf-8") as f:
            aa_text = f.read()

        aa_text = aa_text.replace("Gemini 2.5 Flash", "Gemini 3.8 Flash")
        aa_text = aa_text.replace("gemini-2.5-flash", "gemini-3.8-flash")
        aa_text = aa_text.replace("8 regional hubs", "18 regional calibration hubs")
        aa_text = aa_text.replace("8 metro hubs", "18 metro calibration hubs")

        with open(aa_path, "w", encoding="utf-8") as f:
            f.write(aa_text)
        print("  [Updated] Agent-Architecture.md")

    print("Wiki synchronization completed successfully.")


if __name__ == "__main__":
    repo_directory = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    wiki_directory = sys.argv[1] if len(sys.argv) > 1 else "/home/marty/projects/midgley.wiki"
    sync_wiki(repo_directory, wiki_directory)
