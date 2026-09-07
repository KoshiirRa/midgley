"""
Update Wiki for Firecrawl Web Scraping API (Issue #83)
(scripts/update_wiki_firecrawl.py)
"""

import os
import sys

def update_wiki(wiki_dir: str):
    if not os.path.exists(wiki_dir):
        print(f"Wiki directory '{wiki_dir}' does not exist.")
        return

    # 1. Update Data-Ingestion-and-APIs.md
    dia_path = os.path.join(wiki_dir, "Data-Ingestion-and-APIs.md")
    if os.path.exists(dia_path):
        with open(dia_path, "r", encoding="utf-8") as f:
            dia_text = f.read()

        firecrawl_section = """
---

## 8. Firecrawl Web-to-Markdown Scraper API (Issue #83)
* **Module:** `src/firecrawl_scraper.py` & `src/event_analyzer.py`
* **API Provider:** Firecrawl API (`https://api.firecrawl.dev/v1/scrape`)
* **Coverage:** Ingests deep web articles from breaking energy news portals, refinery operator disclosures, and state motor fuel tax portals, converting raw HTML into clean, structured Markdown with full JavaScript rendering support.
* **Hard Quota Safety Valve Ledger (`data/firecrawl_quota.json`):**
  - Enforces an **800 call/month hard safety cap** (and 30 call/day burst limit) out of the 1,000 free tier allowance.
  - Automatically blocks outgoing API calls when cap is reached, seamlessly routing to the zero-cost native HTML parser.
* **24-Hour Multi-Tier Response Caching:**
  - Persists scraped Markdown at `data/firecrawl_cache.json` and in-memory cache keyed by SHA-256 hash of normalized URLs with a 24-hour TTL (86,400s) to prevent duplicate scraping.
* **Deterministic Offline HTML Fallback ($0 Cost Guarantee):**
  - Built-in `SimpleHTMLTextExtractor` using standard library `urllib` and `html.parser` to strip scripts, styles, navigation, and headers into clean Markdown with 100% offline resilience.
* **URL Event Feature Extraction:**
  - `extract_event_features_from_url()` in `src/event_analyzer.py` safely truncates scraped content to ~1,500 words to protect Gemini Flash token context budgets while extracting structured commodity impact vectors.
"""
        if "Firecrawl Web-to-Markdown Scraper API" not in dia_text:
            dia_text += firecrawl_section
            with open(dia_path, "w", encoding="utf-8") as f:
                f.write(dia_text)
            print("Updated Data-Ingestion-and-APIs.md in wiki")
        else:
            print("Data-Ingestion-and-APIs.md already updated")

    # 2. Update Agent-Architecture.md
    aa_path = os.path.join(wiki_dir, "Agent-Architecture.md")
    if os.path.exists(aa_path):
        with open(aa_path, "r", encoding="utf-8") as f:
            aa_text = f.read()

        if "src/firecrawl_scraper.py" not in aa_text:
            aa_text = aa_text.replace(
                "src/event_analyzer.py",
                "src/event_analyzer.py, src/firecrawl_scraper.py"
            )
            with open(aa_path, "w", encoding="utf-8") as f:
                f.write(aa_text)
            print("Updated Agent-Architecture.md in wiki")

    # 3. Update Self-Hosting.md
    sh_path = os.path.join(wiki_dir, "Self-Hosting.md")
    if os.path.exists(sh_path):
        with open(sh_path, "r", encoding="utf-8") as f:
            sh_text = f.read()

        if "FIRECRAWL_API_KEY" not in sh_text:
            sh_text = sh_text.replace(
                'FINLIGHT_API_KEY="fl_live_..."',
                'FINLIGHT_API_KEY="fl_live_..."\n\n# Firecrawl Web Scraping API (firecrawl.dev) - Enforces 800 call/month safety cap (Issue #83)\nFIRECRAWL_API_KEY="fc-..."'
            )
            with open(sh_path, "w", encoding="utf-8") as f:
                f.write(sh_text)
            print("Updated Self-Hosting.md in wiki")

    # 4. Update Project-History-and-Roadmap.md
    phr_path = os.path.join(wiki_dir, "Project-History-and-Roadmap.md")
    if os.path.exists(phr_path):
        with open(phr_path, "r", encoding="utf-8") as f:
            phr_text = f.read()

        issue_entry = "- **Issue #83**: `[Feature Request] Ingest Firecrawl Web-to-Markdown API for LLM Event Extraction` (Completed)"
        if "Issue #83" not in phr_text:
            phr_text = phr_text.replace(
                "## 📋 Closed & Superseded Issues",
                f"## 📋 Closed & Superseded Issues\n{issue_entry}"
            )
            with open(phr_path, "w", encoding="utf-8") as f:
                f.write(phr_text)
            print("Updated Project-History-and-Roadmap.md in wiki")

if __name__ == "__main__":
    target_dir = sys.argv[1] if len(sys.argv) > 1 else "/home/marty/projects/midgley.wiki"
    update_wiki(target_dir)
