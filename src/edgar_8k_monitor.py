"""
EDGAR 8-K Refinery Operator Monitor (src/edgar_8k_monitor.py)
Polls SEC EDGAR for operationally significant 8-K filings from target refinery operators
and routes relevant disclosures into the intraday event scoring pipeline. (Issue #129)

In production, the Cloudflare Worker (workers/intraday_monitor_worker.ts) handles polling
and D1 deduplication at the edge, routing via INTRADAY_QUEUE -> POST /api/v1/events/queue-consumer.
This module serves as (1) the origin queue-consumer handler, (2) a local dev harness, and
(3) a server-side fallback when the edge worker is disabled.
"""

import os
import re
import time
import json
import logging
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError
from typing import Dict, List, Optional, Any
from datetime import datetime

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DEFAULT_TICKERS: List[str] = ["PBF", "DINO", "MPC", "VLO", "PSX"]

EDGAR_ATOM_URL = (
    "https://www.sec.gov/cgi-bin/browse-edgar"
    "?action=getcompany&CIK={ticker}&type=8-K"
    "&dateb=&owner=include&count=10&search_text=&output=atom"
)

EDGAR_CACHE_FILE = os.path.join("data", "edgar_8k_cache.json")

# Keyword gate — passes only operationally significant 8-Ks;
# eliminates ~85% noise (earnings, exec appointments, debt issuances).
OPERATIONAL_KEYWORDS: List[str] = [
    "outage", "force majeure", "fire", "explosion", "unplanned",
    "shutdown", "capacity reduction", "unit", "turnaround", "fcc",
    "crude distillation", "hydrocracker", "coker", "refinery",
    "pipeline", "leak", "spill", "environmental", "flaring",
    "evacuation", "accident", "incident", "disruption",
]

# EDGAR public rate limit: 10 req/s — sleep between requests
_REQUEST_DELAY_S: float = 0.12


# ---------------------------------------------------------------------------
# HTML text extractor
# ---------------------------------------------------------------------------

class _HTMLTextExtractor(HTMLParser):
    """Strips HTML tags and returns plain text."""
    def __init__(self) -> None:
        super().__init__()
        self._chunks: List[str] = []

    def handle_data(self, data: str) -> None:
        self._chunks.append(data)

    def get_text(self) -> str:
        return " ".join(self._chunks).strip()


def _strip_html(html: str) -> str:
    parser = _HTMLTextExtractor()
    parser.feed(html)
    return parser.get_text()


# ---------------------------------------------------------------------------
# EDGAR 8-K Monitor
# ---------------------------------------------------------------------------

