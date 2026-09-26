#!/usr/bin/env python3
"""
Create GitHub Issue for Pirate Weather integration for historical backtesting & feature calibration.
Tags the issue for milestone v0.8 with appropriate labels and project metadata.
"""

import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request

ISSUE = {
    "id": "WEATHER-PIRATE",
    "title": "feat(weather): Integrate Pirate Weather API connector for point-in-time historical reanalysis & weather feature backfilling",
    "category": "Physical & Alternative Data Ingestion",
    "milestone": "v0.8",
    "labels": ["enhancement", "data-ingestion", "modeling"],
    "effort": "M (Medium)",
    "effort_days": "2-3 days",
    "risk": "Low Risk",
    "risk_color": "Green",
    "body": """### Summary
Integrate the [Pirate Weather API](https://docs.pirateweather.net/en/latest/) as a specialized historical weather reanalysis and hourly backfill connector (`PirateWeatherConnector` in `src/noaa_weather.py`) to empower out-of-sample quantitative model backtesting, historical degree-day calibration, and extreme weather shock verification.

While real-time alerts and live convective outlooks remain served by zero-cost, keyless endpoints (NOAA NWS `api.weather.gov` and `t.wxs.us`), historical multi-year feature engineering currently relies on static curated episode catalogs or heavy manual dataset downloads. Pirate Weather's Dark Sky-compatible "Time Machine" endpoint (`/forecast/{key}/{lat},{lon},{time}`) processes NOAA High-Resolution Rapid Refresh (HRRR, 3km Continental US grid) and ERA5/NBM reanalysis, providing clean point-in-time hourly/daily historical weather telemetry at exact refinery and pipeline terminal coordinates.

### Key Capabilities & Scope
1. **`PirateWeatherConnector` Implementation (`src/noaa_weather.py`):**
   - Implement connector class supporting `fetch_historical_point(lat, lon, timestamp)` and `fetch_historical_range(lat, lon, start_date, end_date)`.
   - Ingest normalized Dark Sky JSON fields (`temperature`, `apparentTemperature`, `dewPoint`, `humidity`, `windSpeed`, `windGust`, `pressure`, `precipAccumulation`, `precipType`).
   - Securely read `PIRATE_WEATHER_API_KEY` from environment with graceful skip/fallback when not configured.
2. **Refining Hub & Logistics Hub Coordinate Mapping:**
   - Map exact coordinates across all active Midgley regional assets:
     - West Tulsa HF Sinclair & Cushing Tank Farms (`36.154, -95.992`)
     - PBF Delaware City Refinery & C&D Canal (`39.683, -75.750`)
     - Marathon Catlettsburg KY & Ohio River Locks (`39.103, -84.512`)
     - Chevron Richmond & Martinez Refineries (`37.804, -122.271`)
     - Colonial Pipeline Selma NC Breakout Hub (`35.612, -77.366`)
     - Paw Creek Petroleum Distribution Terminal (`35.227, -80.843`)
     - Port Everglades & Port Canaveral Marine Terminals (`27.273, -80.358`)
     - Gulf Coast Refining Complex (Houston/Port Arthur/Baton Rouge)
3. **Historical Backtest Feature Engineering (`src/event_calibration.py` & `src/feature_engineering.py`):**
   - Construct historical hourly temperature freeze-off indices ($T < 32^\\circ\\text{F}$ duration) and summer heat stress metrics ($T > 95^\\circ\\text{F}$) for backtest datasets (2021–2026).
   - Calibrate weather shock decay half-lives ($t_{1/2}$) against realized price innovations during historical winter freeze episodes (e.g. Winter Storm Elliott Dec 2022, Winter Storm Heather Jan 2024).
4. **Caching & Bitemporal Ledger Persistence:**
   - Integrate with 3-tier lookup cache (`src/lookup_cache.py`) with permanent TTL on immutable historical queries.
   - Persist historical backfill vintages in `data/pirateweather_vintages.json`.
5. **Data Sources Catalog & Documentation Updates:**
   - Catalog Pirate Weather in `src/sources_generator.py` and `docs/sources.html` under Weather & Environmental Feeds.
   - Update `AGENTS.md`, `ARCHITECTURE.md`, and GitHub Wiki Section `05`.

### Acceptance Criteria
- [ ] `PirateWeatherConnector` implemented in `src/noaa_weather.py` with test coverage in `tests/test_noaa_weather.py`.
- [ ] Point-in-time historical reanalysis queries cached with 3-tier lookup cache and persisted in `data/pirateweather_vintages.json`.
- [ ] Integration tests verify graceful degradation / fallback when `PIRATE_WEATHER_API_KEY` is unset.
- [ ] Historical backtest weather features generated and integrated into econometric event calibration.
- [ ] Documentation updated in `docs/sources.html`, `AGENTS.md`, and GitHub Wiki."""
}


