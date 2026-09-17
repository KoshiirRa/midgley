"""
Semantic Scholar Academic Graph Connector Module (src/semantic_scholar_feed.py)
Issue #264: Integrate Semantic Scholar API for Paper Summarization & Citation Graph Traversal

Queries Semantic Scholar REST API (https://api.semanticscholar.org) to retrieve automated paper TL;DRs,
influential citation counts, and seminal petroleum economics literature.
"""

import os
import json
import logging
import urllib.parse
from typing import Dict, Any, List, Optional
from datetime import datetime
import requests

logger = logging.getLogger(__name__)

CACHE_PATH = os.path.join("data", "semantic_scholar_cache.json")
BASE_SEARCH_URL = "https://api.semanticscholar.org/graph/v1/paper/search"
BASE_PAPER_URL = "https://api.semanticscholar.org/graph/v1/paper"


def _load_semantic_scholar_cache() -> dict:
    """Loads Semantic Scholar query cache from disk."""
    if os.path.exists(CACHE_PATH):
        try:
            with open(CACHE_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.debug(f"Error reading semantic scholar cache: {e}")
    return {}


def _save_semantic_scholar_cache(cache: dict) -> None:
    """Saves Semantic Scholar query cache to disk."""
    if os.environ.get("TESTING") == "1" and not os.environ.get("TEST_TELEMETRY_PERSIST"):
        return
    os.makedirs(os.path.dirname(CACHE_PATH), exist_ok=True)
    try:
        with open(CACHE_PATH, "w", encoding="utf-8") as f:
            json.dump(cache, f, indent=2)
    except Exception as e:
        logger.debug(f"Error saving semantic scholar cache: {e}")


class SemanticScholarConnector:
    """
    Semantic Scholar Academic Graph API Client for Paper TL;DRs & Citation Metrics.
    """

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("SEMANTIC_SCHOLAR_API_KEY", "")
        self.headers = {
            "User-Agent": "Midgley-Energy-Forecasting-Bot/1.0 (+https://github.com/KoshiirRa/midgley)",
            "Accept": "application/json"
        }
        if self.api_key:
            self.headers["x-api-key"] = self.api_key

    def search_papers(
        self,
        query: str,
        limit: int = 5,
        fields: str = "title,abstract,tldr,citationCount,influentialCitationCount,year,openAccessPdf"
    ) -> List[Dict[str, Any]]:
        """
        Searches Semantic Scholar for academic publications matching query.
        """
        clean_query = query.strip()
        cache_key = f"search__{clean_query}__limit={limit}"
        cache = _load_semantic_scholar_cache()

        if cache_key in cache:
            logger.info(f"Semantic Scholar cache hit for search: '{clean_query}'")
            return cache[cache_key].get("results", [])

        if os.environ.get("TESTING") == "1" or os.environ.get("SUPPRESS_OUTBOUND_APIS") == "1":
            # Synthetic result for testing/offline mode
            mock_results = [
                {
                    "paperId": "649def34f8be52c8b66281af98ae772c99cf9315",
                    "title": "Do Gasoline Prices Respond Asymmetrically to Crude Oil Price Shocks?",
                    "year": 2020,
                    "citationCount": 85,
                    "influentialCitationCount": 14,
                    "tldr": "Gasoline prices exhibit asymmetric pass-through with rapid adjustment to crude increases and slower decay for reductions.",
                    "abstract": "This study analyzes high-frequency daily retail and wholesale gasoline prices across major US metropolitan markets.",
                    "openAccessPdf": "https://arxiv.org/pdf/2001.00000.pdf"
                }
            ]
            return mock_results[:limit]

        params = {
            "query": clean_query,
            "limit": min(limit, 20),
            "fields": fields
        }

        try:
            resp = requests.get(BASE_SEARCH_URL, headers=self.headers, params=params, timeout=10)
            if resp.status_code != 200:
                logger.warning(f"Semantic Scholar API search returned HTTP {resp.status_code}")
                return []

            data = resp.json()
            raw_papers = data.get("data", [])
            formatted = []

            for p in raw_papers:
                tldr_obj = p.get("tldr") or {}
                tldr_text = tldr_obj.get("text", "") if isinstance(tldr_obj, dict) else str(tldr_obj)
                oa_pdf = p.get("openAccessPdf") or {}
                pdf_url = oa_pdf.get("url", "") if isinstance(oa_pdf, dict) else str(oa_pdf)

                formatted.append({
                    "paperId": p.get("paperId", ""),
                    "title": p.get("title", ""),
                    "year": p.get("year"),
                    "citationCount": p.get("citationCount", 0),
                    "influentialCitationCount": p.get("influentialCitationCount", 0),
                    "tldr": tldr_text,
                    "abstract": (p.get("abstract") or "")[:400],
                    "openAccessPdf": pdf_url
                })

            cache[cache_key] = {
                "timestamp": datetime.now().isoformat(),
                "query": clean_query,
                "results": formatted
            }
            _save_semantic_scholar_cache(cache)
            return formatted

        except Exception as e:
            logger.warning(f"Semantic Scholar search failed for '{clean_query}': {e}")
            return []

    def get_paper_tldr(self, paper_id_or_doi: str) -> Optional[str]:
        """
        Retrieves automated single-sentence TL;DR for a given paper ID or DOI.
        """
        clean_id = paper_id_or_doi.strip()
        cache_key = f"tldr__{clean_id}"
        cache = _load_semantic_scholar_cache()

        if cache_key in cache:
            return cache[cache_key].get("tldr")

        if os.environ.get("TESTING") == "1" or os.environ.get("SUPPRESS_OUTBOUND_APIS") == "1":
            return "Empirical analysis confirms asymmetric pass-through of crude and wholesale shocks to retail fuel prices."

        url = f"{BASE_PAPER_URL}/{clean_id}?fields=title,tldr,citationCount"
        try:
            resp = requests.get(url, headers=self.headers, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                tldr_obj = data.get("tldr") or {}
                tldr_text = tldr_obj.get("text") if isinstance(tldr_obj, dict) else str(tldr_obj)
                if tldr_text:
                    cache[cache_key] = {
                        "timestamp": datetime.now().isoformat(),
                        "id": clean_id,
                        "tldr": tldr_text
                    }
                    _save_semantic_scholar_cache(cache)
                    return tldr_text
        except Exception as e:
            logger.warning(f"Error fetching TL;DR for paper '{clean_id}': {e}")

        return None
