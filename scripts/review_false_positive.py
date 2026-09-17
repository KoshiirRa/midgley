#!/usr/bin/env python3
"""
Automated False-Positive Anomaly Reviewer (scripts/review_false_positive.py)

Analyzes breaking news headlines flagged as false positives from Discord notifications,
evaluates keyword triggers against src/intraday_event_monitor.py, identifies root causes,
recommends regex exclusion updates for Issue #258, and posts automated diagnostic feedback.
"""

import os
import sys
import re
import json
import argparse
import logging
import urllib.request
import urllib.error
from typing import Dict, Any, List, Optional

# Ensure UTF-8 stdout encoding across all platforms
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# Ensure repository root is in sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.intraday_event_monitor import (
    TRIGGER_KEYWORDS,
    EXCLUDE_KEYWORDS,
    NON_ENERGY_TARIFF_EXCLUDE,
    normalize_headline
)
from src.event_analyzer import extract_event_features_rule_based

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("FalsePositiveReviewer")

ENERGY_CORE_TOKENS = [
    "crude", "oil", "gasoline", "rbob", "refinery", "refining", "pipeline",
    "fuel", "petroleum", "barrel", "bpd", "opec", "tanker", "chokepoint",
    "diesel", "distillate", "cushing", "wti", "brent", "spr", "crack spread"
]


BROAD_POLICY_KEYWORDS = [
    "tariff", "tariffs", "retaliat", "trade war", "sanction", "sanctions",
    "executive order", "boycott", "embargo", "export ban", "import ban"
]

AGRICULTURAL_OIL_TOKENS = [
    "cooking oil", "palm oil", "olive oil", "soybean oil", "canola",
    "vegetable oil", "sunflower oil", "food supply"
]


def analyze_headline_triggers(headline: str, category: str = "", notes: str = "") -> Dict[str, Any]:
    """
    Simulates the fast-path anomaly filter against the headline and determines root cause.
    """
    norm_headline = normalize_headline(headline).lower()

    # 1. Check matching trigger keywords & broad policy triggers
    matched_triggers = [kw for kw in TRIGGER_KEYWORDS if kw in norm_headline]
    matched_policy = [kw for kw in BROAD_POLICY_KEYWORDS if kw in norm_headline]
    matched_ag = [kw for kw in AGRICULTURAL_OIL_TOKENS if kw in norm_headline]

    # 2. Check matching existing exclusions
    matched_excludes = [kw for kw in EXCLUDE_KEYWORDS if kw in norm_headline]
    matched_tariff_excludes = [kw for kw in NON_ENERGY_TARIFF_EXCLUDE if kw in norm_headline]

    # 3. Check for presence of petroleum energy core tokens
    matched_energy_tokens = [tok for tok in ENERGY_CORE_TOKENS if tok in norm_headline]

    # 4. Extract rule-based scoring features
    scores = extract_event_features_rule_based(headline)

    # 5. Determine root-cause diagnosis
    has_energy_context = len(matched_energy_tokens) > 0
    is_macro_policy = len(matched_policy) > 0 or any(kw in matched_triggers for kw in ["tariff", "retaliat", "trade war", "sanction", "executive order"])

    if matched_ag or "cooking oil" in norm_headline:
        diagnosis = (
            f"Tripped oil/commodity keyword on agricultural or edible oils ({matched_ag}) "
            f"rather than petroleum hydrocarbons."
        )
    elif not has_energy_context and is_macro_policy:
        triggers_list = matched_triggers if matched_triggers else matched_policy
        diagnosis = (
            f"Tripped macro policy keyword(s) {triggers_list}, but lacked petroleum commodity "
            f"co-occurrence tokens (e.g., crude, oil, gasoline, refinery). This is a classic non-energy policy false positive."
        )
    elif not matched_triggers:
        diagnosis = "Headline did not match standard TRIGGER_KEYWORDS directly; likely triggered via LLM scoring fallback or custom webhook push."
    else:
        diagnosis = f"Tripped trigger keyword(s) {matched_triggers} with scored price pressure {scores.get('overall_price_pressure', 0.0):+.2f}."

    # 6. Formulate recommended code additions
    suggested_exclusions = []
    words = re.findall(r'\b[a-zA-Z]{4,}\b', norm_headline)
    for word in words:
        if word not in ENERGY_CORE_TOKENS and word not in ["announces", "imposes", "reported", "breaking", "market", "global"]:
            if any(trig in norm_headline for trig in ["tariff", "ban", "sanction", "strike", "outage"]):
                primary_trig = matched_triggers[0] if matched_triggers else (matched_policy[0] if matched_policy else "tariff")
                candidate = f"{word} {primary_trig}"
                if candidate not in NON_ENERGY_TARIFF_EXCLUDE and len(candidate) < 30:
                    suggested_exclusions.append(candidate)

    all_matched = list(dict.fromkeys(matched_triggers + matched_policy))

    return {
        "headline": headline,
        "category": category,
        "notes": notes,
        "matched_triggers": all_matched,
        "matched_excludes": matched_excludes + matched_tariff_excludes,
        "matched_energy_tokens": matched_energy_tokens,
        "has_energy_context": has_energy_context,
        "rule_based_scores": scores,
        "diagnosis": diagnosis,
        "suggested_exclusions": list(dict.fromkeys(suggested_exclusions))[:5]
    }


