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
    Returns list of dicts: [{'id': str, 'title': str, 'authors': List[str], 'published': str, 'summary': str, 'url': str, 'pdf_url': str}]
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
