"""
CORE API Research Paper Monitor Module (src/core_monitor.py)
Fetches and filters recent open-access research papers from CORE API v3 for weekly review reports.
"""

import json
import logging
import os
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

CORE_API_URL = "https://api.core.ac.uk/v3/search/works"

DEFAULT_CORE_QUERY = (
    '("gasoline price forecasting" OR "RBOB futures" OR "oil market volatility" OR '
    '"refining rack margin" OR "time series LLM sentiment energy" OR "commodity price machine learning")'
)


def _parse_date(date_val: Any) -> Optional[datetime]:
    """Helper to parse datetime from various ISO/date representations returned by CORE API."""
    if not date_val:
        return None
    if isinstance(date_val, (int, float)):
        try:
            return datetime(int(date_val), 1, 1, tzinfo=timezone.utc)
        except Exception:
            return None
    if isinstance(date_val, str):
        date_str = date_val.strip()
        if not date_str:
            return None
        try:
            clean_str = date_str.replace("Z", "+00:00")
            dt = datetime.fromisoformat(clean_str)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except Exception:
            pass
        for fmt in ("%Y-%m-%d", "%Y-%m", "%Y"):
            try:
                dt = datetime.strptime(date_str[: len(fmt) if fmt != "%Y" else 4], fmt)
                return dt.replace(tzinfo=timezone.utc)
            except Exception:
                pass
    return None


def _parse_core_item(item: Dict[str, Any]) -> Dict[str, Any]:
    """Extracts and normalizes paper metadata from a single CORE API V3 work object."""
    item_id = str(item.get("id") or item.get("coreId") or "")
    title = item.get("title") or "Untitled Work"
    if isinstance(title, list):
        title = title[0] if title else "Untitled Work"
    title = str(title).strip().replace("\n", " ")

    summary = item.get("abstract") or item.get("description") or ""
    if isinstance(summary, list):
        summary = summary[0] if summary else ""
    summary = str(summary).strip().replace("\n", " ")
    if len(summary) > 250:
        summary = summary[:247] + "..."

    authors_raw = item.get("authors") or item.get("author") or []
    authors: List[str] = []
    if isinstance(authors_raw, list):
        for a in authors_raw:
            if isinstance(a, dict):
                name = a.get("name") or a.get("authorName") or a.get("fullName")
                if name:
                    authors.append(str(name).strip())
            elif isinstance(a, str) and a.strip():
                authors.append(a.strip())
    elif isinstance(authors_raw, str) and authors_raw.strip():
        authors.append(authors_raw.strip())

    if not authors:
        authors = ["Unknown Author"]

    pub_date_val = (
        item.get("publishedDate")
        or item.get("yearPublished")
        or item.get("createdDate")
        or item.get("datePublished")
        or item.get("published")
    )
    pub_dt = _parse_date(pub_date_val)

    doi = item.get("doi") or ""
    if isinstance(doi, list):
        doi = doi[0] if doi else ""
    doi = str(doi).strip()
    if doi.startswith("doi:"):
        doi = doi[4:].strip()

    download_url = item.get("downloadUrl") or item.get("pdfUrl") or ""
    if isinstance(download_url, list):
        download_url = download_url[0] if download_url else ""
    download_url = str(download_url).strip()

    if doi:
        url = doi if doi.startswith("http") else f"https://doi.org/{doi}"
    elif download_url:
        url = download_url
    elif item_id:
        url = f"https://core.ac.uk/works/{item_id}"
    else:
        url = "https://core.ac.uk"

    pdf_url = download_url or (f"https://core.ac.uk/download/pdf/{item_id}.pdf" if item_id else url)

    return {
        "id": item_id,
        "title": title,
        "authors": authors,
        "published": pub_dt.strftime("%Y-%m-%d") if pub_dt else "N/A",
        "published_dt": pub_dt,
        "summary": summary,
        "doi": doi,
        "url": url,
        "pdf_url": pdf_url,
    }


def fetch_recent_core_articles(
    days_back: int = 7,
    max_results: int = 10,
    api_key: Optional[str] = None,
    query: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Queries CORE API (v3) for open-access research papers on energy commodity & forecasting
    indexed in the last `days_back` days.

    Returns list of dicts:
    [{'id': str, 'title': str, 'authors': List[str], 'published': str, 'summary': str, 'doi': str, 'url': str, 'pdf_url': str}]
    """
    effective_api_key = api_key or os.environ.get("CORE_API_KEY")
    search_q = query or DEFAULT_CORE_QUERY

    params = {
        "q": search_q,
        "limit": str(max_results),
        "scroll": "false",
    }
    if effective_api_key:
        params["api_key"] = effective_api_key

    url = f"{CORE_API_URL}?{urllib.parse.urlencode(params)}"
    cutoff_dt = datetime.now(timezone.utc) - timedelta(days=days_back)
    articles = []

    headers = {
        "User-Agent": "Midgley-Forecast-Engine/1.4",
        "Accept": "application/json",
    }
    if effective_api_key:
        headers["Authorization"] = f"Bearer {effective_api_key}"

    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as response:
            raw_body = response.read().decode("utf-8")
            data = json.loads(raw_body)

        results = data.get("results") or data.get("data") or []
        if isinstance(data, list):
            results = data

        for item in results:
            if not isinstance(item, dict):
                continue

            parsed = _parse_core_item(item)
            pub_dt = parsed.pop("published_dt", None)

            if pub_dt and pub_dt < cutoff_dt:
                continue

            articles.append(parsed)

    except Exception as e:
        logger.warning(f"Failed to fetch CORE research articles: {e}")
        return []

    return articles[:max_results]


def format_core_markdown_section(
    days_back: int = 7,
    api_key: Optional[str] = None,
) -> str:
    """
    Formats the list of recent CORE articles into a GitHub Markdown section.
    """
    articles = fetch_recent_core_articles(days_back=days_back, api_key=api_key)
    if not articles:
        return (
            "## 🔬 Relevant CORE Open-Access Research Papers\n\n"
            "_No new open-access research papers matching energy commodity, refining rack margin, or LLM time-series queries "
            f"were indexed on CORE in the last {days_back} days._\n"
        )

    lines = [
        "## 🔬 Relevant CORE Open-Access Research Papers\n",
        f"The following open-access research papers were indexed on CORE within the last {days_back} days and may contain "
        "relevant methodological or empirical insights for the Midgley forecasting architecture:\n",
    ]

    for item in articles:
        author_str = ", ".join(item["authors"][:3])
        if len(item["authors"]) > 3:
            author_str += " et al."

        doi_part = f" | **DOI:** `{item['doi']}`" if item["doi"] else ""

        lines.append(f"### 📄 [{item['title']}]({item['url']})")
        lines.append(f"- **Authors:** {author_str}")
        lines.append(f"- **Published:** `{item['published']}`{doi_part} | **PDF:** [Download]({item['pdf_url']})")
        if item["summary"]:
            lines.append(f"- **Abstract Snippet:** {item['summary']}\n")
        else:
            lines.append("")

    return "\n".join(lines)
