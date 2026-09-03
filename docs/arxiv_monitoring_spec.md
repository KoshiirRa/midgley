# 📚 Specification: arXiv Research Paper Monitoring in Weekly Review (GitHub Issue #51)

**Issue Link:** [KoshiirRa/midgley#51](https://github.com/KoshiirRa/midgley/issues/51)  
**Status:** Open / Documented for Future Implementation  
**Module Target:** `src/arxiv_monitor.py` & `src/weekly_issue_reporter.py`  

---

## 1. Executive Summary & Context

The **Midgley Multi-Agent Forecasting Architecture** executes an automated weekly model review on GitHub Actions (`.github/workflows/weekly_model_review.yml` every Saturday at 08:00 AM US Central / 13:00 UTC). During this review, Agent 7 (`src/weekly_issue_reporter.py`) parses rolling 5-day out-of-time accuracy, updates performance benchmarks in `data/prediction_history.csv`, and publishes a GitHub Issue report detailing MAE, directional accuracy, and calibration recommendations.

**Goal of Issue #51:** Enhance Agent 7 to automatically scan **arXiv.org** for newly published or updated preprints in quantitative finance, energy econometrics, and LLM time-series forecasting published during the preceding 7-day review window. If relevant research papers are identified, they will be formatted and linked directly in the weekly GitHub Issue report to inform ongoing model feature engineering and parameter re-tuning.

---

## 2. Technical Architecture & Data Flow

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    SATURDAY WEEKLY REVIEW PIPELINE                      │
│            (.github/workflows/weekly_model_review.yml)                 │
└────────────────────────────────────┬────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                     src/weekly_issue_reporter.py                        │
└───────────────────┬─────────────────────────────────┬───────────────────┘
                    │                                 │
                    ▼                                 ▼
┌──────────────────────────────────────┐  ┌───────────────────────────────┐
│  data/prediction_history.csv         │  │   src/arxiv_monitor.py        │
│  (Calculates MAE & Hit Rate)        │  │   (Queries arXiv REST API)    │
└───────────────────┬──────────────────┘  └───────────────┬───────────────┘
                    │                                     │
                    └───────────────────┬─────────────────┘
                                        │ Combined Markdown Body
                                        ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                       GITHUB ISSUE REPORT                               │
│  • Rolling 30/60/90-Day Accuracy Metrics                                │
│  • Active 5-Day Out-of-Time Forecasts                                   │
│  • Model Diagnostics & Recommendations                                  │
│  • 📚 Relevant Recent arXiv Research Papers                             │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 3. arXiv REST API Specification

### Endpoint
- **URL:** `http://export.arxiv.org/api/query`
- **Method:** `GET`
- **Authentication:** None required (Public arXiv Export API)
- **Rate Limit Compliance:** Max 1 request per call; minimum 3-second delay between consecutive calls if looped. Timeout limit: 10 seconds.

### Target Categories & Keywords
- **Target Categories:**
  - `q-fin.PR` (Pricing of Securities / Commodities)
  - `econ.EM` (Econometrics)
  - `cs.LG` (Machine Learning)
  - `cs.AI` (Artificial Intelligence)
- **Keyword Query String:**
  ```text
  (cat:q-fin.PR OR cat:econ.EM OR cat:cs.LG OR cat:cs.AI) AND (ti:gasoline OR ti:commodity OR ti:"crude oil" OR ti:"futures price" OR abs:"energy forecasting" OR abs:"RBOB" OR abs:"unleaded gas")
  ```
- **Sorting & Limits:**
  - `sortBy`: `submittedDate`
  - `sortOrder`: `descending`
  - `max_results`: `10`

---

## 4. Proposed Implementation Blueprint

### File 1: `src/arxiv_monitor.py` (New Module)

```python
"""
arXiv Research Paper Monitor Module (src/arxiv_monitor.py)
Fetches and filters recent research preprints from arXiv API for weekly review reports.
"""

import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

ARXIV_API_URL = "http://export.arxiv.org/api/query"
ATOM_NS = {"atom": "http://www.w3.org/2005/Atom", "arxiv": "http://arxiv.org/schemas/atom"}

DEFAULT_QUERY = (
    '(cat:q-fin.PR OR cat:econ.EM OR cat:cs.LG OR cat:cs.AI) AND '
    '(ti:gasoline OR ti:commodity OR ti:"crude oil" OR ti:"futures" OR '
    'abs:"energy forecasting" OR abs:"price prediction" OR abs:"time series")'
)

def fetch_recent_arxiv_articles(days_back: int = 7, max_results: int = 10) -> List[Dict[str, Any]]:
    """
    Queries arXiv API for relevant energy/commodity forecasting papers published in the last `days_back` days.
    Returns list of dicts: [{'title': str, 'authors': List[str], 'published': str, 'summary': str, 'url': str, 'pdf_url': str}]
    """
    params = {
        "search_query": DEFAULT_QUERY,
        "sortBy": "submittedDate",
        "sortOrder": "descending",
        "max_results": max_results
    }
    url = f"{ARXIV_API_URL}?{urllib.parse.urlencode(params)}"
    cutoff_dt = datetime.now(timezone.utc) - timedelta(days=days_back)
    articles = []

    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Midgley-Forecast-Engine/1.4"})
        with urllib.request.urlopen(req, timeout=10) as response:
            xml_data = response.read()

        root = ET.fromstring(xml_data)
        for entry in root.findall("atom:entry", ATOM_NS):
            pub_elem = entry.find("atom:published", ATOM_NS)
            if pub_elem is None or not pub_elem.text:
                continue

            pub_str = pub_elem.text.strip()
            pub_dt = datetime.fromisoformat(pub_str.replace("Z", "+00:00"))

            if pub_dt < cutoff_dt:
                continue  # Filter out papers older than cutoff window

            title_elem = entry.find("atom:title", ATOM_NS)
            title = title_elem.text.strip().replace("\n", " ") if title_elem is not None and title_elem.text else "Untitled"

            summary_elem = entry.find("atom:summary", ATOM_NS)
            summary = summary_elem.text.strip().replace("\n", " ") if summary_elem is not None and summary_elem.text else ""
            if len(summary) > 250:
                summary = summary[:247] + "..."

            authors = []
            for author in entry.findall("atom:author", ATOM_NS):
                name_elem = author.find("atom:name", ATOM_NS)
                if name_elem is not None and name_elem.text:
                    authors.append(name_elem.text.strip())

            link_url = ""
            pdf_url = ""
            for link in entry.findall("atom:link", ATOM_NS):
                href = link.attrib.get("href", "")
                rel = link.attrib.get("rel", "")
                title_attr = link.attrib.get("title", "")
                if rel == "alternate":
                    link_url = href
                elif title_attr == "pdf":
                    pdf_url = href

            id_elem = entry.find("atom:id", ATOM_NS)
            arxiv_id = id_elem.text.split("/abs/")[-1] if id_elem is not None and id_elem.text else ""

            articles.append({
                "id": arxiv_id,
                "title": title,
                "authors": authors,
                "published": pub_dt.strftime("%Y-%m-%d"),
                "summary": summary,
                "url": link_url or f"https://arxiv.org/abs/{arxiv_id}",
                "pdf_url": pdf_url or f"https://arxiv.org/pdf/{arxiv_id}.pdf"
            })

    except Exception as e:
        logger.warning(f"Failed to fetch arXiv research articles: {e}")
        return []

    return articles


def format_arxiv_markdown_section(days_back: int = 7) -> str:
    """
    Formats the list of recent arXiv articles into a Markdown section for weekly GitHub Issues.
    """
    articles = fetch_recent_arxiv_articles(days_back=days_back)
    if not articles:
        return (
            "## 📚 Relevant Recent arXiv Research Papers\n\n"
            "_No new arXiv preprints matching energy market, commodity forecasting, or LLM time-series queries "
            f"were published in the last {days_back} days._\n"
        )

    lines = [
        "## 📚 Relevant Recent arXiv Research Papers\n",
        f"The following research papers were published to arXiv within the last {days_back} days and may contain "
        "relevant methodological or empirical insights for the Midgley forecasting architecture:\n"
    ]

    for item in articles:
        author_str = ", ".join(item["authors"][:3])
        if len(item["authors"]) > 3:
            author_str += " et al."

        lines.append(f"### 📄 [{item['title']}]({item['url']})")
        lines.append(f"- **Authors:** {author_str}")
        lines.append(f"- **Published:** `{item['published']}` | **PDF:** [Download]({item['pdf_url']})")
        lines.append(f"- **Abstract Snippet:** {item['summary']}\n")

    return "\n".join(lines)
```

---

### File 2: `src/weekly_issue_reporter.py` (Integration Point)

In `src/weekly_issue_reporter.py`, import `format_arxiv_markdown_section` and append its output to `generate_weekly_markdown_report()`:

```python
from src.arxiv_monitor import format_arxiv_markdown_section

def generate_weekly_markdown_report() -> str:
    # ... (existing report generation) ...
    
    # Append arXiv Monitoring Section
    arxiv_section = format_arxiv_markdown_section(days_back=7)
    
    report += f"\n---\n\n{arxiv_section}"
    return report
```

---

## 5. Sample Rendered Markdown Output

When 1 or more relevant papers are retrieved:

```markdown
## 📚 Relevant Recent arXiv Research Papers

The following research papers were published to arXiv within the last 7 days and may contain relevant methodological or empirical insights for the Midgley forecasting architecture:

### 📄 [Deep Learning for Energy Commodity Price Forecasting with LLM Sentiment Shocks](https://arxiv.org/abs/2608.12345)
- **Authors:** J. Smith, A. Johnson et al.
- **Published:** `2026-08-22` | **PDF:** [Download](https://arxiv.org/pdf/2608.12345.pdf)
- **Abstract Snippet:** We present a novel hybrid forecasting model that fuses text sentiment vectors from financial news streams with high-frequency futures returns for RBOB gasoline...
```

---

## 6. Testing Strategy

1. **Unit Test (`tests/test_arxiv_monitor.py`):**
   - Mock `urllib.request.urlopen` with sample Atom XML feed payloads.
   - Assert correct parsing of title, authors, published date, arXiv ID, and URLs.
   - Assert date cutoff filtering (exclude papers published >7 days ago).
   - Assert graceful return of empty list `[]` and formatted fallback message on network timeout or HTTP 500 error.
2. **Integration Test (`tests/test_weekly_issue_reporter.py`):**
   - Verify `generate_weekly_markdown_report()` includes the `## 📚 Relevant Recent arXiv Research Papers` section.
3. **Execution Test:**
   - Execute `python -m src.weekly_issue_reporter` locally or on `dev-vm`.

---

## 7. Definition of Done Checklist

- [ ] `src/arxiv_monitor.py` implemented with `fetch_recent_arxiv_articles()` and `format_arxiv_markdown_section()`.
- [ ] `src/weekly_issue_reporter.py` updated to include the arXiv section in weekly reports.
- [ ] Unit tests added in `tests/test_arxiv_monitor.py` and passing (`pytest`).
- [ ] `AGENTS.md` updated under Agent 7 to document arXiv paper monitoring capabilities.
- [ ] GitHub Actions weekly workflow validated on cloud runner.
