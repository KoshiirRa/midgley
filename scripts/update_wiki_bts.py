#!/usr/bin/env python3
import os
import subprocess

def update_wiki(wiki_dir: str):
    if not os.path.exists(wiki_dir):
        print(f"Directory {wiki_dir} does not exist, skipping.")
        return

    # 1. Update Data-Ingestion-and-APIs.md
    apis_path = os.path.join(wiki_dir, "Data-Ingestion-and-APIs.md")
    if os.path.exists(apis_path):
        with open(apis_path, "r", encoding="utf-8") as f:
            content = f.read()

        section = """
## 72. U.S. Bureau of Transportation Statistics (BTS) Freight Transportation Services Index & Tank Truck Demand Data (Issue #74)
* **Module:** `src/bts_transportation.py` (`BTSTransportationConnector`)
* **API Provider:** U.S. Bureau of Transportation Statistics Open Data SODA API (`data.bts.gov/resource/bw6n-ddqk.json`)
* **Cost & Authentication:** 100% Free Public Government Open Data API, zero API key requirement.
* **Key Metrics Ingested:**
  - `tsi_freight`: Seasonally adjusted Freight Transportation Services Index coincident output benchmark.
  - `truck_d11`: Seasonally adjusted Truck Tonnage Index (physical proxy for heavy commercial diesel and motor gasoline consumption).
  - `petroleum_d11`: Pipeline and bulk surface petroleum product transport index.
  - `tsi_passenger` & `tsi_total`: Passenger and composite national transportation indices.
  - `rail_frt_carloads_d11` & `rail_frt_intermodal_d11`: Rail carload and intermodal freight volume indicators.
* **Multi-Tier Fallback Hierarchy:**
  1. **Tier 1 (Live SODA API):** `https://data.bts.gov/resource/bw6n-ddqk.json`
  2. **Tier 2 (FRED Series):** Public FRED CSV series `TSIFRGHT` & `TRUCKD11`.
  3. **Tier 3 (Persistent Benchmark):** `data/bts_tsi_historical.json`.
  4. **Tier 4 (Curated Baseline):** Immutable baseline constant (2020–2026) ensuring 100% offline uptime.
* **Bitemporal Vintage Tracking & Caching:**
  - Persists point-in-time snapshots to `data/bts_vintages.json` via `save_bts_vintage_record()` with `as_of` publication filtering (`get_bts_vintages_as_of()`).
  - 7-day TTL caching via `global_cache` (`data/lookup_cache.sqlite`).
* **Feature Matrix Integration:** Merges `bts_tsi_freight`, `bts_truck_tonnage`, `bts_petroleum_transport`, `bts_tsi_freight_mom_pct`, `bts_truck_tonnage_mom_pct`, `bts_petroleum_transport_mom_pct`, `bts_tsi_total`, and `bts_rail_carloads` with daily forward-filling.
* **REST API Endpoint:** `GET /api/v1/macro/freight-tsi` supporting historical series and `summary_only` real-time demand momentum snapshots.
"""
        if "## 72. U.S. Bureau of Transportation Statistics" not in content:
            content = content.strip() + "\n" + section
            with open(apis_path, "w", encoding="utf-8") as f:
                f.write(content)
            print(f"Updated Data-Ingestion-and-APIs.md in {wiki_dir}")

    # 2. Update Agent-Architecture.md
    agent_path = os.path.join(wiki_dir, "Agent-Architecture.md")
    if os.path.exists(agent_path):
        with open(agent_path, "r", encoding="utf-8") as f:
            agent_content = f.read()

        if "src/bts_transportation.py" not in agent_content:
            agent_content = agent_content.replace(
                "src/alternative_data_feeds.py",
                "src/bts_transportation.py, src/alternative_data_feeds.py"
            )
            agent_content = agent_content.replace(
                "and Baker Hughes drilling rig counts",
                "Baker Hughes drilling rig counts, and U.S. BTS Freight Transportation Index (TSI) & Truck Tonnage (BTSTransportationConnector, Issue #74)"
            )
            with open(agent_path, "w", encoding="utf-8") as f:
                f.write(agent_content)
            print(f"Updated Agent-Architecture.md in {wiki_dir}")

    # 3. Update Self-Hosting.md
    sh_path = os.path.join(wiki_dir, "Self-Hosting.md")
    if os.path.exists(sh_path):
        with open(sh_path, "r", encoding="utf-8") as f:
            sh_content = f.read()

        if "data/bts_vintages.json" not in sh_content:
            sh_content = sh_content.replace(
                "data/baker_hughes_vintages.json",
                "data/bts_vintages.json, data/baker_hughes_vintages.json"
            )
            with open(sh_path, "w", encoding="utf-8") as f:
                f.write(sh_content)
            print(f"Updated Self-Hosting.md in {wiki_dir}")

    # Git commit on wiki if git repo
    if os.path.exists(os.path.join(wiki_dir, ".git")):
        try:
            subprocess.run(["git", "-C", wiki_dir, "add", "."], check=True)
            subprocess.run(["git", "-C", wiki_dir, "commit", "-m", "docs: update wiki for BTS Freight TSI and Truck Demand ingestion (#74)"], check=True)
            print(f"Committed changes to {wiki_dir}")
        except Exception as e:
            print(f"Git commit in {wiki_dir} skipped or already clean: {e}")

if __name__ == "__main__":
    # Update local scratch wiki
    local_wiki = os.path.join(os.getcwd(), "scratch", "midgley.wiki")
    update_wiki(local_wiki)
