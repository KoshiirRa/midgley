"""
Update Wiki Documentation for U.S. Census Bureau ACS Integration (scripts/update_wiki_census.py)
"""

import os
import sys

def update_wiki(wiki_dir: str):
    if not os.path.exists(wiki_dir):
        print(f"Wiki directory {wiki_dir} does not exist.")
        return

    # 1. Update Data-Ingestion-and-APIs.md
    dia_path = os.path.join(wiki_dir, "Data-Ingestion-and-APIs.md")
    if os.path.exists(dia_path):
        with open(dia_path, "r", encoding="utf-8") as f:
            dia_text = f.read()

        census_section = r"""

---

## 🏛️ U.S. Census Bureau ACS Demographics & Commuter Metrics (`src/census_demographics.py`) (Issue #75)

Midgley integrates the **U.S. Census Bureau API** (`api.census.gov`) to ingest demographic, vehicle availability, and commuting patterns across metropolitan statistical areas (MSAs) and refining benchmark counties.

### Survey Tables & Key Indicators
* **Household Vehicle Availability (`B08201`):** Quantifies distribution of 0, 1, 2, 3, and 4+ vehicle households (`vehicles_per_household`, `zero_vehicle_pct`).
* **Commuting Mode Share (`B08301`):** Measures drive-alone, carpooling, public transit, walking, and work-from-home splits (`vehicle_dependency_ratio`, `transit_alternative_index`).
* **Aggregate Travel Time to Work (`B08013`):** Computes average one-way commute duration in minutes (`mean_commute_minutes`).
* **Captive Gasoline Demand Inelasticity Score ($S \in [0.0, 1.0]$):**
  $$S = \text{clip}\left(0.50 \cdot \text{vehicle\_dependency} + 0.25 \cdot \frac{\text{veh\_per\_hh}}{2.0} + 0.25 \cdot \frac{\text{commute\_min}}{30.0} - 0.20 \cdot \text{transit\_alt}, 0.0, 1.0\right)$$

### Adaptive Annual Release Window Caching
* **Release Window Phase (Sept 1 – Sept 30):** Polls daily (`24h TTL`) during the annual September American Community Survey (ACS 1-Year) release period to detect when the new vintage year ($T-1$) is published.
* **Locked Annual Cache Phase (Oct 1 – Aug 31):** Once the new vintage is confirmed, the cache locks forward until the following August 31st (~335+ days) with zero outbound network calls.
* **$0 Compute & Data Cost:** 100% free public government API with deterministic offline baseline profiles.
"""
        if "U.S. Census Bureau ACS Demographics" not in dia_text:
            dia_text += census_section
            with open(dia_path, "w", encoding="utf-8") as f:
                f.write(dia_text)
            print("Updated Data-Ingestion-and-APIs.md in wiki")
        else:
            print("Data-Ingestion-and-APIs.md already contains Census section")

    # 2. Update Regional-Metro-Models.md
    rmm_path = os.path.join(wiki_dir, "Regional-Metro-Models.md")
    if os.path.exists(rmm_path):
        with open(rmm_path, "r", encoding="utf-8") as f:
            rmm_text = f.read()

        rmm_addition = r"""

---

## 🚗 Metro Commuter Dependency & Demand Elasticity Calibration (Issue #75)

Each regional metro model profile (`data/regional_metadata/*.json`) is calibrated with localized Census ACS commuter demographics:
* **Tulsa, OK:** $91.7\%$ vehicle dependency ratio, $1.95$ vehicles/hh, $21.8$ min commute $\rightarrow$ Inelastic demand score $0.885$ (High pricing power).
* **Greenville, NC:** $91.9\%$ vehicle dependency ratio, $1.88$ vehicles/hh, $21.2$ min commute $\rightarrow$ Inelastic demand score $0.879$.
* **Cincinnati, OH:** $87.0\%$ vehicle dependency ratio, $1.86$ vehicles/hh, $25.1$ min commute $\rightarrow$ Inelastic demand score $0.814$.
* **Newark, DE:** $82.0\%$ vehicle dependency ratio, $1.74$ vehicles/hh, $26.4$ min commute $\rightarrow$ Inelastic demand score $0.732$.
* **Oakland / Bay Area, CA:** $67.0\%$ vehicle dependency ratio, $12.5\%$ public transit share, $18.5\%$ WFH $\rightarrow$ Inelastic demand score $0.548$ (Higher consumer substitution elasticity).
"""
        if "Metro Commuter Dependency & Demand Elasticity" not in rmm_text:
            rmm_text += rmm_addition
            with open(rmm_path, "w", encoding="utf-8") as f:
                f.write(rmm_text)
            print("Updated Regional-Metro-Models.md in wiki")
        else:
            print("Regional-Metro-Models.md already contains commuter section")

    # 3. Update Self-Hosting.md in wiki
    sh_path = os.path.join(wiki_dir, "Self-Hosting.md")
    if os.path.exists(sh_path):
        with open(sh_path, "r", encoding="utf-8") as f:
            sh_text = f.read()

        if "CENSUS_API_KEY" not in sh_text:
            sh_text = sh_text.replace(
                'SEC_USER_AGENT="Midgley your@email.com"',
                'SEC_USER_AGENT="Midgley your@email.com"\n# Optional U.S. Census Bureau API Key (api.census.gov - Free public open data)\nCENSUS_API_KEY=""'
            )
            with open(sh_path, "w", encoding="utf-8") as f:
                f.write(sh_text)
            print("Updated Self-Hosting.md in wiki")


if __name__ == "__main__":
    wiki_path = sys.argv[1] if len(sys.argv) > 1 else "/home/marty/projects/midgley.wiki"
    update_wiki(wiki_path)
