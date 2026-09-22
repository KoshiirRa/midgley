#!/usr/bin/env python3
"""
Update GitHub Wiki on dev-vm for Issues #418, #408, #400.
"""

import subprocess
import sys

def update_wiki():
    commands = [
        # Pull latest master on wiki
        'cd /home/marty/projects/midgley.wiki && git pull origin master',
        
        # Run python script directly on dev-vm to update pages
        '''python3 - << 'EOF'
import re

# 1. Update Data-Ingestion-and-APIs.md
with open('/home/marty/projects/midgley.wiki/Data-Ingestion-and-APIs.md', 'r', encoding='utf-8') as f:
    content = f.read()

target_section = """## 71. Headline Arena Energy Benchmark Connector & Probabilistic Calibration (Issue #182)"""

replacement_section = """## 71. Headline Arena Energy Benchmark Connector, 24h Forecast Caching & Civic Challenges (Issues #182, #408, #418)
* **Module:** `src/headline_arena_connector.py`, `scripts/sync_headline_arena.py`, & `src/api_server.py`
* **API Provider:** Headline Arena (`headlinearena.com/api/v1`)
* **Coverage:** RBOB Wholesale Gasoline (`RB`), Cushing WTI Crude Oil (`CL`), and EIA Weekly US Regular Retail Gasoline (`EIA_RETAIL_GASOLINE`).
* **Authentication:** OAuth2 `client_credentials` flow (`POST /api/v1/auth/token`) exchanging `HEADLINE_ARENA_CLIENT_ID` and `HEADLINE_ARENA_CLIENT_SECRET` for short-lived bearer tokens with in-memory TTL caching.
* **Mathematical Quantile Conversion (Brier Scoring over Dead Zones):**
  Converts median forecast $\\mu = P_{50}$, standard deviation $\\sigma = \\frac{P_{90} - P_{10}}{2.5631}$, and spot open price $S_0$ over dead zone $d$ ($0.0030$ for RB, $0.0020$ for CL):
  - $P(\\text{bullish}) = 1 - \\Phi\\left(\\frac{S_0 \\cdot (1+d) - \\mu}{\\sigma}\\right)$
  - $P(\\text{bearish}) = \\Phi\\left(\\frac{S_0 \\cdot (1-d) - \\mu}{\\sigma}\\right)$
  - $P(\\text{neutral}) = \\max\\left(0, 1 - P(\\text{bullish}) - P(\\text{bearish})\\right)$
  - $\\text{direction} = \\operatorname{argmax}(P(\\text{bullish}), P(\\text{neutral}), P(\\text{bearish}))$
  - $\\text{confidence} = \\max(P(\\text{bullish}), P(\\text{neutral}), P(\\text{bearish}))$
* **EIA Weekly Retail Gasoline Civic Challenges (Issue #408):**
  - Continuous Gaussian probability density scoring (closed-form CRPS) formatting (`format_eia_retail_civic_payload` & `submit_macro_forecast`).
  - Evaluates median prediction $P_{50}$ with Gaussian uncertainty standard deviation $\\sigma$ derived from multi-agent quantile intervals or empirical residual standard deviation.
* **Decoupled 24h Pending Forecast Cache & Idempotency Ledger (Issue #418):**
  - **Pending Cache (`data/headline_arena_pending_forecasts.json`):** Persists generated daily forecasts with a 24-hour TTL, decoupling pipeline run times from unpredictable challenge open windows.
  - **Submission Ledger (`data/headline_arena_submitted_ledger.json`):** Tracks challenge IDs that have received predictions, preventing redundant submissions across periodic runs.
  - **Asynchronous 30-Minute Sync Runner (`scripts/sync_headline_arena.py` & `.github/workflows/headline_arena_sync.yml`):** Automatically dispatches active pending forecasts against open Headline Arena challenges every 30 minutes.
* **Environment Isolation & Dev-Test Tagging:**
  - **Dev/Local (`MIDGLEY_ENV=dev`):** Dry-run by default.
  - **Explicit Dev Test Submissions (`--live` / `HEADLINE_ARENA_DEV_SUBMIT=1`):** Reasonings tagged with `[DEV-TEST] [DEVELOPMENT]`.
  - **Production:** Automatic submission during daily pipeline or 30-minute sync timer when configured.
* **REST API Endpoints:**
  - `GET /api/v1/connectors/headline-arena/status`: Check connection, settlement rules, and active pending forecast count.
  - `POST /api/v1/connectors/headline-arena/submit`: Submit or dry-run prediction."""

if target_section in content and "Issue #418" not in content:
    content = content.replace(target_section, replacement_section)
    with open('/home/marty/projects/midgley.wiki/Data-Ingestion-and-APIs.md', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Updated Data-Ingestion-and-APIs.md on dev-vm wiki.")

# 2. Update Regional-Metro-Models.md or Agent-Architecture.md for CARB tax reconciliation
with open('/home/marty/projects/midgley.wiki/Regional-Metro-Models.md', 'r', encoding='utf-8') as f:
    r_content = f.read()

# Replace any old CARB tax breakdown if found
old_tax = "$0.634"
if old_tax in r_content:
    r_content = r_content.replace("$0.634", "$0.596")
    with open('/home/marty/projects/midgley.wiki/Regional-Metro-Models.md', 'w', encoding='utf-8') as f:
        f.write(r_content)
    print("Updated Regional-Metro-Models.md on dev-vm wiki.")

EOF
''',
        # Commit and push wiki
        'cd /home/marty/projects/midgley.wiki && git add -A && git commit -m "docs(wiki): Update Headline Arena 24h cache, civic challenge & CARB tax math (#418, #408, #400)" || true',
        'cd /home/marty/projects/midgley.wiki && git push origin master'
    ]

    for cmd in commands:
        print(f"Executing: {cmd[:60]}...")
        res = subprocess.run(["ssh", "marty@10.42.42.54", cmd], capture_output=True, text=True)
        print("STDOUT:", res.stdout)
        if res.stderr:
            print("STDERR:", res.stderr)
        if res.returncode != 0:
            print(f"Command failed with code {res.returncode}")
            return False
    return True

if __name__ == "__main__":
    if update_wiki():
        print("Wiki update successful!")
    else:
        sys.exit(1)
