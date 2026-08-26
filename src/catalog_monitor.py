"""
Catalog Monitor Engine (src/catalog_monitor.py)
Monitors curated developer catalog indexes (public-apis, free-for-dev, freestuff.dev,
free-for-life, awesome, awesome-selfhosted) for newly added entries.
Evaluates modeling relevance using Gemini 2.5 Flash (with a deterministic heuristic fallback)
and automatically opens GitHub Feature Request issues on KoshiirRa/midgley for worthwhile additions.
"""

import os
import re
import json
import logging
import subprocess
import urllib.request
import urllib.error
from datetime import datetime

logger = logging.getLogger(__name__)

STATE_FILE = os.path.join("data", "catalog_monitors_state.json")

CATALOG_SOURCES = {
    "public-apis": {
        "url": "https://raw.githubusercontent.com/public-apis/public-apis/master/README.md",
        "name": "Public APIs Index (public-apis/public-apis)"
    },
    "free-for-dev": {
        "url": "https://raw.githubusercontent.com/ripienaar/free-for-dev/master/README.md",
        "name": "Free for Developers (ripienaar/free-for-dev)"
    },
    "freestuff.dev": {
        "url": "https://freestuff.dev/",
        "name": "FreeStuff Dev Directory (freestuff.dev)"
    },
    "free-for-life": {
        "url": "https://raw.githubusercontent.com/wdhdev/free-for-life/main/README.md",
        "name": "Free For Life Directory (wdhdev/free-for-life)"
    },
    "awesome": {
        "url": "https://raw.githubusercontent.com/sindresorhus/awesome/main/readme.md",
        "name": "Awesome Meta-List (sindresorhus/awesome)"
    },
    "awesome-selfhosted": {
        "url": "https://raw.githubusercontent.com/awesome-selfhosted/awesome-selfhosted/master/README.md",
        "name": "Awesome Selfhosted (awesome-selfhosted/awesome-selfhosted)"
    }
}


def load_catalog_state() -> dict:
    """Loads persistent catalog state from JSON file."""
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Could not load catalog state from {STATE_FILE}: {e}")
    return {"version": "1.0", "last_scan": None, "known_urls": {cat: [] for cat in CATALOG_SOURCES}}


def save_catalog_state(state: dict):
    """Saves persistent catalog state to JSON file."""
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    state["last_scan"] = datetime.now().isoformat()
    try:
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2)
        logger.info(f"Updated catalog state saved to {STATE_FILE}.")
    except Exception as e:
        logger.error(f"Failed to save catalog state to {STATE_FILE}: {e}")


def fetch_catalog_content(url: str) -> str:
    """Fetches raw text content from the catalog URL."""
    try:
        headers = {"User-Agent": "Midgley-Catalog-Monitor/1.0"}
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=20) as resp:
            return resp.read().decode("utf-8", errors="ignore")
    except Exception as e:
        logger.error(f"Error fetching catalog URL {url}: {e}")
        return ""


def extract_items_from_content(content: str, catalog_key: str) -> list:
    """
    Parses Markdown / HTML content to extract item dicts with: title, url, description, catalog_key.
    """
    items = []
    seen_urls = set()

    # Regex pattern for markdown links: [Title](URL) - Description or | [Title](URL) | Description |
    link_pattern = re.compile(r'\[([^\]]+)\]\((https?://[^\)]+)\)(?:\s*[\:\-\|]\s*|\s+)(.*)', re.IGNORECASE)

    for line in content.splitlines():
        line_str = line.strip()
        if not line_str or line_str.startswith("#"):
            continue

        match = link_pattern.search(line_str)
        if match:
            title = match.group(1).strip()
            url = match.group(2).strip()
            desc = match.group(3).strip().strip("|").strip()

            # Clean URL trailing slashes or quotes
            url_clean = url.rstrip("/")
            if url_clean in seen_urls:
                continue
            seen_urls.add(url_clean)

            # Skip common repo meta links
            if any(skip in url_clean.lower() for skip in ["github.com/sponsors", "twitter.com", "badge", "license"]):
                continue

            items.append({
                "title": title,
                "url": url,
                "description": desc or title,
                "catalog_key": catalog_key
            })

    logger.info(f"Extracted {len(items)} item(s) from catalog '{catalog_key}'.")
    return items