def format_diagnostic_comment(analysis: Dict[str, Any]) -> str:
    """
    Constructs a rich GitHub Issue Markdown comment with root cause analysis and test case.
    """
    headline = analysis["headline"]
    triggers = ", ".join([f"`{t}`" for t in analysis["matched_triggers"]]) or "_None_"
    energy_tokens = ", ".join([f"`{t}`" for t in analysis["matched_energy_tokens"]]) or "_None (Zero energy co-occurrence)_"
    scores = analysis["rule_based_scores"]
    suggested_ex = ", ".join([f'"{ex}"' for ex in analysis["suggested_exclusions"]]) or '"<targeted_exclusion_phrase>"'

    escaped_headline = headline.replace('"', '\\"')

    comment = f"""### 🤖 Automated Agent Diagnostic Review (Issue #258 Sub-Task)

The automated false-positive reviewer analyzed the flagged headline against the anomaly filtering pipeline in `src/intraday_event_monitor.py`:

---

#### 🔍 Root Cause Analysis
- **Triggered Keywords:** {triggers}
- **Petroleum Context Found:** {energy_tokens}
- **Rule-Based Pressure (ΔP):** `{scores.get('overall_price_pressure', 0.0):+.2f}/gal`
- **Rule-Based Supply Disruption (S):** `{scores.get('supply_disruption', 0.0):.2f}`

> **Diagnosis:** {analysis['diagnosis']}

---

#### 🛠️ Recommended Engine Refinement
To permanently suppress similar false positives, update `src/intraday_event_monitor.py`:

```python
# In NON_ENERGY_TARIFF_EXCLUDE or EXCLUDE_KEYWORDS:
NON_ENERGY_TARIFF_EXCLUDE.extend([
    {suggested_ex}
])
```

---

#### 🧪 Regression Unit Test Case
Add this test to `tests/test_intraday_event_monitor.py` to prevent regressions:

```python
def test_false_positive_suppression_{abs(hash(headline)) % 100000}():
    headline = "{escaped_headline}"
    # Should be filtered out before triggering LLM inference
    is_anomaly, _ = evaluate_fast_path_anomaly(headline)
    assert not is_anomaly, f"False positive tripped on: {{headline}}"
```

---
*Generated by Midgley Agent Anomaly Diagnostic Engine • Linked to parent tracking thread #258*
"""
    return comment


def fetch_issue_data(issue_number: int, repo: str = "KoshiirRa/midgley") -> Optional[Dict[str, Any]]:
    """Fetches GitHub issue body and details via REST API."""
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    url = f"https://api.github.com/repos/{repo}/issues/{issue_number}"
    headers = {
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "Midgley-False-Positive-Reviewer"
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"

    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        logger.error(f"Failed to fetch issue #{issue_number}: {e}")
        return None


def post_issue_comment(issue_number: int, comment: str, repo: str = "KoshiirRa/midgley") -> bool:
    """Posts a diagnostic comment to the GitHub issue."""
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if not token:
        logger.warning("No GH_TOKEN or GITHUB_TOKEN available; skipping GitHub comment dispatch.")
        return False

    url = f"https://api.github.com/repos/{repo}/issues/{issue_number}/comments"
    headers = {
        "Accept": "application/vnd.github.v3+json",
        "Authorization": f"Bearer {token}",
        "User-Agent": "Midgley-False-Positive-Reviewer",
        "Content-Type": "application/json"
    }
    payload = json.dumps({"body": comment}).encode("utf-8")

    try:
        req = urllib.request.Request(url, data=payload, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=15) as resp:
            ok = resp.status in (200, 201)
            if ok:
                logger.info(f"Successfully posted diagnostic review comment to Issue #{issue_number}")
            return ok
    except Exception as e:
        logger.error(f"Failed to post comment to Issue #{issue_number}: {e}")
        return False


def parse_headline_from_issue_body(body: str) -> str:
    """Extracts the catalyst headline from an issue body."""
    if not body:
        return ""
    match = re.search(r'### 🚨 Trigger Catalyst\s*>\s*\*?"?(.*?)"?\*?\n', body, re.DOTALL)
    if match:
        return match.group(1).strip()
    match2 = re.search(r'Headline:\s*\*?"?(.*?)"?\*?\n', body)
    if match2:
        return match2.group(1).strip()
    match3 = re.search(r'>\s*\*?"?(.*?)"?\*?', body)
    if match3:
        return match3.group(1).strip()
    return ""


def main():
    parser = argparse.ArgumentParser(description="Automated False-Positive Issue Diagnostic Reviewer")
    parser.add_argument("--issue-number", type=int, help="GitHub Issue number to review")
    parser.add_argument("--headline", type=str, help="Headline text for direct review")
    parser.add_argument("--category", type=str, default="", help="Flagged category")
    parser.add_argument("--notes", type=str, default="", help="User notes")
    parser.add_argument("--repo", type=str, default="KoshiirRa/midgley", help="GitHub repo owner/name")
    parser.add_argument("--dry-run", action="store_true", help="Print report to stdout without posting comment")

    args = parser.parse_args()

    headline = args.headline or ""
    category = args.category
    notes = args.notes

    if args.issue_number:
        logger.info(f"Fetching issue #{args.issue_number} from {args.repo}...")
        issue_data = fetch_issue_data(args.issue_number, repo=args.repo)
        if issue_data:
            body = issue_data.get("body", "")
            extracted_headline = parse_headline_from_issue_body(body)
            if extracted_headline:
                headline = extracted_headline
            elif not headline:
                headline = issue_data.get("title", "").replace("[False Positive]", "").strip()

    if not headline:
        logger.error("No headline found or specified for review.")
        sys.exit(1)

    logger.info(f"Analyzing headline: '{headline}'")
    analysis = analyze_headline_triggers(headline, category=category, notes=notes)
    comment = format_diagnostic_comment(analysis)

    if args.dry_run or not args.issue_number:
        print("\n" + "=" * 80)
        print(comment)
        print("=" * 80 + "\n")
    else:
        post_issue_comment(args.issue_number, comment, repo=args.repo)


if __name__ == "__main__":
    main()