class EDGAR8KMonitor:
    """
    Zero-cost EDGAR 8-K Refinery Operator Monitor.

    Polls SEC EDGAR ATOM RSS feeds for new 8-K filings from target refinery
    operators, keyword-filters for operational relevance, and routes matching
    disclosures into the intraday event pipeline via process_incoming_headline().
    """

    def __init__(
        self,
        tickers: Optional[List[str]] = None,
        cache_file: str = EDGAR_CACHE_FILE,
    ) -> None:
        env_tickers = os.environ.get("EDGAR_8K_TICKERS", "")
        self.tickers: List[str] = (
            tickers
            or [t.strip().upper() for t in env_tickers.split(",") if t.strip()]
            or DEFAULT_TICKERS
        )
        self.cache_file = cache_file
        self.user_agent: str = os.environ.get(
            "SEC_USER_AGENT", "Midgley contact@example.com"
        )
        self._seen: Dict[str, str] = self._load_cache()
        self.is_free_alternative = True
        self.cost_per_query = 0.0

    # ------------------------------------------------------------------
    # Persistent accession-number cache
    # ------------------------------------------------------------------

    def _load_cache(self) -> Dict[str, str]:
        """Load seen accession numbers from disk."""
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, OSError) as e:
                logger.warning(f"[EDGAR8K] Could not load cache: {e}")
        return {}

    def _save_cache(self) -> None:
        """Persist seen accession numbers to disk."""
        os.makedirs(os.path.dirname(self.cache_file) or ".", exist_ok=True)
        try:
            with open(self.cache_file, "w", encoding="utf-8") as f:
                json.dump(self._seen, f, indent=2)
        except OSError as e:
            logger.warning(f"[EDGAR8K] Could not save cache: {e}")

    def _is_seen(self, cache_key: str) -> bool:
        return cache_key in self._seen

    def _mark_seen(self, cache_key: str, filed_at: str) -> None:
        self._seen[cache_key] = filed_at
        self._save_cache()

    # ------------------------------------------------------------------
    # EDGAR ATOM feed fetching
    # ------------------------------------------------------------------

    def _fetch_url(self, url: str) -> Optional[str]:
        """Fetch a URL with the SEC User-Agent header."""
        req = Request(url, headers={"User-Agent": self.user_agent})
        try:
            with urlopen(req, timeout=15) as resp:
                return resp.read().decode("utf-8", errors="replace")
        except HTTPError as e:
            logger.warning(f"[EDGAR8K] HTTP {e.code} fetching {url}")
        except URLError as e:
            logger.warning(f"[EDGAR8K] URL error fetching {url}: {e.reason}")
        except Exception as e:
            logger.warning(f"[EDGAR8K] Unexpected error fetching {url}: {e}")
        return None

    def _fetch_atom_entries(self, ticker: str) -> List[Dict[str, str]]:
        """
        Fetch and parse the EDGAR ATOM RSS feed for a given ticker.
        Returns a list of dicts with keys: accession_id, title, link, filed_at.
        """
        url = EDGAR_ATOM_URL.format(ticker=ticker)
        xml_text = self._fetch_url(url)
        if not xml_text:
            return []

        try:
            root = ET.fromstring(xml_text)
        except ET.ParseError as e:
            logger.warning(f"[EDGAR8K] XML parse error for {ticker}: {e}")
            return []

        ns = {"atom": "http://www.w3.org/2005/Atom"}
        entries = []
        for entry in root.findall("atom:entry", ns):
            title_el = entry.find("atom:title", ns)
            link_el = entry.find("atom:link", ns)
            id_el = entry.find("atom:id", ns)
            updated_el = entry.find("atom:updated", ns)

            title = title_el.text.strip() if title_el is not None and title_el.text else ""
            link = link_el.get("href", "") if link_el is not None else ""
            accession_id = id_el.text.strip() if id_el is not None and id_el.text else ""
            filed_at = updated_el.text.strip() if updated_el is not None and updated_el.text else datetime.utcnow().isoformat()

            if accession_id and title:
                entries.append({
                    "accession_id": accession_id,
                    "title": title,
                    "link": link,
                    "filed_at": filed_at,
                })
        return entries

    # ------------------------------------------------------------------
    # Relevance keyword gate
    # ------------------------------------------------------------------

    @staticmethod
    def is_relevant(text: str) -> bool:
        """
        Returns True if the filing text passes the operational relevance gate.
        Eliminates noise filings (earnings, exec appointments, debt issuances).
        """
        text_lower = text.lower()
        return any(kw in text_lower for kw in OPERATIONAL_KEYWORDS)

    # ------------------------------------------------------------------
    # 8-K HTML body extraction
    # ------------------------------------------------------------------

    def _extract_filing_text(self, filing_index_url: str) -> str:
        """
        Fetch the 8-K filing index page, find the primary document link,
        fetch its HTML, and return stripped plain text.
        """
        index_html = self._fetch_url(filing_index_url)
        if not index_html:
            return ""
        time.sleep(_REQUEST_DELAY_S)

        # Find the primary document link (htm/html) in the filing index
        doc_match = re.search(
            r'href="(/Archives/edgar/data/[^"]+\.htm[l]?)"',
            index_html,
            re.IGNORECASE,
        )
        if not doc_match:
            # Fall back to plain index text
            return _strip_html(index_html)[:4000]

        doc_url = "https://www.sec.gov" + doc_match.group(1)
        doc_html = self._fetch_url(doc_url)
        if not doc_html:
            return ""
        time.sleep(_REQUEST_DELAY_S)

        return _strip_html(doc_html)[:8000]  # Trim to a safe LLM context window

    # ------------------------------------------------------------------
    # Main polling loop
    # ------------------------------------------------------------------

    def poll_ticker(self, ticker: str) -> List[Dict[str, Any]]:
        """
        Poll EDGAR for new 8-K filings from a single ticker.
        Returns a list of scored event dicts for relevant new filings.
        """
        results: List[Dict[str, Any]] = []
        entries = self._fetch_atom_entries(ticker)
        time.sleep(_REQUEST_DELAY_S)

        for entry in entries:
            cache_key = f"{ticker}:{entry['accession_id']}"
            if self._is_seen(cache_key):
                continue

            # Quick relevance check on the entry title before fetching HTML
            title_relevant = self.is_relevant(entry["title"])

            body_text = ""
            if not title_relevant and entry["link"]:
                # Fetch the filing body for a deeper keyword check
                body_text = self._extract_filing_text(entry["link"])

            combined_text = f"{entry['title']} {body_text}"

            if not self.is_relevant(combined_text):
                logger.info(f"[EDGAR8K] Skipping noise filing: {ticker} — {entry['title']}")
                self._mark_seen(cache_key, entry["filed_at"])
                continue

            # Fetch body text if we only checked the title so far
            if not body_text and entry["link"]:
                body_text = self._extract_filing_text(entry["link"])
                combined_text = f"{entry['title']} {body_text}"

            headline = f"{ticker} 8-K: {entry['title']}"
            results.append({
                "ticker": ticker,
                "accession_id": entry["accession_id"],
                "filed_at": entry["filed_at"],
                "headline": headline,
                "body_text": combined_text,
                "url": entry["link"],
                "cache_key": cache_key,
            })

        return results

    def poll_all_tickers(self, route_to_pipeline: bool = True) -> List[Dict[str, Any]]:
        """
        Poll EDGAR for all configured tickers and optionally route relevant
        filings into the intraday event pipeline.

        Args:
            route_to_pipeline: If True, calls process_incoming_headline() for
                each relevant filing. Set to False for dry-run / testing.

        Returns:
            List of processed filing dicts.
        """
        all_results: List[Dict[str, Any]] = []

        for ticker in self.tickers:
            logger.info(f"[EDGAR8K] Polling EDGAR 8-K feed for: {ticker}")
            try:
                filings = self.poll_ticker(ticker)
                for filing in filings:
                    if route_to_pipeline:
                        self._route_to_pipeline(filing)
                    self._mark_seen(filing["cache_key"], filing["filed_at"])
                    all_results.append(filing)
            except Exception as e:
                logger.error(f"[EDGAR8K] Error polling {ticker}: {e}")

        logger.info(f"[EDGAR8K] Poll complete. {len(all_results)} relevant new 8-K(s) routed.")
        return all_results

    # ------------------------------------------------------------------
    # Pipeline routing
    # ------------------------------------------------------------------

    def _route_to_pipeline(self, filing: Dict[str, Any]) -> None:
        """
        Route a relevant 8-K filing into the intraday event scoring pipeline
        via IntradayEventMonitor.process_incoming_headline().
        """
        try:
            from src.intraday_event_monitor import IntradayEventMonitor
            monitor = IntradayEventMonitor()
            result = monitor.process_incoming_headline(
                headline=filing["headline"],
                source="EDGAR_8K",
                url=filing["url"],
            )
            logger.info(
                f"[EDGAR8K] Routed: {filing['headline']} — "
                f"supply_disruption={result.get('supply_disruption', 'N/A')}, "
                f"locales={result.get('target_locales', [])}"
            )
        except Exception as e:
            logger.error(f"[EDGAR8K] Pipeline routing error for {filing['headline']}: {e}")
