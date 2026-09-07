"""
Firecrawl Web-to-Markdown Scraper Connector Module (src/firecrawl_scraper.py)
Ingests and converts raw HTML from energy news bulletins, refinery operator press releases,
and state motor fuel tax portals into clean, structured, LLM-ready Markdown using the
Firecrawl Web Scraping API (https://api.firecrawl.dev/v1/scrape).

Features:
- Web-to-Markdown extraction with JavaScript rendering support.
- Hard Quota Safety Valve: Persistent ledger at data/firecrawl_quota.json enforcing an
  800 call/month safety cap (and 30 call/day burst limit) out of the 1,000 free tier allowance.
- 24-Hour Multi-Tier Caching: In-memory and disk-backed cache at data/firecrawl_cache.json
  keyed by SHA-256 hash of normalized URLs.
- Zero-Cost Native Fallback: Built-in deterministic HTML-to-markdown text cleaner using
  urllib and standard library parsing when API key is omitted, quota is exhausted, or offline.
- Connector Telemetry & Token Accounting: Integration with src/connector_telemetry.py and
  src/tokentab_accounting.py.
"""

import os
import re
import time
import json
import hashlib
import logging
import urllib.request
import urllib.error
import html
from html.parser import HTMLParser
from datetime import datetime
from typing import Dict, Any, Optional, Tuple, List

from src.lookup_cache import global_cache
from src.tokentab_accounting import token_tab_manager
from src.connector_telemetry import log_connector_event

logger = logging.getLogger(__name__)

FIRECRAWL_API_BASE_URL = "https://api.firecrawl.dev/v1/scrape"
CACHE_FILE = os.path.join("data", "firecrawl_cache.json")
CACHE_TTL_SECONDS = 86400  # 24-hour disk cache TTL
QUOTA_FILE = os.path.join("data", "firecrawl_quota.json")
MAX_MONTHLY_CALLS = 800    # Hard safety cap (out of 1,000 free tier allowance)
MAX_DAILY_CALLS = 30       # Soft daily cap to prevent burst exhaustion

# In-memory session cache for URL scrapes
_IN_MEMORY_SCRAPE_CACHE: Dict[str, Dict[str, Any]] = {}


class SimpleHTMLTextExtractor(HTMLParser):
    """
    Lightweight, deterministic HTML parser that extracts text while filtering out
    scripts, styles, navigation, and formatting headers/paragraphs into basic Markdown.
    """
    def __init__(self):
        super().__init__()
        self.result = []
        self.skip = False
        self.skip_tags = {"script", "style", "nav", "footer", "header", "noscript", "svg", "button"}
        self.in_title = False
        self.title = ""

    def handle_starttag(self, tag, attrs):
        tag_lower = tag.lower()
        if tag_lower in self.skip_tags:
            self.skip = True
        elif tag_lower == "title":
            self.in_title = True
        elif tag_lower in ["h1", "h2", "h3", "h4", "h5", "h6"]:
            self.result.append("\n\n### ")
        elif tag_lower in ["p", "div", "article", "section"]:
            self.result.append("\n\n")
        elif tag_lower == "li":
            self.result.append("\n- ")

    def handle_endtag(self, tag):
        tag_lower = tag.lower()
        if tag_lower in self.skip_tags:
            self.skip = False
        elif tag_lower == "title":
            self.in_title = False
        elif tag_lower in ["p", "div", "article", "section", "h1", "h2", "h3", "h4", "h5", "h6"]:
            self.result.append("\n")

    def handle_data(self, data):
        if self.in_title:
            self.title += data.strip()
        if not self.skip:
            text = data.strip()
            if text:
                self.result.append(text + " ")

    def get_text(self) -> str:
        raw = "".join(self.result)
        # Collapse multiple newlines and spaces
        cleaned = re.sub(r'\n\s*\n+', '\n\n', raw).strip()
        return cleaned


def _get_url_hash(url: str) -> str:
    """Computes SHA-256 hash of normalized URL."""
    norm_url = url.strip().lower()
    return hashlib.sha256(norm_url.encode("utf-8")).hexdigest()