def evaluate_item_heuristic(item: dict) -> dict:
    """
    Deterministic domain-specific keyword scoring fallback to rank new catalog items.
    Scored on a scale of 0.0 - 10.0.
    """
    text = (item["title"] + " " + item["description"] + " " + item["url"]).lower()
    score = 2.0
    category = "General Infrastructure"
    target_component = "src/data_ingestion.py"

    keywords_high = [
        "refin", "fuel", "gasoline", "oil", "energy", "petroleum", "noaa", "weather",
        "commodity", "futures", "price", "forecast", "time series", "time-series",
        "rag", "llm", "scrape", "search", "mlops", "feature store", "market data",
        "treasury", "sec", "edgar", "yield", "inflation", "macro"
    ]
    keywords_med = [
        "api", "database", "postgres", "sql", "dashboard", "analytics", "monitoring",
        "cron", "workflow", "tunnel", "security", "webhook", "bot", "auth", "cache",
        "gpu", "tpu", "open-source", "python", "rust", "go"
    ]

    high_hits = sum(1 for k in keywords_high if k in text)
    med_hits = sum(1 for k in keywords_med if k in text)

    score += high_hits * 2.2 + med_hits * 1.0
    score = min(round(score, 1), 9.8)

    if any(k in text for k in ["fuel", "gasoline", "oil", "energy", "refin", "petroleum"]):
        category = "Energy & Petroleum Data Feed"
        target_component = "src/data_ingestion.py"
    elif any(k in text for k in ["noaa", "weather", "temp", "flood", "hurricane"]):
        category = "NOAA & Weather Intelligence"
        target_component = "src/noaa_weather.py"
    elif any(k in text for k in ["rag", "llm", "scrape", "search"]):
        category = "LLM & RAG Event Extraction"
        target_component = "src/event_analyzer.py"
    elif any(k in text for k in ["time series", "time-series", "futures", "commodity"]):
        category = "Quantitative Time-Series Modeling"
        target_component = "src/models.py"
    elif any(k in text for k in ["mlops", "feature store", "analytics", "dashboard", "monitoring"]):
        category = "MLOps & Monitoring Infrastructure"
        target_component = "src/prediction_logger.py"

    return {
        "impact_score": score,
        "category": category,
        "target_component": target_component,
        "is_worthwhile": score >= 7.0,
        "reasoning": f"Item matched {high_hits} high-priority energy/modeling keywords and {med_hits} infrastructure keywords."
    }


def evaluate_item_with_llm(item: dict) -> dict:
    """
    Evaluates new catalog item using Google Gemini Flash via google-genai SDK if GEMINI_API_KEY is present,
    falling back seamlessly to evaluate_item_heuristic().
    """
    gemini_key = os.environ.get("GEMINI_API_KEY")
    if not gemini_key:
        return evaluate_item_heuristic(item)

    try:
        from google import genai
        client = genai.Client(api_key=gemini_key)
        prompt = f"""You are an expert MLOps & Energy Quantitative Analyst evaluating a new software tool/API for the Midgley Unleaded Gasoline Price Prediction Engine.

Evaluate the following candidate tool:
- Title: {item['title']}
- URL: {item['url']}
- Description: {item['description']}
- Source Catalog: {item['catalog_key']}

Respond strictly in valid JSON format with:
{{
    "impact_score": <float 0.0 to 10.0>,
    "category": "<Category Name>",
    "target_component": "<src/file.py or dev-vm>",
    "is_worthwhile": <true/false>,
    "reasoning": "<Concise 1-2 sentence explanation of value for gas price modeling or devops>"
}}"""

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )
        text_resp = response.text.strip()
        if "```json" in text_resp:
            text_resp = text_resp.split("```json")[1].split("```")[0].strip()
        elif "```" in text_resp:
            text_resp = text_resp.split("```")[1].split("```")[0].strip()

        eval_data = json.loads(text_resp)
        eval_data["impact_score"] = float(eval_data.get("impact_score", 5.0))
        eval_data["is_worthwhile"] = eval_data.get("is_worthwhile", eval_data["impact_score"] >= 7.0)
        return eval_data
    except Exception as e:
        logger.debug(f"Gemini LLM evaluation notice ({e}). Falling back to heuristic scorer...")
        return evaluate_item_heuristic(item)


