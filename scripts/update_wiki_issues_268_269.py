#!/usr/bin/env python3
import os
import subprocess

wiki_dir = "/home/marty/projects/midgley.wiki"

# 1. Update Data-Ingestion-and-APIs.md
apis_path = os.path.join(wiki_dir, "Data-Ingestion-and-APIs.md")
if os.path.exists(apis_path):
    with open(apis_path, "r", encoding="utf-8") as f:
        content = f.read()

    section = """
## 41. Dynamic Baker Hughes Rig Count Feed & Bitemporal Vintages (Issue #269)
* **Dynamic Ingestion Connector (`src/alternative_data_feeds.py`):**
  - `BakerHughesDataConnector` dynamically queries active rotary drilling rig counts from open public feeds (FRED `OILRESUS` / EIA open series) with 7-day TTL caching in `global_cache` (`data/lookup_cache.sqlite`).
  - Guarantees exact feature matrix columns: `['date', 'baker_hughes_us_rig_count', 'baker_hughes_oil_rigs', 'baker_hughes_gas_rigs', 'baker_hughes_rig_delta_1w']`.
  - **Bitemporal Vintage Tracking:** `save_baker_hughes_vintage_record()` logs observation snapshots with explicit `as_of` timestamps to `data/baker_hughes_vintages.json` to prevent backtest lookahead bias.
  - **Deterministic Offline Fallback:** Gracefully falls back to curated historical benchmarks if offline.

## 42. Dynamic Executive Social Feed & Weekend Market Gap Classifier (Issue #268)
* **Live Syndication & Polling Engine (`src/executive_social_feed.py`):**
  - `ExecutiveSocialFeedConnector` dynamically polls public Truth Social and Twitter/X syndication RSS feeds with 15-minute lookup caching.
  - **Weekend Market Gap Classifier:** `is_timestamp_weekend()` automatically tags posts published between Friday 17:00 EST and Sunday 18:00 EST (commodity market closures).
  - **Intraday Anomaly Integration:** `fetch_executive_social_headlines()` feeds breaking posts directly into `IntradayEventMonitor.run_polling_cycle()`.
  - **Bitemporal Logging:** Snapshots persisted to `data/executive_social_vintages.json`.
"""
    if "## 41. Dynamic Baker Hughes Rig Count" not in content:
        content = content.strip() + "\n" + section
        with open(apis_path, "w", encoding="utf-8") as f:
            f.write(content)
        print("Updated Data-Ingestion-and-APIs.md in wiki")

# 2. Update Agent-Architecture.md
agent_path = os.path.join(wiki_dir, "Agent-Architecture.md")
if os.path.exists(agent_path):
    with open(agent_path, "r", encoding="utf-8") as f:
        agent_content = f.read()

    if "Dynamic Baker Hughes" not in agent_content:
        agent_content = agent_content.replace(
            "Cboe OVX options volatility, and Baker Hughes drilling rig counts",
            "Cboe OVX options volatility, dynamic Baker Hughes drilling rig counts (BakerHughesDataConnector, Issue #269), and live Executive Social Media feeds (ExecutiveSocialFeedConnector, Issue #268)"
        )
        with open(agent_path, "w", encoding="utf-8") as f:
            f.write(agent_content)
        print("Updated Agent-Architecture.md in wiki")

# 3. Update Self-Hosting.md
sh_path = os.path.join(wiki_dir, "Self-Hosting.md")
if os.path.exists(sh_path):
    with open(sh_path, "r", encoding="utf-8") as f:
        sh_content = f.read()

    if "baker_hughes_vintages.json" not in sh_content:
        sh_content = sh_content.replace(
            "data/eia_vintages.json",
            "data/baker_hughes_vintages.json, data/executive_social_vintages.json, data/eia_vintages.json"
        )
        with open(sh_path, "w", encoding="utf-8") as f:
            f.write(sh_content)
        print("Updated Self-Hosting.md in wiki")

# Git commit on wiki
try:
    subprocess.run(["git", "-C", wiki_dir, "add", "."], check=True)
    subprocess.run(["git", "-C", wiki_dir, "commit", "-m", "docs: update wiki for dynamic Baker Hughes (#269) and Executive Social (#268) feeds"], check=True)
    print("Committed changes to midgley.wiki")
except Exception as e:
    print(f"Git commit in wiki skipped or already committed: {e}")