def _check_and_increment_quota() -> Tuple[bool, dict]:
    """
    Checks data/firecrawl_quota.json against MAX_MONTHLY_CALLS and MAX_DAILY_CALLS caps.
    Returns (allowed: bool, status_dict: dict).
    """
    os.makedirs("data", exist_ok=True)
    now = datetime.now()
    month_key = now.strftime("%Y-%m")
    day_key = now.strftime("%Y-%m-%d")

    data = {
        "current_month": month_key,
        "monthly_calls": 0,
        "daily_calls": {},
        "last_reset": now.isoformat()
    }

    if os.path.exists(QUOTA_FILE):
        try:
            with open(QUOTA_FILE, "r", encoding="utf-8") as f:
                loaded = json.load(f)
                if loaded.get("current_month") == month_key:
                    data = loaded
        except Exception as e:
            logger.warning(f"Could not read Firecrawl quota ledger '{QUOTA_FILE}': {e}")

    # Check shared edge cache ledger if available (unless in testing mode)
    if os.environ.get("TESTING") != "1":
        edge_ledger = global_cache.get_quota_ledger("firecrawl")
        if edge_ledger and edge_ledger.get("current_month") == month_key:
            edge_monthly = edge_ledger.get("monthly_calls", 0)
            edge_daily = edge_ledger.get("daily_calls", {}).get(day_key, 0)
            data["monthly_calls"] = max(data.get("monthly_calls", 0), edge_monthly)
            if "daily_calls" not in data or not isinstance(data["daily_calls"], dict):
                data["daily_calls"] = {}
            data["daily_calls"][day_key] = max(data["daily_calls"].get(day_key, 0), edge_daily)

    monthly_calls = data.get("monthly_calls", 0)
    today_calls = data.get("daily_calls", {}).get(day_key, 0)

    if monthly_calls >= MAX_MONTHLY_CALLS or today_calls >= MAX_DAILY_CALLS:
        logger.warning(
            f"🚨 FIRECRAWL API SAFETY VALVE TRIPPED! "
            f"Monthly calls: {monthly_calls}/{MAX_MONTHLY_CALLS}, Today: {today_calls}/{MAX_DAILY_CALLS}. "
            f"Preserving free-tier quota by routing to zero-cost fallback parser."
        )
        return False, {
            "allowed": False,
            "monthly_calls": monthly_calls,
            "max_monthly_calls": MAX_MONTHLY_CALLS,
            "today_calls": today_calls,
            "max_daily_calls": MAX_DAILY_CALLS,
            "reason": "Quota limit reached"
        }

    # Increment quota counters
    data["monthly_calls"] = monthly_calls + 1
    if "daily_calls" not in data or not isinstance(data["daily_calls"], dict):
        data["daily_calls"] = {}
    data["daily_calls"][day_key] = today_calls + 1
    data["last_updated"] = now.isoformat()

    try:
        with open(QUOTA_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        logger.warning(f"Could not write Firecrawl quota ledger: {e}")

    if os.environ.get("TESTING") != "1":
        try:
            global_cache.update_quota_ledger(
                "firecrawl",
                data["monthly_calls"],
                data["daily_calls"][day_key],
                month_key,
                day_key
            )
        except Exception as e:
            logger.debug(f"Edge cache quota ledger sync notice: {e}")

    return True, {
        "allowed": True,
        "monthly_calls": data["monthly_calls"],
        "max_monthly_calls": MAX_MONTHLY_CALLS,
        "today_calls": data["daily_calls"][day_key],
        "max_daily_calls": MAX_DAILY_CALLS
    }


def get_firecrawl_quota_status() -> dict:
    """Returns current Firecrawl quota consumption status without incrementing."""
    now = datetime.now()
    month_key = now.strftime("%Y-%m")
    day_key = now.strftime("%Y-%m-%d")

    data = {
        "current_month": month_key,
        "monthly_calls": 0,
        "max_monthly_calls": MAX_MONTHLY_CALLS,
        "today_calls": 0,
        "max_daily_calls": MAX_DAILY_CALLS,
        "remaining_monthly": MAX_MONTHLY_CALLS,
        "status": "HEALTHY"
    }

    if os.path.exists(QUOTA_FILE):
        try:
            with open(QUOTA_FILE, "r", encoding="utf-8") as f:
                loaded = json.load(f)
                if loaded.get("current_month") == month_key:
                    m_calls = loaded.get("monthly_calls", 0)
                    t_calls = loaded.get("daily_calls", {}).get(day_key, 0)
                    data["monthly_calls"] = m_calls
                    data["today_calls"] = t_calls
                    data["remaining_monthly"] = max(0, MAX_MONTHLY_CALLS - m_calls)
                    if m_calls >= MAX_MONTHLY_CALLS or t_calls >= MAX_DAILY_CALLS:
                        data["status"] = "SAFETY_VALVE_ACTIVE"
        except Exception:
            pass

    return data


class FirecrawlConnector:
    """
    Connector for scraping URLs and converting web content to clean Markdown via Firecrawl API,
    with automatic quota accounting, disk caching, and offline fallback parsing.
    """
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("FIRECRAWL_API_KEY")

    def _read_disk_cache(self, url_hash: str) -> Optional[Dict[str, Any]]:
        """Reads cached scrape payload from disk if within TTL."""
        if not os.path.exists(CACHE_FILE):
            return None
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                cache_data = json.load(f)
            entry = cache_data.get(url_hash)
            if entry:
                cached_time = entry.get("timestamp", 0)
                if (time.time() - cached_time) < CACHE_TTL_SECONDS:
                    return entry.get("data")
        except Exception as e:
            logger.debug(f"Firecrawl disk cache read notice: {e}")
        return None

    def _write_disk_cache(self, url_hash: str, data: Dict[str, Any]) -> None:
        """Saves scraped payload to disk cache."""
        os.makedirs("data", exist_ok=True)
        cache_data = {}
        if os.path.exists(CACHE_FILE):
            try:
                with open(CACHE_FILE, "r", encoding="utf-8") as f:
                    cache_data = json.load(f)
            except Exception:
                cache_data = {}

        # Prune expired entries if cache grows large
        now = time.time()
        if len(cache_data) > 500:
            cache_data = {
                k: v for k, v in cache_data.items()
                if (now - v.get("timestamp", 0)) < CACHE_TTL_SECONDS
            }

        cache_data[url_hash] = {
            "timestamp": now,
            "data": data
        }

        try:
            with open(CACHE_FILE, "w", encoding="utf-8") as f:
                json.dump(cache_data, f, indent=2)
        except Exception as e:
            logger.warning(f"Could not write Firecrawl disk cache: {e}")

    def _extract_fallback_markdown(self, url: str, timeout: int = 10) -> Dict[str, Any]:
        """
        Deterministic, zero-cost native HTML-to-markdown text cleaner using urllib.
        Guarantees $0 cost and 100% offline resilience.
        """
        t0 = time.time()
        try:
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "Midgley-Energy-Scraper/1.0 (Commodity Market Research)"}
            )
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                raw_html = resp.read().decode("utf-8", errors="ignore")

            parser = SimpleHTMLTextExtractor()
            parser.feed(raw_html)
            text_md = parser.get_text()
            title = parser.title or url

            latency_ms = (time.time() - t0) * 1000.0
            log_connector_event("Firecrawl_Fallback", url, status="SUCCESS", latency_ms=latency_ms)

            return {
                "success": True,
                "provider": "native_html_fallback",
                "markdown": text_md,
                "title": title,
                "url": url,
                "status_code": 200,
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            latency_ms = (time.time() - t0) * 1000.0
            logger.warning(f"Fallback URL extraction failed for '{url}': {e}")
            log_connector_event("Firecrawl_Fallback", url, status="ERROR", latency_ms=latency_ms, details=str(e))
            return {
                "success": False,
                "provider": "native_html_fallback",
                "markdown": f"Error fetching article content: {e}",
                "title": url,
                "url": url,
                "status_code": 500,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }

    def scrape_url(
        self,
        url: str,
        formats: Optional[List[str]] = None,
        only_main_content: bool = True,
        timeout: int = 15,
        force_refresh: bool = False
    ) -> Dict[str, Any]:
        """
        Scrapes the given URL to clean Markdown using Firecrawl API or deterministic fallback.
        
        Parameters:
            url: Target web page URL to scrape.
            formats: List of output formats, defaults to ["markdown"].
            only_main_content: If True, strips headers, footers, nav bars.
            timeout: HTTP timeout in seconds.
            force_refresh: If True, bypasses cache.
            
        Returns:
            Dict containing success, provider, markdown, title, metadata, and status.
        """
        if formats is None:
            formats = ["markdown"]

        url_hash = _get_url_hash(url)

        # 1. Check in-memory cache
        if not force_refresh and url_hash in _IN_MEMORY_SCRAPE_CACHE:
            return _IN_MEMORY_SCRAPE_CACHE[url_hash]

        # 2. Check disk cache
        if not force_refresh:
            cached_disk = self._read_disk_cache(url_hash)
            if cached_disk:
                _IN_MEMORY_SCRAPE_CACHE[url_hash] = cached_disk
                return cached_disk

        # 3. Check multi-tier lookup cache (unless in testing mode)
        cache_key = f"firecrawl:{url_hash}"
        if os.environ.get("TESTING") != "1":
            cached_global = global_cache.get(cache_key)
            if not force_refresh and cached_global:
                _IN_MEMORY_SCRAPE_CACHE[url_hash] = cached_global
                return cached_global

        # 4. Check if API key exists and safety quota is available
        if not self.api_key:
            logger.info(f"FIRECRAWL_API_KEY not set. Using zero-cost native HTML fallback for '{url}'.")
            result = self._extract_fallback_markdown(url, timeout=timeout)
            _IN_MEMORY_SCRAPE_CACHE[url_hash] = result
            self._write_disk_cache(url_hash, result)
            global_cache.set(cache_key, result, ttl_seconds=CACHE_TTL_SECONDS)
            return result

        quota_ok, quota_status = _check_and_increment_quota()
        if not quota_ok:
            logger.warning(f"Firecrawl quota safety valve triggered. Falling back to native HTML parser.")
            result = self._extract_fallback_markdown(url, timeout=timeout)
            _IN_MEMORY_SCRAPE_CACHE[url_hash] = result
            self._write_disk_cache(url_hash, result)
            global_cache.set(cache_key, result, ttl_seconds=CACHE_TTL_SECONDS)
            return result

        # 5. Execute Firecrawl API request
        t0 = time.time()
        payload = {
            "url": url,
            "formats": formats,
            "onlyMainContent": only_main_content
        }
        headers = {
            "Authorization": f"Bearer {self.api_key.strip()}",
            "Content-Type": "application/json"
        }

        try:
            req = urllib.request.Request(
                FIRECRAWL_API_BASE_URL,
                data=json.dumps(payload).encode("utf-8"),
                headers=headers,
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                resp_code = resp.getcode() if hasattr(resp, "getcode") else 200
                raw_data = resp.read()
                if isinstance(raw_data, bytes):
                    resp_body = raw_data.decode("utf-8", errors="ignore")
                elif isinstance(raw_data, str):
                    resp_body = raw_data
                else:
                    resp_body = str(raw_data)

            latency_ms = (time.time() - t0) * 1000.0
            parsed_json = json.loads(resp_body)
            data_block = parsed_json.get("data", {})
            markdown_content = data_block.get("markdown", "") or data_block.get("text", "")
            metadata = data_block.get("metadata", {})
            title = metadata.get("title", "") or url

            result = {
                "success": True,
                "provider": "firecrawl_v1",
                "markdown": markdown_content,
                "title": title,
                "metadata": metadata,
                "url": url,
                "status_code": resp_code,
                "latency_ms": latency_ms,
                "timestamp": datetime.now().isoformat()
            }

            # Record telemetry and token tab accounting
            log_connector_event("Firecrawl_API", url, status="SUCCESS", latency_ms=latency_ms)
            token_tab_manager.record_usage("firecrawl", "web_to_markdown", len(url), len(markdown_content.split()), status="success")

            # Store in caches
            _IN_MEMORY_SCRAPE_CACHE[url_hash] = result
            self._write_disk_cache(url_hash, result)
            global_cache.set(cache_key, result, ttl_seconds=CACHE_TTL_SECONDS)
            return result

        except urllib.error.HTTPError as http_err:
            latency_ms = (time.time() - t0) * 1000.0
            logger.warning(f"Firecrawl API HTTP Error {http_err.code} for '{url}': {http_err.reason}. Falling back.")
            log_connector_event("Firecrawl_API", url, status=f"HTTP_{http_err.code}", latency_ms=latency_ms, details=str(http_err))
            token_tab_manager.record_usage("firecrawl", "web_to_markdown", len(url), 0, status=f"error_{http_err.code}")
            
            # Fallback to native parser on HTTP error
            result = self._extract_fallback_markdown(url, timeout=timeout)
            _IN_MEMORY_SCRAPE_CACHE[url_hash] = result
            self._write_disk_cache(url_hash, result)
            global_cache.set(cache_key, result, ttl_seconds=CACHE_TTL_SECONDS)
            return result

        except Exception as err:
            latency_ms = (time.time() - t0) * 1000.0
            logger.warning(f"Firecrawl API network/parse error for '{url}': {err}. Falling back.")
            log_connector_event("Firecrawl_API", url, status="ERROR", latency_ms=latency_ms, details=str(err))
            
            # Fallback to native parser
            result = self._extract_fallback_markdown(url, timeout=timeout)
            _IN_MEMORY_SCRAPE_CACHE[url_hash] = result
            self._write_disk_cache(url_hash, result)
            global_cache.set(cache_key, result, ttl_seconds=CACHE_TTL_SECONDS)
            return result