def infer_issue_domain_labels(eval_res: dict, item: dict) -> list:
    """
    Infers standard repository domain labels (data-ingestion, infrastructure, modeling,
    dashboard, integration, api, security) based on catalog evaluation metadata.
    Returns a list of label names starting with 'enhancement'.
    """
    labels = ["enhancement"]
    cat = (eval_res.get("category", "") or "").lower()
    comp = (eval_res.get("target_component", "") or "").lower()
    title = (item.get("title", "") or "").lower()
    desc = (item.get("description", "") or "").lower()
    text = f"{title} {desc} {cat} {comp}"

    if any(k in text for k in ["feed", "ingest", "weather", "noaa", "news", "data source", "eia", "usgs", "census", "sec", "edgar", "stream", "dataset"]):
        labels.append("data-ingestion")
    
    if any(k in text for k in ["cron", "database", "postgres", "sql", "runner", "workflow", "tunnel", "docker", "mlops", "metabase", "archivebox", "dagu", "trigger.dev", "serverless"]):
        labels.append("infrastructure")

    if any(k in text for k in ["model", "time series", "time-series", "forecasting", "predict", "feature", "estimator", "neuralprophet", "xgboost", "ridge", "geopandas", "prophet"]):
        labels.append("modeling")

    if any(k in text for k in ["ui", "dashboard", "frontend", "card", "embed", "design system", "visual"]):
        labels.append("dashboard")

    if any(k in text for k in ["integration", "home assistant", "lubelogger", "android auto", "coupler", "sync"]):
        labels.append("integration")

    if any(k in text for k in ["mcp", "endpoint", "webhook", "gateway", "rest api"]):
        labels.append("api")

    if any(k in text for k in ["security", "auth", "hmac", "access control"]):
        labels.append("security")

    if any(k in text for k in ["token", "prompt", "token-efficiency", "quota", "cost savings", "lightweight", "pre-filter", "wxs.us", "zero-token"]):
        labels.append("token-efficiency")

    if len(labels) == 1:
        if any(k in text for k in ["ingest", "data", "api"]):
            labels.append("data-ingestion")
        else:
            labels.append("infrastructure")

    return list(dict.fromkeys(labels))


def open_github_issue_for_item(item: dict, eval_res: dict, dry_run: bool = False) -> str:
    """
    Opens a GitHub Feature Request issue on KoshiirRa/midgley for worthwhile catalog additions,
    tagging it with standard domain labels.
    """
    labels = infer_issue_domain_labels(eval_res, item)
    labels_str = ",".join(labels)
    title = f"[Feature Request] Ingest {item['title']} ({eval_res['category']})"
    body = f"""## Summary
Automatically discovered new candidate tool **[{item['title']}]({item['url']})** from developer catalog \`{item['catalog_key']}\`.

**Description:** {item['description']}

## Modeling Evaluation & Value
- **Modeling Category:** \`{eval_res['category']}\`
- **Estimated Impact Score:** **\`{eval_res['impact_score']}/10.0\`**
- **Architecture Target:** \`{eval_res['target_component']}\`
- **Rationale:** {eval_res['reasoning']}
- **Assigned Labels:** \`{labels_str}\`

## Acceptance Criteria
- [ ] Implement {item['title']} client/connector in \`{eval_res['target_component']}\`.
- [ ] Add integration test suite.
- [ ] Verify non-null data retrieval."""

    if dry_run:
        safe_title = title.encode('ascii', errors='replace').decode('ascii')
        logger.info(f"[DRY-RUN] Would create issue: {safe_title} with labels [{labels_str}]")
        print(f"[DRY-RUN] Created Issue Title: {safe_title} | Labels: [{labels_str}]")
        return f"https://github.com/KoshiirRa/midgley/issues/dry-run-{item['title'].lower().replace(' ', '-')}"

    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    try:
        issue_file = "temp_catalog_issue.md"
        with open(issue_file, "w", encoding="utf-8") as f:
            f.write(body)

        env = dict(os.environ)
        if token:
            env["GH_TOKEN"] = token
            env["GITHUB_TOKEN"] = token

        cmd = ["gh", "issue", "create", "--repo", "KoshiirRa/midgley", "--title", title, "--body-file", issue_file, "--label", labels_str]
        res = subprocess.run(cmd, capture_output=True, text=True, check=True, env=env)
        url = res.stdout.strip()
        if os.path.exists(issue_file):
            os.remove(issue_file)
        logger.info(f"GitHub issue created via gh CLI: {url} with labels [{labels_str}]")
        return url
    except Exception as e:
        logger.warning(f"gh CLI issue creation notice ({e}). Trying REST API fallback...")

    if not token:
        logger.warning("No GH_TOKEN or GITHUB_TOKEN set for REST API issue creation.")
        return ""

    try:
        api_url = "https://api.github.com/repos/KoshiirRa/midgley/issues"
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "Authorization": f"Bearer {token}",
            "User-Agent": "Midgley-Catalog-Monitor",
            "Content-Type": "application/json"
        }
        payload = json.dumps({"title": title, "body": body, "labels": labels}).encode("utf-8")
        req = urllib.request.Request(api_url, data=payload, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=15) as response:
            res_data = json.loads(response.read().decode("utf-8"))
            html_url = res_data.get("html_url", "")
            logger.info(f"GitHub issue created via REST API: {html_url} with labels [{labels_str}]")
            return html_url
    except Exception as e:
        logger.error(f"Failed to create GitHub issue via REST API: {e}")
        return ""