def get_github_token():
    """Retrieve GitHub token safely without exposing plaintext credentials in CLI."""
    for var in ["GH_TOKEN", "GITHUB_TOKEN"]:
        t = os.environ.get(var)
        if t:
            return t.strip()

    try:
        p = subprocess.Popen(
            ["git", "credential", "fill"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        stdout, _ = p.communicate("protocol=https\nhost=github.com\n")
        for line in stdout.splitlines():
            if line.startswith("password="):
                return line.split("=", 1)[1].strip()
    except Exception as e:
        print(f"Error querying git credential helper: {e}", file=sys.stderr)

    return None


def get_or_create_milestone(token: str, milestone_title: str) -> int | None:
    """Find or create milestone number by title in KoshiirRa/midgley."""
    url = "https://api.github.com/repos/KoshiirRa/midgley/milestones?state=all"
    req = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "midgley-agent"
        }
    )
    try:
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode())
            for m in data:
                if m.get("title", "").strip().lower() == milestone_title.strip().lower():
                    return m.get("number")
    except Exception as e:
        print(f"Could not query milestones: {e}", file=sys.stderr)

    # If not found, attempt to create milestone
    create_url = "https://api.github.com/repos/KoshiirRa/midgley/milestones"
    payload = {"title": milestone_title, "state": "open"}
    req_create = urllib.request.Request(
        create_url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github.v3+json",
            "Content-Type": "application/json",
            "User-Agent": "midgley-agent"
        }
    )
    try:
        with urllib.request.urlopen(req_create) as resp:
            data = json.loads(resp.read().decode())
            return data.get("number")
    except Exception as e:
        print(f"Could not create milestone {milestone_title}: {e}", file=sys.stderr)

    return None


def create_github_issue(token: str, issue_dict: dict, milestone_num: int | None) -> dict:
    """Create a single issue via GitHub REST API."""
    url = "https://api.github.com/repos/KoshiirRa/midgley/issues"
    payload = {
        "title": issue_dict["title"],
        "body": issue_dict["body"],
        "labels": issue_dict["labels"]
    }
    if milestone_num is not None:
        payload["milestone"] = milestone_num

    data_bytes = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data_bytes,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github.v3+json",
            "Content-Type": "application/json",
            "User-Agent": "midgley-agent"
        }
    )
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        err_body = e.read().decode()
        return {"error": e.code, "message": err_body}
    except Exception as e:
        return {"error": str(e)}


def update_local_roadmap(issue_num: int, issue_dict: dict):
    """Update master_roadmap_summary.json and evaluated_master_roadmap.json with newly created issue."""
    summary_path = "master_roadmap_summary.json"
    evaluated_path = "evaluated_master_roadmap.json"

    if os.path.exists(summary_path):
        with open(summary_path, "r", encoding="utf-8") as f:
            summary_data = json.load(f)
    else:
        summary_data = []

    if os.path.exists(evaluated_path):
        with open(evaluated_path, "r", encoding="utf-8") as f:
            evaluated_data = json.load(f)
    else:
        evaluated_data = []

    # Check if already present
    summary_data = [s for s in summary_data if s.get("title") != issue_dict["title"] and s.get("number") != issue_num]
    evaluated_data = [e for e in evaluated_data if e.get("title") != issue_dict["title"] and e.get("number") != issue_num]

    summary_entry = {
        "number": issue_num,
        "title": issue_dict["title"],
        "status": "Ready",
        "milestone": issue_dict["milestone"],
        "labels": issue_dict["labels"],
        "body_preview": issue_dict["body"][:250] + "..."
    }
    summary_data.append(summary_entry)

    eval_entry = {
        "number": issue_num,
        "title": issue_dict["title"],
        "category": issue_dict["category"],
        "status": "Ready",
        "milestone": issue_dict["milestone"],
        "labels": issue_dict["labels"],
        "effort": issue_dict["effort"],
        "effort_days": issue_dict["effort_days"],
        "risk": issue_dict["risk"],
        "risk_color": issue_dict["risk_color"],
        "body_snippet": issue_dict["body"][:250] + "..."
    }
    evaluated_data.append(eval_entry)

    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary_data, f, indent=2)

    with open(evaluated_path, "w", encoding="utf-8") as f:
        json.dump(evaluated_data, f, indent=2)

    print(f"Updated {summary_path} and {evaluated_path} for issue #{issue_num}.")


def main():
    print(f"Creating GitHub issue for: {ISSUE['title']}...")
    token = get_github_token()
    if not token:
        print("GitHub token not found. Cannot create issue on GitHub.")
        sys.exit(1)

    milestone_num = get_or_create_milestone(token, ISSUE["milestone"])
    print(f"Target milestone '{ISSUE['milestone']}' resolved to GitHub milestone number: {milestone_num}")

    res = create_github_issue(token, ISSUE, milestone_num)
    if "number" in res:
        issue_num = res["number"]
        issue_url = res["html_url"]
        print(f"\nSUCCESS! Created GitHub Issue #{issue_num}: {issue_url}")
        update_local_roadmap(issue_num, ISSUE)
    else:
        print(f"\nFAILED to create issue: {res}")
        sys.exit(1)


if __name__ == "__main__":
    main()
