"""
Script to update midgley wiki with Issue #54 (Air Quality Telemetry & Refinery Outage Ingestion).
"""

import os
import shutil

wiki_dir = "/home/marty/projects/midgley/wiki_tmp"
repo_dir = "/home/marty/projects/midgley"

# 1. Update Self-Hosting.md
shutil.copyfile(os.path.join(repo_dir, "SELF_HOSTING.md"), os.path.join(wiki_dir, "Self-Hosting.md"))
print("Copied updated SELF_HOSTING.md to wiki_tmp/Self-Hosting.md")

# 2. Update Data-Ingestion-and-APIs.md
apis_file = os.path.join(wiki_dir, "Data-Ingestion-and-APIs.md")
with open(apis_file, "r", encoding="utf-8") as f:
    apis_content = f.read()

aqi_section = """
---

## 29. Multi-Feed Air Quality Ingestion, EPA AirNow Ozone Alerts & Summer-Blend RVP Compliance (Issues #54 & #73)
* **Module:** `src/aqi_feed.py` | **REST APIs:** `GET /api/v1/aqi/live`, `GET /api/v1/aqi/ozone-alerts` | **MCP Tools:** `get_refinery_aqi_anomalies`, `get_regional_ozone_alerts`
* **API Providers:**
  - **EPA AirNow API (`airnowapi.org`):** Federal municipal monitoring network tracking real-time ground-level ozone ($\text{O}_3$), $\text{PM}_{2.5}$, and $\text{PM}_{10}$ observations across 7 regional hubs. Flags Ozone Action Days ($\text{AQI}_{\text{O3}} \ge 101$) to compute statutory Reid Vapor Pressure (RVP) summer-blend compliance surcharges.
  - **PurpleAir API:** Crowdsourced optical particulate sensors ($\text{PM}_{1.0}, \text{PM}_{2.5}, \text{PM}_{10}$) within 15 km fence-line polygons downwind of refining facilities.
  - **OpenAQ API:** Global open environmental stations providing continuous chemical gas monitoring ($\text{SO}_2, \text{NO}_2, \text{O}_3, \text{CO}$) to confirm sulfurous flaring.
  - **WAQI (World Air Quality Index):** Global bounding box fallback.
* **Cost & Credentials:** Free developer tier (500 req/hr with `AIRNOW_API_KEY`), 1-hour EPA AirNow lookup caching (`global_cache`), and 100% deterministic offline fallback.
* **Monitored Refining Corridors & Target Hubs:**
  1. `bay_area` / `94612` (PADD 5): Chevron Richmond (245k bpd), PBF Martinez (157k bpd), Valero Benicia (145k bpd) (CARB 7.0 psi RVP, +$0.180/gal summer base).
  2. `tulsa` / `74101` (PADD 2): HF Sinclair West Tulsa (85k bpd) and Phillips 66 Ponca City (200k bpd) (9.0 psi RVP, +$0.050/gal summer base).
  3. `delaware_valley` / `19711` (PADD 1B): PBF Delaware City (180k bpd) and Phillips 66 Bayway (238k bpd) (9.0 psi RVP, +$0.060/gal summer base).
  4. `tri_state` / `45202` (PADD 2): Marathon Catlettsburg (291k bpd) along the Ohio River Valley (EPA Non-Attainment 7.8 psi RVP, +$0.085/gal summer base).
  5. `carolinas_coastal` / `27834` (PADD 1C): Selma Terminal / Colonial & Plantation Pipelines (+$0.045/gal summer base).
  6. `carolinas_piedmont` / `28202` (PADD 1C): Paw Creek Terminal / Charlotte Metro Hub (+$0.048/gal summer base).
  7. `south_florida` / `34984` (PADD 1C): Port Everglades Terminal / Waterborne Marine Freight (+$0.055/gal summer base).
* **Statutory Summer Blend & Ozone Compliance Engine:**
  - Evaluates statutory seasonal transition dates (Summer Blend: May 1 to Sept 15; Spring/Fall Shoulder: April & late Sept/early Oct; Winter: Oct 16 to Mar 31).
  - Triggers an additional +$0.040/gal margin penalty during acute Ozone Action Days due to stringent anti-smog compliance and boutique blendstock constraints.
* **Statistical Anomaly Scoring & Wildfire Discrimination:**
  - Standardized rolling 30-day $Z$-scores for fine particulates ($Z_{\text{PM2.5}}$) and sulfur dioxide ($Z_{\text{SO2}}$).
  - **Outage Alert Trigger:** $Z_{\text{PM2.5}} \ge 3.5$ AND $Z_{\text{SO2}} \ge 2.5$ flags catastrophic fluid catalytic cracking (FCC) unit trips and emergency flaring, providing a **12 to 24 hour lead time** over commercial media.
  - **Wildfire Discrimination:** When $Z_{\text{PM2.5}} \ge 3.5$ but $Z_{\text{SO2}} < 1.5$, anomalies are classified as ambient wildfire or agricultural haze, suppressing false-positive refinery outage alerts.
"""

if "## 29. Multi-Feed Air Quality Ingestion" not in apis_content:
    apis_content = apis_content.rstrip() + "\n" + aqi_section
    with open(apis_file, "w", encoding="utf-8") as f:
        f.write(apis_content)
    print("Appended Section 29 to Data-Ingestion-and-APIs.md")

# 3. Update Agent-Architecture.md
agent_file = os.path.join(wiki_dir, "Agent-Architecture.md")
with open(agent_file, "r", encoding="utf-8") as f:
    agent_content = f.read()

if "`src/aqi_feed.py`" not in agent_content:
    agent_content = agent_content.replace(
        "`src/event_analyzer.py`, `src/finlight_feed.py`",
        "`src/event_analyzer.py`, `src/finlight_feed.py`, `src/aqi_feed.py`, `src/usgs_seismic.py`, `src/usgs_water_feed.py`"
    )
    with open(agent_file, "w", encoding="utf-8") as f:
        f.write(agent_content)
    print("Updated Agent-Architecture.md")

# 4. Update Project-History-and-Roadmap.md
roadmap_file = os.path.join(wiki_dir, "Project-History-and-Roadmap.md")
with open(roadmap_file, "r", encoding="utf-8") as f:
    roadmap_content = f.read()

if "Issue #54" not in roadmap_content:
    roadmap_content = roadmap_content.replace(
        '* **Milestone 1: Regular Model v1.5 "Houdry"** — Intraday 15-minute tick calibration during active commodity trading hours.',
        '* **Milestone 1: Regular Model v1.5 "Houdry"** — Intraday 15-minute tick calibration during active commodity trading hours (Issue #54 Multi-Feed AQI Flaring Ingestion, Issue #55 USGS Seismic, Issue #56 USGS Water Data).'
    )
    with open(roadmap_file, "w", encoding="utf-8") as f:
        f.write(roadmap_content)
    print("Updated Project-History-and-Roadmap.md")

print("All wiki files updated successfully.")