def run_catalog_monitors(dry_run: bool = False, init_baseline: bool = False) -> dict:
    """
    Main runner for checking all 6 developer catalogs, detecting diffs against catalog_monitors_state.json,
    evaluating new items, and opening GitHub issues for worthwhile additions.
    Returns a summary dict.
    """
    state = load_catalog_state()
    known_urls = state.get("known_urls", {})

    discovered_new_items = []
    issues_created = []

    for cat_key, info in CATALOG_SOURCES.items():
        logger.info(f"Scanning catalog: {info['name']}...")
        content = fetch_catalog_content(info["url"])
        if not content:
            continue

        extracted = extract_items_from_content(content, cat_key)
        cat_known = set(known_urls.get(cat_key, []))

        # Check if this is the initial baseline run for this catalog
        is_initial_run = len(cat_known) == 0 or init_baseline

        new_for_cat = []
        for item in extracted:
            item_url_clean = item["url"].rstrip("/")
            if item_url_clean not in cat_known:
                if not is_initial_run:
                    new_for_cat.append(item)
                cat_known.add(item_url_clean)

        logger.info(f"Catalog '{cat_key}': total {len(cat_known)} URLs recorded ({len(new_for_cat)} new items for evaluation).")
        known_urls[cat_key] = list(cat_known)

        for new_item in new_for_cat:
            eval_res = evaluate_item_with_llm(new_item)
            discovered_new_items.append({
                "item": new_item,
                "evaluation": eval_res
            })

            if eval_res["is_worthwhile"]:
                logger.info(f"Item '{new_item['title']}' scored {eval_res['impact_score']}/10. Opening GitHub issue...")
                issue_url = open_github_issue_for_item(new_item, eval_res, dry_run=dry_run)
                if issue_url:
                    issues_created.append({
                        "title": new_item["title"],
                        "url": issue_url,
                        "score": eval_res["impact_score"],
                        "category": eval_res["category"]
                    })

    state["known_urls"] = known_urls
    if not dry_run or init_baseline:
        save_catalog_state(state)

    summary = {
        "catalogs_scanned": len(CATALOG_SOURCES),
        "new_items_discovered": len(discovered_new_items),
        "worthwhile_items": len(issues_created),
        "issues_created": issues_created,
        "details": discovered_new_items
    }
    return summary


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print("Running Catalog Monitor Engine (dry-run)...")
    res = run_catalog_monitors(dry_run=True)
    print(f"Catalog Monitor Summary: Discovered {res['new_items_discovered']} new items across {res['catalogs_scanned']} catalogs. {res['worthwhile_items']} issues created.")
